"use strict";

const app = document.getElementById("app");
const STAT_LABELS = { faith: "Вера", stability: "Стабильность", food: "Еда", followers: "Паства" };

let token = localStorage.getItem("cult-token");
let view = null;
let busy = false;
let editing = null;    // { kind: "cult" } | { kind: "follower", index }
let editError = "";
let notice = "";

/* ── вспомогательное ─────────────────────────────────────────────────────── */

// Создаёт элемент. Текст добавляется только как текст (никакого innerHTML),
// поэтому имя вроде <script> безопасно.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child);
  }
  return node;
}

function fillBar(percent) {
  const fill = el("div", { class: "fill" });
  fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
  return fill;
}

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["X-Session"] = token;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = {};
  try { data = await res.json(); } catch (_) { /* не JSON */ }
  if (!res.ok) {
    const err = new Error(data.error || "Ошибка сервера");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

// Единая точка действий: блокирует кнопки на время запроса и обновляет состояние.
async function act(method, path, body, { keepNotice = false } = {}) {
  if (busy) return;
  busy = true;
  render();
  let restart = false;
  try {
    const data = await api(method, path, body);
    if (data.token) {
      token = data.token;
      localStorage.setItem("cult-token", token);
    }
    view = data.view;
    editing = null;
    editError = "";
    if (!keepNotice) notice = "";
  } catch (err) {
    if (err.status === 401 && path !== "/api/new") {
      restart = true;      // сессия пропала (например, сервер перезапустили)
    } else {
      if (err.data && err.data.view) view = err.data.view;
      if (editing) editError = err.message;
      else notice = err.message;
    }
  } finally {
    busy = false;
  }
  if (restart) {
    token = null;
    localStorage.removeItem("cult-token");
    editing = null;
    notice = "Сессия потерялась (возможно, сервер перезапускали). Игра начата заново.";
    return act("POST", "/api/new", undefined, { keepNotice: true });
  }
  render();
}

function startEdit(target) { editing = target; editError = ""; render(); }
function cancelEdit() { editing = null; editError = ""; render(); }

function confirmNew() {
  if (confirm("Начать заново? Текущая партия будет потеряна.")) act("POST", "/api/new");
}

/* ── компоненты ──────────────────────────────────────────────────────────── */

function editButton(label, onclick) {
  return el("button", { class: "icon", type: "button", title: label, "aria-label": label, disabled: busy, onclick }, "✎");
}

function nameEditor({ value, max, label, onSave }) {
  const input = el("input", { class: "edit", type: "text", value, maxlength: max, "aria-label": label, disabled: busy });
  const save = () => onSave(input.value);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") save();
    if (e.key === "Escape") cancelEdit();
  });
  return el("span", { class: "editor" },
    input,
    el("button", { class: "mini", type: "button", onclick: save, disabled: busy }, "OK"),
    el("button", { class: "mini", type: "button", onclick: cancelEdit }, "Отмена"),
    editError && el("span", { class: "err", role: "alert" }, editError));
}

function renderHeader() {
  const isEditing = editing && editing.kind === "cult";
  const nameBlock = isEditing
    ? nameEditor({
        value: view.cult_name, max: 40, label: "Название культа",
        onSave: (v) => act("POST", "/api/rename/cult", { name: v }),
      })
    : el("h1", { class: "cult-name" }, view.cult_name,
        editButton("Переименовать культ", () => startEdit({ kind: "cult" })));

  const inSetup = view.phase === "setup";
  const progress = el("div", { class: "progress", "aria-hidden": "true" }, fillBar((view.day / view.win_day) * 100));

  return el("header", { class: "top" },
    el("div", {},
      el("p", { class: "sub" }, inSetup ? "Основание культа" : `День ${view.day} из ${view.win_day}`),
      nameBlock,
      inSetup ? null : progress),
    el("button", { class: "ghost small", type: "button", disabled: busy, onclick: confirmNew }, "Новая игра"));
}

function changesRow(changes) {
  return el("div", { class: "changes" }, changes.map((c) =>
    el("span", { class: "chip " + (c.delta > 0 ? "pos" : "neg") },
      `${STAT_LABELS[c.stat]} ${c.delta > 0 ? "+" : "−"}${Math.abs(c.delta)}`)));
}

function renderStory() {
  const box = el("section", { class: "card story", "aria-live": "polite" });
  const v = view;
  if (notice) box.append(el("p", { class: "notice", role: "status" }, notice));

  if (v.phase === "setup") {
    box.append(
      el("h2", {}, "Ты основываешь культ"),
      el("p", { class: "lead" },
        "Дай имя культу и, если хочешь, первым последователям: нажми ✎ рядом с именем. " +
        "Дальше тридцать дней и новый выбор каждый день. Продержись, не потеряв ни веру, ни паству, ни голову."),
      el("button", { class: "primary", type: "button", disabled: busy, onclick: () => act("POST", "/api/start") }, "Основать культ"));
    return box;
  }

  if (v.phase === "won") {
    box.append(
      el("h2", { class: "win" }, "Победа"),
      el("p", { class: "lead" }, v.summary),
      el("button", { class: "primary", type: "button", disabled: busy, onclick: () => act("POST", "/api/new") }, "Сыграть ещё раз"));
    return box;
  }

  for (const line of v.messages) box.append(el("p", { class: "log" }, line));
  if (v.event_text) box.append(el("p", { class: v.phase === "event" ? "lead" : "lead muted" }, v.event_text));

  if (v.phase === "event") {
    box.append(el("ol", { class: "choices" }, v.choices.map((text, i) =>
      el("li", {}, el("button", {
        class: "choice", type: "button", disabled: busy,
        onclick: () => act("POST", "/api/choose", { index: i }),
      }, el("span", { class: "num" }, i + 1), el("span", {}, text))))));
    return box;
  }

  if (v.outcome) box.append(el("p", { class: "outcome" }, v.outcome));
  if (v.changes.length) box.append(changesRow(v.changes));

  if (v.phase === "outcome") {
    box.append(el("button", { class: "primary", type: "button", disabled: busy, onclick: () => act("POST", "/api/next") }, "Следующий день →"));
  } else if (v.phase === "over") {
    box.append(
      el("h2", { class: "doom" }, "Конец"),
      el("p", { class: "lead" }, v.ending),
      el("p", { class: "muted" }, v.summary),
      el("button", { class: "primary", type: "button", disabled: busy, onclick: () => act("POST", "/api/new") }, "Начать заново"));
  }
  return box;
}

function statBar(label, value, cls) {
  const bar = el("div", {
    class: "bar " + cls, role: "progressbar", "aria-label": label,
    "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": value,
  }, fillBar(value));
  return el("div", { class: "stat" }, el("div", { class: "stat-row" }, el("span", {}, label), el("strong", {}, value)), bar);
}

function renderStats() {
  const s = view.stats;
  return el("section", { class: "card" },
    el("h2", { class: "side-title" }, "Состояние"),
    statBar(STAT_LABELS.faith, s.faith, "faith"),
    statBar(STAT_LABELS.stability, s.stability, "stability"),
    el("div", { class: "pair" },
      el("span", {}, "Еда ", el("strong", {}, s.food)),
      el("span", {}, "Паства ", el("strong", {}, s.followers))));
}

function renderFollowers() {
  const items = view.followers.map((f, i) => {
    const isEditing = editing && editing.kind === "follower" && editing.index === i;
    if (isEditing) {
      return el("li", {}, nameEditor({
        value: f.name, max: 24, label: `Новое имя для ${f.name}`,
        onSave: (v) => act("POST", "/api/rename/follower", { index: i, name: v }),
      }));
    }
    return el("li", {},
      el("div", {}, el("span", { class: "fname" }, f.name), el("span", { class: "traits" }, f.traits.join(", "))),
      editButton(`Переименовать: ${f.name}`, () => startEdit({ kind: "follower", index: i })));
  });
  return el("section", { class: "card" },
    el("h2", { class: "side-title" }, `Паства · ${view.followers.length}`),
    el("ul", { class: "followers" }, items));
}

/* ── отрисовка ───────────────────────────────────────────────────────────── */

function render() {
  if (!view) return;
  document.title = `${view.cult_name} · симулятор культа`;
  app.replaceChildren(
    renderHeader(),
    el("main", { class: "layout" }, renderStory(), el("aside", { class: "side" }, renderStats(), renderFollowers())));

  const input = app.querySelector("input.edit");
  if (input) {
    input.focus();
    input.select();
  } else if (view.phase === "outcome") {
    const next = app.querySelector("button.primary");
    if (next && !next.disabled) next.focus({ preventScroll: true });
  }
}

// Цифры 1–9 выбирают вариант, пока не печатаем в поле ввода
document.addEventListener("keydown", (e) => {
  if (!view || view.phase !== "event" || busy) return;
  if (e.ctrlKey || e.metaKey || e.altKey || e.target.closest("input, textarea")) return;
  if (/^[1-9]$/.test(e.key)) {
    const index = Number(e.key) - 1;
    if (index < view.choices.length) act("POST", "/api/choose", { index });
  }
});

async function init() {
  if (token) {
    try {
      view = (await api("GET", "/api/state")).view;
      render();
      return;
    } catch (_) {
      token = null;
      localStorage.removeItem("cult-token");
    }
  }
  await act("POST", "/api/new");
}

init();
