import { useEffect, useRef, useState } from "react";
import { Button } from "@fluentui/react-components";
import { BookOpen24Regular, Play24Regular, Pulse24Regular } from "@fluentui/react-icons";
import { diagnosisStatuses, requestDiagnosis, summarizeDiagnosis } from "./services/diagnosis";
import "./diagnosis.css";

const types = { fact: "文档陈述", inference: "模型推断", pending: "待验证" };

export default function DiagnosisPage({ devices, initialDeviceId = "AC-07", initialQuestion = "" }) {
  const [deviceId, setDeviceId] = useState(initialDeviceId);
  const [question, setQuestion] = useState(initialQuestion || "现场巡检发现驱动端异响，振动在慢升速过程中明显加剧。需要核对哪些证据？");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeSource, setActiveSource] = useState(null);
  const [contextChecks, setContextChecks] = useState({ sampledAt: false, measuringPoint: false, operatingMode: false });
  const [verifiedItems, setVerifiedItems] = useState({});
  const request = useRef(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (initialDeviceId) setDeviceId(initialDeviceId);
    if (initialQuestion) setQuestion(initialQuestion);
  }, [initialDeviceId, initialQuestion]);

  function clearResult() {
    setResult(null);
    setError("");
    setActiveSource(null);
    setVerifiedItems({});
  }

  async function diagnose(event) {
    event.preventDefault();
    if (busy) return;
    const controller = new AbortController();
    request.current = controller;
    clearResult();
    setBusy(true);
    try {
      const response = await requestDiagnosis({ deviceId, question, signal: controller.signal });
      if (!controller.signal.aborted) {
        setResult(response);
        setActiveSource(response.sources[0]?.key || null);
      }
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message || "诊断服务不可用，请检查网络后重试。");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const source = result?.sources.find((item) => item.key === activeSource);
  const origin = !result ? "尚未生成结果" : result.transport === "local-demo"
    ? "本地固定样例 · 未调用模型" : result.is_mock ? "服务端模拟或降级结果 · 非真实模型诊断" : "服务端标记为真实模型 · 仍需人工核验";
  const pending = result?.statements.filter((item) => item.type === "pending") || [];
  const selectedDevice = devices.find((item) => item.id === deviceId);
  const contextLabels = {
    sampledAt: "已记录采样时间",
    measuringPoint: "已注明测点与单位",
    operatingMode: "已确认当前工况",
  };
  const preparedCount = Object.values(contextChecks).filter(Boolean).length;
  const resultSummary = summarizeDiagnosis(result);
  const verifiedCount = pending.filter((_, index) => verifiedItems[index]).length;

  return <>
    <header className="page-header"><div><h1>诊断工作台</h1><p>先核对证据，再形成判断。诊断建议不能替代现场专业确认。</p></div></header>
    <div className="diagnostic-origin" role="status"><Pulse24Regular /><span>{origin}</span><span>不自动操作设备或创建工单</span></div>
    <div className="grounded-layout">
      <aside className="panel grounded-input">
        <h2>现场信息</h2>
        <form onSubmit={diagnose}>
          <label htmlFor="diagnosis-device">目标设备</label>
          <select id="diagnosis-device" value={deviceId} disabled={busy} onChange={(event) => { setDeviceId(event.target.value); clearResult(); }}>
            {!devices.some((item) => item.id === "AC-07") && <option value="AC-07">AC-07 · 演示设备</option>}
            {devices.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.name}</option>)}
          </select>
          {selectedDevice && <section className="device-context" aria-label="当前设备上下文">
            <div><span>设备位置</span><strong>{selectedDevice.location}</strong></div>
            <div><span>设备类型</span><strong>{selectedDevice.type}</strong></div>
            <div><span>演示状态</span><strong>{selectedDevice.state} · 健康值 {selectedDevice.health}</strong></div>
          </section>}
          <label htmlFor="diagnosis-question">现场现象与问题</label>
          <textarea id="diagnosis-question" rows={7} maxLength={2000} required disabled={busy} value={question} onChange={(event) => { setQuestion(event.target.value); clearResult(); }} />
          <small>请写明时间、测点和单位。不要输入企业敏感信息。</small>
          <fieldset className="context-checks">
            <legend><span>诊断准备度</span><strong>{preparedCount}/3 已补充</strong></legend>
            {Object.entries(contextLabels).map(([key, label]) => <label key={key}>
              <input type="checkbox" checked={contextChecks[key]} onChange={(event) => setContextChecks((current) => ({ ...current, [key]: event.target.checked }))} />
              <span>{label}</span>
            </label>)}
            <small>勾选项仅保存在本页，用于提醒资料是否齐全，不会传给诊断接口。</small>
          </fieldset>
          <Button appearance="primary" type="submit" icon={<Play24Regular />} disabled={busy || !question.trim()}>{busy ? "正在请求诊断" : "开始诊断"}</Button>
          {busy && <Button type="button" onClick={() => { request.current?.abort(); setBusy(false); setError("已取消本次诊断，未生成结论。"); }}>取消请求</Button>}
        </form>
        <p className="grounded-note">设备型号由服务端档案决定，页面不提交覆盖型号。关联告警与诊断保存将在统一业务接口完成后接入。</p>
      </aside>
      <section className="panel grounded-result" aria-busy={busy}>
        <div className="panel-title"><div><Pulse24Regular /><h2>判断与依据</h2></div><span>{result ? diagnosisStatuses[result.status] : "等待诊断"}</span></div>
        {error && <p className="diagnostic-error" role="alert">{error}</p>}
        {busy && <p role="status" className="grounded-empty">正在请求服务端。尚未确认检索或模型步骤完成。</p>}
        {!result && !busy && <div className="grounded-empty"><h3>从一个明确的现场问题开始</h3><p>结果会区分文档陈述、模型推断与待验证项。没有证据时会明确显示，不预填诊断结论。</p></div>}
        {result && <>
          <section className="diagnosis-summary" aria-label="诊断结果摘要">
            <div><span>文档陈述</span><strong>{resultSummary.fact}</strong></div>
            <div><span>模型推断</span><strong>{resultSummary.inference}</strong></div>
            <div><span>待验证</span><strong>{resultSummary.pending}</strong></div>
            <div><span>原文证据</span><strong>{resultSummary.sources}</strong></div>
            <p>{resultSummary.pending > 0 ? "当前状态：证据待补齐" : "当前状态：仍需人工复核"}</p>
          </section>
          <p className="diagnostic-answer">{result.answer}</p>
          <div className="statement-list">{result.statements.map((item, index) => <article key={index} className={`statement statement-${item.type}`}>
            <span className="statement-index">{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{types[item.type]}</strong><p>{item.text}</p>
              {item.sourceKey ? <Button appearance="subtle" onClick={() => setActiveSource(item.sourceKey)}>查看依据：{item.source}</Button>
                : <small>{item.source ? `引用未唯一匹配：${item.source}` : "未提供直接引用，需人工核对"}</small>}
            </div>
          </article>)}</div>
          <section className="verification-next"><div className="verification-heading"><h3>证据补采清单</h3>{pending.length > 0 && <strong>{verifiedCount}/{pending.length} 已现场核对</strong>}</div>{pending.length
            ? <div className="verification-list">{pending.map((item, index) => <label key={index} className={verifiedItems[index] ? "checked" : ""}><input type="checkbox" checked={Boolean(verifiedItems[index])} onChange={(event) => setVerifiedItems((current) => ({ ...current, [index]: event.target.checked }))} /><span>{item.text}</span></label>)}</div>
            : <p>服务端未提供待验证项，不能据此认为已经验证充分。请补充现场记录并由维护人员复核。</p>}
            <small>勾选记录不会保存，也不会生成任务。尚未建立校准模型，不展示诊断置信度或预测概率。</small>
          </section>
          <div className="grounded-confirm"><Button disabled>人工确认并生成工单</Button><p>等待 B 包持久化与确认接口，当前结果未保存到业务数据库。</p></div>
        </>}
      </section>
      <aside className="panel grounded-sources" aria-label="证据阅读器">
        <div className="panel-title"><div><BookOpen24Regular /><h2>证据阅读器</h2></div><span>{result?.sources.length || 0} 条</span></div>
        {!result?.sources.length && <p className="grounded-empty">暂无可核对的原文片段。</p>}
        <div className="source-picker">{result?.sources.map((item, index) => <button key={item.key} type="button" aria-pressed={item.key === activeSource} onClick={() => setActiveSource(item.key)}><span>证据 {index + 1}</span><strong>{item.title}</strong><small>第 {item.page} 页</small></button>)}</div>
        {source && <section className="source-reading" aria-live="polite"><h3>{source.title}</h3><dl><dt>文档编号</dt><dd>{source.document_id}</dd><dt>位置</dt><dd>第 {source.page} 页</dd><dt>文档版本</dt><dd>当前接口未提供</dd></dl><blockquote>{source.snippet}</blockquote><p>这是服务端返回的片段，不是全文。检索分数不是故障概率；该片段是否支持结论仍需人工判断。</p></section>}
      </aside>
    </div>
  </>;
}
