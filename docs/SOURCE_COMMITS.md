# 集成来源与可复现记录

本提交分支从 A 前端业务分支 `task/a-r7-business-ops` 建立。B、C 服务分别以独立目录纳入，保留原始功能分支和 PR 历史，便于核查各成员的增量开发过程。

| 部分 | 本地来源提交 | GitHub PR | 对应目录 |
|---|---|---|---|
| A 前端 | `a3e8c979db1cd3707e23d7619db243709dd8df3e` | [#30](https://github.com/lxiaotian685-web/forgepilot-ai/pull/30)、[#32](https://github.com/lxiaotian685-web/forgepilot-ai/pull/32) | `frontend/` |
| B 业务服务 | `c227358` | [#31](https://github.com/lxiaotian685-web/forgepilot-ai/pull/31) | `services/business/` |
| C 知识诊断服务 | `1997c9d` | [#29](https://github.com/lxiaotian685-web/forgepilot-ai/pull/29)、[#33](https://github.com/lxiaotian685-web/forgepilot-ai/pull/33) | `services/knowledge/` |

本次集成只复制源码、测试、配置模板、虚构演示文档和接口说明；不包含 `.git`、虚拟环境、缓存、SQLite 数据库或知识库运行时 JSON。三部分各自使用 `app` Python 包，因此必须在各自服务目录启动，不能把三个 `app` 目录混放到同一个 Python 路径。

`scripts/start-demo.ps1` 在 Windows 上启动三个本机进程，生成会话签名密钥并初始化虚构 SQLite 种子数据。正式部署需要分别构建 B/C 服务，配置 HTTPS、受控跨域、持久化数据库与真实模型；演示密码和运行模式不得直接用于公网。
