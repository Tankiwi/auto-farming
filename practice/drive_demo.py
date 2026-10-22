#!/usr/bin/env python3
"""drive_demo.py —— 最小行车演示：让小车低速前进几秒然后停止。

用法（在车上）:
    export ROS_DOMAIN_ID=77
    python3 drive_demo.py                # 默认: 0.1 m/s 前进 3 秒
    python3 drive_demo.py --speed 0.05 --seconds 5
    python3 drive_demo.py --turn 0.3     # 原地左转 3 秒
    python3 drive_demo.py --side 0.1     # 麦轮横移（这台车的特色）

只发布 /cmd_vel，不订阅传感器、不碰串口。
前提：车型配置已修好、原厂驱动已在跑，否则指令无人接收，车不会动（安全）。
"""

import argparse

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

SPEED_LIMIT = 0.2          # 安全上限 m/s；教学期不许超过


class DriveDemo(Node):

    def __init__(self, speed: float, seconds: float):
        super().__init__('drive_demo')
        # 发布者：消息类型 Twist，话题 /cmd_vel，队列深度 10
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.speed = speed
        self.seconds = seconds
        self.elapsed = 0.0
        # 关键①：用定时器"持续"发布。/cmd_vel 是速度指令，
        # 不是"走3秒"的命令——你不一直发，车就不知道该保持多快。
        self.timer = self.create_timer(0.1, self.tick)   # 10 Hz
        self.get_logger().info(
            f'开始: {speed} m/s 前进 {seconds} 秒 (Ctrl+C 随时急停)')

    def tick(self):
        self.elapsed += 0.1
        cmd = Twist()
        if self.elapsed <= self.seconds:
            cmd.linear.x = self.speed       # x: 前正后负 (m/s)
            # cmd.linear.y = ...           # y: 左正右负 —— 麦轮横移用 --side 演示
            # cmd.angular.z = ...          # z: 左旋正右旋负 (rad/s)
        # 超过时间后 cmd 保持全零，继续发布零速 = 主动"按住"停车
        self.pub.publish(cmd)
        if self.elapsed > self.seconds and self.elapsed > self.seconds + 1.0:
            self.get_logger().info('已完成并保持停车，退出。')
            raise SystemExit

    def stop_and_die(self):
        # 关键②：任何退出路径都先补发一次全零，再销毁节点
        self.pub.publish(Twist())
        self.destroy_node()


def main():
    parser = argparse.ArgumentParser(description='低速行车演示')
    parser.add_argument('--speed', type=float, default=0.1,
                        help=f'前进速度 m/s，上限 {SPEED_LIMIT}')
    parser.add_argument('--seconds', type=float, default=3.0,
                        help='行驶秒数')
    parser.add_argument('--turn', type=float, default=0.0,
                        help='改为原地旋转，rad/s（如 0.3 左转）')
    parser.add_argument('--side', type=float, default=0.0,
                        help='改为横移，m/s（麦轮专属，如 0.1 左移）')
    args = parser.parse_args()

    speed = max(min(args.speed, SPEED_LIMIT), -SPEED_LIMIT)  # 裁剪到安全范围

    rclpy.init()
    node = DriveDemo(speed, args.seconds)
    try:
        # 关键③：spin 是"值班循环"，定时器到点就调 tick()
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.stop_and_die()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
