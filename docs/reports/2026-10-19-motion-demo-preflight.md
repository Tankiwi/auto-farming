# 2026-10-19：整车示例车型前检终止与串口退出修复

## 用户提供日志

用户在 Jetson 执行 `python3 ~/motion-demo.py --run --clear-confirmed`，贴出的输出包括：

```text
Rosmaster Serial Opened! Baudrate=115200
----------------create receive threading--------------
Firmware=3.5; board car_type=1
Exception in thread task_serial_receive:
...
File ".../Rosmaster_Lib.py", line 258, in __receive_data
File ".../serialposix.py", line 575, in read
    buf = os.read(self.fd, size - len(read))
TypeError: 'NoneType' object cannot be interpreted as an integer
...
RuntimeError: Expected firmware 3.5 / X3PLUS type 2; no motion plan sent; do not auto-reconfigure
serial Close!
```

这是用户日志证据，本轮 agent 未连接设备、读取部署哈希或复跑。可确认示例已由用户上传并尝试执行，不能继续把部署状态写成“用户从未运行”；具体文件一致性仍待核对。

## 两个问题分别解释

1. **动作计划被车型检查拒绝**：固件返回 3.5，底板车型返回 1。安装库常量 1 为 X3、2 为 X3PLUS；这说明底板报告的配置与示例要求不一致，不改变本机实物为 X3 Plus 的用户确认。`Rosmaster(car_type=2)` 只指定当前对象发包车型，不自动把底板保存配置改成 2。
2. **接收线程与串口关闭竞争**：归档的 3.3.1 接收函数是 `while True` 阻塞读取，没有退出开关；旧示例启动它后直接关闭串口，线程可能仍在读，产生 fd 为 None 的异常。源码及异常位置支持此判断；本地假串口验证清理修复，真实设备复验尚未做。

动作列表打印只表示预览，日志没有进入 `Starting in 3 s` 或各动作阶段，因此非零底盘动作计划未执行。旧版 `finally` 仍会尝试发三次零速度，原厂构造此前也已发送开舵机扭矩指令；不能把此次运行说成完全无控制指令或纯只读。日志不提供实物是否保持静止的独立证据。

## 本地修复与验证

[motion-demo.py](../../modules/chassis/motion-demo.py)保留固件/车型检查，不将预期改为 1、不自动调用持久化 `set_car_type(2)`。增加可结束的接收会话：仍使用归档原厂私有解析入口，将底层读超时设为 0.05 秒，退出时设置事件并等待线程完成，再关闭串口；不修改已安装原厂库。此适配依赖已核对的 3.3.1 私有实现，升级库后需重新核对。异常前检退出改为打印简明 ABORTED 信息；最终清理发三次不带车型字段的四路零 PWM。

回归：[test-motion-demo.py](../../modules/chassis/tests/test-motion-demo.py)，Windows 仓库根执行 `python -B modules/chassis/tests/test-motion-demo.py`。两项通过：车型 1 必须被拒绝；加载真实归档库解析函数、使用假串口返回 3.5/1 时，动作函数不被调用、未发速度功能码、三次零 PWM、线程退出后关闭串口。初次测试因 Windows 无 SIGHUP，修正测试中的 Linux 信号模拟后通过，未修改生产代码的 Linux 限制。默认预览也通过。

本次仅本地修复和文档记录，未上传新版本、修改底板车型、发起动作或验证硬件停车。重新上传后，底板仍报告 1 就仍会停止在前检；这不是修复失效。下一步核对实物/固件的车型设置流程及持久化影响，确认后单独配置、读回并重做低速整车验收，不能通过删除检查绕过。

## 用户后续运行修复版与显式配置入口

用户随后贴出 `Firmware=3.5; board car_type=1`、简明 `ABORTED: Board mismatch...` 和 `serial Close!`，没有再出现接收线程异常。这是用户日志证明修复版已在设备运行的有限证据；部署哈希和重复稳定性未核对，动作计划仍未执行，底板仍为 1。

为使下一步配置可单独执行，新增 `--configure-x3plus --clear-confirmed`，与 `--run` 互斥：只接受已核对的固件 3.5 和原车型 1/2，原为 1 时明确调用官方 `set_car_type(2)` 写带 0x5F 标志的持久配置，等待后重新请求车型；读回 2 才报告 CONFIGURED，然后退出，不调用动作计划。失败不自动重试，不自动回滚；真实掉电保持与运动影响未验证，后续如需回退应单独评估后恢复旧值 1，不能把回退当作已实测流程。构造开舵机扭矩、最终零 PWM 清理的副作用仍在。

新增选项仅本地准备，尚未上传或在实物写入。四项离线回归通过，覆盖显式单次持久化并读回、不执行动作、读回失败无重试以及原车型拒绝/线程清理。此模拟验证不代表底板实际配置成功。
