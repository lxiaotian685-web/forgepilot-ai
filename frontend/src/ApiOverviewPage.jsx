import { Button } from "@fluentui/react-components";
import { useState } from "react";
import { activeWorkOrders } from "./services/workOrderLifecycle.js";

export default function ApiOverviewPage({ navigate, devices, alerts, workOrders, error }) {
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const selectedDevice = devices.find((device) => device.id === selectedDeviceId) || devices[0];
  const openAlerts = alerts.filter((item) => item.status !== "已关闭");
  const activeOrders = activeWorkOrders(workOrders);
  const healthValues = devices.map((item) => item.health).filter((value) => typeof value === "number");
  const averageHealth = healthValues.length ? (healthValues.reduce((sum, value) => sum + value, 0) / healthValues.length).toFixed(1) : "—";
  return <>
    <div className="page-heading"><div><h1>维护总览</h1><p>当前组织的设备、告警与工单</p></div><span className="tone-badge tone-success">服务器数据</span></div>
    {error && <p role="alert">{error}</p>}
    <div className="metric-strip"><div><span>设备</span><strong>{devices.length}</strong><small>台</small></div><div><span>平均健康度</span><strong>{averageHealth}</strong><small>{healthValues.length ? "/ 100" : "暂无测量"}</small></div><div><span>未关闭告警</span><strong>{openAlerts.length}</strong><small>项</small></div><div><span>未完成工单</span><strong>{activeOrders.length}</strong><small>项</small></div></div>
    <div className="dashboard-grid"><section className="panel task-panel"><div className="panel-title"><h2>待处理告警</h2><Button onClick={() => navigate("alerts")}>查看全部</Button></div>{openAlerts.slice(0, 5).map((item) => <button className="recent-item" key={item.id} onClick={() => navigate("alerts")}><strong>{item.title}</strong><small>{item.device} · {item.level} · {item.status}</small></button>)}{!openAlerts.length && <p>暂无待处理告警</p>}</section><section className="panel recent-panel"><div className="panel-title"><h2>待办工单</h2><Button onClick={() => navigate("orders")}>查看全部</Button></div>{activeOrders.slice(0, 5).map((item) => <button className="recent-item" key={item.id} onClick={() => navigate("orders")}><strong>{item.title}</strong><small>{item.deviceId} · {item.owner || "未指派"} · {item.status}</small></button>)}{!activeOrders.length && <p>暂无未完成工单</p>}</section></div>
    <section className="panel overview-live-device"><div className="panel-title"><h2>设备快速查看</h2><span className="tone-badge tone-success">服务器设备清单</span></div><div className="overview-device-switcher" role="tablist" aria-label="切换设备">{devices.map((device) => <button key={device.id} role="tab" aria-selected={selectedDevice?.id === device.id} onClick={() => setSelectedDeviceId(device.id)}><strong>{device.id}</strong><small>{device.name}</small></button>)}</div>{selectedDevice ? <div key={selectedDevice.id} className="overview-device-content" role="tabpanel"><div className="overview-device-caption"><strong>{selectedDevice.id} · {selectedDevice.name}</strong><span>{selectedDevice.location || selectedDevice.plant || "位置未记录"} · {selectedDevice.state || "状态未记录"} · 健康度 {typeof selectedDevice.health === "number" ? selectedDevice.health : "暂无测量"}</span></div><p className="panel-note">服务器尚未提供此设备的历史测点趋势；可在设备中心查看已上报参数。</p><Button onClick={() => navigate("devices")}>进入设备中心</Button></div> : <div className="device-empty">当前组织暂无设备</div>}</section>
  </>;
}
