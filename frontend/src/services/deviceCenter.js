export const DEVICE_IMPORT_HEADERS = ["设备编号", "设备名称", "设备类型", "厂区", "位置"];

function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function filterDevices(devices, filters = {}) {
  const query = normalize(filters.query);
  return devices.filter((device) => {
    const matchesQuery = !query || [device.id, device.name, device.type, device.location, device.plant]
      .some((value) => normalize(value).includes(query));
    const matchesType = !filters.type || device.type === filters.type;
    const matchesState = !filters.state || device.state === filters.state;
    const matchesPlant = !filters.plant || device.plant === filters.plant;
    return matchesQuery && matchesType && matchesState && matchesPlant;
  });
}

function parseCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const source = String(text || "").replace(/^\uFEFF/, "");
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (char === '"' && quoted && source[index + 1] === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && source[index + 1] === "\n") index += 1;
      row.push(cell.trim());
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else cell += char;
  }
  row.push(cell.trim());
  if (row.some(Boolean)) rows.push(row);
  if (quoted) throw new Error("CSV 中存在未闭合的引号");
  return rows;
}

export function parseDeviceImport(text, existingIds = []) {
  const rows = parseCsvRows(text);
  if (!rows.length) return { rows: [], errors: ["文件为空"] };
  const headers = rows[0];
  const missingHeaders = DEVICE_IMPORT_HEADERS.filter((header) => !headers.includes(header));
  if (missingHeaders.length) return { rows: [], errors: [`缺少表头：${missingHeaders.join("、")}`] };

  const existing = new Set(existingIds.map(normalize));
  const seen = new Set();
  const parsed = rows.slice(1).map((values, rowIndex) => {
    const source = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
    const device = {
      id: source["设备编号"].trim(),
      name: source["设备名称"].trim(),
      type: source["设备类型"].trim(),
      plant: source["厂区"].trim(),
      location: source["位置"].trim(),
      health: null,
      state: "待接入",
      alert: 0,
      importRow: rowIndex + 2,
    };
    const errors = [];
    for (const [key, label] of [["id", "设备编号"], ["name", "设备名称"], ["type", "设备类型"], ["plant", "厂区"], ["location", "位置"]]) {
      if (!device[key]) errors.push(`${label}不能为空`);
    }
    const normalizedId = normalize(device.id);
    if (normalizedId && existing.has(normalizedId)) errors.push("设备编号已存在");
    if (normalizedId && seen.has(normalizedId)) errors.push("文件内设备编号重复");
    if (normalizedId) seen.add(normalizedId);
    return { ...device, errors };
  });
  return { rows: parsed, errors: [] };
}

export function createDeviceImportTemplate(plant = "一号装配厂") {
  return `${DEVICE_IMPORT_HEADERS.join(",")}\nM-001,示例电机,电机,${plant},动力站 Bay01\n`;
}
