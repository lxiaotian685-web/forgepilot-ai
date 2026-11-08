# ForgePilot 评审版本清单（2026-11-08）

本清单用于校赛评审期核对材料，不授权自动发布或修改线上环境。

| 项目 | 固定值 |
|---|---|
| 项目 | 制造领航 ForgePilot |
| GitHub | <https://github.com/lxiaotian685-web/forgepilot-ai> |
| 线上演示 | <https://forgepilot.xiaotianworks.cn/> |
| 项目介绍 | <https://forgepilot.xiaotianworks.cn/showcase/> |
| 演示视频 | <https://b23.tv/7BG5CCJ> |
| 校赛提交包基线 | `89c69c7` |
| 2026-11-08 线上与 GitHub main 基线 | `5d8e5fb04fc2c11c7a28e0b4b6004647c5325f78` |
| 当前候选分支 | `task/a-r8-evaluation-hardening` |
| 技术文档 | `docs/tech-report/ForgePilot_技术说明_20261031.pdf` |
| 数据边界 | 全部设备、告警、工单与说明书均为虚构演示数据 |
| 模型边界 | 线上接入真实 DeepSeek；输出仅作初步分析，最终结论需人工核验与主管验收 |
| 存储边界 | 公网 SQLite/JSON 为演示存储，尚未接入持久化 PostgreSQL |

## 评审期发布纪律

- 未完成回归、材料核对和人工批准前，不合并候选分支到 `main`。
- 不重新部署 CloudBase 云托管服务，不解绑或更换 `forgepilot.xiaotianworks.cn` 域名。
- 不清空、迁移或批量改写线上演示数据。
- 飞书提交成功截图与“查看提交记录”仅由队长本人核验和留存。

## 统一业务口径

`设备查询 → 证据检索 → AI 初步分析 → 现场核验工单 → 人工核验 → 主管验收 → 审计追溯`

AI 不直接控制设备，也不替代工程师作最终判断；证据不足时必须明确标记并进入现场核验任务。

## 文件校验值（SHA256）

| 文件 | SHA256 |
|---|---|
| 仓库技术 PDF | `7E2A8BCFCD52CAD91CADFA2190A1C21C80F478474E2D92F47ED2BFFF23CB2C2D` |
| `00_提交前阅读.txt` | `CC024838F1D7CC8CEA2B7A606A20282D5AD8E662D14CED4525201679367F6F77` |
| `01_作品介绍文档_ForgePilot_校赛版.pdf` | `EE52B7ADE4B5C003A1034C5900E64CDBC263A5DFADE060A507B75BAFC8EC5B0B` |
| `02_当前源码获取_ForgePilot_89c69c7.txt` | `55E240E4BC0A9A01B01AA9451463C85AE671433B2B4D96317B33A281CF6184BF` |
| `03_技术说明文档_ForgePilot_17页.pdf` | `BC700A58083426B67F640457A46DBCE7558461ADCB11A90771C457E8B8B4768B` |
| `04_演示视频核对.txt` | `00EC9F89651D7DDC7255AB2842C771411A4F78B13705489BFA832DF9642CBAB1` |
| `05_源码获取说明.txt` | `CB58DA0455AC5769C664F1AF5698F88A7D09D932616BCBB79382B24ECA341FA4` |

校赛六文件包位置：`C:\Users\ZhuanZ（无密码）\Desktop\ForgePilot_校赛提交_20261107`。该目录为已提交材料的本地留档，不在候选分支中改写。
