# 无人农场小车数字文档中心

这里保存项目的环境基线、操作方法、历史证据、方案和待验证事项，供团队长期维护与交接。

文档更新：2026-10-20。最新证据：用户四传感器启动日志及随后 SSH 只读复查；底盘动作证据仍为 2026-10-19。

现有设备记录围绕带机械臂的 ROSMASTER X3 Plus。历史已验证雷达/相机短时数据和 Noetic 课程仿真；机械臂六舵机可读，用户确认均已手动测试，1～5 号有八次有限往返通过日志。底盘 1 路 PWM 已有动作，地面测试其他编码器变化不能据此判故障，其余路仍未独立验收。官方 Python 库的全部 38 个公开方法已归档；整车示例因底板车型读回 1（预期 Plus 为 2）而拒绝动作，线程修复版用户运行正常退出，新增显式车型配置选项暂无上车结果。整车速度控制、机械臂完整限位/联动、急停与导航仍待验收，详见[状态](docs/status.md)。

新增传感器启动器与 Python 读取入口，支持 Astra、Microdia、雷达、九轴 IMU。用户日志中 IMU 连续接收约 24.35 Hz、校验错误 0；两相机与雷达本轮仅确认启动流程，随后只读复查时驱动已不在运行，详见[传感器指南](docs/guides/sensors.md)与[日志报告](docs/reports/2026-10-20-sensors-startup.md)。

## 从这里开始

| 任务 | 入口 |
|---|---|
| 阅读完整文档 | [docs 导航](docs/README.md) |
| 连接与操作 | [使用指南](docs/guides/README.md) |
| 传感器上传、选择、读取、停止 | [传感器指南](docs/guides/sensors.md)、[本轮启动与复查](docs/reports/2026-10-20-sensors-startup.md) |
| 底盘动作与当前车型问题 | [底盘指南](docs/guides/chassis.md)、[官方 Python API](docs/references/rosmaster-motion-api.md)、[用户前检日志](docs/reports/2026-10-19-motion-demo-preflight.md) |
| 硬件、软件与实现定位 | [硬件环境](docs/environment/hardware.md)、[软件环境](docs/environment/software.md)、[架构与代码地图](docs/architecture.md) |
| 排障与未知信息 | [故障排查](docs/troubleshooting/README.md)、[待验证清单](docs/pending.md) |
| 查卖家基础控制资料 | [9 份课程、附件和适用边界](docs/references/basic-control-courses.md) |
| 查机械臂课程仿真 | [仿真复现](docs/guides/arm.md#课程仿真复现)、[第 1 课验收](docs/reports/2026-10-11-moveit-configuration.md)、[第 2～8 课验收](docs/reports/2026-10-11-moveit-courses-2-8.md) |
| 查证据与变化 | [变更记录](docs/changes/README.md)、[本次仓库审查](docs/reports/2026-10-17-repository-audit.md) |
| 了解旋耕与农场作业设想 | [方案边界](docs/plans/farm-workflow.md)，尚未确认已实施 |

## 目录约定

- `docs/`：人阅读的集中版，也是手工维护的正文来源。
- `modules/`：按机械臂、感知、底盘、主机放相关文件及自动生成的文档副本；机械臂有教程/舵机脚本，底盘有 PWM 测试、官方速度示例和离线回归，感知有驱动启动器、被动 IMU 接收器和订阅示例；尚无完整整车工作空间归档。
- `tools/docs/`：文档同步、链接与原件校验工具。
- `skills/`：项目维护 skill 的源码；`dist/` 保存同步打包的分发版。
- `archive/unclassified/`：与工程无关或用途未确定的原文件，不作为项目依赖。

Agent 从 [AGENTS.md](AGENTS.md) 选择模块，在模块同级读取相关文档；通常无需扫描全仓库或通读 PDF。正文文件名采用小写英文与连字符，标题和内容保留中文。迁移前路径及校验值保存在[文件清单](docs/reports/2026-10-17-file-inventory.json)。

在仓库根使用 Python 3 执行：

```sh
python tools/docs/doc_tools.py sync
python tools/docs/doc_tools.py check
```

2026-10-17 已完成文档迁移、模块副本和维护工具建设。2026-10-18 主分支采用此结构，并迁入 dev 历史课程知识；范围和旧路径映射见[分支迁移记录](docs/reports/2026-10-18-branch-migration.md)。该工作没有改变设备配置、部署脚本或设备验收结果。
