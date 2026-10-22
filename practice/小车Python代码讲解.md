# 小车 Python 代码讲解（rclpy 逐段入门）

更新：2026-10-22｜适用：ROSMASTER X3 Plus（Jetson，ROS 2 Humble，ROS_DOMAIN_ID=77）
代码来源：本仓库真实脚本（`drive_demo.py`、`modules/sensors/read-sensors.py` 等），不是泛泛教程。
用法：配合作业目录 `practice/drive_demo.py` 对照阅读；每段代码先看注释，再看下方逐条解释。

---

## 0. 你的代码在哪一层

```
你的 .py 文件（本页讲的东西）
    ↕ 话题（/cmd_vel、/scan ...）
原厂驱动节点 / 传感器驱动
    ↕
Rosmaster_Lib（串口库）→ 底板 → 电机/舵机
```

一句话：**你写 Python，只跟"话题"打交道**；串口层是别人写好的。

---

## 1. 每个节点都有的骨架（5 件套）

```python
import rclpy                              # ① ROS 2 的 Python 库，所有节点都从它开始
from rclpy.node import Node               # ② Node 是"节点"这个类的模具

class MyNode(Node):                       # ③ 你的节点 = 继承 Node，加自己的功能
    def __init__(self):
        super().__init__('my_node')       # ④ 先执行父类初始化，括号里是节点名（全局唯一）

def main():
    rclpy.init()                          # ⑤ 整个程序只调一次：接通 ROS 通信底座
    node = MyNode()                       #     造出你的节点对象
    rclpy.spin(node)                      # ⑥ "值班循环"：卡在这里，一直处理消息和定时器
    node.destroy_node()                   # ⑦ 退出前打扫干净
    rclpy.shutdown()                      #     断开通信底座

main()
```

逐条解释：

| 行 | 意思 | MCU 类比 |
|---|---|---|
| `import rclpy` | 引入 ROS 2 的 Python 接口 | `#include` 库 |
| `class MyNode(Node)` | 一个类就是一个节点；想造几个节点就写几个类 | 一个 .c 文件一个模块 |
| `super().__init__('my_node')` | 节点名是它在 ROS 网络里的身份证，`ros2 node list` 看到的就是它 | 设备地址 |
| `rclpy.init()` | 初始化整个通信系统，一个程序只调一次 | 上电初始化外设 |
| `rclpy.spin(node)` | 死循环：有消息来就调你的回调，定时器到点就调你的函数 | `while(1){...}` 主循环 |
| `destroy_node()/shutdown()` | 释放资源 | 关外设、复位 |

---

## 2. 发布话题：让车动

来自 `practice/drive_demo.py`：

```python
from geometry_msgs.msg import Twist               # 速度消息的类型

self.pub = self.create_publisher(Twist, '/cmd_vel', 10)   # 造发布者

cmd = Twist()            # 造一条空消息
cmd.linear.x = 0.1       # 前进 0.1 米/秒（负数 = 后退）
cmd.angular.z = 0.0      # 旋转 0 弧度/秒（正 = 左转）
self.pub.publish(cmd)    # 发出去
```

逐条解释：

- **`Twist`**：ROS 规定的"速度"消息，固定三个有用的字段：

| 字段 | 含义 | 单位 | 正方向 |
|---|---|---|---|
| `linear.x` | 前后速度 | m/s | 前 + / 后 − |
| `linear.y` | 左右平移 | m/s | 左 + / 右 −（**只有麦轮车有，这台是**） |
| `angular.z` | 旋转速度 | rad/s | 左旋 + / 右旋 − |

- **`'/cmd_vel'`**：话题名。全车约定俗成"控制车速度的话题叫这个"，原厂驱动就在另一头听。
- **`10`**：队列深度——你发得比对方收得快时，最多缓存 10 条，再旧的丢掉。
- **最关键的规则**：`/cmd_vel` 的意思是"**从现在起按这个速度走**"，不是"走 3 秒"。
  所以必须配合定时器**反复发**（见下一节），停下来时发全零。

---

## 3. 定时器：让代码按节拍跑

```python
self.timer = self.create_timer(0.1, self.tick)   # 每 0.1 秒自动调一次 tick
self.elapsed = 0.0                                # 自己记一个计数器

def tick(self):
    self.elapsed += 0.1                           # 每次被调 +0.1 秒
    ...
```

逐条解释：

- `create_timer(秒, 函数名)`：到点就调你的函数，**你不用写 while 循环**——`spin()` 内部替你等。
- 这就是"为什么 spin 是值班循环"：定时器和消息都靠它才动起来。没有 `spin()`，定时器永远不响。
- 用途：行车代码 10 Hz 发 `/cmd_vel`；状态上报 1 Hz 打印；都是它。

---

## 4. 订阅话题：收传感器数据

来自 `modules/sensors/read-sensors.py`（精简）：

```python
from rclpy.qos import qos_profile_sensor_data     # 传感器专用 QoS
from sensor_msgs.msg import LaserScan

class SensorReader(Node):
    def __init__(self):
        super().__init__('farm_sensor_reader')
        self.create_subscription(
            LaserScan,            # 消息类型
            '/scan',              # 话题名
            self.on_scan,         # 来数据时自动调用的函数（回调）
            qos_profile_sensor_data)   # 收货方式（见第 5 节）

    def on_scan(self, msg):       # 每来一帧雷达数据，这个函数被自动调用一次
        nearest = min(msg.ranges) # msg 就是 LaserScan，字段直接取
        print(f'最近障碍 {nearest:.2f} 米')
```

逐条解释：

| 概念 | 意思 | MCU 类比 |
|---|---|---|
| 回调函数 | 你**不主动调用**它；数据到达那一刻系统替你调 | 中断服务函数 ISR |
| `msg` | 那一帧数据的容器，字段由消息类型决定 | 收到的数据帧结构体 |
| 订阅 | 向 ROS 系统登记"这个话题的每帧都给我" | 开中断、设中断向量 |

**发布和订阅的节奏差异**（最容易混的点）：
- 订阅 = 事件驱动：数据来了才动，没来就闲着；
- 发布 = 主动循环：**你必须自己定时发**（配 `create_timer`）。

---

## 5. QoS：收不到数据的头号原因

```python
self.create_subscription(LaserScan, '/scan', self.on_scan,
                         qos_profile_sensor_data)   # ✅ 传感器专用
```

- QoS = 收货方式。传感器驱动默认用"尽力而为"（丢几帧没关系，要快）；
- 你的订阅若用默认的"可靠"模式（要求每帧必达），**双方模式不匹配，一条都收不到，还不报错**；
- 记住：**订传感器话题，最后那个参数永远写 `qos_profile_sensor_data`**。这不是可选项，是保命项。

---

## 6. 常用消息字段速查（怎么从 msg 里取数）

来自 `read-sensors.py` 的真实取值代码：

```python
# LaserScan —— 雷达一圈
msg.ranges          # 列表：2000 个距离值（米）；inf/nan/0 = 无效点
msg.range_min       # 有效最小距离（低于此是盲区）
msg.range_max       # 有效最大距离
msg.header.stamp    # 时间戳（这帧数据是几点几秒拍的）

# Imu —— 九轴
msg.linear_acceleration.x    # x 轴加速度 m/s²（.y .z 同理）
msg.angular_velocity.z       # z 轴角速度 rad/s（判断"在不在转弯"就看它）

# Image —— 图像（要配 cv_bridge 转 numpy 才好处理）
image = bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
image.shape                  # (高, 宽, 通道)；深度图是 16UC1，数值单位毫米
image[h//2, w//2]            # 中心像素；除以 1000 = 几米（深度图）

# Twist —— 速度指令（你是发送方）
cmd.linear.x ; cmd.linear.y ; cmd.angular.z
```

实践技巧：不确定字段有什么，跑一句 `ros2 interface show sensor_msgs/msg/LaserScan`，
或 `ros2 topic echo /scan --field ranges` 直接看真实数据长什么样。

---

## 7. 日志：别只用 print

```python
self.get_logger().info('正常信息')       # 白色
self.get_logger().warn('警告')           # 黄色
self.get_logger().error('出错了')        # 红色
```

好处：带节点名和时间戳，比裸 `print` 好排查；警告/错误在日志里能按级别过滤。

---

## 8. 命令行参数：让一个脚本多种用法

来自 `start-sensors.py` 的惯用法：

```python
import argparse
parser = argparse.ArgumentParser(description='传感器启动器')
parser.add_argument('sensors', nargs='*', default=['all'],
                    help='astra / microdia / lidar / imu / all')
args = parser.parse_args()
# 之后 args.sensors 就是命令行给的东西：python3 start-sensors.py lidar imu
```

用途：`drive_demo.py --speed 0.05 --seconds 5` 就是这么实现的——
不用改代码就能换速度和时长，调车时特别方便。

---

## 9. 优雅退出：Ctrl+C 之后必须做的三件事

来自 `drive_demo.py`：

```python
try:
    rclpy.spin(node)
except (KeyboardInterrupt, SystemExit):
    pass                       # 用户按了 Ctrl+C：不崩溃，当作正常结束
finally:
    node.pub.publish(Twist())  # ① 补发一条全零速度 = 确保车停
    node.destroy_node()        # ② 注销节点
    if rclpy.ok():
        rclpy.shutdown()       # ③ 断开 ROS
```

为什么 `finally` 里有零速兜底：**车的"断线自动停车"还没验收**，
你程序退出的瞬间如果不主动发零，车理论上可能带着最后一条速度继续走。
凡是发 `/cmd_vel` 的程序，退出路径必须有这条。

---

## 10. 进阶预告：不订话题的脚本长什么样

`read-imu.py`（IMU 接收器）**不用 rclpy**——它是纯串口程序：
打开 `/dev/myserial` → 不停读字节 → 按帧头 `ff fb` 切帧 → 校验和验证 → 解析数值。
它的核心是一个 `FrameDecoder` 类：把零散字节攒进缓冲区、找帧头、核对校验和。

现在不用学，知道有这层即可；等你的"安全停车"节点跑顺了，想深挖"数据从哪来"时再回头看
`modules/sensors/read-imu.py` 和 [rosmaster-protocol.md](D:\作业\4无人农场\auto-farming\docs\references\rosmaster-protocol.md)。

---

## 11. 检查你学会没有（自查清单）

- [ ] 能默写 5 件套骨架（import → class → init → spin → shutdown）
- [ ] 知道发布要配定时器"持续发"，订阅是回调"被动收"
- [ ] 知道订传感器必须带 `qos_profile_sensor_data`
- [ ] 能说出 Twist 三个字段和这台车特有的 `linear.y`
- [ ] 退出路径有零速兜底
- [ ] 跑通过：`ros2 topic echo /cmd_vel` 看自己的 drive_demo 发了什么

下一步实战：把 `drive_demo.py` 改成"前进 2 秒 → 右转 1 秒 → 停"，用 echo 验证。
改完这个，你就可以开始写"读 /scan、近了就发零"的安全停车节点了。
