# 文档导航

更新：2026-10-20。最新传感器证据见[用户启动日志与随后只读复查](reports/2026-10-20-sensors-startup.md)；底盘局部测试及车型前检保持 2026-10-19 的验证范围。

## 按任务阅读

| 目的 | 文档 |
|---|---|
| 了解已知能力与阶段 | [状态](status.md)、[待验证信息](pending.md) |
| 查询设备与连接 | [硬件和接线](environment/hardware.md)、[软件环境](environment/software.md) |
| 连接、启动、检查、停止 | [使用指南总览](guides/README.md)、[远程连接](guides/remote-access.md)、[传感器](guides/sensors.md)、[录制回放](guides/data-recording.md)、[机械臂教程](guides/arm.md) |
| 启动指定传感器、用 Python 读数据 | [上传与参数入口](guides/sensors.md#按参数启动驱动)、[订阅读取](guides/sensors.md#python-读取示例)、[九轴 IMU](guides/sensors.md#九轴-imu-读取) |
| 遇到故障 | [故障排查](troubleshooting/README.md) |
| 测试底盘电机 | [底盘分步指南](guides/chassis.md)、[2026-10-19 实测](reports/2026-10-19-motor-test.md) |
| 上传整车示例、处理车型前检 | [上传与版本核对](guides/chassis.md#上传与版本核对)、[显式车型配置](guides/chassis.md#显式设置-x3-plus-车型)、[用户日志](reports/2026-10-19-motion-demo-preflight.md) |
| 使用官方 Python 运动接口 | [全部 38 个公开方法与限制](references/rosmaster-motion-api.md)、[安装源码清单](reports/2026-10-19-rosmaster-api-inventory.json) |
| 定位代码和接口 | [架构与代码地图](architecture.md)、[底板功能码参考](references/rosmaster-protocol.md) |
| 按模块理解 | [机械臂](modules/arm.md)、[感知](modules/sensors.md)、[底盘](modules/chassis.md)、[主机](modules/host.md) |
| 了解尚未实施的方案 | [农场作业方案](plans/farm-workflow.md) |
| 查原始资料 | [参考资料索引](references/README.md)、[15 份机械臂课程](references/arm-courses.md)、[9 份基础控制课程与附件](references/basic-control-courses.md)、[照片](references/photos.md) |
| 复现机械臂课程仿真 | [操作步骤](guides/arm.md#课程仿真复现)、[第 1 课](reports/2026-10-11-moveit-configuration.md)、[第 2～8 课](reports/2026-10-11-moveit-courses-2-8.md) |
| 回溯过程 | [变更记录](changes/README.md)、[2026-10-11 测试](reports/2026-10-11-static-tests.md)、[阶段快照](reports/2026-10-11-milestone.md) |
| 分支知识迁移 | [main 新结构与 dev 迁移范围](reports/2026-10-18-branch-migration.md) |
| 了解本次整理 | [审查报告](reports/2026-10-17-repository-audit.md)、[逐文件迁移清单](reports/2026-10-17-file-inventory.json) |
| 维护文档 | [维护规范](maintenance.md)、[可选模板](templates.md)、[skill 源码](../skills/robot-doc-governance/SKILL.md)、[分发包](../dist/robot-doc-governance.zip)、[工具说明](../tools/docs/README.md) |

## 两种阅读位置

人可一直在本目录按上表阅读。Agent 可在[模块目录](../modules/README.md)读取同级 `README.md` 与任务文档，这些正文由集中版生成；具体映射见 [agent-mirrors.json](agent-mirrors.json)。修改集中版后同步，副本不单独编辑。历史报告与原始 PDF 按任务需要打开，不自动并入每个模块。

本仓库未包含完整 ROS 工作空间、自定义底板固件或长期原始测试日志；文档中出现的远端路径不表示本地已有源码。
