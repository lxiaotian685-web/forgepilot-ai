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
  Search24Regular,
  ShieldLock24Regular,
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

const navItems = [
  { id: "overview", label: "维护总览", icon: Board24Regular },
  { id: "devices", label: "设备中心", icon: Database24Regular },
  { id: "alerts", label: "告警中心", icon: Alert24Regular, count: 3 },
  { id: "diagnosis", label: "诊断工作台", icon: Bot24Regular },
  { id: "knowledge", label: "知识证据", icon: BookOpen24Regular },
  { id: "orders", label: "维护工单", icon: ClipboardTask24Regular, count: 5 },
  { id: "audit", label: "审计记录", icon: ShieldLock24Regular },
];

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
          <div className="panel-title"><div><Bot24Regular /><h2>最近诊断</h2></div></div>
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
          <Button appearance="primary" icon={<Bot24Regular />} onClick={() => navigate("diagnosis")}>进入诊断工作台</Button>
        </section>
      </div>
    </>
  );
}

function DiagnosisPage({ notify, navigate, evidence }) {
  const [running, setRunning] = useState(false);
  return (
    <>
      <PageHeader title="诊断工作台" description="DIAG-20250518-0941 · AC-07 驱动端振动异常" />
      <div className="diagnosis-layout">
        <aside className="panel diagnosis-input">
          <div className="panel-title"><div><Database24Regular /><h2>诊断输入</h2></div></div>
          <label>目标设备<input value="AC-07 螺杆空气压缩机" readOnly /></label>
          <label>关联告警<input value="ALT-0941 振动持续超限" readOnly /></label>
          <label>现场现象<textarea defaultValue="现场巡检发现驱动端异响，振动在慢升速过程中明显加剧。" /></label>
          <div className="tag-list"><ToneBadge>高频振动</ToneBadge><ToneBadge>轴承异响</ToneBadge><ToneBadge>温升</ToneBadge></div>
          <Button onClick={() => notify("诊断草稿已保存")}>保存草稿</Button>
        </aside>
        <main className="diagnosis-main">
          <section className="conflict-banner"><Alert24Regular /><div><strong>参数版本冲突，需人工核验</strong><span>设备数据库为 0.80 MPa，说明书 RevC 为 0.75 MPa。</span></div><Button onClick={() => notify("已记录采用设备铭牌数据")}>核对来源</Button></section>
          <section className="panel">
            <div className="panel-title"><div><Bot24Regular /><h2>Agent 执行步骤</h2></div><Button appearance="primary" icon={<Play24Regular />} onClick={() => { setRunning(true); notify("诊断流程已启动"); }}>{running ? "诊断运行中" : "开始诊断"}</Button></div>
            <div className="stepper">
              {["读取设备事实与告警事件", "检索技术说明书与行业标准", "核对数据库参数和文档版本", "生成候选故障原因", "推荐现场检查步骤"].map((step, index) => (
                <div className="step" key={step}><span className={index < 2 || running ? "done" : ""}>{index < 2 || running ? "✓" : index + 1}</span><div><strong>{step}</strong><small>{index < 2 ? "已完成，工具结果可展开查看" : running ? "处理中" : "等待执行"}</small></div></div>
              ))}
            </div>
          </section>
          <section className="panel diagnosis-result">
            <div className="result-heading"><div><ToneBadge tone="danger">高风险</ToneBadge><h2>轴承外圈早期疲劳剥落</h2></div><strong>91.4%</strong></div>
            <p>振动包络谱出现 148.5 Hz 特征频率，结合 SKF-6312 外圈故障频率与温升趋势，建议安排降载并在 48 小时内停机检查。</p>
            <div className="evidence-columns"><div><h3>支持证据</h3><ul><li>BPFO 特征频率稳定出现</li><li>振动峰值超过阈值 73.7%</li><li>驱动端温度持续上升</li></ul></div><div><h3>排除项</h3><ul><li>排气压力仍在正常范围</li><li>电机电流无显著波动</li></ul></div></div>
            <div className="confirm-box"><strong>人工确认</strong><label><input type="radio" name="decision" defaultChecked /> 确认当前结论并生成维护工单</label><label><input type="radio" name="decision" /> 退回补充现场信息</label><Button appearance="primary" onClick={() => navigate("orders")}>生成维护工单</Button></div>
          </section>
        </main>
        <aside className="panel evidence-rail">
          <div className="panel-title"><div><BookOpen24Regular /><h2>证据与引用</h2></div><Badge appearance="filled">3</Badge></div>
          {evidence.slice(0, 3).map((item, index) => <div className="evidence-card" key={item.name}><div><ToneBadge tone={index === 0 ? "success" : "neutral"}>{index === 0 ? "已采纳" : "候选"}</ToneBadge><strong>{94.6 - index * 5.4}%</strong></div><h3>{item.name}</h3><p>{index === 0 ? "第 6.3 节，第 42 页：轴承振动评定与停机检查限值。" : "与当前设备和告警参数相关的标准片段。"}</p><Button appearance="subtle">查看原文</Button></div>)}
        </aside>
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

function App() {
  const [activePage, setActivePage] = useState("overview");
  const [toast, setToast] = useState("");
  const [workspaceData, setWorkspaceData] = useState(demoData);
  const [dataSource, setDataSource] = useState("mock");
  const activeNav = useMemo(() => navItems.find((item) => item.id === activePage), [activePage]);
  const notify = (message) => { setToast(message); window.setTimeout(() => setToast(""), 2600); };

  useEffect(() => {
    let active = true;
    loadWorkspaceData().then(({ data, source }) => {
      if (!active) return;
      setWorkspaceData(data);
      setDataSource(source);
      if (source === "fallback") notify("业务接口暂不可用，已切换为演示数据");
    });
    return () => { active = false; };
  }, []);

  const { alerts, auditRows, devices, evidence, trendData, workOrders } = workspaceData;
  const pages = {
    overview: <OverviewPage navigate={setActivePage} workOrders={workOrders} trendData={trendData} />,
    devices: <DevicePage navigate={setActivePage} devices={devices} trendData={trendData} />,
    alerts: <AlertsPage navigate={setActivePage} notify={notify} alerts={alerts} trendData={trendData} />,
    diagnosis: <DiagnosisPage navigate={setActivePage} notify={notify} evidence={evidence} />,
    knowledge: <KnowledgePage notify={notify} evidence={evidence} />,
    orders: <OrdersPage notify={notify} workOrders={workOrders} />,
    audit: <AuditPage auditRows={auditRows} />,
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wrench24Regular /></span><span><strong>制造领航</strong><small>ForgePilot</small></span></div>
        <nav aria-label="主导航">{navItems.map((item) => { const Icon = item.icon; return <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => setActivePage(item.id)}><Icon /><span>{item.label}</span>{item.count ? <em>{item.count}</em> : null}</button>; })}</nav>
        <div className="sidebar-foot"><span>比赛演示环境</span><small>请勿录入真实敏感数据</small></div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <button className="plant-select"><Building24Regular /><span>一号装配厂</span><small>Plant #1</small></button>
          <div className="breadcrumb">运行中心 / <strong>{activeNav?.label}</strong></div>
          <div className="top-actions"><span className="sync-state"><i />系统运行正常</span><Badge appearance="tint">{dataSource === "api" ? "API 数据" : "演示数据"}</Badge><Button appearance="subtle" icon={<Alert24Regular />} aria-label="通知" /><Avatar name="李振华" color="colorful" /><span className="user-name"><strong>李振华</strong><small>维护主管</small></span></div>
        </header>
        <main className="page-content">{pages[activePage]}</main>
        <footer className="app-footer"><span>ForgePilot 工业设备维护工作台</span><span>数据延迟 12ms · 自动刷新</span></footer>
      </div>
      {toast && <div className="toast" role="status"><CheckmarkCircle24Regular />{toast}</div>}
    </div>
  );
}

export default App;
