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
```

临时 API 路径集中定义在 `src/services/api.js`。B、C 任务包确认 OpenAPI 后，只需在该适配器中调整路径和响应映射。API 不可用时，页面自动回退到演示数据并显示提示。

## 构建

```powershell
cd frontend
npm run build
```

构建产物位于 `dist/`。当前生产资源基路径为 `/forgepilot/`，用于腾讯云 CloudBase 子目录部署。

## 当前边界

- 页面默认使用虚构演示数据，不包含真实企业信息。
- 按钮、导航、筛选和状态反馈可用于演示，已具备统一 API 适配入口。
- 当前 API 路径是等待 B、C 契约评审的临时约定，不能视为最终接口。

