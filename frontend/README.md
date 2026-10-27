# ForgePilot 前端

React + Vite 工作台。完整架构、安装与联调步骤见仓库根目录 `README.md`。

开发预览：在本目录执行 `npm ci` 和 `npm run dev`。默认 `VITE_DATA_MODE=mock`，只显示明确标记的虚构样例；按根目录 `scripts/start-demo.ps1` 启动时自动切换为 API 模式并连接 B/C 服务。

验证：`npm test`（74 项）与 `npm run build`。Vite 资源基路径为 `/forgepilot/`。模型密钥只能配置在 C 后端，不得放进 `VITE_` 环境变量。
