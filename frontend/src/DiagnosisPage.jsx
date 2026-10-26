import { useEffect, useRef, useState } from "react";
import { Button } from "@fluentui/react-components";
import { BookOpen24Regular, Play24Regular, Pulse24Regular } from "@fluentui/react-icons";
import { diagnosisStatuses, requestDiagnosis, summarizeDiagnosis } from "./services/diagnosis";
import { confirmDiagnosis, loadDiagnosisAudit, saveDiagnosis } from "./services/workflow";
import { loadDeviceParameters } from "./services/api.js";
import { buildMeasurementQuestion } from "./services/measurementPrompt.js";
import "./diagnosis.css";

const types = { fact: "文档陈述", inference: "模型推断", pending: "待验证" };

export default function DiagnosisPage({ devices, session, initialDeviceId = "AC-07", initialQuestion = "" }) {
  const [deviceId, setDeviceId] = useState(initialDeviceId);
  const [question, setQuestion] = useState(initialQuestion || (session?.isPreview ? "现场巡检发现驱动端异响，振动在慢升速过程中明显加剧。需要核对哪些证据？" : ""));
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeSource, setActiveSource] = useState(null);
  const [contextChecks, setContextChecks] = useState({ sampledAt: false, measuringPoint: false, operatingMode: false });
  const [verifiedItems, setVerifiedItems] = useState({});
  const [riskLevel, setRiskLevel] = useState("");
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [savedDiagnosis, setSavedDiagnosis] = useState(null);
  const [confirmedOrder, setConfirmedOrder] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [workflowMessage, setWorkflowMessage] = useState("");
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
    setRiskLevel("");
    setSavedDiagnosis(null);
    setConfirmedOrder(null);
    setAuditEvents([]);
    setWorkflowMessage("");
  }

  async function persistDiagnosis() {
    if (workflowBusy) return;
    setWorkflowBusy(true);
    setWorkflowMessage("");
    try {
      const saved = await saveDiagnosis({ deviceId, question, result, riskLevel, session });
      setSavedDiagnosis(saved);
      setWorkflowMessage(`诊断 ${saved.id} 已保存，等待人工确认。`);
    } catch (failure) {
      setWorkflowMessage(failure.message || "诊断保存失败。");
    } finally {
      setWorkflowBusy(false);
    }
  }

  async function confirmAndCreateOrder() {
    if (workflowBusy || !savedDiagnosis?.id) return;
    setWorkflowBusy(true);
    setWorkflowMessage("");
    try {
      const confirmed = await confirmDiagnosis({
        diagnosisId: savedDiagnosis.id,
        title: `${deviceId} 诊断处理`,
        priority: riskLevel === "high" ? "P1 紧急" : riskLevel === "medium" ? "P2 高" : "P3 中",
        note: "前端诊断工作台人工确认",
        session,
      });
      setSavedDiagnosis(confirmed.diagnosis);
      setConfirmedOrder(confirmed.workOrder);
      let events = [];
      try {
        events = await loadDiagnosisAudit({ diagnosisId: savedDiagnosis.id, session });
      } catch (auditFailure) {
        setWorkflowMessage(`工单 ${confirmed.workOrder.id} 已生成。审计记录暂无法读取：${auditFailure.message}`);
      }
      setAuditEvents(events);
      if (events.length) setWorkflowMessage(`工单 ${confirmed.workOrder.id} 已生成，并核对 ${events.length} 条诊断审计记录。`);
    } catch (failure) {
      setWorkflowMessage(failure.message || "人工确认失败。");
    } finally {
      setWorkflowBusy(false);
    }
  }

  async function runDiagnosis(nextQuestion) {
    if (busy) return;
    const controller = new AbortController();
    request.current = controller;
    clearResult();
    setBusy(true);
    try {
      const response = await requestDiagnosis({ deviceId, question: nextQuestion, signal: controller.signal, session });
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

  async function diagnose(event) {
    event.preventDefault();
    await runDiagnosis(question);
  }

  async function diagnoseFromMeasurements() {
    if (busy || !session?.accessToken) return;
    setBusy(true);
    setError("");
    try {
      const measurements = await loadDeviceParameters(deviceId, session.accessToken);
      const nextQuestion = buildMeasurementQuestion(deviceId, measurements);
      setQuestion(nextQuestion);
      setContextChecks((current) => ({ ...current, sampledAt: measurements.some((item) => item.recordedAt), measuringPoint: true }));
      setBusy(false);
      await runDiagnosis(nextQuestion);
    } catch (failure) { setBusy(false); setError(failure.message); }
  }

  const source = result?.sources.find((item) => item.key === activeSource);
  const origin = !result ? "尚未生成结果" : result.transport === "local-demo"
    ? "本地固定样例 · 未调用模型" : result.is_mock ? "服务端模拟或降级结果 · 非真实模型诊断" : "服务端标记为真实模型 · 仍需人工核验";
  const pending = result?.statements.filter((item) => item.type === "pending") || [];
  const suggestions = result?.verification_suggestions || [];
  const selectedDevice = devices.find((item) => item.id === deviceId);
  const contextLabels = {
    sampledAt: "已记录采样时间",
    measuringPoint: "已注明测点与单位",
    operatingMode: "已确认当前工况",
  };
  const preparedCount = Object.values(contextChecks).filter(Boolean).length;
  const resultSummary = summarizeDiagnosis(result);
  const verificationItems = [
    ...pending.map((item) => item.text),
    ...suggestions.map((item) => `${item.missing_evidence}：${item.to_verify}`),
  ];
  const verifiedCount = verificationItems.filter((_, index) => verifiedItems[index]).length;

  return <>
    <header className="page-header"><div><h1>诊断工作台</h1><p>先核对证据，再形成判断。诊断建议不能替代现场专业确认。</p></div></header>
    <div className="diagnostic-origin" role="status"><Pulse24Regular /><span>{origin}</span><span>不自动操作设备或创建工单</span></div>
    <div className="grounded-layout">
      <aside className="panel grounded-input">
        <h2>现场信息</h2>
        <form onSubmit={diagnose}>
          <label htmlFor="diagnosis-device">目标设备</label>
          <select id="diagnosis-device" value={deviceId} disabled={busy} onChange={(event) => { setDeviceId(event.target.value); clearResult(); }}>
            {session?.isPreview && !devices.some((item) => item.id === "AC-07") && <option value="AC-07">AC-07 · 演示设备</option>}
            {devices.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.name}</option>)}
          </select>
          {selectedDevice && <section className="device-context" aria-label="当前设备上下文">
            <div><span>设备位置</span><strong>{selectedDevice.location}</strong></div>
            <div><span>设备类型</span><strong>{selectedDevice.type}</strong></div>
            <div><span>设备状态</span><strong>{selectedDevice.state} · 健康值 {selectedDevice.health ?? "待接入"}</strong></div>
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
          {!session?.isPreview && <Button type="button" disabled={busy || !deviceId} onClick={diagnoseFromMeasurements}>读取设备测点并诊断</Button>}
          {busy && <Button type="button" onClick={() => { request.current?.abort(); setBusy(false); setError("已取消本次诊断，未生成结论。"); }}>取消请求</Button>}
        </form>
        <p className="grounded-note">设备型号由服务端档案决定，页面不提交覆盖型号。测点自动提问需要实际采集数据；没有阈值时不会断言超限。</p>
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
          {result.conflicts.length > 0 && <section className="diagnostic-conflicts" aria-label="事实冲突">
            <h3>检测到事实冲突</h3>
            {result.conflicts.map((conflict, index) => <article key={`${conflict.field}-${index}`}>
              <strong>{conflict.field}</strong>
              <ul>{conflict.sources.map((item, sourceIndex) => <li key={`${item.origin}-${sourceIndex}`}><span>{item.origin}</span>：{item.value}{item.ref ? `（${item.ref}）` : ""}</li>)}</ul>
            </article>)}
          </section>}
          <div className="statement-list">{result.statements.map((item, index) => <article key={index} className={`statement statement-${item.type}`}>
            <span className="statement-index">{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{types[item.type]}</strong><p>{item.text}</p>
              {item.sourceKey ? <Button appearance="subtle" onClick={() => setActiveSource(item.sourceKey)}>查看依据{item.sourceKeys.length > 1 ? `（${item.sourceKeys.length} 条，先打开第 1 条）` : item.source ? `：${item.source}` : ""}</Button>
                : <small>{item.source ? `引用未唯一匹配：${item.source}` : "未提供直接引用，需人工核对"}</small>}
            </div>
          </article>)}</div>
          <section className="verification-next"><div className="verification-heading"><h3>证据补采清单</h3>{verificationItems.length > 0 && <strong>{verifiedCount}/{verificationItems.length} 已现场核对</strong>}</div>{verificationItems.length
            ? <div className="verification-list">{verificationItems.map((item, index) => <label key={index} className={verifiedItems[index] ? "checked" : ""}><input type="checkbox" checked={Boolean(verifiedItems[index])} onChange={(event) => setVerifiedItems((current) => ({ ...current, [index]: event.target.checked }))} /><span>{item}</span></label>)}</div>
            : <p>服务端未提供待验证项，不能据此认为已经验证充分。请补充现场记录并由维护人员复核。</p>}
            <small>勾选记录不会保存，也不会生成任务。尚未建立校准模型，不展示诊断置信度或预测概率。</small>
          </section>
          <section className="grounded-confirm" aria-label="诊断确认与建单">
            <label htmlFor="diagnosis-risk">人工风险分级</label>
            <select id="diagnosis-risk" value={riskLevel} disabled={workflowBusy || Boolean(savedDiagnosis)} onChange={(event) => setRiskLevel(event.target.value)}>
              <option value="">请选择</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option>
            </select>
            <div className="workflow-actions">
              <Button appearance="primary" disabled={workflowBusy || Boolean(savedDiagnosis) || result.transport !== "api" || result.is_mock || result.status !== "ok" || !riskLevel} onClick={persistDiagnosis}>{savedDiagnosis ? "诊断已保存" : workflowBusy ? "正在处理" : "保存诊断"}</Button>
              <Button disabled={workflowBusy || !savedDiagnosis || Boolean(confirmedOrder)} onClick={confirmAndCreateOrder}>{confirmedOrder ? "工单已生成" : "人工确认并生成工单"}</Button>
            </div>
            <p>{result.transport !== "api" || result.is_mock || result.status !== "ok" ? "只有真实接口返回且证据校验通过的诊断才能保存。" : "风险等级由人工选择；确认后由 B 服务幂等生成工单。"}</p>
            {workflowMessage && <p className="workflow-message" role="status">{workflowMessage}</p>}
            {savedDiagnosis && <dl className="workflow-result"><dt>诊断编号</dt><dd>{savedDiagnosis.id}</dd>{confirmedOrder && <><dt>工单编号</dt><dd>{confirmedOrder.id}</dd><dt>审计记录</dt><dd>{auditEvents.length ? `${auditEvents.length} 条已核对` : "待管理员权限核对"}</dd></>}</dl>}
          </section>
        </>}
      </section>
      <aside className="panel grounded-sources" aria-label="证据阅读器">
        <div className="panel-title"><div><BookOpen24Regular /><h2>证据阅读器</h2></div><span>{result?.sources.length || 0} 条</span></div>
        {!result?.sources.length && <p className="grounded-empty">暂无可核对的原文片段。</p>}
        <div className="source-picker">{result?.sources.map((item, index) => <button key={item.key} type="button" aria-pressed={item.key === activeSource} onClick={() => setActiveSource(item.key)}><span>证据 {index + 1}</span><strong>{item.title}</strong><small>{item.page === null ? "页码未知" : `第 ${item.page} 页`} · 分块 {item.chunk_index}</small></button>)}</div>
        {source && <section className="source-reading" aria-live="polite"><h3>{source.title}</h3><dl><dt>引用编号</dt><dd>{source.id}</dd><dt>文档编号</dt><dd>{source.document_id}</dd><dt>位置</dt><dd>{source.page === null ? "页码未知" : `第 ${source.page} 页`} · 分块 {source.chunk_index}</dd><dt>文档版本</dt><dd>{source.version}</dd></dl><blockquote>{source.snippet}</blockquote><p>这是服务端返回的片段，不是全文。检索分数不是故障概率；该片段是否支持结论仍需人工判断。</p></section>}
      </aside>
    </div>
  </>;
}
