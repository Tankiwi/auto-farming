# 底盘目录阅读入口

从本目录 [README.md](README.md) 开始，只展开任务需要的文件：

- [基础控制资料](vendor/basic-control/README.md)：9 份课程、附件、来源及原文冲突。
- [电机分步指南](../../docs/guides/chassis.md)：只读检查、PWM 测试与停止限制；[motor-check.py](motor-check.py) 为本地测试源码。
- [官方 Python API 清单](../../docs/references/rosmaster-motion-api.md)：38 个公开方法、参数差异和副作用。
- [motion-demo.py](motion-demo.py)：默认预览；线程修复版用户运行正常退出，车型仍为 1，动作被拒绝。新增显式配置选项仅离线通过，暂无上车结果；构造会开启机械臂扭矩，运行前读底盘指南。
- [hardware.md](hardware.md)：接线与别名。
- [environment.md](environment.md)：环境配置与整车启动限制。
- [troubleshooting.md](troubleshooting.md)：已知故障与历史边界。

正文是生成副本，来源链接与校验值在文件开头；只修改来源，完成后从仓库根运行 `python tools/docs/doc_tools.py sync` 和 `python tools/docs/doc_tools.py check`。同一正文无需两处都读。跨模块任务再查[全局架构](../../docs/architecture.md)；未提供的源码、接口及设备状态明确为待验证。
