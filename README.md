# 无人农场小车数字文档中心

这里保存项目的环境基线、操作方法、历史证据、方案和待验证事项，供团队长期维护与交接。

文档更新：2026-10-18。最近设备验证：2026-10-18（SSH、底板协议和 1～6 号舵机分步测试）。

现有设备记录围绕带机械臂的 ROSMASTER X3 Plus。历史验证覆盖 SSH、雷达与相机短时数据、底盘 USB 对应关系，以及 Noetic 容器内 ROS master；dev 的历史记录补充了第 1 课 6/6 fake 规划执行与第 2～8 课仿真示例验收；底板版本和六舵机位置查询已通，用户最新提供 1～5 号八次约 10°往返通过日志，并确认所有舵机均已手动测试。6 号新日志和早先失败条件差异待补；RViz 画面、从零配置生成、整臂联动、限位、急停、底盘运动、建图和导航仍未验收。详细边界见[状态](docs/status.md)与[真机操作入口](docs/guides/arm.md#2026-10-18真机单舵机入口)。

## 从这里开始

| 任务 | 入口 |
|---|---|
| 阅读完整文档 | [docs 导航](docs/README.md) |
| 连接与操作 | [使用指南](docs/guides/README.md) |
| 硬件、软件与实现定位 | [硬件环境](docs/environment/hardware.md)、[软件环境](docs/environment/software.md)、[架构与代码地图](docs/architecture.md) |
| 排障与未知信息 | [故障排查](docs/troubleshooting/README.md)、[待验证清单](docs/pending.md) |
| 查卖家基础控制资料 | [9 份课程、附件和适用边界](docs/references/basic-control-courses.md) |
| 查机械臂课程仿真 | [仿真复现](docs/guides/arm.md#课程仿真复现)、[第 1 课验收](docs/reports/2026-10-11-moveit-configuration.md)、[第 2～8 课验收](docs/reports/2026-10-11-moveit-courses-2-8.md) |
| 查证据与变化 | [变更记录](docs/changes/README.md)、[本次仓库审查](docs/reports/2026-10-17-repository-audit.md) |
| 了解旋耕与农场作业设想 | [方案边界](docs/plans/farm-workflow.md)，尚未确认已实施 |

## 目录约定

- `docs/`：人阅读的集中版，也是手工维护的正文来源。
- `modules/`：按机械臂、感知、底盘、主机放相关文件及自动生成的文档副本。机械臂包含教程入口和单舵机测试脚本，其他模块尚无设备源码归档。
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
