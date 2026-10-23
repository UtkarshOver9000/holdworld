// Chapter 1: the Call Theatre. Replays any simulated call, frame by frame, from its recorded trace.
import { HW, h, s, $, fmt, fitCanvas, decodeTrace, loadTraces, ARMS, LABEL_INFO, header, on, helplineName, showTip, hideTip, visible } from "./core.js";
import { dtmfHz } from "./overview.js";

const ST = { tr: null, t: 0, playing: false, speed: 16, last: 0, audio: false, voice: false, spoken: new Set() };
let els = {};

export function featuredList() {
  const ids = new Set(HW.trace_ids);
  const A = HW.arm_rows, S = HW.stress_rows;
  const find = (pred) => { for (const r of A) { const o = { arm: r[0], hl: r[1], task: r[2], seed: r[3], ok: r[4], tid: r[5], end: r[6] }; if (ids.has(o.tid) && pred(o)) return o.tid; } return null; };
  const sfind = (sc, arm, okPred = () => true) => { for (const r of S) { if (r[0] === sc && r[1] === arm && ids.has(r[4]) && okPred(r)) return r[4]; } for (const r of S) if (r[0] === sc && r[1] === arm && ids.has(r[4])) return r[4]; return null; };
  return [
    ["HoldForMe reaches a person and connects you (bank complaint)", find((o) => o.arm === "D" && o.ok && o.task === "psu_complaint") || find((o) => o.arm === "D" && o.ok && o.task.includes("complaint"))],
    ["HoldForMe finishes a dispute itself and reads the number back (Pine)", find((o) => o.arm === "D" && o.ok && o.task === "psu_dispute") || find((o) => o.arm === "D" && o.ok && ["air_baggage", "ecom_refund"].includes(o.task))],
    ["Cancels a subscription, refuses retention offers (Pine)", find((o) => o.arm === "D" && o.task === "tel_cancel" && o.ok) || find((o) => o.arm === "D" && o.task === "tel_cancel")],
    ["Negotiates a plan discount (Pine)", find((o) => o.arm === "D" && o.task === "tel_negotiate" && o.ok) || find((o) => o.arm === "D" && o.task === "tel_negotiate")],
    ["A recording that sounds human: the scripted bot falls for it", sfind("S6", "B")],
    ["…and HoldForMe doesn't (Google Hold for Me's core problem)", sfind("S6", "D", (r) => r[3])],
    ["The bank's own voicebot answers: agent-to-agent handshake", sfind("S18", "D", (r) => r[3])],
    ["Menu changed since the script was recorded: the bot gets lost", sfind("S19", "B")],
    ["Same changed menu: HoldForMe reads it blind (Sierra)", sfind("S19", "D", (r) => r[3])],
    ["User gives short code 199 from another network", sfind("S13", "B")],
    ["HoldForMe dials the toll-free number instead", sfind("S13", "D", (r) => r[3])],
    ["Voice platform on default settings hangs up on hold music", sfind("S17", "C")],
    ["A person gives up on hold, the way real callers do", find((o) => o.arm === "A" && o.end === "agent_hangup") || find((o) => o.arm === "A")],
    ["40 s disclaimer: HoldForMe waits its turn", sfind("S3", "D", (r) => r[3])],
    ["PIN-gated bank: HoldForMe never types your PIN", sfind("S20", "D", (r) => r[3])],
  ].filter((x) => x[1]);
}

export function render(root) {
  root.append(header("1 · The call theatre", "Watch a call, frame by frame",
    "Every frame below is replayed from a recorded simulation trace: what the helpline really played, what the agent heard (with speech-to-text errors), what it believed, and what it did. Pick a call, press play, and drag the timeline. Turn on <b>tones</b> to hear India's real ringback cadence and the DTMF keypad frequencies; <b>voice</b> reads the prompts aloud."));
  els.picker = h("select", { id: "call-picker", onchange: (e) => open(e.target.value, true) });
  els.play = h("button", { class: "btn primary", id: "call-play", onclick: () => toggle() }, "▶ Play");
  els.scrub = h("input", { type: "range", min: 0, max: 100, step: 0.1, value: 0, oninput: (e) => seek(+e.target.value) });
  els.clock = h("span", { class: "clock" }, "00:00");
  els.speed = h("div", { class: "seg" }, [1, 4, 16, 64].map((v) => h("button", { class: v === ST.speed ? "on" : "", onclick: (e) => { ST.speed = v; [...els.speed.children].forEach((b) => b.classList.toggle("on", b === e.target)); } }, `${v}×`)));
  const skip = h("button", { class: "btn", id: "call-skip", onclick: () => skipHold() }, "⏭ Skip to pickup");
  const tone = h("button", { class: "btn", onclick: (e) => { ST.audio = !ST.audio; e.target.classList.toggle("on", ST.audio); audio.init(); } }, "🔊 tones");
  const voice = h("button", { class: "btn", onclick: (e) => { ST.voice = !ST.voice; e.target.classList.toggle("on", ST.voice); if (!ST.voice) speechSynthesis.cancel(); } }, "🗣 voice");
  root.append(h("div", { class: "transport", id: "call-transport" }, els.picker, els.play, h("button", { class: "btn", onclick: () => seek(0) }, "⟲"), els.speed, skip, tone, voice, els.scrub, els.clock));
  els.head = h("div", { class: "card", id: "call-head", style: { marginBottom: "14px" } });
  root.append(els.head);
  els.tree = h("div", { class: "tree" });
  els.menuText = h("div", { class: "chips" });
  els.chat = h("div", { class: "chat", id: "call-chat" });
  els.ear = h("canvas", { class: "ear", id: "call-ear" });
  els.keypad = h("div", { class: "keypad" }, ..."123456789*0#".split("").map((k) => h("div", { "data-k": k }, k, h("small", {}, ""))));
  els.phone = h("div", { class: "phone", id: "call-phone" }, h("div", { class: "notch" }), h("div", { class: "notes" }));
  els.status = h("div", {});
  root.append(h("div", { class: "theatre" },
    h("div", { class: "col" },
      h("div", { class: "card", id: "call-tree" }, h("h3", {}, "The menu, as the agent finds it"), h("div", { class: "sub" }, "Revealed as it's explored · ● current · ◌ the goal"), els.tree),
      h("div", { class: "card tight" }, h("h3", {}, "Menu as text ", h("span", { class: "muted", style: { fontWeight: 400, fontSize: "12px" } }, "(Google's Direct My Call)")), els.menuText)),
    h("div", { class: "col" },
      h("div", { class: "card" }, h("h3", {}, "The conversation"), els.chat),
      h("div", { class: "card", id: "call-ear-card" }, h("h3", {}, "What the agent hears ", h("span", { class: "muted", style: { fontWeight: 400, fontSize: "12px" } }, "top band = truth · lines = classifier scores · bottom = belief 'is this a person?'")), els.ear, earLegend())),
    h("div", { class: "col right" },
      h("div", { class: "card" }, h("h3", {}, "Keypad (ITU-T Q.23 tones)"), els.keypad),
      h("div", { class: "card" }, h("h3", {}, "Your phone"), els.phone),
      h("div", { class: "card", id: "call-status" }, h("h3", {}, "Live state"), els.status))));
  loadTraces().then(() => { fillPicker(); const first = featuredList()[0]; if (first) open(first[1], false); });
  on("open-trace", ({ id, play, t }) => { loadTraces().then(() => { document.getElementById("call").scrollIntoView({ behavior: "smooth" }); open(id, play); if (t !== undefined) seek(t); }); });
  requestAnimationFrame(tick);
}

function earLegend() {
  const keys = ["ivr_prompt", "hold_music", "hold_announcement", "agent_like_recording", "human_live", "ai_agent", "ringback", "silence"];
  return h("div", { class: "legend", style: { marginTop: "6px" } }, keys.map((k) => h("span", {}, h("i", { style: { background: LABEL_INFO[k].color } }), LABEL_INFO[k].name)),
    h("span", {}, h("i", { style: { background: "#e6edf7" } }), "speech"), h("span", {}, h("i", { style: { background: "#9085e9" } }), "music"),
    h("span", {}, h("i", { style: { background: "#c98500" } }), "synthetic voice"), h("span", {}, h("i", { style: { background: "#199e70" } }), "room sound"));
}

function fillPicker() {
  const sel = els.picker;
  sel.innerHTML = "";
  const g1 = h("optgroup", { label: "Featured calls" });
  for (const [title, id] of featuredList()) g1.append(h("option", { value: id }, title));
  sel.append(g1);
  const titles = Object.fromEntries(HW.stress.scenarios.map((x) => [x.id, x.title]));
  const g2 = h("optgroup", { label: "Stress scenarios (seed 0)" });
  const seen = new Set();
  for (const r of HW.stress_rows) {
    const [sc, arm, seed, pass, tid] = r;
    if (seed !== 0 || seen.has(tid) || !HW.trace_ids.includes(tid)) continue;
    seen.add(tid);
    g2.append(h("option", { value: tid }, `${sc} · ${ARMS[arm]?.name || arm} · ${titles[sc]} ${pass ? "✓" : "✗"}`));
  }
  sel.append(g2);
  const g3 = h("optgroup", { label: "Every task (seed 0)" });
  for (const r of HW.arm_rows) {
    const [arm, hl, task, seed, ok, tid] = r;
    if (seed !== 0 || !HW.trace_ids.includes(tid) || seen.has(tid)) continue;
    seen.add(tid);
    g3.append(h("option", { value: tid }, `${ARMS[arm]?.name || arm} · ${helplineName(hl)} · ${task} ${ok ? "✓" : "✗"}`));
  }
  sel.append(g3);
}

export function open(id, play) {
  const ct = window.HW_TRACES && window.HW_TRACES[id];
  if (!ct) return;
  ST.tr = decodeTrace(ct);
  els.picker.value = id;
  ST.t = 0; ST.spoken = new Set(); speechSynthesis.cancel?.();
  els.scrub.max = ST.tr.dur;
  buildHead(); buildTree(); renderChat(true); renderPhone(true); bindEar(); renderAll();
  ST.playing = !!play;
  els.play.textContent = ST.playing ? "❚❚ Pause" : "▶ Play";
}
export const theatre = { open, seek: (t) => seek(t), play: () => { ST.playing = true; els.play.textContent = "❚❚ Pause"; }, setSpeed: (v) => { ST.speed = v; [...els.speed.children].forEach((b) => b.classList.toggle("on", b.textContent === `${v}×`)); }, skipHold: () => skipHold(), state: ST };

function toggle() { ST.playing = !ST.playing; els.play.textContent = ST.playing ? "❚❚ Pause" : "▶ Play"; if (ST.playing) audio.init(); }
function seek(t) { if (!ST.tr) return; ST.t = Math.max(0, Math.min(ST.tr.dur, t)); ST.spoken = new Set(ST.tr.tx.filter((x) => x.t < ST.t).map((x, i) => x.t + x.text)); speechSynthesis.cancel?.(); renderChat(true); renderPhone(true); renderAll(); }
function skipHold() { if (!ST.tr) return; const tr = ST.tr; const target = tr.pk ? tr.pk - 6 : tr.qe ? tr.qe + 5 : ST.t; seek(target); }

function buildHead() {
  const tr = ST.tr, r = tr.r, hl = HW.helplines[r.helpline];
  const ok = r.success;
  const task = hl.tasks.find((x) => x.id === r.task);
  const sc = r.scenario !== "base" ? HW.stress.scenarios.find((x) => x.id === r.scenario) : null;
  els.head.innerHTML = "";
  els.head.append(
    h("div", { class: "callhead" }, h("span", { class: "goal" }, "“" + (task ? task.goal : r.task) + "”"),
      h("span", { class: `badge ${ok ? "ok" : "bad"}` }, ok ? "SUCCESS" : "FAILED"), h("span", { class: "badge" }, r.end_reason.replace(/_/g, " "))),
    h("div", { class: "chips", style: { marginTop: "8px" } },
      h("span", { class: "chip live", style: { borderColor: ARMS[r.arm]?.color } }, `caller: ${ARMS[r.arm]?.name || r.arm}`),
      h("span", { class: "chip" }, `${hl.name} (${hl.brand})`), h("span", { class: "chip" }, `menu source: ${hl.tag === "OFFICIAL" ? "official page" : "assumed"}`),
      h("span", { class: "chip" }, `mode ${r.mode}`), h("span", { class: "chip" }, r.platform.replace("_", " ")),
      h("span", { class: "chip" }, `goal type: ${r.goal_type.replace("_", " ")}${r.pine ? " · Pine: " + r.pine : ""}`),
      sc ? h("span", { class: "chip live" }, `${sc.id}: ${sc.title}`) : null,
      h("span", { class: "chip" }, `language: ${tr.lang === "hi" ? "Hindi" : "English"}`)));
}

// ---------------------------------------------------------------- the menu tree
function buildTree() {
  const tr = ST.tr, hl = HW.helplines[tr.r.helpline];
  els.tree.innerHTML = "";
  const nodes = hl.nodes, lang = tr.lang === "hi" ? 2 : 1;
  const label = {}, parent = {};
  for (const [nid, n] of Object.entries(nodes)) for (const o of n.opts) if (!parent[o[3]]) { parent[o[3]] = nid; label[o[3]] = [o[0], o[lang] || o[1]]; }
  for (const [nid, n] of Object.entries(nodes)) if (n.next && !parent[n.next]) { parent[n.next] = nid; label[n.next] = ["#", fieldName(n.field)]; }
  for (const [nid, n] of Object.entries(nodes)) if (n.agent && !parent[n.agent]) { parent[n.agent] = nid; label[n.agent] = ["9", "executive"]; }
  const target = (hl.tasks.find((x) => x.id === tr.r.task) || {}).target;
  const anc = new Set(); let c = target; while (c) { anc.add(c); c = parent[c]; }
  els.treeRows = [];
  const add = (nid, depth) => {
    const n = nodes[nid];
    const [k, lbl] = label[nid] || ["", "Start: welcome + language"];
    const row = h("div", { class: "trow", "data-id": nid, style: { paddingLeft: depth * 14 + "px" } },
      h("span", { class: "tk" }, k), h("span", { class: "tl" }, leafName(n, lbl)));
    row.dataset.depth = depth;
    els.treeRows.push({ nid, row, depth, parent: parent[nid], target: nid === target, anc: anc.has(nid) });
    els.tree.append(row);
    for (const o of n.opts) if (nodes[o[3]] && parent[o[3]] === nid) add(o[3], depth + 1);
    if (n.next && nodes[n.next] && parent[n.next] === nid) add(n.next, depth + 1);
    if (n.agent && nodes[n.agent] && parent[n.agent] === nid) add(n.agent, depth + 1);
  };
  add(hl.root, 0);
  els.tree.querySelectorAll(".trow").forEach((r) => r.addEventListener("click", () => {
    const i = tr.visited.indexOf(r.dataset.id); if (i >= 0) seek(tr.vt[i] || 0);
  }));
}
function fieldName(f) { return { acct_last4: "last 4 digits", acct_last5: "last 5 digits", card_last4: "card digits", dob: "date of birth", birth_year: "birth year", customer_id: "customer ID", tpin: "PIN (user types it)", mobile: "mobile number", otp: "OTP", ticket: "complaint no.", consumer_no: "consumer no.", order_id: "order no.", file_no: "file no.", pnr: "booking ref" }[f] || f; }
function leafName(n, lbl) {
  if (n.type === "queue") return `☎ ${lbl} → queue: ${n.dept}`;
  if (n.type === "fact") return `ℹ ${lbl}`;
  if (n.type === "action") return `✓ ${lbl}`;
  if (n.type === "collect") return `⌨ enter ${fieldName(n.field)}`;
  if (n.type === "message") return `⚠ ${lbl} (dead end)`;
  return lbl;
}
function updateTree() {
  const tr = ST.tr, t = ST.t;
  const visitedNow = [];
  tr.visited.forEach((nid, i) => { if ((tr.vt[i] ?? 0) <= t) visitedNow.push(nid); });
  const vis = new Set(visitedNow), cur = visitedNow[visitedNow.length - 1];
  const expanded = new Set(visitedNow.concat([HW.helplines[tr.r.helpline].root]));
  for (const r of els.treeRows) {
    const show = r.depth <= 1 || expanded.has(r.parent) || vis.has(r.nid);
    r.row.style.display = show ? "" : "none";
    r.row.classList.toggle("visited", vis.has(r.nid));
    r.row.classList.toggle("current", r.nid === cur && t < tr.dur);
    r.row.classList.toggle("target", r.target);
  }
}

// ---------------------------------------------------------------- conversation
const WHO = { ivr: "IVR", network: "Operator", exec: "Executive", agent: "Caller", platform: "Voice platform", hold: "Hold", user: "You" };
function renderChat(full) {
  const tr = ST.tr, t = ST.t;
  if (full) { els.chat.innerHTML = ""; els.chatN = 0; }
  const items = tr.tx;
  while (els.chatN < items.length && items[els.chatN].t <= t) {
    const x = items[els.chatN++];
    els.chat.append(msg(x, tr));
    if (ST.voice && ST.speed <= 4 && !full) speak(x);
  }
  els.chat.scrollTop = els.chat.scrollHeight;
}
function msg(x, tr) {
  const who = x.who, lab = x.label;
  if (lab === "dtmf") return h("div", { class: "msg event" }, `⌨ ${who === "agent" ? ARMS[tr.r.arm]?.name || "caller" : who} pressed ${x.text}  ·  ${x.text.split("").map(dtmfHz).filter(Boolean)[0] || ""}`);
  if (lab === "bridge") return h("div", { class: "msg event" }, "📞 Person detected — ringing your phone");
  if (lab === "alert") return h("div", { class: "msg event" }, { otp: "📱 Asked you for the OTP the bank just sent", press_key: "📱 Asked you to tap a key on your phone", secret: "🔒 Asked you to type your PIN yourself", primed: "📱 Warned you: a person should answer soon", human: "📱 Alerted you" }[x.text] || `📱 ${x.text}`);
  const cls = who === "agent" ? "agent" : who === "platform" ? "platform" : who === "exec" ? "exec" : who === "network" ? "network" : "ivr";
  let name = WHO[who] || who;
  if (who === "agent") name = ARMS[tr.r.arm]?.name || "Caller";
  if (who === "exec" && lab === "ai_agent") name = "Bank voicebot";
  if (lab === "hold_announcement") name = "Hold message";
  if (lab === "agent_like_recording") name = "Recording (sounds human!)";
  const intent = x.intent ? h("span", { class: "chip", style: { marginLeft: "6px", fontSize: "10px" } }, x.intent) : null;
  return h("div", { class: `msg ${cls}` }, h("span", { class: "who" }, `${fmt.clock(x.t)} · ${name}`, intent), x.text);
}
function speak(x) {
  if (!("speechSynthesis" in window) || x.label === "dtmf" || x.label === "bridge" || x.label === "alert") return;
  const u = new SpeechSynthesisUtterance(x.text.slice(0, 220));
  u.lang = /[ऀ-ॿ]/.test(x.text) ? "hi-IN" : "en-IN";
  u.rate = Math.min(2, ST.speed);
  speechSynthesis.speak(u);
}

// ---------------------------------------------------------------- phone + status
function renderPhone(full) {
  const tr = ST.tr, t = ST.t, notes = els.phone.querySelector(".notes");
  const items = [];
  const add = (b, txt) => items.push([b, txt]);
  if (t < 3) add("HoldForMe", `Calling ${helplineName(tr.r.helpline)} for you…`);
  for (const x of tr.tx) {
    if (x.t > t) break;
    if (x.label === "alert") add(`HoldForMe · ${fmt.clock(x.t)}`, { otp: "The bank sent you an OTP. Tap to share it.", press_key: "Please tap the key shown on your keypad.", secret: "Type your PIN yourself; I never see it.", primed: "A person should pick up in about a minute. Keep your phone close.", human: "A person is on the line." }[x.text] || x.text);
    if (x.label === "bridge") add(`HoldForMe · ${fmt.clock(x.t)}`, "A real person answered. Connecting you now.");
  }
  const ringing = tr.br !== null && tr.br !== undefined && t >= tr.br && (tr.uj === null || tr.uj === undefined || t < tr.uj);
  els.phone.classList.toggle("ringing", ringing);
  if (ringing) add("Incoming call", "HoldForMe — executive waiting");
  if (tr.uj !== null && tr.uj !== undefined && t >= tr.uj) add("On call", `Connected to the executive at ${fmt.clock(tr.uj)}`);
  if (t >= tr.dur - 0.5) add("Call ended", tr.r.end_reason.replace(/_/g, " "));
  const key = JSON.stringify(items);
  if (notes.dataset.renderKey !== key) {
    notes.replaceChildren(...items.map(([title, body]) => h("div", { class: "note" }, h("b", {}, title), body)));
    notes.dataset.renderKey = key;
  }
}

function statusUpdate() {
  const tr = ST.tr, t = ST.t, r = tr.r;
  const i = Math.max(0, Math.min(tr.n - 1, Math.round((t - tr.t[0]) / 0.5)));
  const lab = tr.label[i];
  let phase = "Dialling";
  if (t >= 6) phase = "Phone menu (IVR)";
  if (tr.qe !== null && tr.qe !== undefined && t >= tr.qe) phase = "On hold";
  if (tr.pk !== null && tr.pk !== undefined && t >= tr.pk) phase = lab === "ai_agent" ? "Bank voicebot" : "Executive on the line";
  if (tr.uj !== null && tr.uj !== undefined && t >= tr.uj) phase = "Connected to you";
  if (t >= tr.dur - 0.5) phase = "Ended: " + r.end_reason.replace(/_/g, " ");
  let bel = null;
  for (const [bt, bv] of tr.belief) { if (bt > t) break; bel = bv; }
  const belTxt = bel === null ? "–" : bel > 1.2 ? `person (${bel.toFixed(1)})` : bel < -1 ? `recording (${bel.toFixed(1)})` : `unsure (${bel.toFixed(1)})`;
  let patience = null;
  if (tr.pk !== null && tr.pk !== undefined && t >= tr.pk && !(tr.uj !== null && tr.uj !== undefined && t >= tr.uj)) {
    let reset = tr.pk + 3.5;
    for (const x of tr.tx) { if (x.t > t) break; if (x.t >= tr.pk && x.who === "agent" && x.label === "caller") reset = x.t + (x.intent === "stall" ? 50 : 0); }
    patience = Math.max(0, Math.min(1, 1 - (t - reset) / Math.max(1, tr.pat)));
  }
  els.status.innerHTML = "";
  const row = (k, v) => h("div", { class: "stat" }, h("span", {}, k), h("b", {}, v));
  els.status.append(
    row("Phase", phase), row("Truth now", (LABEL_INFO[lab] || {}).name || lab),
    row("Agent believes", belTxt),
    row("On hold for", tr.qe !== null && tr.qe !== undefined && t >= tr.qe ? fmt.sec(Math.min(t, tr.pk || t) - tr.qe) : "–"),
    row("Time to a person", tr.pk ? fmt.sec(tr.pk) : "never"),
    row("Detection delay", r.detect_latency !== null && r.detect_latency !== undefined ? `${r.detect_latency.toFixed(1)} s` : "–"),
    row("False alerts", String(r.false_alerts)), row("Cost (₹, est.)", fmt.inr(r.cost_inr)),
  );
  if (patience !== null) els.status.append(h("div", { style: { marginTop: "8px", fontSize: "12px", color: "var(--text-2)" } }, `Executive's patience with silence (${tr.pat} s, assumed)`), h("div", { class: "meter patience" }, h("i", { style: { width: patience * 100 + "%" } })));
  if (tr.why && t >= (tr.br || tr.pk || 1e9)) els.status.append(h("div", { class: "chips", style: { marginTop: "8px" } }, Object.entries(tr.why).map(([k, v]) => h("span", { class: "chip" }, `${k}: ${v === true ? "yes" : v}`))));
}

// ---------------------------------------------------------------- the ear
function drawEar() {
  const tr = ST.tr, t = ST.t, cv = els.ear;
  const { ctx, w, h: H } = fitCanvas(cv);
  ctx.clearRect(0, 0, w, H);
  const win = 60, t0 = Math.max(0, t - win * 0.75), t1 = t0 + win;
  const X = (x) => (x - t0) / win * w;
  const band = 22, rowH = 26, top = band + 8;
  const ov = H - 26;
  for (let i = 0; i < tr.n; i++) {
    const ft = tr.t[i];
    if (ft < t0 - 0.5 || ft > t1) continue;
    ctx.fillStyle = (LABEL_INFO[tr.label[i]] || {}).color || "#222";
    ctx.fillRect(X(ft - 0.5), 0, Math.ceil(w / win * 0.5) + 1, band);
  }
  const series = [["speech", "#e6edf7"], ["music", "#9085e9"], ["synth", "#c98500"], ["room", "#199e70"]];
  series.forEach(([k, col], si) => {
    const y0 = top + si * rowH;
    ctx.fillStyle = "#0a101b"; ctx.fillRect(0, y0, w, rowH - 4);
    ctx.strokeStyle = col; ctx.lineWidth = 1.6; ctx.beginPath();
    let first = true;
    for (let i = 0; i < tr.n; i++) {
      const ft = tr.t[i]; if (ft < t0 - 0.5 || ft > t1 || ft > t) continue;
      const y = y0 + (rowH - 6) * (1 - tr[k][i]) + 1;
      if (first) { ctx.moveTo(X(ft), y); first = false; } else ctx.lineTo(X(ft), y);
    }
    ctx.stroke();
  });
  // belief row
  const by = top + 4 * rowH, bh = ov - by - 8;
  if (tr.belief.length) {
    const Y = (v) => by + bh * (1 - (Math.max(-4, Math.min(4, v)) + 4) / 8);
    ctx.fillStyle = "#0a101b"; ctx.fillRect(0, by, w, bh);
    ctx.setLineDash([3, 3]); ctx.strokeStyle = "#199e70"; ctx.beginPath(); ctx.moveTo(0, Y(1.2)); ctx.lineTo(w, Y(1.2)); ctx.stroke();
    ctx.strokeStyle = "#d55181"; ctx.beginPath(); ctx.moveTo(0, Y(-1)); ctx.lineTo(w, Y(-1)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#6c7a92"; ctx.font = "10px IBM Plex Mono"; ctx.fillText("person ↑", 4, Y(1.2) - 3); ctx.fillText("recording ↓", 4, Y(-1) + 11);
    ctx.fillStyle = "#3987e5";
    for (const [bt, bv] of tr.belief) { if (bt < t0 || bt > t1 || bt > t) continue; ctx.beginPath(); ctx.arc(X(bt), Y(bv), 2.6, 0, Math.PI * 2); ctx.fill(); }
  } else { ctx.fillStyle = "#6c7a92"; ctx.font = "11px IBM Plex Sans"; ctx.fillText("this caller has no live 'is it a person?' model", 6, by + 14); }
  // events
  let tagRow = 0;
  const ev = (x, col, txt) => {
    if (x === null || x === undefined || x < t0 || x > t1) return;
    ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(X(x), 0); ctx.lineTo(X(x), ov - 4); ctx.stroke();
    ctx.font = "600 10px IBM Plex Mono"; const tw = ctx.measureText(txt).width + 8, ty = 2 + (tagRow++ % 2) * 10;
    const tx = Math.min(w - tw - 2, X(x) + 3);
    ctx.fillStyle = "#070b12d8"; ctx.fillRect(tx, ty, tw, 12); ctx.fillStyle = col; ctx.fillText(txt, tx + 4, ty + 9);
  };
  ev(tr.pk, "#199e70", "person picks up");
  ev(tr.br, "#3987e5", "connect user");
  ev(tr.uj, "#5ef0b4", "user joins");
  for (const x of tr.tx) if (x.who === "agent" && (x.intent === "probe" || x.intent === "stall")) ev(x.t, "#c98500", x.intent === "probe" ? "'hello?'" : "stall");
  // cursor
  ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(X(t), 0); ctx.lineTo(X(t), ov - 4); ctx.stroke();
  // overview of the whole call
  ctx.fillStyle = "#0a101b"; ctx.fillRect(0, ov, w, 20);
  const step = Math.max(1, Math.floor(tr.n / w));
  for (let i = 0; i < tr.n; i += step) { ctx.fillStyle = (LABEL_INFO[tr.label[i]] || {}).color || "#222"; ctx.fillRect(tr.t[i] / tr.dur * w, ov + 4, Math.max(1, w / tr.n * step) + 0.5, 12); }
  ctx.strokeStyle = "#fff"; ctx.strokeRect(t0 / tr.dur * w, ov + 1, Math.max(4, win / tr.dur * w), 18);
  ctx.fillStyle = "#6c7a92"; ctx.font = "10px IBM Plex Mono"; ctx.textAlign = "right"; ctx.fillText(`window ${fmt.clock(t0)}–${fmt.clock(t1)} · whole call below`, w - 4, by - 4); ctx.textAlign = "left";
}
let earBound = false;
function bindEar() {
  if (earBound) return; earBound = true;
  els.ear.addEventListener("click", (e) => { const r = els.ear.getBoundingClientRect(); if (e.clientY - r.top > r.height - 26) seek((e.clientX - r.left) / r.width * ST.tr.dur); });
  els.ear.addEventListener("mousemove", (e) => {
    const tr = ST.tr; if (!tr) return; const r = els.ear.getBoundingClientRect();
    const t0 = Math.max(0, ST.t - 45), ft = t0 + (e.clientX - r.left) / r.width * 60;
    const i = Math.max(0, Math.min(tr.n - 1, Math.round((ft - tr.t[0]) / 0.5)));
    showTip(e, `<b>${fmt.clock(tr.t[i])}</b> ${(LABEL_INFO[tr.label[i]] || {}).name}<br>speech ${tr.speech[i].toFixed(2)} · music ${tr.music[i].toFixed(2)}<br>synthetic ${tr.synth[i].toFixed(2)} · room ${tr.room[i].toFixed(2)}`);
  });
  els.ear.addEventListener("mouseleave", hideTip);
}

function updateKeypad() {
  const tr = ST.tr, t = ST.t;
  els.keypad.querySelectorAll("div").forEach((d) => { d.classList.remove("hit"); d.querySelector("small").textContent = ""; });
  for (const x of tr.tx) {
    if (x.label !== "dtmf" || x.t > t) continue;
    const k = Math.floor((t - x.t) / 0.2);
    if (k >= 0 && k < x.text.length && t - x.t < x.text.length * 0.2 + 0.25) {
      const d = els.keypad.querySelector(`[data-k="${CSS.escape(x.text[k])}"]`);
      if (d) { d.classList.add("hit"); d.querySelector("small").textContent = dtmfHz(x.text[k]).replace(" Hz", ""); audio.dtmf(x.text[k], x.t + k * 0.2); }
    }
  }
}

function tick(now) {
  requestAnimationFrame(tick);
  const dt = ST.last ? Math.min(0.1, (now - ST.last) / 1000) : 0; ST.last = now;
  if (!ST.tr) return;
  bindEar();
  if (ST.playing) {
    ST.t += dt * ST.speed;
    if (ST.t >= ST.tr.dur) { ST.t = ST.tr.dur; ST.playing = false; els.play.textContent = "▶ Play"; }
  }
  if (!visible(els.ear) && !ST.playing) return;
  renderAll(now);
  audio.frame(ST);
}

function renderAll(now = performance.now()) {
  if (!ST.tr) return;
  els.scrub.value = ST.t; els.clock.textContent = fmt.clock(ST.t);
  renderChat(false); updateTree(); drawEar(); updateKeypad(); statusUpdate();
  if (Math.floor(now / 250) !== els.lastPhone) { els.lastPhone = Math.floor(now / 250); renderPhone(); }
  // menus shown as text (Direct My Call): one per menu reached so far
  const mt = ST.tr.menu || [];
  const reached = 1 + ST.tr.vt.filter((v, i) => v <= ST.t && HW.helplines[ST.tr.r.helpline].nodes[ST.tr.visited[i]]?.type === "menu").length;
  const key = ST.tr.id + ":" + Math.min(reached, mt.length);
  if (els.menuText.dataset.id !== key) {
    els.menuText.dataset.id = key;
    els.menuText.innerHTML = "";
    if (!mt.length) els.menuText.append(h("span", { class: "muted" }, "This caller doesn't show menus as text."));
    mt.slice(0, Math.min(reached, mt.length)).slice(-3).forEach((m, i) => els.menuText.append(h("div", { style: { width: "100%" } }, h("div", { class: "muted", style: { fontSize: "11px" } }, i === 0 && reached <= 1 ? "language menu" : "menu heard"), h("div", { class: "chips" }, m.map((x) => h("span", { class: "chip" }, x))))));
  }
}

// ---------------------------------------------------------------- audio: India's real tones
const audio = {
  ctx: null, ring: null, music: null, lastKey: -1,
  init() { if (this.ctx) return; try { this.ctx = new AudioContext(); } catch { /* no audio */ } },
  frame(st) {
    if (!this.ctx) return;
    const tr = st.tr, t = st.t;
    const on = st.audio && st.playing && st.speed <= 4;
    const i = Math.max(0, Math.min(tr.n - 1, Math.round((t - tr.t[0]) / 0.5)));
    const lab = tr.label[i];
    // ringback: 400 Hz modulated by 25 Hz, cadence 0.4 on 0.2 off 0.4 on 2.0 off (Asterisk [in])
    let ringOn = false;
    if (on && lab === "ringback") { const c = t % 3.0; ringOn = c < 0.4 || (c >= 0.6 && c < 1.0); }
    this.ring = this.tone(this.ring, ringOn, () => {
      const o = this.ctx.createOscillator(), m = this.ctx.createOscillator(), mg = this.ctx.createGain(), g = this.ctx.createGain();
      o.frequency.value = 400; m.frequency.value = 25; mg.gain.value = 0.5; g.gain.value = 0.08;
      m.connect(mg); mg.connect(g.gain); o.connect(g); g.connect(this.ctx.destination); o.start(); m.start();
      return { stop: () => { o.stop(); m.stop(); } };
    });
    this.music = this.tone(this.music, on && lab === "hold_music", () => {
      const g = this.ctx.createGain(); g.gain.value = 0.035; g.connect(this.ctx.destination);
      const os = [261.6, 329.6, 392.0, 493.9].map((f, j) => { const o = this.ctx.createOscillator(); o.type = "triangle"; o.frequency.value = f; const og = this.ctx.createGain(); og.gain.value = 0; o.connect(og); og.connect(g); o.start(); const lfo = setInterval(() => { og.gain.setTargetAtTime(Math.random() < 0.5 ? 0.6 : 0, this.ctx.currentTime, 0.3); }, 700 + j * 150); return { o, lfo }; });
      return { stop: () => os.forEach(({ o, lfo }) => { clearInterval(lfo); o.stop(); }) };
    });
  },
  tone(node, want, make) { if (want && !node) return make(); if (!want && node) { node.stop(); return null; } return node; },
  dtmf(k, when) {
    if (!this.ctx || !ST.audio || !ST.playing || ST.speed > 4 || this.lastKey === when) return;
    this.lastKey = when;
    const grid = ["123", "456", "789", "*0#"], R = [697, 770, 852, 941], C = [1209, 1336, 1477];
    for (let r = 0; r < 4; r++) { const c = grid[r].indexOf(k); if (c < 0) continue;
      for (const f of [R[r], C[c]]) { const o = this.ctx.createOscillator(), g = this.ctx.createGain(); o.frequency.value = f; g.gain.value = 0.06; o.connect(g); g.connect(this.ctx.destination); o.start(); o.stop(this.ctx.currentTime + 0.1); } }
  },
};
