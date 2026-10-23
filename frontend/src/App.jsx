import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Badge,
  Button,
  Input,
  ProgressBar,
} from "@fluentui/react-components";
import {
  Add24Regular,
  Alert24Regular,
  ArrowSync24Regular,
  Board24Regular,
  BookOpen24Regular,
  Bot24Regular,
  Building24Regular,
  CheckmarkCircle24Regular,
  ChevronRight24Regular,
  ClipboardTask24Regular,
  Database24Regular,
  Dismiss24Regular,
  Filter24Regular,
  MoreHorizontal24Regular,
  Play24Regular,
  Pulse24Regular,
  PeopleTeam24Regular,
  Search24Regular,
  ShieldLock24Regular,
  SignOut24Regular,
  Wrench24Regular,
} from "@fluentui/react-icons";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import * as demoData from "./data";
import { loadWorkspaceData } from "./services/api";
import { authService, canAccessPage, getAllowedPageIds, roleLabels } from "./services/auth";
import DiagnosisPage from "./DiagnosisPage";

const navItems = [
  { id: "overview", label: "维护总览", icon: Board24Regular },
  { id: "devices", label: "设备中心", icon: Database24Regular },
  { id: "alerts", label: "告警中心", icon: Alert24Regular, count: 3 },
  { id: "diagnosis", label: "诊断工作台", icon: Pulse24Regular },
  { id: "knowledge", label: "知识证据", icon: BookOpen24Regular },
  { id: "orders", label: "维护工单", icon: ClipboardTask24Regular, count: 5 },
  { id: "audit", label: "审计记录", icon: ShieldLock24Regular },
  { id: "people", label: "人员与权限", icon: PeopleTeam24Regular },
];

const dataMode = import.meta.env.VITE_DATA_MODE || "mock";

function createDemoSession(role) {
  return {
    accessToken: "local-preview-only",
    tokenType: "Preview",
    expiresIn: 0,
    user: { id: `preview-${role}`, email: `${role}@preview.local`, displayName: "演示用户" },
    organization: { id: "preview-org", code: "preview", name: "一号装配厂（演示）" },
    role,
    isPreview: true,
  };
}

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationCode, setOrganizationCode] = useState("");
  const [previewRole, setPreviewRole] = useState("manager");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const previewMode = dataMode !== "api";

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      onLogin(await authService.login({ email, password, organizationCode }));
    } catch (loginError) {
      setError(loginError.message || "登录失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-intro">
        <span className="login-kicker">FORGEPILOT · INDUSTRIAL OPERATIONS</span>
        <h1>制造领航</h1>
        <p>面向设备诊断与维修闭环的工业协同工作台。</p>
        <div className="login-safety"><ShieldLock24Regular /><span><strong>按组织与岗位授权</strong><small>登录后只显示当前角色允许访问的模块。</small></span></div>
      </section>
      <section className="login-card">
        <div><small>ACCOUNT ACCESS</small><h2>登录工作台</h2><p>使用企业账号进入所属工厂。</p></div>
        {previewMode ? (
          <div className="preview-login">
            <ToneBadge tone="warning">本地演示模式</ToneBadge>
            <p>当前未连接身份服务。可选择角色检查界面权限；该入口不代表真实认证。</p>
            <label>演示角色<select value={previewRole} onChange={(event) => setPreviewRole(event.target.value)}>{["owner", "admin", "manager", "technician", "viewer"].map((role) => <option key={role} value={role}>{roleLabels[role]}</option>)}</select></label>
            <Button appearance="primary" onClick={() => onLogin(createDemoSession(previewRole))}>进入权限演示</Button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <label>企业邮箱<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></label>
            <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
            <label>组织代码（选填）<input value={organizationCode} onChange={(event) => setOrganizationCode(event.target.value)} autoComplete="organization" /></label>
            {error && <p className="login-error" role="alert">{error}</p>}
            <Button appearance="primary" type="submit" disabled={submitting}>{submitting ? "正在验证…" : "登录"}</Button>
          </form>
        )}
        <small className="login-footnote">请勿在演示环境录入真实生产秘密或个人敏感信息。</small>
      </section>
    </main>
  );
}

function ToneBadge({ children, tone = "neutral" }) {
  return <span className={`tone-badge tone-${tone}`}>{children}</span>;
}

function PageHeader({ title, description, action, onAction }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && (
        <Button appearance="primary" icon={<Add24Regular />} onClick={onAction}>
          {action}
        </Button>
      )}
    </header>
  );
}

function Toolbar({ placeholder = "搜索设备、工单或记录", children }) {
  return (
    <div className="toolbar">
      <Input className="search-input" contentBefore={<Search24Regular />} placeholder={placeholder} />
      {children}
      <Button icon={<Filter24Regular />}>筛选</Button>
      <Button icon={<ArrowSync24Regular />}>刷新</Button>
    </div>
  );
}

function TrendChart({ data, compact = false }) {
  return (
    <div className={compact ? "chart chart-compact" : "chart"} aria-label="AC-07 振动与温度趋势图">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 18, left: compact ? -18 : 0, bottom: 0 }}>
          <CartesianGrid stroke="#dbe4ef" strokeDasharray="3 4" vertical={false} />
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#687386" }} axisLine={false} tickLine={false} />
          <YAxis yAxisId="left" domain={[2, 9]} tick={{ fontSize: 11, fill: "#687386" }} axisLine={false} tickLine={false} />
          <YAxis yAxisId="right" orientation="right" domain={[60, 100]} hide={compact} tick={{ fontSize: 11, fill: "#687386" }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ border: "1px solid #cbd6e4", borderRadius: 6, fontSize: 12 }} />
          {!compact && <Legend verticalAlign="top" align="left" height={32} />}
          <ReferenceLine yAxisId="left" y={4.5} stroke="#c4312e" strokeDasharray="5 4" label={{ value: "警戒 4.5", fill: "#a4262c", fontSize: 11 }} />
          <Line isAnimationActive={false} yAxisId="left" name="驱动端振动 mm/s" type="monotone" dataKey="vibration" stroke="#0f5a91" strokeWidth={3} dot={false} activeDot={{ r: 5 }} />
          {!compact && <Line isAnimationActive={false} yAxisId="right" name="排气温度 °C" type="monotone" dataKey="temperature" stroke="#d45522" strokeWidth={2} dot={false} />}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function OverviewPage({ navigate, workOrders, trendData }) {
  return (
    <>
      <PageHeader title="维护总览" description="一号装配厂设备健康、告警与工单处置概况" action="发起诊断" onAction={() => navigate("diagnosis")} />
      <div className="metric-strip">
        <div><span>设备健康度</span><strong>91.4</strong><small>/ 100</small></div>
        <div><span>待确认告警</span><strong className="text-danger">3</strong><small>项</small></div>
        <div><span>进行中工单</span><strong>5</strong><small>项</small></div>
        <div><span>今日诊断</span><strong>3</strong><small>次</small></div>
      </div>
      <div className="dashboard-grid">
        <section className="panel task-panel">
          <div className="panel-title"><div><Alert24Regular /><h2>待处理事项</h2></div><Button appearance="subtle" onClick={() => navigate("alerts")}>查看全部</Button></div>
          <div className="task-row task-critical">
            <ToneBadge tone="danger">一级紧急</ToneBadge>
            <div className="task-copy"><strong>AC-07 驱动端振动持续超限</strong><span>已持续 44 分钟，当前值 7.82 mm/s</span></div>
            <Button appearance="primary" onClick={() => navigate("alerts")}>处理告警</Button>
          </div>
          <div className="task-row task-warning">
            <ToneBadge tone="warning">待人工确认</ToneBadge>
            <div className="task-copy"><strong>P-102 气蚀风险诊断待复核</strong><span>AI 结论置信度 84%，需主管确认</span></div>
            <Button onClick={() => navigate("diagnosis")}>进入诊断</Button>
          </div>
          <div className="task-row">
            <ToneBadge>即将逾期</ToneBadge>
            <div className="task-copy"><strong>WO-20250518-02 密封检查</strong><span>距离计划完成还剩 35 分钟</span></div>
            <Button onClick={() => navigate("orders")}>查看工单</Button>
          </div>
        </section>
        <section className="panel health-panel">
          <div className="panel-title"><div><CheckmarkCircle24Regular /><h2>设备健康概览</h2></div><ToneBadge tone="success">48 台在线</ToneBadge></div>
          <div className="health-score"><strong>91.4</strong><span>整体健康度</span></div>
          <ProgressBar value={0.914} thickness="large" color="success" />
          <div className="health-legend"><span><i className="good" />良好 41</span><span><i className="watch" />关注 4</span><span><i className="bad" />异常 3</span></div>
        </section>
        <section className="panel trend-panel">
          <div className="panel-title"><div><Board24Regular /><h2>AC-07 设备健康趋势</h2></div><div className="segmented"><button className="active">近 2 小时</button><button>近 7 天</button><button>近 30 天</button></div></div>
          <p className="panel-note">08:58 开始持续超限，振动峰值 7.82 mm/s</p>
          <TrendChart data={trendData} />
        </section>
        <section className="panel recent-panel">
          <div className="panel-title"><div><Pulse24Regular /><h2>最近诊断</h2></div></div>
          {["AC-07 轴承早期疲劳剥落", "P-102 动静环轻度气蚀", "R-03 润滑油黏度劣化"].map((item, index) => (
            <button className="recent-item" key={item} onClick={() => navigate("diagnosis")}>
              <span className={`severity severity-${index + 1}`} />
              <span><strong>{item}</strong><small>{index === 0 ? "置信度 91.4% · 28 分钟前" : `${index + 1} 小时前`}</small></span>
              <ChevronRight24Regular />
            </button>
          ))}
        </section>
      </div>
      <section className="panel table-panel">
        <div className="panel-title"><div><ClipboardTask24Regular /><h2>进行中工单</h2></div><Button appearance="subtle" onClick={() => navigate("orders")}>查看全部</Button></div>
        <OrderTable rows={workOrders.slice(0, 3)} onSelect={() => navigate("orders")} />
      </section>
    </>
  );
}

function DevicePage({ navigate, devices, trendData }) {
  const [selected, setSelected] = useState(devices[0]);
  return (
    <>
      <PageHeader title="设备中心" description="统一查看设备身份、健康状态和维护上下文" action="录入设备" />
      <Toolbar placeholder="搜索设备编号、名称、型号或位置">
        <select aria-label="厂区"><option>一号装配厂</option></select>
        <select aria-label="健康状态"><option>全部状态</option><option>需关注</option><option>运行正常</option></select>
      </Toolbar>
      <div className="split-layout">
        <section className="panel table-panel grow">
          <table className="data-table">
            <thead><tr><th>设备编号</th><th>设备名称</th><th>类型</th><th>所属位置</th><th>健康状态</th><th>告警</th></tr></thead>
            <tbody>{devices.map((device) => (
              <tr key={device.id} className={selected.id === device.id ? "selected" : ""} onClick={() => setSelected(device)}>
                <td><strong>{device.id}</strong></td><td><strong>{device.name}</strong></td><td>{device.type}</td><td>{device.location}</td>
                <td><ToneBadge tone={device.health < 60 ? "danger" : device.health < 90 ? "warning" : "success"}>{device.state} {device.health}</ToneBadge></td>
                <td>{device.alert || "无"}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
        <aside className="panel detail-drawer">
          <div className="drawer-heading"><div><small>设备实时摘要</small><h2>{selected.id} {selected.name}</h2></div><Button appearance="subtle" icon={<Dismiss24Regular />} aria-label="关闭预览" /></div>
          <div className="equipment-identity"><span>{selected.type}</span><strong>{selected.location}</strong></div>
          <div className="health-callout"><span>综合健康评分</span><strong>{selected.health}/100</strong></div>
          <h3>关键运行指标</h3>
          <div className="sensor-list">
            <div><span>驱动端振动 RMS</span><strong className="text-danger">7.82 mm/s</strong><small>警戒 4.50 mm/s</small></div>
            <div><span>排气温度</span><strong>88.5 °C</strong><small>预警 85.0 °C</small></div>
            <div><span>润滑油压差</span><strong>0.28 MPa</strong><small>正常范围</small></div>
          </div>
          <TrendChart data={trendData} compact />
          <Button appearance="primary" icon={<Play24Regular />} onClick={() => navigate("diagnosis")}>发起诊断</Button>
        </aside>
      </div>
    </>
  );
}

function AlertsPage({ navigate, notify, alerts, trendData }) {
  const [selected, setSelected] = useState(alerts[0]);
  return (
    <>
      <PageHeader title="告警中心" description="确认、指派并追踪设备异常处置过程" />
      <div className="status-tabs"><button className="active">全部 24</button><button>待确认 3</button><button>处理中 5</button><button>已关闭 16</button></div>
      <Toolbar placeholder="搜索告警编号、设备或规则"><select><option>全部等级</option></select><select><option>全部设备</option></select></Toolbar>
      <div className="split-layout alerts-layout">
        <section className="panel alert-list">
          {alerts.map((alert) => (
            <button key={alert.id} className={`alert-item ${selected.id === alert.id ? "selected" : ""}`} onClick={() => setSelected(alert)}>
              <span className={alert.level.includes("一级") ? "alert-bar critical" : "alert-bar warning"} />
              <span className="alert-copy"><span><ToneBadge tone={alert.level.includes("一级") ? "danger" : "warning"}>{alert.level}</ToneBadge><small>{alert.time}</small></span><strong>{alert.title}</strong><em>{alert.device}</em><span><small>负责人：{alert.owner}</small><small>{alert.status}</small></span></span>
            </button>
          ))}
        </section>
        <section className="panel alert-detail">
          <div className="detail-kicker"><ToneBadge tone="danger">{selected.level}</ToneBadge><span>{selected.id}</span></div>
          <h2>{selected.title}</h2>
          <p>{selected.device}</p>
          <div className="action-row">
            <Button appearance="primary" onClick={() => notify("告警已确认，并记录当前操作人和时间")}>确认告警</Button>
            <Button onClick={() => notify("已指派给张工")}>指派处理</Button>
            <Button icon={<MoreHorizontal24Regular />} aria-label="更多操作" />
          </div>
          <div className="reading-grid"><div><span>当前值</span><strong className="text-danger">7.82 mm/s</strong></div><div><span>告警阈值</span><strong>4.50 mm/s</strong></div><div><span>采样频率</span><strong>1,000 Hz</strong></div><div><span>特征频率</span><strong>148.5 Hz</strong></div></div>
          <TrendChart data={trendData} compact />
          <div className="context-note"><strong>规则来源</strong><span>Rule #VIB-RMS-004，连续 3 个采样周期超过 ISO 4.5 mm/s 阈值。</span></div>
          <Button appearance="primary" icon={<Pulse24Regular />} onClick={() => navigate("diagnosis")}>进入诊断工作台</Button>
        </section>
      </div>
    </>
  );
}


function KnowledgePage({ notify, evidence }) {
  const [selected, setSelected] = useState(evidence[0]);
  return <><PageHeader title="知识证据" description="管理说明书、检修规程、行业标准和诊断引用" action="上传文档" onAction={() => notify("上传入口将在文档接口完成后接入")} /><Toolbar placeholder="搜索文档标题、章节或适用设备"><select><option>全部文档类型</option></select><select><option>全部解析状态</option></select></Toolbar><div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>文档标题</th><th>类型</th><th>版本</th><th>适用设备</th><th>来源</th><th>解析状态</th></tr></thead><tbody>{evidence.map((item) => <tr key={item.name} className={selected.name === item.name ? "selected" : ""} onClick={() => setSelected(item)}><td><strong>{item.name}</strong><small>{item.chunks} 个切片</small></td><td>{item.type}</td><td>{item.version}</td><td>{item.device}</td><td>{item.source}</td><td><ToneBadge tone={item.state === "可用" ? "success" : "warning"}>{item.state}</ToneBadge></td></tr>)}</tbody></table></section><aside className="panel document-preview"><div className="drawer-heading"><div><small>当前文档</small><h2>{selected.name}</h2></div><ToneBadge tone="success">ACTIVE</ToneBadge></div><div className="document-meta"><div><span>版本</span><strong>{selected.version}</strong></div><div><span>切片数量</span><strong>{selected.chunks}</strong></div><div><span>适用设备</span><strong>{selected.device}</strong></div></div><h3>命中证据预览</h3><blockquote>当驱动端轴承实测振动速度有效值超过 4.5 mm/s，或检测到 BPFO 特征频率出现周期性谱线尖峰时，应在 48 小时内执行降载或停机检查。</blockquote><div className="action-row"><Button appearance="primary">打开原文</Button><Button>查看引用记录</Button></div></aside></div></>;
}

function OrderTable({ rows, onSelect }) {
  return <table className="data-table"><thead><tr><th>工单号</th><th>标题</th><th>优先级</th><th>负责人</th><th>状态</th><th>更新</th></tr></thead><tbody>{rows.map((order) => <tr key={order.id} onClick={() => onSelect?.(order)}><td><strong>{order.id}</strong></td><td>{order.title}</td><td><ToneBadge tone={order.priority.includes("P1") ? "danger" : "neutral"}>{order.priority}</ToneBadge></td><td>{order.owner}</td><td>{order.status}</td><td>{order.updated}</td></tr>)}</tbody></table>;
}

function OrdersPage({ notify, workOrders }) {
  const [selected, setSelected] = useState(workOrders[0]);
  return <><PageHeader title="维护工单" description="管理诊断转单、现场执行、计时与验收闭环" action="创建工单" onAction={() => notify("工单草稿已创建")} /><div className="status-tabs"><button className="active">列表视图</button><button>看板视图</button><button>日历排程</button></div><Toolbar placeholder="搜索工单号、标题、设备或负责人"><select><option>全部状态</option></select><select><option>全部优先级</option></select></Toolbar><div className="split-layout orders-layout"><section className="panel order-list">{workOrders.map((order) => <button key={order.id} className={`order-card ${selected.id === order.id ? "selected" : ""}`} onClick={() => setSelected(order)}><span><strong>{order.id}</strong><ToneBadge tone={order.priority.includes("P1") ? "danger" : "neutral"}>{order.priority}</ToneBadge></span><h3>{order.title}</h3><small>{order.owner} · {order.status} · {order.updated}</small></button>)}</section><section className="panel order-detail"><div className="drawer-heading"><div><small>{selected.id}</small><h2>{selected.title}</h2></div><Button appearance="primary" onClick={() => notify("工单已提交验收")}>提交验收</Button></div><div className="order-meta"><div><span>负责人</span><strong>{selected.owner}</strong></div><div><span>目标设备</span><strong>AC-07 · Bay03</strong></div><div><span>计划窗口</span><strong>今日 09:30 至 12:00</strong></div></div><div className="timer"><span>现场维保执行计时中</span><strong>01:42:21</strong><ProgressBar value={0.68} /></div><h3>标准化现场检修规程</h3><div className="checklist">{["停机电气闭锁挂牌", "拆卸防护罩并检查轴承", "提取废润滑脂样本", "更换 SKF-6312 轴承", "加注润滑脂并复核振动"].map((step, index) => <label key={step} className={index < 3 ? "checked" : ""}><input type="checkbox" defaultChecked={index < 3} /> <span><strong>步骤 {index + 1}：{step}</strong><small>{index < 3 ? "已由张工确认" : "等待执行"}</small></span></label>)}</div></section></div></>;
}

function AuditPage({ auditRows }) {
  const [selected, setSelected] = useState(auditRows[0]);
  return <><PageHeader title="审计记录" description="只读、可验证的业务操作与人工决策轨迹" /><div className="metric-strip audit-metrics"><div><span>今日入库记录</span><strong>1,842</strong><small>条</small></div><div><span>签名校验通过率</span><strong className="text-success">100%</strong></div><div><span>被拦截越权操作</span><strong className="text-danger">1</strong><small>起</small></div></div><Toolbar placeholder="搜索请求号、业务对象或操作者"><select><option>全部操作者</option></select><select><option>全部动作</option></select></Toolbar><div className="split-layout"><section className="panel table-panel grow"><table className="data-table"><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>业务对象</th><th>结果</th></tr></thead><tbody>{auditRows.map((row) => <tr key={`${row.time}-${row.action}`} className={selected.time === row.time ? "selected" : ""} onClick={() => setSelected(row)}><td>{row.time}</td><td>{row.user}</td><td><ToneBadge>{row.action}</ToneBadge></td><td>{row.object}</td><td><ToneBadge tone="success">{row.result}</ToneBadge></td></tr>)}</tbody></table></section><aside className="panel audit-detail"><div className="panel-title"><div><ShieldLock24Regular /><h2>审计凭证详情</h2></div><ToneBadge tone="success">签名有效</ToneBadge></div><div className="audit-section"><span>操作人</span><strong>{selected.user}</strong><small>维护主管 · ENG-0819</small></div><div className="audit-section"><span>动作说明</span><strong>{selected.action}</strong><p>操作已写入只读审计流水，并关联业务对象 {selected.object}。</p></div><div className="before-after"><div><span>变更前</span><strong>待人工确认</strong></div><div><span>变更后</span><strong>处理中</strong></div></div><code>REQ-20250518-0944-8812<br />SHA-256: e3b0c44298fc1c149afbf4c8996fb924</code></aside></div></>;
}

function PeoplePage({ session }) {
  const roleRows = ["owner", "admin", "manager", "technician", "viewer"];
  return <><PageHeader title="人员与权限" description="核对当前组织身份与各岗位可见范围；成员增删改将在人员接口交付后开放" /><div className="identity-strip"><div><span>当前人员</span><strong>{session.user.displayName}</strong><small>{session.user.email}</small></div><div><span>所属组织</span><strong>{session.organization.name}</strong><small>{session.organization.code}</small></div><div><span>当前岗位</span><strong>{roleLabels[session.role]}</strong><small>{session.role}</small></div></div><section className="panel people-panel"><div className="panel-title"><div><PeopleTeam24Regular /><h2>岗位权限基线</h2></div><ToneBadge tone="warning">待人员接口联调</ToneBadge></div><div className="people-notice"><strong>为什么现在不能新增人员？</strong><span>后端当前只提供登录身份和角色，尚未提供组织成员列表、邀请、停用和改岗接口。这里不使用虚构成员数据；接口交付后再接入真实人员管理。</span></div><table className="data-table permission-table"><thead><tr><th>岗位</th><th>可访问模块</th><th>人员管理</th></tr></thead><tbody>{roleRows.map((role) => <tr key={role}><td><strong>{roleLabels[role]}</strong><small>{role}</small></td><td>{getAllowedPageIds(role).filter((page) => page !== "people").map((page) => navItems.find((item) => item.id === page)?.label).join("、")}</td><td>{canAccessPage(role, "people") ? <ToneBadge tone="success">可查看</ToneBadge> : <ToneBadge>不可见</ToneBadge>}</td></tr>)}</tbody></table></section></>;
}

function WorkspaceApp({ session, onLogout }) {
  const [activePage, setActivePage] = useState("overview");
  const [toast, setToast] = useState("");
  const [workspaceData, setWorkspaceData] = useState(demoData);
  const [dataSource, setDataSource] = useState("mock");
  const [connectedResources, setConnectedResources] = useState([]);
  const allowedNavItems = useMemo(() => navItems.filter((item) => canAccessPage(session.role, item.id)), [session.role]);
  const activeNav = useMemo(() => allowedNavItems.find((item) => item.id === activePage), [activePage, allowedNavItems]);
  const notify = (message) => { setToast(message); window.setTimeout(() => setToast(""), 2600); };
  const navigate = (pageId) => {
    if (canAccessPage(session.role, pageId)) setActivePage(pageId);
    else notify("当前岗位没有访问该模块的权限");
  };

  useEffect(() => {
    let active = true;
    loadWorkspaceData({ accessToken: session.isPreview ? undefined : session.accessToken }).then(({ data, source, connectedResources: connected }) => {
      if (!active) return;
      setWorkspaceData(data);
      setDataSource(source);
      setConnectedResources(connected);
      if (source === "fallback") notify("业务接口暂不可用，已切换为演示数据");
      if (source === "hybrid") notify("设备、告警和工单已按可用接口接入，其他模块保留演示数据");
    }).catch((error) => {
      if (error.status === 401 || error.status === 403) onLogout("登录已过期或权限已变更，请重新登录");
      else notify("业务接口暂不可用，请稍后重试");
    });
    return () => { active = false; };
  }, [session.accessToken, session.isPreview]);

  const { alerts, auditRows, devices, evidence, trendData, workOrders } = workspaceData;
  const pages = {
    overview: <OverviewPage navigate={navigate} workOrders={workOrders} trendData={trendData} />,
    devices: <DevicePage navigate={navigate} devices={devices} trendData={trendData} />,
    alerts: <AlertsPage navigate={navigate} notify={notify} alerts={alerts} trendData={trendData} />,
    diagnosis: <DiagnosisPage devices={devices} />,
    knowledge: <KnowledgePage notify={notify} evidence={evidence} />,
    orders: <OrdersPage notify={notify} workOrders={workOrders} />,
    audit: <AuditPage auditRows={auditRows} />,
    people: <PeoplePage session={session} />,
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wrench24Regular /></span><span><strong>制造领航</strong><small>ForgePilot</small></span></div>
        <nav aria-label="主导航">{allowedNavItems.map((item) => { const Icon = item.icon; return <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => navigate(item.id)}><Icon /><span>{item.label}</span>{item.count ? <em>{item.count}</em> : null}</button>; })}</nav>
        <div className="sidebar-foot"><span>比赛演示环境</span><small>请勿录入真实敏感数据</small></div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <button className="plant-select"><Building24Regular /><span>{session.organization.name}</span><small>{session.organization.code}</small></button>
          <div className="breadcrumb">运行中心 / <strong>{activeNav?.label}</strong></div>
          <div className="top-actions"><span className="sync-state"><i />系统运行正常</span><Badge appearance="tint" title={connectedResources.length ? `已连接：${connectedResources.join(", ")}` : "当前使用内置演示数据"}>{dataSource === "hybrid" ? "业务 API + 演示" : "演示数据"}</Badge><Button appearance="subtle" icon={<Alert24Regular />} aria-label="通知" /><Avatar name={session.user.displayName} color="colorful" /><span className="user-name"><strong>{session.user.displayName}</strong><small>{roleLabels[session.role]}</small></span><Button appearance="subtle" icon={<SignOut24Regular />} onClick={() => onLogout()} aria-label="退出登录">退出</Button></div>
        </header>
        <main className="page-content">{pages[activePage]}</main>
        <footer className="app-footer"><span>ForgePilot 工业设备维护工作台</span><span>数据延迟 12ms · 自动刷新</span></footer>
      </div>
      {toast && <div className="toast" role="status"><CheckmarkCircle24Regular />{toast}</div>}
    </div>
  );
}

function App() {
  const [session, setSession] = useState(() => authService.getStoredSession());
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!session || session.isPreview) return;
    let active = true;
    authService.refresh(session).then((value) => { if (active) setSession(value); }).catch((error) => {
      if (!active) return;
      authService.clear();
      setSession(null);
      setMessage(error.message || "登录状态已失效");
    });
    return () => { active = false; };
  }, []);

  const logout = (reason = "") => {
    authService.clear();
    setSession(null);
    setMessage(reason);
  };

  if (!session) return <><LoginPage onLogin={(value) => { setMessage(""); setSession(value); }} />{message && <div className="toast" role="status"><Alert24Regular />{message}</div>}</>;
  return <WorkspaceApp session={session} onLogout={logout} />;
}

export default App;
