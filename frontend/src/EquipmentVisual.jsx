import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { deviceProfiles } from "./data.js";
import "./equipment-visual.css";

export default function EquipmentVisual({ deviceId = "AC-07", compact = false }) {
  const profile = deviceProfiles[deviceId];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const colors = compact ? ["#83c8ee", "#ffb483"] : ["#1676a8", "#c65a22"];
  return <figure className={`equipment-visual ${compact ? "equipment-visual-compact" : ""}`}>
    <figcaption><div><strong>{compact ? "让每一次异常，都有处置路径" : `${deviceId} · 设备指标趋势`}</strong><span>{compact ? "设备监测 / 知识诊断 / 工单协同 · 示例数据" : "演示参考数据 · 非实时采集"}</span></div></figcaption>
    {profile?.trend?.length ? <>
      <div className="equipment-legend">{profile.series.map((series, index) => <span key={series.key} style={{ color: colors[index % colors.length] }}><i />{series.label}</span>)}</div>
      <div className="equipment-chart" key={deviceId} aria-label={`${deviceId} 示例指标趋势`}><ResponsiveContainer width="100%" height="100%"><LineChart data={profile.trend} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke={compact ? "#315571" : "#e3ebf0"} strokeDasharray="3 5" />
        <XAxis dataKey="time" tick={{ fill: compact ? "#b6d4e7" : "#62788b", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={35} />
        {profile.series.map((series, index) => <YAxis key={series.key} yAxisId={series.key} orientation={index ? "right" : "left"} hide={compact} width={48} domain={["auto", "auto"]} tick={{ fill: colors[index % colors.length], fontSize: 11 }} axisLine={false} tickLine={false} />)}
        <Tooltip contentStyle={{ border: "1px solid #d6e1e9", borderRadius: 8, color: "#23445d", fontSize: 13 }} labelFormatter={label => `${label} · 示例采样`} />
        {profile.series.map((series, index) => <Line key={series.key} yAxisId={series.key} type="monotone" dataKey={series.key} name={series.label} stroke={colors[index % colors.length]} strokeWidth={index ? 2.5 : 3} dot={false} activeDot={{ r: 5 }} isAnimationActive={!reducedMotion} animationDuration={1100} animationBegin={index * 120} animationEasing="ease-out" />)}
      </LineChart></ResponsiveContainer></div>
      {!compact && <div className="equipment-reference">{profile.metrics.map(metric => <div key={metric.label}><span>{metric.label}</span><strong>{metric.value} <small>{metric.unit}</small></strong><small>示例参考：{metric.limit}</small></div>)}</div>}
    </> : <p className="panel-note">此设备暂无已配置的示例趋势。</p>}
    {compact && <div className="login-process"><span><b>01</b>发现异常</span><span><b>02</b>追溯证据</span><span><b>03</b>完成维修</span></div>}
  </figure>;
}
