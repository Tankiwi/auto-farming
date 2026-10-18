# ROSMASTER 基础控制厂商资料

整理：2026-10-18。来源为用户提供的卖家目录 `05、ROSMASTER基础控制教程`，未核实发布版本、下载日期及许可。本页是资料导航与适用性说明；厂商步骤不构成本项目设备操作授权或验收结果。

## 原件与课程入口

原目录 24 个文件，经 SHA-256 核对为 12 组相同内容，每组仅保存一份。9 份 PDF 共 26 页，以及刷写工具和驱动 ZIP 保留原字节；历史日志脱敏后保存。原目录未修改，原名、来源相对路径、大小、原始与归档 SHA-256、去重对应关系见[导入清单](../reports/2026-10-18-basic-control-inventory.json)。

| 编号 | 原标题与归档原件 | 页数 | 内容与使用边界 |
|---|---|---:|---|
| 01 | [更新扩展板固件](../../modules/chassis/vendor/basic-control/01-firmware-update.pdf) | 3 | Windows、CH340、mcuisp、BOOT0/RESET；未附 HEX，不能据此确定本机固件文件 |
| 02 | [关闭开机自启动大程序](../../modules/chassis/vendor/basic-control/02-disable-autostart.pdf) | 3 | 临时关闭、Startup Applications 禁用/恢复、手动启动；须核对本机启动机制 |
| 03 | [安装 Rosmaster 驱动库](../../modules/chassis/vendor/basic-control/03-install-driver-library.pdf) | 7 | V3.3.1 安装示例、导入和 API 摘要；未附 `py_install.zip` 或库源码 |
| 04 | [蜂鸣器鸣笛](../../modules/chassis/vendor/basic-control/04-buzzer.pdf) | 2 | `set_beep`，关闭参数为 0；本机未测试 |
| 05 | [控制 PWM 舵机](../../modules/chassis/vendor/basic-control/05-pwm-servo.pdf) | 2 | 四路 PWM、供电跳线；不能套用为六轴总线机械臂的编号和供电依据 |
| 06 | [RGB 炫彩灯条特效展示](../../modules/chassis/vendor/basic-control/06-rgb-effects.pdf) | 2 | 灯效与单灯控制；LED 数量描述与第 03 课不同 |
| 07 | [控制电机正转反转](../../modules/chassis/vendor/basic-control/07-motor-control.pdf) | 2 | `set_motor` 为开环 PWM，未使用编码器测速；轮序仅为麦轮示例 |
| 08 | [控制机器人运动](../../modules/chassis/vendor/basic-control/08-car-motion.pdf) | 3 | 速度、PID、自动上报和恢复出厂；参数持久化及按键描述需核对 |
| 09 | [控制串口舵机](../../modules/chassis/vendor/basic-control/09-uart-servo.pdf) | 2 | 六舵机角度读写、扭矩；应先读本项目[机械臂映射](../modules/arm.md#舵机角度与原始位置映射)与[真机入口](../guides/arm.md#2026-10-18真机单舵机入口) |

配套附件：

- [mcuisp.exe](../../modules/chassis/vendor/basic-control/mcuisp.exe)：卖家提供的 Windows 刷写程序，只归档，未运行或验证签名、版本及兼容性。
- [CH340 驱动 ZIP](../../modules/chassis/vendor/basic-control/ch340-driver.zip)：9 个 ZIP 条目，含安装程序与驱动文件；CRC 检查通过，未安装，适用 Windows 版本待确认。
- [脱敏历史刷写日志](../../modules/chassis/vendor/basic-control/program-logs-redacted.txt)：2021—2023 年多种固件的旧记录；设备标识和绝对路径已移除，固件文件名仅用于解释来源。不是本项目设备刷写证据。

## 按任务使用

这些课程主要使用 Jetson 上的 Python / Jupyter 和 `Rosmaster_Lib`，并非每一步都依赖 ROS master。Windows 刷写、Jetson 宿主机与 Noetic 教程容器应分别核对，不能因标题包含 ROS 就直接在某个环境执行。

- **管理串口占用**：第 02 课把关闭桌面终端作为临时关闭方法，并以 `start_rosmaster_app` 为自启动项。手动恢复示例是 `bash /home/jetson/Rosmaster/rosmaster/start_app.sh`。这些是厂商环境路径，不是本机已验证恢复步骤。本项目已有串口占用与恢复记录见[机械臂指南](../guides/arm.md)，不能用关闭 SSH 窗口代替确认进程停止。
- **核对 Python 库**：第 03 课示例从 `~/Desktop/py_install` 执行 `sudo python3 setup.py install`，明确会覆盖旧库；本机历史读回为 3.3.1，并不意味着需要重装。实施前应核对实际解释器、导入位置、现有版本和可恢复安装包；本批资料没有回退包，安装与回退未验证。
- **查示例源码**：第 03—09 课依次引用 `Rosmaster/Samples/3.test_rosmaster.ipynb`、`4.beep.ipynb`、`5.pwm_servo.ipynb`、`6.rgb_effect.ipynb`、`7.motor.ipynb`、`8.car_motion.ipynb`、`9.arm_servo.ipynb`。这些是 PDF 中的参考路径，本批资料无 Notebook 或视频，不能视作本地已有源码。
- **准备真机控制**：先按[底盘交接要求](../modules/chassis.md#底盘接入恢复时的交接资料)核对板卡、接线、车型、固件、单位、限位和串口独占。本项目底盘运动及停车未测试；六个舵机有位置应答，但仅 6 号有限动作已确认，返回精度未通过。课程参数范围不等于实物安全范围。
- **判断与停止**：后续测试需分别确认协议应答、反馈、实物动作和停止，超时、无应答或异常动作即判该项未通过。第 04 课的蜂鸣器关闭参数、第 06 课的停止灯效不是底盘/机械臂急停；本批 PDF 未提供本机已验收的运动停止、通信超时或断电恢复规程。未知步骤保持待验证，不能靠对象析构、关闭窗口或结束 Python 推断电机已停。

## 原文冲突与缺口

1. 第 03 课第 6—7 页把 `set_uart_servo_angle` 写为 7—9 号及三舵机说明；第 09 课第 1 页写为 1—6 号。本机六舵机映射以已读安装库和实测记录为依据，不能合并两套编号。
2. 第 03 课第 5 页 LED 编号为 0—13，第 06 课第 2 页为 0—16；实际灯数、固件与库的范围待核对。
3. 第 08 课第 2 页恢复出厂按键为 K2，第 3 页改为 KEY1；已渲染抽查原页确认。未核对板卡前不选择其中一种，也不把恢复出厂作为常规排障步骤。
4. 第 03 课第 4 页描述每 10 ms 一包、四类数据各 40 ms 更新；第 08 课第 2 页简写为每 40 ms 一次。不能据此认定本机总包频率，需核对源码和实测。
5. 第 01 课使用 `Rosmaster_V3.1.hex` 示例，不能据此替换本机已读回的 `3.5` 版本。当前目录没有 `.hex` / `.bin`，不能关闭[固件待验证项](../pending.md)。刷写成功提示只说明厂商流程的预期，不能替代刷后协议、运动与停止验收；备份和恢复文件待补。
6. 第 08 课的 `forever=True`、`reset_flash_value()` 与第 03 课的改舵机 ID/中位、扭矩接口具有持久配置或实物影响，未在本次执行；恢复出厂不能当成无损回退。

本次已提取全部 26 页文字，抽查第 03 课第 6 页及第 08 课第 2—3 页渲染图。未逐页校对电路图片、验证外链或执行课程命令。文中出厂账号说明不复制到导航或操作步骤，不能作为当前设备认证依据。其他原文保持原字节，疑点以本页说明为准。
