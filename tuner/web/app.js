const STATUS = {
  draft: "черновик",
  approved: "утверждён",
  sliced: "нарезан",
  printed: "напечатан",
};

const LEVELS = {
  basic: new Set(["basic"]),
  advanced: new Set(["basic", "advanced"]),
  expert: new Set(["basic", "advanced", "expert"]),
  all: new Set(["basic", "advanced", "expert", "all"]),
};

const CUSTOM_KEY = "printerTunerCustom";
const VIS_KEY = "printerTunerVisibility";

const state = {
  catalog: null,
  presets: [],
  current: null,
  edits: {},
  visibility: localStorage.getItem(VIS_KEY) || "basic",
  onlyChanged: false,
  query: "",
  custom: new Set(JSON.parse(localStorage.getItem(CUSTOM_KEY) || "[]")),
  openCategories: new Set(),
  printerOpen: false,
  cards: { machines: [], filaments: [], nozzles: [] },
  cardById: { machines: {}, filaments: {}, nozzles: {} },
  applied: { machines: new Set(), filaments: new Set(), nozzles: new Set() },
  addKind: "machines",
};

const $ = (id) => document.getElementById(id);

function norm(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  return String(value).trim();
}

function initialOf(key) {
  const preset = state.current;
  if (!preset) return "";
  if (Object.prototype.hasOwnProperty.call(preset.settings, key)) return preset.settings[key];
  if (Object.prototype.hasOwnProperty.call(preset.baseline, key)) return preset.baseline[key];
  return "";
}

function valueOf(key) {
  if (Object.prototype.hasOwnProperty.call(state.edits, key)) return state.edits[key];
  return initialOf(key);
}

function isProposed(key) {
  const preset = state.current;
  if (!preset || !Object.prototype.hasOwnProperty.call(preset.settings, key)) return false;
  const base = Object.prototype.hasOwnProperty.call(preset.baseline, key) ? preset.baseline[key] : "";
  return norm(preset.settings[key]) !== norm(base);
}

function isEdited(key) {
  if (!Object.prototype.hasOwnProperty.call(state.edits, key)) return false;
  return norm(state.edits[key]) !== norm(initialOf(key));
}

function levelVisible(field) {
  if (state.visibility === "custom") return state.custom.has(field.key);
  return LEVELS[state.visibility].has(field.level);
}

function matchesQuery(field) {
  const q = state.query.trim().toLowerCase();
  if (!q) return true;
  return [field.label, field.key, field.hint].join(" ").toLowerCase().includes(q);
}

function showMessage(text) {
  const node = $("message");
  node.hidden = !text;
  node.textContent = text || "";
}

async function load() {
  const [catalog, presets, machines, filaments, nozzles] = await Promise.all([
    fetch("/api/fields").then((res) => res.json()),
    fetch("/api/presets").then((res) => res.json()),
    fetch("/api/machines").then((res) => res.json()),
    fetch("/api/filaments").then((res) => res.json()),
    fetch("/api/nozzles").then((res) => res.json()),
  ]);
  state.catalog = catalog;
  state.presets = presets;
  state.cards.machines = machines;
  state.cards.filaments = filaments;
  state.cards.nozzles = nozzles;
  await Promise.all([
    cacheCards("machines", machines),
    cacheCards("filaments", filaments),
    cacheCards("nozzles", nozzles),
  ]);
  $("visibility").value = state.visibility;
  renderPresetList();
  if (presets.length) await openPreset(presets[0].id);
  else showMessage("В library/presets пока нет файлов.");
}

async function cacheCards(kind, items) {
  const pairs = await Promise.all(items.map(async (item) => {
    const data = await fetch(`/api/${kind}/${item.id}`).then((res) => res.json());
    return [item.id, data];
  }));
  state.cardById[kind] = Object.fromEntries(pairs);
}

function renderPresetList() {
  const list = $("preset-list");
  list.replaceChildren();
  for (const item of state.presets) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    if (state.current && state.current.id === item.id) button.className = "active";
    button.innerHTML = `${escapeHtml(item.title)}<small>${STATUS[item.status] || item.status}${item.nozzle_mm ? ` · сопло ${item.nozzle_mm}` : ""}</small>`;
    button.addEventListener("click", () => {
      if (dirty() && !confirm("Есть несохранённые правки. Перейти к другому пресету?")) return;
      openPreset(item.id);
    });
    li.append(button);
    list.append(li);
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function openPreset(id) {
  const res = await fetch(`/api/presets/${id}`);
  if (!res.ok) {
    showMessage("Не удалось открыть пресет.");
    return;
  }
  state.current = await res.json();
  state.edits = {};
  state.applied = { machines: new Set(), filaments: new Set(), nozzles: new Set() };
  state.openCategories = new Set();
  const today = new Date().toISOString().slice(0, 10);
  $("print-date").value = today;
  $("print-note").value = "";
  $("note").value = state.current.note || "";
  showMessage("");
  renderPresetList();
  render();
}

function dirty() {
  return Object.keys(state.edits).some(isEdited) || $("note").value !== (state.current?.note || "");
}

function proposedKeys() {
  if (!state.current) return [];
  return Object.keys(state.current.settings).filter(isProposed);
}

function cardOf(kind) {
  const preset = state.current;
  if (!preset) return null;
  const id = { machines: preset.printer_id, filaments: preset.filament_id, nozzles: preset.nozzle_id }[kind];
  return state.cardById[kind][id] || null;
}

function sourceOf(key) {
  const nozzle = cardOf("nozzles");
  if (nozzle && Object.prototype.hasOwnProperty.call(nozzle.settings || {}, key)) return "сопло";
  const filament = cardOf("filaments");
  if (filament && Object.prototype.hasOwnProperty.call(filament.settings || {}, key)) return "филамент";
  const printer = cardOf("machines");
  if (printer && Object.prototype.hasOwnProperty.call(printer.settings || {}, key)) return "принтер";
  const preset = state.current;
  if (preset && (Object.prototype.hasOwnProperty.call(preset.settings, key) || Object.prototype.hasOwnProperty.call(preset.baseline, key))) {
    return "этот заход";
  }
  return "";
}

function fillSelect(select, items, selected) {
  const signature = items.map((item) => item.id).join("|");
  if (select.dataset.signature !== signature) {
    select.replaceChildren();
    for (const item of items) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.warn ? `${item.title} · осторожно` : item.title;
      select.append(option);
    }
    select.dataset.signature = signature;
  }
  if (selected && [...select.options].some((option) => option.value === selected)) select.value = selected;
}

function syncStack() {
  const preset = state.current;
  if (!preset) return;
  fillSelect($("printer"), state.cards.machines, preset.printer_id);
  fillSelect($("filament"), state.cards.filaments, preset.filament_id);
  fillSelect($("nozzle"), state.cards.nozzles, preset.nozzle_id);
  const warnings = ["machines", "filaments", "nozzles"]
    .map((kind) => cardOf(kind)?.warn)
    .filter(Boolean);
  const node = $("hardware-warn");
  node.hidden = warnings.length === 0;
  node.textContent = warnings.join(" ");
}

function applyCard(kind, id) {
  const card = state.cardById[kind][id];
  const preset = state.current;
  if (!card || !preset) return;
  if (kind === "machines") preset.printer_id = id;
  if (kind === "filaments") {
    preset.filament_id = id;
    preset.material = card.title;
  }
  if (kind === "nozzles") {
    preset.nozzle_id = id;
    if (card.nozzle_mm) preset.nozzle_mm = card.nozzle_mm;
  }
  const previous = state.applied[kind] || new Set();
  for (const key of previous) {
    if (!Object.prototype.hasOwnProperty.call(card.settings || {}, key)) delete state.edits[key];
  }
  state.applied[kind] = new Set(Object.keys(card.settings || {}));
  for (const [key, value] of Object.entries(card.settings || {})) {
    state.edits[key] = value;
    if (!isEdited(key)) delete state.edits[key];
  }
  render();
}

function render() {
  const preset = state.current;
  if (!preset || !state.catalog) return;
  $("title").textContent = preset.title || preset.id;
  const status = $("status");
  status.textContent = STATUS[preset.status] || preset.status;
  status.className = `status ${preset.status || ""}`;
  $("meta").textContent = [
    preset.part ? `деталь: ${preset.part}` : "",
    preset.scenario ? `сценарий: ${preset.scenario}` : "",
    preset.gcode ? `g-code: ${preset.gcode}` : "",
  ].filter(Boolean).join(" · ");
  syncStack();

  const proposed = proposedKeys();
  const edited = Object.keys(state.edits).filter(isEdited);
  $("counts").textContent = `предложено ${proposed.length} · ваши правки ${edited.length}`;

  const byKey = new Map(state.catalog.fields.map((field) => [field.key, field]));
  const hiddenProposed = proposed.filter((key) => {
    const field = byKey.get(key);
    return field && field.category !== "machine_settings" && !levelVisible(field);
  }).length;
  renderPrinterPanel();
  const banner = $("hidden-note");
  if (!state.onlyChanged && hiddenProposed) {
    banner.hidden = false;
    banner.textContent = `Вне этого списка изменено ${hiddenProposed}. Включите «Только изменённые» или более подробные настройки печати.`;
  } else banner.hidden = true;

  const settings = $("settings");
  settings.replaceChildren();
  const categories = state.catalog.categories;
  const startOpen = state.visibility === "basic" || state.visibility === "advanced";
  for (const category of categories) {
    if (category.id === "machine_settings") continue;
    const fields = state.catalog.fields.filter((field) => field.category === category.id && visible(field));
    if (!fields.length) continue;
    const hasChange = fields.some((field) => isProposed(field.key) || isEdited(field.key));
    if (!state.openCategories.has(category.id) && !state.openCategories.has(`closed:${category.id}`)) {
      if (startOpen || hasChange) state.openCategories.add(category.id);
    }
    const section = document.createElement("section");
    section.className = "category";
    const head = document.createElement("button");
    head.type = "button";
    const open = state.openCategories.has(category.id) || state.query.trim() !== "";
    head.textContent = `${open ? "▾" : "▸"} ${category.label} (${fields.length})`;
    head.addEventListener("click", () => {
      if (state.openCategories.has(category.id)) {
        state.openCategories.delete(category.id);
        state.openCategories.add(`closed:${category.id}`);
      } else {
        state.openCategories.delete(`closed:${category.id}`);
        state.openCategories.add(category.id);
      }
      render();
    });
    section.append(head);
    if (open) {
      for (const field of fields) section.append(renderRow(field));
    }
    settings.append(section);
  }

  const prints = $("prints");
  prints.replaceChildren();
  for (const item of preset.prints || []) {
    const li = document.createElement("li");
    li.className = item.result || "";
    const result = { success: "успех", partial: "частично", fail: "неудача" }[item.result] || item.result;
    li.textContent = `${item.date || ""} — ${result}. ${item.note || ""}`;
    prints.append(li);
  }
}

function renderPrinterPanel() {
  const box = $("printer-settings");
  const button = $("printer-settings-toggle");
  const all = state.catalog.fields.filter((field) => field.category === "machine_settings");
  const changed = all.filter((field) => isProposed(field.key) || isEdited(field.key)).length;
  const fields = all.filter(printerVisible);
  const query = state.query.trim();
  const open = state.printerOpen || ((query !== "" || state.onlyChanged) && fields.length > 0);
  button.setAttribute("aria-expanded", open ? "true" : "false");
  button.textContent = !open && changed ? `Настройки · ${changed}` : "Настройки";
  if (!open) {
    box.hidden = true;
    box.replaceChildren();
    return;
  }
  box.hidden = false;
  box.replaceChildren();
  const lead = document.createElement("p");
  lead.className = "lead";
  lead.textContent = "Стол, стартовый код и пределы машины. От списка «Настройки печати» не зависят.";
  box.append(lead);
  if (!fields.length) {
    const empty = document.createElement("p");
    empty.className = "banner";
    empty.textContent = "В настройках принтера по этому фильтру ничего нет.";
    box.append(empty);
    return;
  }
  const section = document.createElement("section");
  section.className = "category";
  for (const field of fields) section.append(renderRow(field));
  box.append(section);
}

function printerVisible(field) {
  if (!matchesQuery(field)) return false;
  if (state.onlyChanged) return isProposed(field.key) || isEdited(field.key);
  return true;
}

function visible(field) {
  if (!matchesQuery(field)) return false;
  if (state.onlyChanged) return isProposed(field.key) || isEdited(field.key);
  return levelVisible(field);
}

function renderRow(field) {
  const row = document.createElement("div");
  row.dataset.key = field.key;
  const classes = ["row"];
  if (isEdited(field.key)) classes.push("edited");
  else if (isProposed(field.key)) classes.push("proposed");
  if (field.readonly) classes.push("readonly");
  row.className = classes.join(" ");

  const name = document.createElement("label");
  name.className = "field-name";
  name.tabIndex = 0;
  const title = document.createElement("span");
  title.className = "name-text";
  title.textContent = field.label;
  const source = document.createElement("span");
  source.className = "source";
  source.textContent = sourceOf(field.key);
  name.append(title, source);
  const show = (event) => showTip(field.hint, event.clientX, event.clientY);
  name.addEventListener("mouseenter", show);
  name.addEventListener("mousemove", show);
  name.addEventListener("mouseleave", hideTip);
  name.addEventListener("focus", (event) => showTip(field.hint, event.target.getBoundingClientRect().left, event.target.getBoundingClientRect().bottom));
  name.addEventListener("blur", hideTip);

  const control = buildControl(field);
  const unit = document.createElement("span");
  unit.className = "unit";
  const raw = valueOf(field.key);
  const unset = raw === "" || raw === null || raw === undefined;
  unit.textContent = unset && field.type === "bool" ? "не в этом пресете" : (field.unit || "");
  row.append(name, control, unit);
  return row;
}

function buildControl(field) {
  const value = valueOf(field.key);
  if (field.type === "text" && (field.readonly || String(value).length > 80 || field.key.includes("gcode"))) {
    const area = document.createElement("textarea");
    area.value = value === null || value === undefined ? "" : String(value);
    area.readOnly = field.readonly;
    area.addEventListener("input", () => setEdit(field, area.value));
    return area;
  }
  if (field.type === "bool") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = value === true || value === "True" || value === "true";
    input.disabled = field.readonly;
    input.addEventListener("change", () => setEdit(field, input.checked));
    return input;
  }
  if (field.type === "enum" || field.type === "extruder") {
    const select = document.createElement("select");
    select.disabled = field.readonly;
    const options = field.options.slice();
    if (value !== "" && value !== null && !options.some((opt) => opt.value === String(value))) {
      options.unshift({ value: String(value), label: String(value) });
    }
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "не задано";
    select.append(empty);
    for (const opt of options) {
      const node = document.createElement("option");
      node.value = opt.value;
      node.textContent = opt.label;
      select.append(node);
    }
    select.value = value === null || value === undefined ? "" : String(value);
    select.addEventListener("change", () => setEdit(field, select.value === "" ? null : select.value));
    return select;
  }
  const input = document.createElement("input");
  input.type = field.type === "int" || field.type === "float" ? "number" : "text";
  if (field.type === "float") input.step = "any";
  if (field.type === "int") input.step = "1";
  input.disabled = field.readonly;
  if (value === null || value === undefined || value === "") input.placeholder = "не в этом пресете";
  input.value = value === null || value === undefined ? "" : String(value);
  input.addEventListener("input", () => {
    if (input.value === "") setEdit(field, null);
    else if (field.type === "int") setEdit(field, Number.parseInt(input.value, 10));
    else if (field.type === "float") setEdit(field, Number(input.value));
    else setEdit(field, input.value);
  });
  return input;
}

function setEdit(field, value) {
  if (typeof value === "number" && Number.isNaN(value)) return;
  state.edits[field.key] = value;
  if (!isEdited(field.key)) delete state.edits[field.key];
  const row = document.querySelector(`[data-key="${CSS.escape(field.key)}"]`);
  if (row) {
    row.classList.toggle("edited", isEdited(field.key));
    row.classList.toggle("proposed", !isEdited(field.key) && isProposed(field.key));
  }
  updateCounts();
}

function updateCounts() {
  const edited = Object.keys(state.edits).filter(isEdited);
  $("counts").textContent = `предложено ${proposedKeys().length} · ваши правки ${edited.length}`;
}

function showTip(text, x, y) {
  const tip = $("tip");
  tip.hidden = false;
  tip.textContent = text;
  const pad = 14;
  const width = Math.min(360, window.innerWidth - 24);
  tip.style.maxWidth = `${width}px`;
  let left = x + pad;
  let top = y + pad;
  tip.style.left = "0px";
  tip.style.top = "0px";
  const rect = tip.getBoundingClientRect();
  if (left + rect.width > window.innerWidth - 8) left = window.innerWidth - rect.width - 8;
  if (top + rect.height > window.innerHeight - 8) top = y - rect.height - pad;
  tip.style.left = `${Math.max(8, left)}px`;
  tip.style.top = `${Math.max(8, top)}px`;
}

function hideTip() {
  $("tip").hidden = true;
}

function payload(status) {
  const preset = structuredClone(state.current);
  for (const [key, value] of Object.entries(state.edits)) {
    if (isEdited(key)) preset.settings[key] = value;
  }
  preset.note = $("note").value;
  if (status) preset.status = status;
  return preset;
}

async function savePreset(preset) {
  const res = await fetch(`/api/presets/${preset.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preset),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || "не сохранилось");
  state.current = preset;
  state.edits = {};
  state.presets = await fetch("/api/presets").then((item) => item.json());
  renderPresetList();
  render();
}

function settingsChanged() {
  return Object.keys(state.edits).some(isEdited);
}

$("visibility").addEventListener("change", () => {
  state.visibility = $("visibility").value;
  localStorage.setItem(VIS_KEY, state.visibility);
  state.openCategories = new Set();
  render();
});

$("only-changed").addEventListener("change", () => {
  state.onlyChanged = $("only-changed").checked;
  render();
});

$("search").addEventListener("input", () => {
  state.query = $("search").value;
  render();
});

$("save").addEventListener("click", async () => {
  try {
    const changed = settingsChanged();
    const next = payload(changed ? "draft" : state.current.status);
    await savePreset(next);
    showMessage(changed ? "Правки записаны. Статус снова «черновик», пока не нажмёте «Утвердить»." : "Записано.");
  } catch (error) {
    showMessage(error.message);
  }
});

$("approve").addEventListener("click", async () => {
  try {
    await savePreset(payload("approved"));
    showMessage("Утверждено. Можно отдавать этот файл на слайс.");
  } catch (error) {
    showMessage(error.message);
  }
});

$("add-print").addEventListener("click", async () => {
  try {
    const next = payload(null);
    next.prints = next.prints || [];
    next.prints.push({
      date: $("print-date").value,
      result: $("print-result").value,
      note: $("print-note").value.trim(),
    });
    next.status = "printed";
    await savePreset(next);
    $("print-note").value = "";
    showMessage("Результат печати записан в пресет.");
  } catch (error) {
    showMessage(error.message);
  }
});

$("custom-open").addEventListener("click", () => {
  renderCustom();
  $("custom-dialog").showModal();
});

$("custom-clear").addEventListener("click", () => {
  state.custom = new Set();
  persistCustom();
  renderCustom();
  render();
});

$("custom-changed").addEventListener("click", () => {
  for (const key of proposedKeys()) state.custom.add(key);
  for (const key of Object.keys(state.edits)) if (isEdited(key)) state.custom.add(key);
  persistCustom();
  renderCustom();
  render();
});

function persistCustom() {
  localStorage.setItem(CUSTOM_KEY, JSON.stringify([...state.custom]));
}

function renderCustom() {
  const box = $("custom-list");
  box.replaceChildren();
  for (const category of state.catalog.categories) {
    if (category.id === "machine_settings") continue;
    const fields = state.catalog.fields.filter((field) => field.category === category.id);
    if (!fields.length) continue;
    const head = document.createElement("h3");
    head.textContent = category.label;
    box.append(head);
    for (const field of fields) {
      const label = document.createElement("label");
      label.className = "custom-item";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = state.custom.has(field.key);
      input.addEventListener("change", () => {
        if (input.checked) state.custom.add(field.key);
        else state.custom.delete(field.key);
        persistCustom();
        render();
      });
      label.append(input, document.createTextNode(field.label));
      box.append(label);
    }
  }
}

load().catch((error) => showMessage(error.message));

$("printer-settings-toggle").addEventListener("click", () => {
  state.printerOpen = $("printer-settings-toggle").getAttribute("aria-expanded") !== "true";
  render();
});

$("printer").addEventListener("change", () => applyCard("machines", $("printer").value));
$("filament").addEventListener("change", () => applyCard("filaments", $("filament").value));
$("nozzle").addEventListener("change", () => applyCard("nozzles", $("nozzle").value));

function openAdd(kind, title) {
  state.addKind = kind;
  $("add-title").textContent = title;
  $("add-name").value = "";
  $("add-id").value = "";
  $("add-dialog").showModal();
}

$("printer-add").addEventListener("click", () => openAdd("machines", "Копия принтера"));
$("filament-add").addEventListener("click", () => openAdd("filaments", "Копия филамента"));
$("nozzle-add").addEventListener("click", () => openAdd("nozzles", "Копия сопла"));

$("add-form").addEventListener("submit", async (event) => {
  if (event.submitter && event.submitter.value !== "save") return;
  event.preventDefault();
  const kind = state.addKind;
  const id = $("add-id").value.trim();
  const current = cardOf(kind);
  if (!current) return;
  const copy = structuredClone(current);
  copy.id = id;
  copy.title = $("add-name").value.trim();
  copy.verified = false;
  copy.warn = copy.warn || "Копия, на этом столе ещё не проверена.";
  copy.source = "copy";
  const res = await fetch(`/api/${kind}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(copy),
  });
  const body = await res.json();
  if (!res.ok) {
    showMessage(body.error || "не сохранилось");
    return;
  }
  state.cards[kind].push({ id, title: copy.title, warn: copy.warn, verified: false, nozzle_mm: copy.nozzle_mm });
  state.cardById[kind][id] = copy;
  $("printer").dataset.signature = "";
  $("filament").dataset.signature = "";
  $("nozzle").dataset.signature = "";
  if (kind === "machines") state.current.printer_id = id;
  if (kind === "filaments") state.current.filament_id = id;
  if (kind === "nozzles") state.current.nozzle_id = id;
  $("add-dialog").close();
  render();
});

const CURA_MODES = {
  machines: {
    title: "Машина из Cura",
    note: "Берутся стол, стартовый код и числовые пределы. Ретракт, температуры и сопло остаются у своих карточек. Драйверы и направляющие в файле Cura не описаны.",
    placeholder: "Название, например Ender или Ghost",
    list: "/api/cura-machines",
    kind: "machines",
    label: (item) => `${item.name}${item.manufacturer ? ` · ${item.manufacturer}` : ""}`,
  },
  filaments: {
    title: "Филамент из Cura",
    note: "Температуры, стол и обдув. Ретракт этой машины из файла Cura не берётся.",
    placeholder: "PLA, PETG, eSUN или 1.75",
    list: "/api/cura-materials",
    kind: "filaments",
    label: (item) => `${item.name}${item.material ? ` · ${item.material}` : ""}${item.diameter ? ` · ${item.diameter} мм` : ""}`,
  },
  nozzles: {
    title: "Сопло из Cura",
    note: "Диаметры из вариантов Cura. Подставляются ширины линий. Стартовый код и ретракт не меняются.",
    placeholder: "0.25, 0.8, 1",
    list: "/api/cura-nozzles",
    kind: "nozzles",
    label: (item) => item.name,
  },
};

let curaMode = "machines";

function openCura(mode) {
  curaMode = mode;
  const spec = CURA_MODES[mode];
  $("cura-title").textContent = spec.title;
  $("cura-note").textContent = spec.note;
  $("cura-search").placeholder = spec.placeholder;
  $("cura-search").value = "";
  searchCura();
  $("cura-dialog").showModal();
}

$("printer-cura").addEventListener("click", () => openCura("machines"));
$("filament-cura").addEventListener("click", () => openCura("filaments"));
$("nozzle-cura").addEventListener("click", () => openCura("nozzles"));

$("cura-search").addEventListener("input", () => searchCura());

async function searchCura() {
  const spec = CURA_MODES[curaMode];
  const query = $("cura-search").value.trim();
  const items = await fetch(`${spec.list}?q=${encodeURIComponent(query)}`).then((res) => res.json());
  const box = $("cura-list");
  box.replaceChildren();
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "custom-item";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Взять";
    button.addEventListener("click", () => importCura(item.id));
    row.append(button, document.createTextNode(spec.label(item)));
    box.append(row);
  }
  if (!items.length) box.textContent = "Ничего не найдено.";
}

async function importCura(id) {
  const spec = CURA_MODES[curaMode];
  const res = await fetch(`${spec.list}/${id}`, { method: "POST" });
  const card = await res.json();
  if (!res.ok) {
    showMessage(card.error || "импорт не удался");
    return;
  }
  const kind = spec.kind;
  state.cardById[kind][id] = card;
  if (!state.cards[kind].some((item) => item.id === id)) {
    state.cards[kind].push({ id, title: card.title, warn: card.warn, verified: false, nozzle_mm: card.nozzle_mm });
  }
  $("printer").dataset.signature = "";
  $("filament").dataset.signature = "";
  $("nozzle").dataset.signature = "";
  if (kind === "machines") state.current.printer_id = id;
  if (kind === "filaments") state.current.filament_id = id;
  if (kind === "nozzles") state.current.nozzle_id = id;
  applyCard(kind, id);
  $("cura-dialog").close();
  showMessage("Карточка взята из Cura. В живой слайсер она не записана.");
}
