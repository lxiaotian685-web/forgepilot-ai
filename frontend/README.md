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
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 构建

```powershell
cd frontend
npm run build
```

## 当前边界

- 页面使用虚构演示数据，不包含真实企业信息。
- 按钮、导航、筛选和状态反馈可用于演示，尚未接入后端 API。
- 下一阶段应先确定设备、告警、诊断、证据、工单的接口契约，再替换 `src/data.js` 中的演示数据。

