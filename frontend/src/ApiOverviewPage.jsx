import { Button } from "@fluentui/react-components";

export default function ApiOverviewPage({ navigate, devices, alerts, workOrders, error }) {
  const openAlerts = alerts.filter((item) => item.status !== "已关闭");
  const activeOrders = workOrders.filter((item) => !["已完成", "已取消"].includes(item.status));
  const healthValues = devices.map((item) => item.health).filter((value) => typeof value === "number");
  const averageHealth = healthValues.length ? (healthValues.reduce((sum, value) => sum + value, 0) / healthValues.length).toFixed(1) : "—";
  return <>
    <div className="page-heading"><div><h1>维护总览</h1><p>当前组织的设备、告警与工单</p></div><span className="tone-badge tone-success">服务器数据</span></div>
    {error && <p role="alert">{error}</p>}
    <div className="metric-strip"><div><span>设备</span><strong>{devices.length}</strong><small>台</small></div><div><span>平均健康度</span><strong>{averageHealth}</strong><small>{healthValues.length ? "/ 100" : "暂无测量"}</small></div><div><span>未关闭告警</span><strong>{openAlerts.length}</strong><small>项</small></div><div><span>未完成工单</span><strong>{activeOrders.length}</strong><small>项</small></div></div>
    <div className="dashboard-grid"><section className="panel task-panel"><div className="panel-title"><h2>待处理告警</h2><Button onClick={() => navigate("alerts")}>查看全部</Button></div>{openAlerts.slice(0, 5).map((item) => <button className="recent-item" key={item.id} onClick={() => navigate("alerts")}><strong>{item.title}</strong><small>{item.device} · {item.level} · {item.status}</small></button>)}{!openAlerts.length && <p>暂无待处理告警</p>}</section><section className="panel recent-panel"><div className="panel-title"><h2>待办工单</h2><Button onClick={() => navigate("orders")}>查看全部</Button></div>{activeOrders.slice(0, 5).map((item) => <button className="recent-item" key={item.id} onClick={() => navigate("orders")}><strong>{item.title}</strong><small>{item.deviceId} · {item.owner || "未指派"} · {item.status}</small></button>)}{!activeOrders.length && <p>暂无未完成工单</p>}</section></div>
  </>;
}
