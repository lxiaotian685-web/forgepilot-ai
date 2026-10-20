# ForgePilot Frontend

制造领航 ForgePilot 的 React Web 工作台。当前版本完成第一阶段 UI 基础，包括应用壳层、演示数据和七个可切换业务工作区。

## 已实现页面

- 维护总览
- 设备中心
- 告警中心
- 诊断工作台
- 知识证据
- 维护工单
- 审计记录

## 技术栈

- React 18
- Vite 7
- Fluent UI React v9
- Fluent System Icons
- Recharts

## 本地运行

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

打开 `http://127.0.0.1:5173`。

默认使用 `src/data.js` 中的脱敏演示数据，不需要后端即可运行。

## 接入业务 API

在 `.env.local` 中配置：

```env
VITE_DATA_MODE=api
VITE_API_BASE_URL=http://localhost:8000
VITE_API_ORGANIZATION_ID=demo-org
VITE_API_USER_ID=demo@example.com
```

API 路径和响应转换集中定义在 `src/services/api.js`。当前已按 B 包 OpenAPI 接入设备、告警和工单分页接口；知识证据、审计记录和趋势数据等待 C/B 后续接口，继续明确使用演示数据。某个业务接口不可用时，只回退对应模块，不会让已经可用的接口一起失效。

## 构建

```powershell
cd frontend
npm run build
```

构建产物位于 `dist/`。当前生产资源基路径为 `/forgepilot/`，用于腾讯云 CloudBase 子目录部署。

## 当前边界

### 诊断证据工作台

`npm test` 验证诊断适配器；`npm run build` 检查生产构建。

诊断页已按 C 包 `/api/v1/chat` 接入，支持文档陈述、模型推断、待验证项与证据片段切换。
当前旧契约用 `《标题》第N页` 匹配引用，无法唯一匹配时明确显示未匹配，不猜测来源。
服务端未提供文档版本和原文 URL，页面不编造，也不声称展示全文。

- `VITE_DATA_MODE=mock`：只展示固定界面样例，明确提示没有分析输入或调用模型。
- `VITE_DATA_MODE=api`：POST 到 `VITE_DIAGNOSIS_API_BASE_URL`，留空时使用 `VITE_API_BASE_URL`。接口失败显示错误，不悄悄回退为成功诊断。
- 服务器的 `is_mock=true` 始终标为模拟或降级；`false` 仅显示为服务端标记的真实模型，仍需人工核验。
- 支持取消与 30 秒超时；重新输入、换设备后清除旧结论，避免把旧诊断绑定到新设备。
- 工单生成目前禁用，等待 B 的诊断保存与确认接口。结果不持久化，不能声称已完成端到端闭环。

本地可分开启动 B 与 C 服务并分别配置 URL；浏览器跨域需要服务端 CORS 或同源代理。
不得把模型密钥放入任何 `VITE_` 环境变量。生产认证与公开写入保护需 B 包完成后再开放。

- 页面默认使用虚构演示数据，不包含真实企业信息。
- 按钮、导航、筛选和状态反馈可用于演示，已具备统一 API 适配入口。
- 设备、告警和工单路径已对齐 B 包第一版 OpenAPI；知识证据、审计记录和趋势路径仍待后续契约。

