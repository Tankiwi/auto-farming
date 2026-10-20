#!/usr/bin/env python3
"""Passive Rosmaster 3.3.1 IMU receiver; never sends serial commands.

Run on Jetson with ROS sourced, or via start-sensors.py imu.
Requires the board's auto-report to already be enabled. No Rosmaster object is
constructed. Conversion follows the archived vendor source, not a calibration.
"""
from pathlib import Path
import struct
import subprocess
import time


PORT = '/dev/myserial'


class FrameDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.bad_checksums = 0

    def feed(self, data):
        self.buffer.extend(data)
        frames = []
        while len(self.buffer) >= 4:
            index = self.buffer.find(b'\xff\xfb')
            if index < 0:
                self.buffer[:] = self.buffer[-1:]
                break
            del self.buffer[:index]
            if len(self.buffer) < 4:
                break
            length = self.buffer[2]
            if not 3 <= length <= 64:
                del self.buffer[0]
                continue
            if len(self.buffer) < length + 2:
                break
            packet = bytes(self.buffer[:length + 2])
            if sum(packet[2:-1]) & 255 != packet[-1]:
                self.bad_checksums += 1
                del self.buffer[0]
                continue
            del self.buffer[:length + 2]
            frames.append((packet[3], packet[4:-1]))
        return frames


def decode_raw(function, payload):
    """Wire order: gyro xyz, accel xyz, magnetometer xyz (signed int16).

    Return raw nine values, vendor-converted gyro (rad/s) and accel (m/s^2).
    Magnetometer units are not established, so do not publish MagneticField/Tesla.
    """
    if function not in (0x0B, 0x0E) or len(payload) != 18:
        return None
    raw = struct.unpack('<9h', payload)
    if function == 0x0B:
        gyro = (raw[0] / 3754.9, -raw[1] / 3754.9, -raw[2] / 3754.9)
        accel = tuple(value / 1671.84 for value in raw[3:6])
    else:
        gyro = tuple(value / 1000.0 for value in raw[:3])
        accel = tuple(value / 1000.0 for value in raw[3:6])
    return raw, gyro, accel


def decode_attitude(function, payload):
    if function != 0x0C or len(payload) != 6:
        return None
    return tuple(value / 10000.0 for value in struct.unpack('<3h', payload))


def main():
    import fcntl
    import serial
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from std_msgs.msg import Float64MultiArray, Int32MultiArray, MultiArrayDimension

    if not Path(PORT).is_char_device():
        raise RuntimeError(f'底板串口不存在：{PORT}')
    with open('/tmp/farm-arm-check.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owners = subprocess.run(['fuser', PORT], capture_output=True, text=True, timeout=5)
        if owners.returncode not in (0, 1) or owners.stdout.strip():
            raise RuntimeError('底板串口已占用或无法核对占用情况；请检查已有底盘/机械臂程序。')
        # Opening the serial interface is necessary; no write() calls are made.
        with serial.Serial(PORT, 115200, timeout=0.02, exclusive=True) as port:
            rclpy.init()
            node = Node('farm_imu_reader')
            imu_pub = node.create_publisher(Imu, '/imu/data_raw', qos_profile_sensor_data)
            raw_pub = node.create_publisher(Int32MultiArray, '/imu/raw9', qos_profile_sensor_data)
            rpy_pub = node.create_publisher(Float64MultiArray, '/imu/rpy', qos_profile_sensor_data)
            decoder = FrameDecoder()
            started = last_raw = time.monotonic()
            last_log = 0.0
            received_raw = False
            count = 0
            exit_code = 0
            node.get_logger().info('只接收底板上报；不发送串口指令。等待 IMU 数据……')
            try:
                while rclpy.ok():
                    for function, payload in decoder.feed(port.read(min(port.in_waiting or 1, 4096))):
                        decoded = decode_raw(function, payload)
                        if decoded is not None:
                            raw, gyro, accel = decoded
                            msg = Imu()
                            msg.header.stamp = node.get_clock().now().to_msg()
                            msg.header.frame_id = 'imu_link'
                            msg.orientation_covariance[0] = -1.0
                            msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = gyro
                            msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = accel
                            imu_pub.publish(msg)
                            raw_msg = Int32MultiArray()
                            dim = MultiArrayDimension()
                            dim.label = f'gyro_xyz,accel_xyz,mag_xyz; report=0x{function:02x}; raw_int16'
                            dim.size = dim.stride = 9
                            raw_msg.layout.dim = [dim]
                            raw_msg.data = list(raw)
                            raw_pub.publish(raw_msg)
                            last_raw = time.monotonic()
                            received_raw = True
                            count += 1
                        attitude = decode_attitude(function, payload)
                        if attitude is not None:
                            msg = Float64MultiArray()
                            dim = MultiArrayDimension()
                            dim.label = 'roll,pitch,yaw; radians; vendor attitude, frame not calibrated'
                            dim.size = dim.stride = 3
                            msg.layout.dim = [dim]
                            msg.data = list(attitude)
                            rpy_pub.publish(msg)
                    now = time.monotonic()
                    if now - last_log >= 1.0:
                        if received_raw:
                            node.get_logger().info(
                                f'IMU count={count} age={now-last_raw:.2f}s bad_checksum={decoder.bad_checksums}')
                        last_log = now
                    if (not received_raw and now-started > 10) or (received_raw and now-last_raw > 3):
                        node.get_logger().error(
                            '没有持续收到有效九轴上报，退出。检查串口/底板自动上报；本程序不会自动修改上报配置。')
                        exit_code = 1
                        break
                    rclpy.spin_once(node, timeout_sec=0)
            except KeyboardInterrupt:
                pass
            finally:
                node.destroy_node()
                if rclpy.ok():
                    rclpy.shutdown()
            return exit_code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise SystemExit(f'IMU 读取失败：{exc}')
