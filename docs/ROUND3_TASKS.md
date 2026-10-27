# ForgePilot 第三轮任务 2026-10-20

已完成模块开发不代表全系统可以验收。PR #10 最新 CI 已成功，并合并到 C 任务包分支。

| 负责人 | 本轮任务 | 任务分支 | PR 目标 |
| --- | --- | --- | --- |
| 林同学 | [#11 诊断持久化与人工确认建单](https://github.com/lxiaotian685-web/forgepilot-ai/issues/11) | task/b-diagnosis-persistence | feature/data-service-platform |
| 龚同学 | [#12 真实模型 有据诊断与联调](https://github.com/lxiaotian685-web/forgepilot-ai/issues/12) | task/c-grounded-diagnosis | feature/ai-agent-rag |
| 梁同学 | [#13 诊断接口与证据工作台](https://github.com/lxiaotian685-web/forgepilot-ai/issues/13) | task/a-evidence-workspace | feature/product-web-experience |

三个远端任务分支均已建立。先保存本地工作，再 `git fetch origin`；首次使用时 `git switch --track origin/<自己的任务分支>`，已有本地分支则 `git switch <自己的任务分支>`。不要覆盖未提交的工作，不要直接向 main 推送。

B 负责数据库、鉴权、业务接口和统一 app/main.py 挂载；C 负责 RAG 路由、模型适配器、证据与联调用例；A 负责页面与调用。新增 API 契约先写 docs/api-contracts，由三人确认，不能互相覆盖入口文件。integration/e2e-v1 尚未建立，待统一入口方案确认后再创建。

建议 10 月 22 日前对齐契约、24 日前交模块 PR、26 日前闭环验收，27 至 31 日测试部署与功能冻结。11 月 1 至 5 日完成比赛材料并提前提交；请各成员在 Issue 回复可完成日期。

本轮优先创新：结论与证据联动阅读、缺失证据清单；维修前后对照待合法数据具备再做。不把 MockLLM 或检索命中率当成真实诊断能力。

详细 Word 见 [本轮分工与联调方案](./ForgePilot-Round3-20261020.docx)。后续变动以 Issue 讨论为准。
