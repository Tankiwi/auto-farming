# 机械臂 ROS 1 与 MoveIt 入门

更新：2026-10-18｜适用：Jetson 宿主机真机测试及 Noetic 课程容器；课程最后验证 2026-10-11，单舵机最后验证 2026-10-18。
用途：课程配置与仿真准备，以及[宿主机单舵机真机测试](#2026-10-18真机单舵机入口)。课程历史证据见[教程容器记录](../changes/README.md#2026-10-11机械臂教程需要进入预装的-ros-1-容器)，新测试见[单舵机实测](../reports/2026-10-18-arm-servo-test.md)。原始课程见[课程索引](../references/arm-courses.md)。

## 1. 为什么 roscore 找不到

厂商《1、MoveIt配置.pdf》第 1 页要求运行 `roscore`、`rosrun moveit_setup_assistant moveit_setup_assistant`，属于 ROS 1。小车宿主机为 Ubuntu 22.04.5、ROS 2 Humble，`/opt/ros` 只有 `humble`，因此宿主机终端找不到 `roscore`。

ROS 1 已在本机 Docker 镜像 `yahboomtechnology/ros-noetic:3.0.5` 中，镜像内为 Ubuntu 20.04.6、ROS Noetic。无需为这个问题重装系统或给 Humble 补装 `roscore`。

实测存在的软件包：`moveit_setup_assistant`、`arm_moveit_demo`、`x3plus_moveit_config`。镜像内车型变量使用 `X3plus`；宿主机 ROS 2 配置使用 `x3plus`，两套环境不能直接混用。

## 2. 已部署的教程入口

小车脚本：`/home/jetson/farm-tools/arm-noetic.sh`。

本地副本：[modules/arm/arm-noetic.sh](../../modules/arm/arm-noetic.sh)。容器名称固定为 `farm-arm-noetic`，多个终端操作同一个容器。首次创建后保留容器，可停止后再次启动。

容器不映射 USB、串口或底盘设备，网络使用 `none`，ROS master 在容器内部的 `127.0.0.1:11311`。支持通过只读 X11 socket 与认证文件连接 Jetson 桌面，使用软件渲染。它适用于本课配置步骤；不能直接拿来控制真机或与其他机器的 ROS 节点通信。

保存配置时使用容器内 `/root/farm_data`，对应小车宿主机 `/home/jetson/farm-arm-data`。该目录在停止或移除容器后仍保留。保存在容器其他位置的修改不具备同样的外部持久化保证。

## 3. 现在按这几步做

### 第一步：终端 A 启动 roscore

在 SSH 登录后的小车终端，或者小车桌面终端执行：

```bash
bash /home/jetson/farm-tools/arm-noetic.sh core
```

看到 `started core service [/rosout]` 表示 master 已启动。保持该终端运行。不要在另一个终端重复启动第二个 master。

### 第二步：终端 B 打开配置助手

打开第二个小车终端（SSH 可另开一个连接），执行：

```bash
bash /home/jetson/farm-tools/arm-noetic.sh setup
```

图形窗口显示在 **Jetson 的桌面 `:0`**，不会显示在 Windows PowerShell 中。需要在小车连接的显示器，或能看到该桌面的远程桌面中操作。远程桌面连接若使用另一套显示会话，需先核对 `DISPLAY`；本入口默认针对当前 `:0` 会话。

### 第三步：选择配置路线

跟随第一课从头学习，可选择 `Create New MoveIt Configuration Package`，URDF 文件为：

```text
/root/yahboomcar_ws/src/yahboomcar_description/urdf/yahboomcar_X3plus.urdf
```

此文件存在已核对，模型加载、碰撞矩阵和规划组配置仍需按课程逐步验收。新生成的配置包保存为 `/root/farm_data/x3plus_moveit_config_tutorial`，避免覆盖预装配置。

若只是查看已有配置，可选择 `Edit Existing MoveIt Configuration Package`，目录为 `/root/yahboomcar_ws/src/x3plus_moveit_config`。不要把“已有配置存在”理解为实物关节零位、限位或底板协议已经验证。

### 第四步：结束

关闭配置助手，在终端 A 按 `Ctrl+C` 停止 `roscore`。需要停止容器时执行：

```bash
bash /home/jetson/farm-tools/arm-noetic.sh stop
```

以后再次运行 `core` 会启动并复用这个容器。关闭 SSH 窗口不等于可靠地停止容器内程序。

## 4. 检查命令

进入已经加载 ROS 1 工作空间的容器终端：

```bash
bash /home/jetson/farm-tools/arm-noetic.sh shell
```

然后执行：

```bash
echo "$ROS_VERSION $ROS_DISTRO"
rosnode list
rospack find moveit_setup_assistant
rospack find x3plus_moveit_config
```

预期环境为 `1 noetic`。只有终端 A 正在运行 master 时，`rosnode list` 才能正常连接。退出此交互终端用 `exit`。

## 5. 原厂启动脚本的问题

`/home/jetson/run_docker.sh` 使用 `xhost +`，并绑定固定 USB 编号和多个设备。2026-10-11 实测 `/dev/camera_depth` 不存在；其中硬编码 USB 路径也不等同于当时相机别名所指路径。直接运行可能因设备不存在而失败。当时保留原脚本，另部署独立教程入口；本次仅迁移本地副本。

## 6. 重启与待验证边界

桌面重新登录或小车重启后，X11 认证文件可能变化。若 `core` 正常但助手提示无法连接显示，先核对当前桌面的 `DISPLAY` 与 `XAUTHORITY`，不要直接执行 `xhost +`。旧容器可能需要在保存配置后重新创建以更新认证挂载；不要未经备份就删除容器。

2026-10-11 完成 ROS master 和软件环境检查，容器内 `xdpyinfo` 成功，并通过 `xwininfo` 确认配置助手已创建标题为 `MoveIt Setup Assistant` 的 1090×600 窗口。测试程序结束，容器保留并停止，执行第一步即可重启。未截图核对窗口内容。模型加载、配置生成、RViz 规划、真实舵机通信与运动、远程桌面画面验收分别记录，不能用 `roscore` 成功替代。

## 2026-10-18：恢复真机接入前的只读检查

用户确认底板已刷回，具体固件版本尚待核对。通过新地址 SSH 登录后读到 `/dev/myserial -> ttyUSB1`；`fuser` 与进程查询显示 PID 3292 的 `python3 /home/jetson/Rosmaster/rosmaster/rosmaster_main.py` 正在占用串口。PID 仅为当次快照，下一次操作需重新查询。教程容器 `farm-arm-noetic` 状态为 `Exited (255)`，未启动。

读取远端源码发现原厂主程序创建 `Rosmaster` 对象并启动接收线程，含机械臂角度读取逻辑；`Rosmaster_Lib.py` 中存在单舵机和多舵机角度接口。此项仅证明源码存在，不代表运行中导入路径、固件协议或机械臂响应已核实。后续先确认现有服务的管理和恢复方式、协调串口占用，再核验固件及角度读取；本次未停止服务、未查询硬件协议、未发送运动指令。运动、限位和停止继续待验证。

## 2026-10-18：真机单舵机入口

此前“协议与运动未复测”已由本节有限范围的实测取代，详见[测试记录](../reports/2026-10-18-arm-servo-test.md)。底板版本应答为 `3.5`，六个舵机位置查询通过，6 号约 10°往返后用户确认看到了动作且正常。返回位置偏差约 1.7°，超过脚本容差；精确返回未通过。2、3 号原始位置超出原厂角度换算范围，未测试其他关节，暂不执行整臂回零或 MoveIt 真机运动。

在 **Jetson 宿主机终端**执行默认查询（无需 Docker 或 ROS）：

```bash
python3 /home/jetson/farm-tools/arm-check.py
```

本地源码为 [arm-check.py](../../modules/arm/arm-check.py)，已部署并核对哈希。脚本仅暂停已识别的原厂串口使用者，结束恢复，不卸载服务或修改开机配置。默认查询不创建 `Rosmaster` 对象，避免其构造函数自动开启全部扭矩。

1～6 号舵机的软件角度与原始位置值关系、方向及源码依据见[舵机映射表](../modules/arm.md#舵机角度与原始位置映射)；库换算区间不等于实物安全限位。

复现 6 号约 -10°、停留 3 秒并返回的测试，仅在底盘静止、原厂程序无其他控制任务、机械臂周围清空、无抓取负载、现场可立即断电时执行：

```bash
python3 /home/jetson/farm-tools/arm-check.py --move-servo6 --clear-confirmed
```

每个方向 2000 ms，仅向 6 号发送动作，不自动开启扭矩或重新校准。先读取稳定位置，未达目标则不发下一条动作；返回超容差会报错，不自动追调。本次实际就因返回偏差报非零，不能将“看到了动作”当作精确定位通过。若出现异响、卡住或碰撞，现场断电；断电后注意失去支撑。`Ctrl+C` 仅结束测试程序并恢复原厂进程，不能保证中断已发送的动作。软件急停与重新上电恢复尚待测试。

同日后续检查：六个静止读数均在库换算区间，2/3 号不再越界，但 6 号约 3°测试仍因返回偏差超容差而终止，其他关节未动。此结果不支持直接开展整臂动作。本地脚本现为减 300（约 24.55°），设备保留减 122；上面的设备命令仅描述已核对的设备版本，勿把本地约 -10°旧注释当作当前幅度，见[完整后续记录](../reports/2026-10-18-arm-servo-test.md#同日后续全舵机静态复查与-6-号约-3测试)。

## 最新分步测试限制

同日用户指定的 1～5 号测试已实际执行，取代此前“未动其余关节”的当前状态。1 号最初约 3°有反馈，但其后约 6°重复测试未复现；最终五个舵机约 6°指令均未明显到达，用户确认无明显运动、无异常。一次查询超时经后续只读恢复，原因未定位。记录见[分步测试](../reports/2026-10-18-arm-servo-test.md#同日再测用户指定-15-号先约-3后约-6)。

当前应先排查实际扭矩/控制状态、供电和固件/通信，不能因为可读位置就继续加大角度或宣布运动通过。已停止动作并恢复原厂程序；没有开启全部扭矩或执行整臂回零，软件急停尚未验收。

## 三参数封装测试函数

本地新增独立模块 [arm.py](../../modules/arm/arm.py)，无需导入旧的 `arm-check.py`，不依赖其本地幅度差值。只需三个参数：

```python
from arm import test_motor

result = test_motor(2, 5, 2000)
print(result)
```

这是在 **Jetson 上、`arm.py` 所在目录或同级脚本中**调用的例子：读取 2 号当前角度，沿库定义的正方向增加约 5°，用 2000 ms 完成单程；去程反馈通过后停留 1 秒，再用相同时间返回本次起点。返回起点不是整臂回零。

| 参数 | 单位与范围 | 含义 |
|---|---|---|
| `motor_id` | 整数 1～6 | 总线舵机编号，不是底盘电机编号 |
| `amplitude_deg` | 有符号角度，`0 < abs(value) <= 10` | 相对当前位置的增减量；正负依照[安装库映射](../modules/arm.md#舵机角度与原始位置映射)，不保证统一的实物顺/逆时针 |
| `duration_ms` | 整数 500～2000 ms | 每个方向的运动时间；不含查询、等待、停留和返回所需总时间 |

这些是当前测试函数的保守输入限制，不是设备全部能力或实物安全限位。函数拒绝非有限数值、低于位置分辨率的幅度、起点不稳定及越出库区间附近测试边界的目标；不静默裁剪输入，不修改零点或限位。

本次仅本地编写，**尚未上传或真机执行新模块**。需要使用时，在 Windows PowerShell 的仓库根目录上传这一份文件：

```powershell
scp .\modules\arm\arm.py jetson@192.168.43.53:/home/jetson/farm-tools/arm.py
```

然后在 Jetson 宿主机终端运行，三个位置参数与 Python 函数相同：

```bash
cd /home/jetson/farm-tools
python3 arm.py 2 5 2000
```

`python3 arm.py --help` 只显示帮助、不连接串口；负幅度例如 `python3 arm.py 2 -5 2000`。依赖 Python 3、pyserial 与 `fuser`，不需 ROS 或 Docker。模块在 Windows 可导入/查看帮助，真实串口会话仅支持 Jetson Linux；本机代码修改不会自动同步小车。

### 反馈结果与停止规则

返回字典包括目标/起点/实测位置、软件换算角度、实测幅度、位置误差与 `status`：

| `status` | 含义 |
|---|---|
| `passed` | 去程检测到明显位置变化，去程和返回均满足原有 ±15 位置单位容差；仍需现场观察 |
| `no_movement` | 位移未达到本次目标位移一半（且至少 2 个单位），不认为发出命令就是动作成功 |
| `target_not_reached` | 有位置变化，但去程误差超过 ±15 单位 |
| `return_out_of_tolerance` | 去程通过，返回误差超过 ±15 单位 |

去程未通过时不发送返回、补偿或重复动作，实际可能停在部分移动后的位置；异常通信会抛出异常并清理会话，也不自动追发指令。命令行状态码 0 仅对应 `passed`，1 对应反馈未通过，2 对应参数/通信/系统异常；Python 函数调用者可检查返回字典或捕获异常。没有“手动确认通过”或自动放宽容差。

函数与旧脚本共用测试锁，识别并临时暂停已知原厂串口使用者，结束恢复，异常有 30 秒恢复看门狗；未知或多个串口使用者会拒绝访问。仅按已核对协议发送单舵机位置指令，**不自动开启全部舵机扭矩**。当前 1～5 号无明显动作的根因并未因此修复，仍需定位实际使能、供电或固件/通信状态。

调用运动函数前保持底盘静止、原厂程序无其他控制任务、周围清空和无负载，现场可立即断电；返回目标可能已经发到板卡，`Ctrl+C`、异常退出或暂停进程都不是机械臂急停。完整限位、断电/重新上电恢复及软件急停未验收。

离线验证在 Windows 仓库根执行：

```powershell
python modules/arm/tests/test-arm.py
```

10 项模拟测试覆盖六舵机正负方向/帧编码、无位移误判、部分到达、返回超差、超时后不重发、异常清理、非法参数和越界拒绝；不打开串口、不暂停真实进程，不能替代部署与真机验收。

## 厂商课程原件

课程文件、适用边界和原文疑点见[课程索引](../references/arm-courses.md)。
