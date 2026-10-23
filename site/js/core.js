// Shared helpers: data access, formatting, colours, trace decoding, tooltips.
export const HW = window.HW;
export const $ = (s, el = document) => el.querySelector(s);
export const $$ = (s, el = document) => [...el.querySelectorAll(s)];

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
}
export const svgNS = "http://www.w3.org/2000/svg";
export function s(tag, attrs = {}, ...kids) {
  const e = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) e.setAttribute(k, v);
  for (const k of kids.flat()) if (k !== null && k !== undefined) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
}

export const fmt = {
  pct: (w) => (!w || w[0] === null || w[0] === undefined) ? "–" : `${Math.round(w[0] * 100)}%`,
  ci: (w) => (!w || w[0] === null) ? "" : `${Math.round(w[1] * 100)}–${Math.round(w[2] * 100)}%`,
  sec: (x) => x === null || x === undefined ? "–" : x >= 60 ? `${Math.floor(x / 60)}m ${String(Math.round(x % 60)).padStart(2, "0")}s` : `${Math.round(x)}s`,
  clock: (x) => { x = Math.max(0, x); const m = Math.floor(x / 60), s2 = Math.floor(x % 60); return `${String(m).padStart(2, "0")}:${String(s2).padStart(2, "0")}`; },
  hhmm: (x) => { const hh = Math.floor(x / 3600) % 24, mm = Math.floor((x % 3600) / 60); return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`; },
  int: (x) => x === null || x === undefined ? "–" : Math.round(x).toLocaleString("en-IN"),
  inr: (x) => x === null || x === undefined ? "–" : `₹${x.toFixed(x < 10 ? 2 : 0)}`,
  num: (x, d = 1) => x === null || x === undefined ? "–" : Number(x).toFixed(d),
};

// arms: colour follows the entity everywhere (validated palette, dark surface)
export const ARMS = {
  D: { name: "HoldForMe", color: "#3987e5", short: "D" },
  A: { name: "Human caller", color: "#d95926", short: "A" },
  C: { name: "Basic agent", color: "#199e70", short: "C" },
  B: { name: "Scripted bot", color: "#c98500", short: "B" },
  O: { name: "Oracle", color: "#d55181", short: "O" },
};
export const ARM_ORDER = ["D", "A", "C", "B", "O"];

export const LABELS = ["ringback", "busy_tone", "network_announcement", "ivr_prompt", "ivr_waiting", "hold_music",
  "hold_announcement", "agent_like_recording", "silence", "human_live", "human_listening", "ai_agent", "data_burst", "disconnected"];
export const LABEL_INFO = {
  ringback: { name: "Ringback", color: "#4a5a74" }, busy_tone: { name: "Busy tone", color: "#4a5a74" },
  network_announcement: { name: "Operator message", color: "#6c7a92" }, ivr_prompt: { name: "IVR prompt", color: "#3987e5" },
  ivr_waiting: { name: "IVR waiting", color: "#1d3657" }, hold_music: { name: "Hold music", color: "#9085e9" },
  hold_announcement: { name: "Hold announcement", color: "#c98500" }, agent_like_recording: { name: "Recording that sounds human", color: "#d55181" },
  silence: { name: "Silence", color: "#1a2232" }, human_live: { name: "Live human", color: "#199e70" },
  human_listening: { name: "Human listening", color: "#0f5a40" }, ai_agent: { name: "Bank voicebot", color: "#d95926" },
  data_burst: { name: "Agent-to-agent data", color: "#e66767" }, disconnected: { name: "Disconnected", color: "#0a0f17" },
};
export const TAG_COLOR = { DATA: "var(--t-data)", OFFICIAL: "var(--t-official)", STD: "var(--t-std)", ATLAS: "var(--t-atlas)", ASSUMED: "var(--t-assumed)" };
export const tag = (t) => h("span", { class: `tag ${t}` }, t);

const ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_";
const dec = (str) => Array.from(str, (c) => ALPHA.indexOf(c) / 63);
const traceCache = new Map();
export function decodeTrace(ct) {
  if (traceCache.has(ct.id)) return traceCache.get(ct.id);
  const n = ct.n;
  const t = Array.from({ length: n }, (_, i) => ct.t0 + i * 0.5);
  const tr = {
    id: ct.id, r: ct.r, t, n, label: Array.from(ct.L, (c) => LABELS[ALPHA.indexOf(c)] || "silence"),
    speech: dec(ct.sp), music: dec(ct.mu), synth: dec(ct.sy), room: dec(ct.ro), agent: Array.from(ct.ag, Number),
    segs: ct.seg.map(([a, b, l, x, sp]) => ({ s: a, e: b, l, x, sp })), belief: ct.bel || [], tx: ct.tx || [],
    visited: ct.vis || [], vt: ct.vt || [], qe: ct.qe, dur: ct.dur || (t[n - 1] || 0), hl: ct.hl || ct.r.helpline,
    task: ct.task || ct.r.task, goal: ct.goal || "", pk: ct.pk, br: ct.br, uj: ct.uj, pat: ct.pat, menu: ct.menu || [],
    lang: ct.lang, why: ct.why,
  };
  traceCache.set(ct.id, tr);
  return tr;
}

let tracesPromise = null;
export function loadTraces() {
  if (window.HW_TRACES) return Promise.resolve(window.HW_TRACES);
  if (!tracesPromise) tracesPromise = new Promise((ok, err) => {
    const sc = document.createElement("script");
    sc.src = "data/traces.js?t=" + encodeURIComponent(HW.generated_at || Date.now());
    sc.onload = () => ok(window.HW_TRACES);
    sc.onerror = err;
    document.head.append(sc);
  });
  return tracesPromise;
}

export const bus = new EventTarget();
export const emit = (name, detail) => bus.dispatchEvent(new CustomEvent(name, { detail }));
export const on = (name, fn) => bus.addEventListener(name, (e) => fn(e.detail));

const tipEl = () => document.getElementById("tip");
export function showTip(ev, html) {
  const t = tipEl();
  t.innerHTML = html;
  t.hidden = false;
  const pad = 14, w = t.offsetWidth, hgt = t.offsetHeight;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > innerWidth - 8) x = ev.clientX - w - pad;
  if (y + hgt > innerHeight - 8) y = ev.clientY - hgt - pad;
  t.style.left = x + "px"; t.style.top = y + "px";
}
export const hideTip = () => { tipEl().hidden = true; };

// canvas sized for the device pixel ratio
export function fitCanvas(cv) {
  const r = cv.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(10, Math.round(r.width)), hh = Math.max(10, Math.round(r.height));
  if (cv.width !== w * dpr || cv.height !== hh * dpr) { cv.width = w * dpr; cv.height = hh * dpr; }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h: hh };
}

export function header(kicker, title, lede) {
  return h("header", {}, h("div", { class: "kicker" }, kicker), h("h2", {}, title), h("p", { class: "lede", html: lede }));
}

export function param(key) { return HW.provenance.params.find((p) => p.key === key); }
export function paramTag(key) { const p = param(key); return p ? tag(p.tag) : ""; }

export const helplineName = (id) => (HW.helplines[id] && HW.helplines[id].name) || id;
export function traceTitle(tr) {
  const r = tr.r;
  return `${ARMS[r.arm] ? ARMS[r.arm].name : r.arm} · ${helplineName(r.helpline)} · ${r.scenario === "base" ? r.task : r.scenario}`;
}
export const visible = (el) => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; };
