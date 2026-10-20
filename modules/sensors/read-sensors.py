#!/usr/bin/env python3
"""Run on Jetson Humble after starting sensor drivers. Ctrl+C exits.

Only subscribes to sensor topics; never starts drivers or opens chassis serial.
Prints one summary per second. 'age' measures time since local reception.
"""
import math
import time
from functools import partial

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, Imu, LaserScan, PointCloud2
from std_msgs.msg import Float64MultiArray, Int32MultiArray


class SensorReader(Node):
    def __init__(self):
        super().__init__('farm_sensor_reader')
        self.bridge = CvBridge()
        self.latest = {}
        self.counts = {}
        topics = {
            '/scan': LaserScan,
            '/camera/color/image_raw': Image,
            '/camera/depth/image_raw': Image,
            '/camera/ir/image_raw': Image,
            '/camera/depth/points': PointCloud2,
            '/camera/color/camera_info': CameraInfo,
            '/camera/depth/camera_info': CameraInfo,
            '/camera/ir/camera_info': CameraInfo,
            '/microdia/image_raw': Image,
            '/microdia/camera_info': CameraInfo,
            '/imu/data_raw': Imu,
            '/imu/raw9': Int32MultiArray,
            '/imu/rpy': Float64MultiArray,
        }
        self.topics = topics
        self.subs = [self.create_subscription(
            kind, topic, partial(self.receive, topic), qos_profile_sensor_data
        ) for topic, kind in topics.items()]
        self.create_timer(1.0, self.report)

    def receive(self, topic, msg):
        self.latest[topic] = (time.monotonic(), msg)
        self.counts[topic] = self.counts.get(topic, 0) + 1

    def report(self):
        for topic in self.topics:
            if topic not in self.latest:
                print(f'{topic}: waiting for data', flush=True)
                continue
            received, msg = self.latest[topic]
            if isinstance(msg, LaserScan):
                valid = [x for x in msg.ranges
                         if math.isfinite(x) and msg.range_min <= x <= msg.range_max
                         and x > 0]
                detail = f'points={len(msg.ranges)} valid={len(valid)}'
                if valid:
                    detail += f' nearest={min(valid):.3f}m'
            elif isinstance(msg, Image):
                try:
                    # RGB/IR retain their encoding; depth 16UC1 retains uint16.
                    image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                    detail = f'{image.shape} {msg.encoding}'
                    if topic == '/camera/depth/image_raw' and msg.encoding == '16UC1':
                        # This installed Astra driver uses millimetres for 16UC1.
                        value = int(image[msg.height // 2, msg.width // 2])
                        detail += f' center={value / 1000:.3f}m' if value else ' center=invalid'
                except Exception as exc:
                    detail = f'image conversion failed: {exc}'
            elif isinstance(msg, PointCloud2):
                detail = f'points={msg.width * msg.height} frame={msg.header.frame_id}'
            elif isinstance(msg, Imu):
                a, g = msg.linear_acceleration, msg.angular_velocity
                detail = (f'accel=({a.x:.3f},{a.y:.3f},{a.z:.3f})m/s^2 '
                          f'gyro=({g.x:.3f},{g.y:.3f},{g.z:.3f})rad/s')
            elif isinstance(msg, (Int32MultiArray, Float64MultiArray)):
                label = msg.layout.dim[0].label if msg.layout.dim else ''
                detail = f'{label} {list(msg.data)}'
            else:
                detail = f'fx={msg.k[0]:.2f} fy={msg.k[4]:.2f}'
            stamp = (f'{msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d}'
                     if hasattr(msg, 'header') else 'unavailable')
            print(f'{topic}: n={self.counts[topic]} age={time.monotonic()-received:.2f}s '
                  f'stamp={stamp} {detail}', flush=True)


def main():
    rclpy.init()
    node = SensorReader()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
