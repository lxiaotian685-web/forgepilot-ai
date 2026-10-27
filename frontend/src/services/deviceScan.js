export function parseDeviceQr(raw) {
  const text = String(raw || "").trim();
  if (!text || text.length > 2048) throw new Error("二维码内容为空或过长");
  let value;
  if (text.startsWith("{")) {
    try { value = JSON.parse(text); } catch { throw new Error("设备二维码 JSON 格式无效"); }
  } else {
    let url;
    try { url = new URL(text); } catch { throw new Error("二维码须包含设备 JSON 或 forgepilot://device 链接"); }
    if (url.protocol !== "forgepilot:" || url.hostname !== "device") throw new Error("不是 ForgePilot 设备二维码");
    value = Object.fromEntries(["id", "name", "type", "plant", "location"].map((key) => [key, url.searchParams.get(key) || ""]));
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("设备信息格式无效");
  return Object.fromEntries(["id", "name", "type", "plant", "location"].map((key) => [key, String(value[key] || "").trim().slice(0, 255)]));
}
