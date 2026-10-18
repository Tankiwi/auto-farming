# dev 旧版通用操作指南的使用边界

2026-10-18 整理。dev `60399af` 仍包含根目录的《X3Plus 麦轮机械臂机器人 —— 完整操作指南》；该文件不是 dev 独有新增，main 曾在 `eab398d` 明确移出。本次保留这一取舍，不恢复旧根目录和另一套操作正文。原文可按固定提交从 Git 历史读取：

```powershell
git show '60399af:# X3Plus 麦轮机械臂机器人 —— 完整操作指南.md'
```

| 原指南知识 | 当前入口与适用边界 |
|---|---|
| 虚拟机 ROS 1、ROS_MASTER_URI / ROS_IP、多机通信 | [软件环境](../environment/software.md)；当前是宿主机 Humble + 隔离 Noetic 容器，不直接套用双机 ROS 1 配置 |
| MoveIt 示例、规划组、夹爪 fake 目标 | [第 1 课](../reports/2026-10-11-moveit-configuration.md)、[第 2～8 课](../reports/2026-10-11-moveit-courses-2-8.md)；以有日期的实测配置为准 |
| 真机 bringup、sim:=false、TargetAngle 与夹爪 | [机械臂指南](../guides/arm.md)；MoveIt 真机链路未验收，不能从当前单舵机测试外推 |
| MediaPipe、色块搬运、巡线清障 | [课程 9～15 原件及疑点](arm-courses.md)；仅参考，未验证实体功能、按键、速度及参数 |
| rosbag、关节 CSV、图像保存、数据归档 | [数据录制回放](../guides/data-recording.md)；原文为 ROS 1 例子，Humble 用 ROS 2 工具，录制与回放待验收；控制话题回放前必须隔离真实执行器 |
| 账号、组网、预设 home、舵机与关节对照 | [当前待验证](../pending.md)；原文默认账号、NAT 一定不通、双 master 描述及 home 目标不能当成本机事实；实体关节名称/方向仍需核实 |

以上为历史参考分流，不增加工程验收结论；原文的全流程命令、动作幅度和通用建议不替代当前操作指南。
