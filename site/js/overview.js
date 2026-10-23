// Chapter 0: what HoldWorld is, and an animated pass of one real simulated call through the system.
import { HW, h, fmt, fitCanvas, visible, decodeTrace, loadTraces, ARMS, emit } from "./core.js";

export function featuredTraceId(pred) {
  const ids = HW.trace_ids;
  const rows = HW.arm_rows;
  for (const r of rows) {
    const [arm, hl, task, seed, ok, tid] = r;
    if (ids.includes(tid) && pred({ arm, hl, task, seed, ok, tid })) return tid;
  }
  return ids[0];
}

export function render(root) {
  const real = HW.real, hold = HW.holdout, proof = HW.proof || {};
  const nCalls = HW.arm_rows.length + HW.stress_rows.length;
  root.append(
    h("header", {},
      h("div", { class: "kicker" }, "HoldForMe · simulation lane"),
      h("h1", {}, "HoldWorld: a simulated India of customer-care lines"),
      h("p", { class: "lede", html: `An AI agent dials a helpline, gets through the phone menu, waits on hold, notices the moment a real person answers, and either connects you or finishes the task itself. HoldWorld builds the helplines it calls from <b>official Indian menus</b>, runs the queue on <b>${fmt.int(real.records)} real call-centre records</b>, and scores every half-second of every call against the truth. It also models what <b>Google Hold for Me</b>, <b>Pine</b> and <b>Sierra</b> do, so you can see where HoldForMe stands.` })),
    h("canvas", { class: "hero-canvas", id: "hero-cv" }),
    h("div", { class: "row", style: { marginTop: "8px" } }, h("span", { class: "muted", id: "hero-cap" }, "Loading the featured call…"), h("span", { class: "sp" }),
      h("button", { class: "btn", onclick: () => emit("open-trace", { id: featured, play: true }) }, "Open this call in the theatre →")),
    h("div", { class: "kpis" },
      kpi(fmt.int(real.records), "real calls replayed", "Anonymous Bank, every call of 1999", "DATA"),
      kpi(hold.corr_wait.toFixed(3), "held-out replay match", `wait correlation on ${hold.days.length} days the fit never saw`, "DATA"),
      kpi(Object.keys(HW.helplines).length, "helpline archetypes", "3 from official bank menus", "OFFICIAL"),
      kpi(fmt.int(nCalls), "simulated calls", "5 callers, 20 stress scenarios", "DATA"),
      kpi(proof.total ? `${proof.passed}/${proof.total}` : "–", "tests passing", proof.ran_at ? `run ${proof.ran_at}` : "run python -m holdworld test", "DATA")),
  );
  let featured = featuredTraceId((r) => r.arm === "D" && r.ok && r.hl === "psu_bank" && r.task === "psu_complaint") ||
    featuredTraceId((r) => r.arm === "D" && r.ok);
  loadTraces().then((T) => { if (T[featured]) startHero(decodeTrace(T[featured])); });
}

function kpi(v, l, s2, t) {
  return h("div", { class: "kpi" }, h("div", { class: "v" }, String(v)), h("div", { class: "l" }, l), h("div", { class: "s" }, h("span", { class: `tag ${t}` }, t), s2));
}

// ---------------------------------------------------------------------------------------------
function startHero(tr) {
  const cv = document.getElementById("hero-cv"), cap = document.getElementById("hero-cap");
  const nodes = [
    { k: "user", t: "You", s: "user's phone" }, { k: "agent", t: "HoldForMe", s: "AI agent" },
    { k: "net", t: "Phone network", s: "Indian PSTN" }, { k: "ivr", t: "IVR menu", s: "keys & speech" },
    { k: "queue", t: "Hold queue", s: "music · announcements" }, { k: "exec", t: "Executive", s: "a real person" },
  ];
  // phases from the real trace (hold compressed so the loop stays short)
  const keys = tr.tx.filter((x) => x.label === "dtmf").map((x) => x.text);
  const holdS = tr.r.t_hold, lat = tr.r.detect_latency;
  const phases = [
    { d: 2.2, txt: "You ask: 'lodge a complaint about a failed UPI payment'. HoldForMe dials the bank.", path: ["user", "agent", "net", "ivr"] },
    ...keys.slice(0, 4).map((k) => ({ d: 1.6, txt: `The menu speaks; HoldForMe presses ${k} (tones ${dtmfHz(k)}).`, path: ["agent", "net", "ivr"], key: k })),
    { d: 4.5, txt: `On hold for ${fmt.sec(holdS)}: music, 'your call is important', a recording that sounds like a person. HoldForMe listens and ignores them.`, path: ["ivr", "queue"], hold: true },
    { d: 2.2, txt: `A person picks up. HoldForMe recognises a live voice ${lat !== null && lat !== undefined ? lat.toFixed(1) + " s" : "quickly"} after the first word.`, path: ["queue", "exec"], pickup: true },
    { d: 2.0, txt: "It asks the executive to wait: 'One moment please, I'm connecting the account holder.'", path: ["exec", "agent"], stall: true },
    { d: 2.6, txt: `Your phone rings. You join ${tr.uj && tr.br ? (tr.uj - tr.br).toFixed(0) + " s later" : ""}; the executive is still there. Handed over.`, path: ["agent", "user"], ring: true },
    { d: 2.6, txt: `Done: ${fmt.sec(tr.r.t_total)} of phone time, about ${fmt.num(tr.r.user_minutes, 1)} minutes of yours.`, path: ["user", "exec"], done: true },
  ];
  const total = phases.reduce((a, p) => a + p.d, 0);
  let t0 = performance.now();
  const notes = Array.from({ length: 26 }, () => ({ x: Math.random(), y: Math.random(), v: 0.2 + Math.random() * 0.5 }));
  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible(cv)) { t0 += 16; return; }
    const { ctx, w, h: H } = fitCanvas(cv);
    let t = ((((now - t0) / 1000) % total) + total) % total, i = 0;
    while (t > phases[i].d) { t -= phases[i].d; i++; }
    const ph = phases[i], f = t / ph.d;
    cap.textContent = ph.txt;
    ctx.clearRect(0, 0, w, H);
    const pad = 70, y = H * 0.52, gap = (w - pad * 2) / (nodes.length - 1);
    const pos = Object.fromEntries(nodes.map((n, j) => [n.k, { x: pad + j * gap, y }]));
    // wires
    ctx.lineWidth = 2;
    for (let j = 0; j < nodes.length - 1; j++) {
      const a = pos[nodes[j].k], b = pos[nodes[j + 1].k];
      ctx.strokeStyle = "#1f2b44"; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    if (ph.done) {
      const a = pos.user, b = pos.exec;
      ctx.strokeStyle = "#199e70"; ctx.lineWidth = 4; ctx.globalAlpha = 0.6 + 0.4 * Math.sin(now / 200);
      ctx.beginPath(); ctx.moveTo(a.x, a.y - 30); ctx.quadraticCurveTo((a.x + b.x) / 2, y - 120, b.x, b.y - 30); ctx.stroke(); ctx.globalAlpha = 1;
    }
    // hold music notes
    if (ph.hold) {
      const q = pos.queue;
      ctx.fillStyle = "#9085e9";
      ctx.font = "16px IBM Plex Sans";
      for (const n of notes) {
        n.y -= 0.004 * n.v; if (n.y < 0) n.y = 1;
        ctx.globalAlpha = 0.25 + 0.6 * n.y;
        ctx.fillText(n.x > 0.5 ? "♪" : "♫", q.x - 60 + n.x * 120, y - 40 - (1 - n.y) * 90);
      }
      ctx.globalAlpha = 1;
    }
    // nodes
    for (const n of nodes) {
      const p = pos[n.k];
      const lit = ph.path.includes(n.k);
      const glow = (n.k === "exec" && (ph.pickup || ph.stall || ph.done)) || (n.k === "user" && (ph.ring || ph.done)) || (n.k === "agent" && ph.pickup);
      ctx.beginPath(); ctx.arc(p.x, p.y, 30, 0, Math.PI * 2);
      ctx.fillStyle = glow ? "#103a2c" : lit ? "#122a4a" : "#0d1524"; ctx.fill();
      ctx.lineWidth = glow ? 3 : 2; ctx.strokeStyle = glow ? "#199e70" : lit ? "#3987e5" : "#26344f"; ctx.stroke();
      if (n.k === "user" && ph.ring) { ctx.beginPath(); ctx.arc(p.x, p.y, 36 + 8 * Math.sin(now / 90), 0, Math.PI * 2); ctx.strokeStyle = "#199e7088"; ctx.stroke(); }
      ctx.fillStyle = "#e6edf7"; ctx.font = "600 13px IBM Plex Sans"; ctx.textAlign = "center";
      ctx.fillText(n.t, p.x, p.y + 52); ctx.fillStyle = "#6c7a92"; ctx.font = "11px IBM Plex Mono"; ctx.fillText(n.s, p.x, p.y + 68);
      ctx.font = "18px IBM Plex Sans"; ctx.fillStyle = lit || glow ? "#fff" : "#6c7a92";
      ctx.fillText({ user: "📱", agent: "🤖", net: "📶", ivr: "☎", queue: "⏳", exec: "🧑" }[n.k], p.x, p.y + 6);
    }
    // packet travelling along this phase's path
    const path = ph.path.map((k) => pos[k]);
    const segs = Math.max(1, path.length - 1), u = Math.max(0, Math.min(f * segs, segs - 1e-6)), si = Math.floor(u), lf = u - si;
    const a = path[si], b = path[si + 1] || a;
    const px = a.x + (b.x - a.x) * lf, py = a.y + (b.y - a.y) * lf;
    const grad = ctx.createRadialGradient(px, py, 0, px, py, 22);
    grad.addColorStop(0, ph.done ? "#5ef0b4" : "#9cc6ff"); grad.addColorStop(1, "transparent");
    ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(px, py, 22, 0, Math.PI * 2); ctx.fill();
    if (ph.key) { ctx.font = "600 22px IBM Plex Mono"; ctx.fillStyle = "#fff"; ctx.fillText(ph.key, pos.ivr.x, y - 48); }
    if (ph.stall) bubble(ctx, pos.agent.x + 30, y - 70, "One moment please…");
    if (ph.pickup) bubble(ctx, pos.exec.x - 40, y - 70, "Good day, how may I help you?");
    // timeline
    const tl = (phases.slice(0, i).reduce((a2, p) => a2 + p.d, 0) + t) / total;
    ctx.fillStyle = "#1c2740"; ctx.fillRect(pad, H - 18, w - pad * 2, 3);
    ctx.fillStyle = "#3987e5"; ctx.fillRect(pad, H - 18, (w - pad * 2) * tl, 3);
    ctx.textAlign = "left"; ctx.font = "11px IBM Plex Mono"; ctx.fillStyle = "#6c7a92";
    ctx.fillText(`replaying ${ARMS[tr.r.arm].name} · ${HW.helplines[tr.r.helpline].name} · seed ${tr.r.seed} (hold compressed)`, pad, 22);
  }
  requestAnimationFrame(frame);
}

function bubble(ctx, x, y, txt) {
  ctx.font = "12px IBM Plex Sans";
  const w = ctx.measureText(txt).width + 18;
  ctx.fillStyle = "#18233a"; ctx.strokeStyle = "#3987e5"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(x - w / 2, y - 14, w, 24, 8); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#e6edf7"; ctx.textAlign = "center"; ctx.fillText(txt, x, y + 2);
}

const ROWS = [697, 770, 852, 941], COLS = [1209, 1336, 1477];
export function dtmfHz(k) {
  const grid = ["123", "456", "789", "*0#"];
  for (let r = 0; r < 4; r++) { const c = grid[r].indexOf(k); if (c >= 0) return `${ROWS[r]}+${COLS[c]} Hz`; }
  return "";
}
