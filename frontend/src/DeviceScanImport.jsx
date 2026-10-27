import { useEffect, useRef, useState } from "react";
import { Button, Input } from "@fluentui/react-components";
import { parseDeviceQr } from "./services/deviceScan.js";

const fields = [["id", "设备编号"], ["name", "设备名称"], ["type", "设备类型"], ["plant", "厂区"], ["location", "位置"]];

export default function DeviceScanImport({ existingIds, defaultPlant, onImport, onClose }) {
  const [raw, setRaw] = useState("");
  const [device, setDevice] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const frameRef = useRef(0);
  const stop = () => {
    cancelAnimationFrame(frameRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setScanning(false);
  };
  useEffect(() => () => { cancelAnimationFrame(frameRef.current); streamRef.current?.getTracks().forEach((track) => track.stop()); }, []);
  const decode = (text) => {
    try { const parsed = parseDeviceQr(text); setDevice({ ...parsed, plant: parsed.plant || defaultPlant }); setRaw(text); setError(""); stop(); }
    catch (failure) { setError(failure.message); }
  };
  const start = async () => {
    if (!window.BarcodeDetector || !navigator.mediaDevices?.getUserMedia) return setError("当前浏览器不支持摄像头扫码，请粘贴二维码内容");
    try {
      const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setScanning(true);
      setError("");
      const scan = async () => {
        if (!streamRef.current) return;
        try {
          const codes = await detector.detect(videoRef.current);
          if (codes[0]?.rawValue) { decode(codes[0].rawValue); return; }
        } catch { /* camera frame not ready */ }
        frameRef.current = requestAnimationFrame(scan);
      };
      frameRef.current = requestAnimationFrame(scan);
    } catch (failure) { stop(); setError(`无法启用摄像头：${failure.message}`); }
  };
  const save = async () => {
    const missing = fields.filter(([key]) => !device?.[key]?.trim()).map(([, label]) => label);
    if (missing.length) return setError(`请补全：${missing.join("、")}`);
    if (existingIds.some((id) => id.toLowerCase() === device.id.toLowerCase())) return setError("设备编号已存在");
    setBusy(true);
    try { await onImport(device); onClose(); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <div className="modal-backdrop" role="presentation"><section className="panel work-order-form"><div className="form-heading"><h2>扫码导入设备</h2><Button onClick={() => { stop(); onClose(); }}>关闭</Button></div><p>扫描 ForgePilot 设备二维码后核对信息，再保存到当前组织。</p><video ref={videoRef} muted playsInline style={{ width: "100%", maxHeight: 280, display: scanning ? "block" : "none" }} /><div className="form-actions"><Button onClick={scanning ? stop : start}>{scanning ? "停止扫码" : "打开摄像头"}</Button></div><label>或粘贴二维码内容<textarea value={raw} onChange={(event) => setRaw(event.target.value)} placeholder='{"id":"M-001","name":"电机","type":"电机","plant":"厂区","location":"动力站"}' /></label><Button onClick={() => decode(raw)}>读取内容</Button>{device && <div className="form-grid">{fields.map(([key, label]) => <label key={key}>{label}<Input value={device[key]} onChange={(_, data) => setDevice((current) => ({ ...current, [key]: data.value }))} /></label>)}</div>}{error && <p role="alert">{error}</p>}<div className="form-actions"><Button appearance="primary" disabled={!device || busy} onClick={save}>{busy ? "正在保存" : "确认导入服务器"}</Button></div></section></div>;
}
