# 感知目录阅读入口

从本目录 [README.md](README.md) 开始，只展开任务需要的文件：

- [operations.md](operations.md)：传感器启动、检查、停止。
- [environment.md](environment.md)：ROS 2 环境。
- [hardware.md](hardware.md)：硬件与设备别名。
- [recording.md](recording.md)：录制回放。
- [troubleshooting.md](troubleshooting.md)：故障排查。
- [start-sensors.py](start-sensors.py)：选择 astra/microdia/lidar/imu/all，编程前核对前检与进程清理；不自动做话题就绪验收。
- [read-imu.py](read-imu.py)：被动接收共享底板串口，不发串口控制指令；[read-sensors.py](read-sensors.py) 只订阅并打印，不启动驱动。
- 离线测试：[协议解析](tests/test-read-imu.py)、[启动器](tests/test-start-sensors.py)。设备实测与部署哈希边界见 operations.md，不把本地测试当成现场通过。

正文是生成副本，来源链接与校验值在文件开头；只修改来源，完成后从仓库根运行 `python tools/docs/doc_tools.py sync` 和 `python tools/docs/doc_tools.py check`。同一正文无需两处都读。跨模块任务再查[全局架构](../../docs/architecture.md)；未提供的源码、接口及设备状态明确为待验证。
