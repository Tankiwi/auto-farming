# 硬件与连接关系

更新：2026-10-20｜新增 USB/视频节点只读核对与用户传感器启动日志；其他硬件仍按各自历史证据，不表示逐项重新识别。

来源：[历史测试](../reports/2026-10-11-static-tests.md)、[历史照片](../references/photos.md)及原使用说明中的用户确认记录；这些是历史依据，不是本次设备读回。

## 硬件与系统基线

| 项目 | 确认结果 | 依据 |
|---|---|---|
| 整车 | ROSMASTER X3 Plus，带机械臂 | 用户确认与现场照片 |
| 主机 | NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super | 设备树返回字符串 |
| 系统 | Ubuntu 22.04.5 LTS | SSH 实测 |
| 架构／内核 | aarch64；5.15.148-tegra | SSH 实测 |
| ROS | ROS 2 Humble，宿主机可直接使用 | SSH 实测 |
| 雷达 | YDLIDAR TG30；固件 2.1；硬件版本 1 | 驱动读回信息 |
| 雷达选择名称 | 原厂启动配置中的 `4ROS` | 现有代码与成功复测 |
| Astra 相机 | 一套设备提供 RGB、深度、红外；本机使用 Astra Plus 配置 | 历史采集、当前 USB 与用户启动日志 |
| 第二套相机 | Microdia/Sonix USB 彩色相机，0c45:6340；video0 为采集、video1 为元数据 | 本轮设备能力查询；物理位置、出图待验 |
| 九轴 IMU | 底板经 myserial 上报三轴加速度/角速度/磁场；芯片型号未识别 | 用户日志连续接收计数，原始实值/单位/轴向/标定待验 |
| 底盘控制板 | 电机控制扩展板，USB 使用 CH340 | 用户照片、拔插对比 |
| 控制板精确版本 | 待确认；说明书示例为 YB-ERF01-V3.0 | 文档示例不可代替实物型号 |
| 底板固件 | 2026-10-18 用户确认刷回；2026-10-19 版本应答 3.5；实际文件和目标板卡仍待归档 | 用户确认与协议读回，取代当前仍为未知自定义固件的状态 |
| 底板保存的车型 | 2026-10-19 两次用户日志报告 1，库中 X3PLUS 为 2；暂无改为 2 的成功读回 | [整车前检日志](../reports/2026-10-19-motion-demo-preflight.md)；此配置值不改变实物 X3 Plus 的确认 |
| 机械臂 | 已安装；六舵机通信及有限动作记录见专题，实物限位/零位未验收 | [2026-10-18 测试](../reports/2026-10-18-arm-servo-test.md) |

早期 `x3/a1` 是系统配置，不是硬件识别结果。A1 测试超时已由正确 YDLIDAR 驱动的成功测试解释，不再将它作为雷达故障证据。


## 连接关系与设备映射

```text
Windows 笔记本
  └─ 网络 → Jetson（SSH；RDP/VNC 服务已开启）
                ├─ USB HUB → YDLIDAR 转接板 Data → 彩色线 → 雷达
                ├─ USB HUB → Orbbec RGB / 深度相机
                └─ USB 数据线 → CH340 → 底盘控制板 → 四个电机
                                           └─ 机械臂（控制尚未验证）
```

黑色盒子上带 `Data/Power` 和 `TX/RX/5V/GND` 标识的模块，已由用户追线确认是雷达转接板。彩色排线连接 OLED 的部分也已单独辨认，均不能当成底盘通信线。

| 别名 | 当日目标 | 说明 |
|---|---|---|
| `/dev/ydlidar` | `/dev/ttyUSB0` | 雷达；CP2102，USB ID `10c4:ea60` |
| `/dev/rplidar` | `/dev/ttyUSB0` | 现有 udev 同时创建的别名；名称不代表实物是 RPLIDAR |
| `/dev/myserial` | `/dev/ttyUSB1` | 底盘；CH340，USB ID `1a86:7523` |

用户拔除底盘数据线时，`myserial`、`ttyUSB1` 和 CH340 同时消失，雷达保留；插回后恢复。故底盘 USB 对应关系已验证。`ttyUSB` 编号可能变化，应优先使用已经核对的设备别名。用户将底盘线称为 Type-B，说明书标为 Micro-USB 数据口，具体插头以实物为准。

2026-10-19 本轮读回 `/dev/myserial -> /dev/ttyUSB2`，115200 下版本与编码器有校验正确的应答。上表是 2026-10-11 映射快照，不作为当前 ttyUSB 编号依据；本轮未重验雷达/相机映射或 USB 拔插。底盘实物轮位、PWM 通道与编码器编号尚未逐一对应，详见[底盘测试](../reports/2026-10-19-motor-test.md)。

## 2026-10-20 第二相机视频节点核对

Microdia USB ID `0c45:6340`，udev 名称 Sonix USB 2.0 Camera；当前 `/dev/video0` 为 Video Capture、`/dev/video1` 为同一相机的 Metadata Capture，并非两台设备。相机内核驱动为 `uvcvideo`，支持 YUYV 640×480 等模式；稳定 by-id 别名与原始查询见[第二相机指南](../guides/sensors.md#microdia-第二相机核对)、[证据](../reports/2026-10-20-microdia-inventory.json)。本轮只查询能力，物理安装位置、图像采集和标定仍待验证。
