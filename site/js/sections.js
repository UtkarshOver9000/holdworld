// Chapters 3-10: wait times, handoff race, Pine mode, evidence, parity, provenance, proof.
import { HW, h, fmt, fitCanvas, visible, header, tag, ARMS, ARM_ORDER, emit, loadTraces, decodeTrace, helplineName, showTip, hideTip, param } from "./core.js";
import { barsH, lines, columns, legend } from "./charts.js";

// ---------------------------------------------------------------------------------- waits
export function renderWaits(root) {
  root.append(header("3 · Wait times", "How long will I wait if I call at 7 pm?",
    "Google's phone app shows expected wait by hour for US toll-free numbers. HoldWorld does the same for every helpline, from its queue model. The hourly shape and the patience curve come from the real 1999 year; each line's volume and staffing are set per archetype. The telecom line is staffed so <b>97% of callers reach an executive within 90 s</b>, which sits inside TRAI's benchmark and the published Airtel (95.2–98.3%) and Jio (99.0–99.97%) ranges."));
  const grid = h("div", { class: "grid g3", id: "waits-grid" });
  for (const [hid, w] of Object.entries(HW.waits)) {
    const byH = Array(24).fill(null), p90 = Array(24).fill(null);
    for (const r of w.stats) { byH[r.hour] = r.median / 60; p90[r.hour] = r.p90 / 60; }
    const hl = HW.helplines[hid];
    const peak = w.stats.reduce((a, r) => (r.median > (a?.median ?? -1) ? r : a), null);
    const best = w.stats.filter((r) => w.agents[r.hour] > 0).reduce((a, r) => (r.median < (a?.median ?? 1e9) ? r : a), null);
    grid.append(h("div", { class: "card" },
      h("h3", {}, hl.name, h("span", { class: "sp" }), tag(w.tag)),
      h("div", { class: "sub" }, `${hl.brand} · open ${hl.hours[0]}:00–${hl.hours[1]}:00`),
      columns(byH, { width: 320, height: 120, whisk: p90, fmt: (v) => `${v.toFixed(1)} min median`, xlab: (i) => `${i}:00`, labelEvery: 6, color: hid === "telecom" ? "#199e70" : "#3987e5" }),
      h("div", { class: "row", style: { fontSize: "12.5px", marginTop: "6px" } },
        h("span", {}, `Worst ${peak ? peak.hour + ":00" : "–"} · ${peak ? fmt.sec(peak.median) : "–"}`), h("span", { class: "sp" }),
        h("span", { class: "muted" }, `Best ${best ? best.hour + ":00" : "–"} · ${best ? fmt.sec(best.median) : "–"}`)),
      w.answered_90s ? h("div", { class: "note", style: { marginTop: "8px", borderLeftColor: "#199e70" } }, `TRAI check: ${(w.answered_90s * 100).toFixed(1)}% answered within 90 s (benchmark 95%).`) : null));
  }
  root.append(grid);
}

// ---------------------------------------------------------------------------------- handoff race
export function renderHandoff(root) {
  root.append(header("4 · The handoff race", "Will you get on the line before the executive hangs up?",
    `When a person finally answers, HoldForMe has to get <i>you</i> there before they give up on the silence. Your answer time follows a large real call log (median ${param("user.answer_s.median").value} s, upper quartile ${param("user.answer_s.p75").value} s). How long an executive tolerates silence has never been published, so it's swept here; the India Hold Atlas will measure it. Run a few handoffs, then try the stall line and merge mode (M2).`));
  const st = { mode: "M1", stall: true, pat: 10, runs: [], anim: null };
  const cv = h("canvas", { style: { height: "200px" }, id: "race-cv" });
  const tally = h("div", { class: "chips" });
  const seg = (opts, key) => { const e = h("div", { class: "seg" }, opts.map(([v, l]) => h("button", { class: st[key] === v ? "on" : "", onclick: (ev) => { st[key] = v; [...e.children].forEach((b) => b.classList.toggle("on", b === ev.target)); st.runs = []; } }, l))); return e; };
  const pat = h("input", { type: "range", min: 4, max: 30, step: 1, value: st.pat, oninput: (e) => { st.pat = +e.target.value; patL.textContent = `${st.pat} s patience`; st.runs = []; } });
  const patL = h("span", { class: "chip" }, `${st.pat} s patience`);
  const run = () => {
    const med = param("user.answer_s.median").value, p75 = param("user.answer_s.p75").value, sigma = Math.log(p75 / med) / 0.6745;
    const z = Math.sqrt(-2 * Math.log(Math.random())) * Math.cos(2 * Math.PI * Math.random());
    const miss = st.mode === "M1" && Math.random() < param("user.miss_p").value;
    const answer = st.mode === "M2" ? 1.5 + Math.random() * 1.5 : med * Math.exp(sigma * z) + 1;
    const budget = st.pat + (st.stall ? 2 * param("exec.stall_extension_s").value * param("exec.max_stalls").value : 0);
    st.anim = { t: 0, answer: miss ? 999 : answer, budget, stallAt: st.stall ? 1.2 : null, done: false };
  };
  const auto = () => { for (let i = 0; i < 200; i++) { run(); st.runs.push(st.anim.answer <= st.anim.budget); } st.anim = null; };
  root.append(h("div", { class: "transport", id: "race-controls" }, h("button", { class: "btn primary", onclick: run }, "▶ Run one handoff"), h("button", { class: "btn", onclick: auto }, "⚡ Run 200"),
    seg([["M1", "M1 · agent rings you"], ["M2", "M2 · you merged the call"]], "mode"), seg([[true, "stall on"], [false, "stall off"]], "stall"), pat, patL, h("span", { class: "sp" }), tally));
  const g = HW.handoff_grid;
  const cols = { "M1|no stall": "#d95926", "M1|stall": "#3987e5", "M2|no stall": "#c98500", "M2|stall": "#199e70" };
  const chart = lines(Object.entries(g.success).map(([k, v]) => ({ name: k.replace("|", " · "), color: cols[k], points: g.patience.map((p, i) => [p, v[i] * 100]) })),
    { width: 560, height: 230, xfmt: (v) => `${Math.round(v)} s`, yfmt: (v) => `${Math.round(v)}%`, ymax: 100, xlabel: "executive's patience with silence", ylabel: "handoffs that succeed" });
  const modes = Object.entries(HW.modes).map(([k, w]) => ({ label: k.replace("|", " · "), value: w[0] * 100, lo: w[1] * 100, hi: w[2] * 100, color: k.includes("M2") ? "#199e70" : k.includes("M3") ? "#9085e9" : "#3987e5" }));
  root.append(h("div", { class: "grid g2" }, h("div", { class: "card" }, h("h3", {}, "One handoff, live"), cv),
    h("div", { class: "card" }, h("h3", {}, "4,000 handoffs per point ", tag("ASSUMED")), h("div", { class: "sub" }, "The x-axis (patience) is an assumption, swept from 4 to 30 s until the Atlas measures it."), chart)));
  root.append(h("div", { class: "card", style: { marginTop: "14px" } }, h("h3", {}, "Full simulated calls on the airline line, by mode"), h("div", { class: "sub" }, "M1: the agent dials from its own number and rings you. M2: you dial and merge HoldForMe in, so you're already on the line (registered-mobile checks pass; your phone line stays busy). M3: take the helpline's callback offer."),
    barsH(modes, { max: 100, fmt: (v) => `${Math.round(v)}`, unit: "%", width: 720, labelW: 140 })));
  const loop = (now) => {
    requestAnimationFrame(loop);
    if (!visible(cv)) return;
    const { ctx, w, h: H } = fitCanvas(cv);
    ctx.clearRect(0, 0, w, H);
    const a = st.anim;
    const span = 70, X = (s2) => 110 + (w - 140) * Math.min(s2, span) / span;
    ctx.font = "12px IBM Plex Sans"; ctx.fillStyle = "#a9b6cb";
    ctx.fillText("Executive", 12, 52); ctx.fillText("Your phone", 12, 122);
    ctx.fillStyle = "#0a101b"; ctx.fillRect(110, 40, w - 140, 18); ctx.fillRect(110, 110, w - 140, 18);
    for (let s2 = 0; s2 <= span; s2 += 10) { ctx.fillStyle = "#6c7a92"; ctx.font = "10px IBM Plex Mono"; ctx.fillText(`${s2}s`, X(s2) - 8, 160); }
    if (a) {
      a.t += 1 / 60 * 6;
      const budgetLeft = Math.max(0, a.budget - a.t);
      ctx.fillStyle = "#199e70"; ctx.fillRect(110, 40, Math.max(0, X(Math.min(a.budget, span)) - 110) * (budgetLeft / a.budget), 18);
      ctx.fillStyle = "#e6edf7"; ctx.fillText(`patience left ${budgetLeft.toFixed(0)} s`, 116, 53);
      const ringEnd = Math.min(a.t, a.answer);
      ctx.fillStyle = "#3987e5"; ctx.fillRect(110, 110, X(ringEnd) - 110, 18);
      ctx.fillStyle = "#e6edf7"; ctx.fillText(a.t < a.answer ? `ringing ${a.t.toFixed(0)} s…` : `you answered at ${a.answer.toFixed(0)} s`, 116, 123);
      if (a.stallAt !== null && a.t > a.stallAt) { ctx.fillStyle = "#c98500"; ctx.fillText("“One moment please, connecting the account holder” → patience extended", 110, 88); }
      ctx.strokeStyle = "#fff"; ctx.beginPath(); ctx.moveTo(X(a.t), 30); ctx.lineTo(X(a.t), 140); ctx.stroke();
      if (!a.done && (a.t >= a.answer || a.t >= a.budget)) {
        a.done = true; st.runs.push(a.answer <= a.budget);
      }
      if (a.done) { ctx.font = "600 18px IBM Plex Sans"; ctx.fillStyle = a.answer <= a.budget ? "#5ef0b4" : "#ff9a9a"; ctx.fillText(a.answer <= a.budget ? "✓ You made it: handed over" : "✗ The executive hung up", w - 330, 190); }
    } else { ctx.fillStyle = "#6c7a92"; ctx.fillText("Press 'Run one handoff'", 110, 190); }
    const ok = st.runs.filter(Boolean).length;
    tally.innerHTML = "";
    tally.append(h("span", { class: "chip live" }, `${ok}/${st.runs.length} succeeded${st.runs.length ? ` (${Math.round(ok / st.runs.length * 100)}%)` : ""}`));
  };
  requestAnimationFrame(loop);
}

// ---------------------------------------------------------------------------------- Pine mode
export function renderPine(root) {
  root.append(header("5 · Pine mode", "When HoldForMe does the task itself",
    "Pine (US, $25M Series A) has its agent talk to the company and finish the job. In HoldWorld, the executive runs a script: verification questions, an OTP sent to your registered mobile, retention offers before a cancellation, a discount ladder you have to push, and a reference number at the end. HoldForMe answers from your details, relays the OTP from your phone, refuses offers you didn't want, and reads the reference number back until the executive confirms it."));
  const pick = h("select", { id: "pine-pick" });
  const view = h("div", { class: "chat", style: { height: "460px" }, id: "pine-chat" });
  const steps = h("div", { class: "chips", id: "pine-steps" });
  const go = h("button", { class: "btn primary", onclick: () => play() }, "▶ Replay conversation");
  root.append(h("div", { class: "transport" }, pick, go, h("button", { class: "btn", onclick: () => emit("open-trace", { id: pick.value, play: true }) }, "Open in the theatre →"), h("span", { class: "sp" }), steps));
  root.append(h("div", { class: "grid", style: { gridTemplateColumns: "minmax(0,1fr) 300px" } }, h("div", { class: "card" }, view), h("div", { class: "card", id: "pine-score" })));
  let timer = null;
  loadTraces().then((T) => {
    const opts = HW.arm_rows.filter((r) => r[0] === "D" && ["psu_dispute", "tel_cancel", "tel_negotiate", "air_refund", "air_baggage", "ecom_refund"].includes(r[2]) && T[r[5]]);
    const seen = new Set();
    for (const r of opts) { if (seen.has(r[2])) continue; seen.add(r[2]); pick.append(h("option", { value: r[5] }, `${helplineName(r[1])} · ${r[2]} ${r[4] ? "✓" : "✗"}`)); }
    pick.onchange = () => play();
    play();
  });
  function play() {
    clearInterval(timer);
    const tr = decodeTrace(window.HW_TRACES[pick.value]);
    const lines = tr.tx.filter((x) => tr.pk && x.t >= tr.pk - 1 && (x.who === "exec" || x.who === "agent"));
    view.innerHTML = ""; let i = 0;
    const flags = { disclose: false, verify: false, otp: false, offer: false, push: false, readback: false };
    const score = document.getElementById("pine-score");
    const draw = () => {
      steps.innerHTML = "";
      for (const [k, l] of [["disclose", "Says it's an AI"], ["verify", "Verification"], ["otp", "OTP relayed"], ["offer", "Offer handled"], ["push", "Negotiated"], ["readback", "Read-back confirmed"]])
        steps.append(h("span", { class: `pill ${flags[k] ? "pass" : "part"}` }, `${flags[k] ? "✓" : "…"} ${l}`));
      const r = tr.r;
      score.innerHTML = "";
      score.append(h("h3", {}, r.success ? "Task completed" : "Task not completed"), h("div", { class: "sub" }, r.end_reason.replace(/_/g, " ")),
        h("div", { class: "stat" }, h("span", {}, "Reference captured correctly"), h("b", {}, r.captured_ok === null ? "–" : r.captured_ok ? "yes" : "no")),
        h("div", { class: "stat" }, h("span", {}, "Discount won"), h("b", {}, r.discount === null ? "–" : `${r.discount}%`)),
        h("div", { class: "stat" }, h("span", {}, "Retention offer accepted"), h("b", {}, r.accepted_offer === null ? "–" : r.accepted_offer ? "yes (unwanted)" : "no")),
        h("div", { class: "stat" }, h("span", {}, "Your time spent"), h("b", {}, `${fmt.num(r.user_minutes, 1)} min`)),
        h("div", { class: "stat" }, h("span", {}, "Total call"), h("b", {}, fmt.sec(r.t_total))),
        h("div", { class: "stat" }, h("span", {}, "Transfers"), h("b", {}, String(r.transfers))));
    };
    draw();
    timer = setInterval(() => {
      if (i >= lines.length) { clearInterval(timer); return; }
      const x = lines[i++];
      if (x.intent === "disclose") flags.disclose = true;
      if (x.intent === "provide") flags.verify = true;
      if (x.intent === "provide" && /^[0-9 ]{11}$/.test(x.text) && tr.tx.some((y) => y.label === "alert" && y.text === "otp")) flags.otp = true;
      if (x.intent === "decline_offer" || x.intent === "accept_offer") flags.offer = true;
      if (x.intent === "push") flags.push = true;
      if (x.who === "exec" && /correct|सही/.test(x.text)) flags.readback = true;
      const isAgent = x.who === "agent";
      view.append(h("div", { class: `msg ${isAgent ? "agent" : "exec"}` }, h("span", { class: "who" }, `${fmt.clock(x.t)} · ${isAgent ? "HoldForMe" : x.label === "ai_agent" ? "Bank voicebot" : "Executive"}`, x.intent ? h("span", { class: "chip", style: { marginLeft: "6px", fontSize: "10px" } }, x.intent) : null), x.text));
      view.scrollTop = view.scrollHeight;
      draw();
    }, 650);
  }
}

// ---------------------------------------------------------------------------------- evidence
export function renderEvidence(root) {
  const A = HW.arms.summary;
  root.append(header("7 · Evidence", "Five callers, every task, every stress test",
    `Every helpline task, ${Math.max(...Object.values(A).map((v) => v.n))} calls per caller, then 20 stress scenarios, each built around one thing real calls break. Bars show the share of calls that succeeded, with 95% intervals. <b>Click any cell in the stress matrix to replay that exact call.</b> HoldForMe's failures are real findings, not hidden: they're the misheard words, impatient executives and gated menus the build has to handle.`));
  const succ = ARM_ORDER.filter((a) => A[a]).map((a) => ({ label: ARMS[a].name, value: A[a].success[0] * 100, lo: A[a].success[1] * 100, hi: A[a].success[2] * 100, color: ARMS[a].color, sub: `${A[a].n} calls` }));
  const umin = ARM_ORDER.filter((a) => A[a]).map((a) => ({ label: ARMS[a].name, value: A[a].user_minutes_mean, color: ARMS[a].color, sub: "mean minutes of the user's own time" }));
  const fa = ARM_ORDER.filter((a) => A[a]).map((a) => ({ label: ARMS[a].name, value: A[a].false_alerts_per_call, color: ARMS[a].color, sub: "times the user was rung for a recording" }));
  root.append(h("div", { class: "grid g3", id: "ev-arms" },
    h("div", { class: "card" }, h("h3", {}, "Tasks completed"), barsH(succ, { max: 100, fmt: (v) => Math.round(v), unit: "%", width: 440, labelW: 110 })),
    h("div", { class: "card" }, h("h3", {}, "Your own time per task"), h("div", { class: "sub" }, "A human caller spends the whole call; AI callers cost you only alerts, OTPs and the conversation itself."), barsH(umin, { fmt: (v) => v.toFixed(1), unit: " min", width: 440, labelW: 110 })),
    h("div", { class: "card" }, h("h3", {}, "False alarms per call"), h("div", { class: "sub" }, "Your phone rang, but it was a recording."), barsH(fa, { fmt: (v) => v.toFixed(2), width: 440, labelW: 110 }))));
  if (HW.noise_sweep?.length) {
    const noiseSeries = ARM_ORDER.filter((a) => HW.noise_sweep.some((r) => r.arm === a)).map((arm) => ({
      name: ARMS[arm].name, color: ARMS[arm].color,
      points: HW.noise_sweep.filter((r) => r.arm === arm).map((r) => [r.wer * 100, r.success[0] * 100]),
    }));
    root.append(h("div", { class: "card", style: { marginTop: "14px" }, id: "noise-sweep" },
      h("h3", {}, "Call success as the phone line gets noisier", tag("DATA")),
      h("div", { class: "sub" }, "Poor-channel replay at 10–50% word error rates. Each point uses 30 seeds in the full run; the legend names each caller. S12 is grounded at the published 34.8% worst-case phone error rate."),
      lines(noiseSeries, { width: 820, height: 250, xfmt: (v) => `${Math.round(v)}%`, yfmt: (v) => `${Math.round(v)}%`, xlabel: "word error rate", ylabel: "call success", marks: [{ x: 35, text: "published worst case", dy: 0 }] })));
  }
  if (HW.sensitivity?.length) {
    const factors = [...new Set(HW.sensitivity.map((r) => r.factor))];
    const maxDelta = Math.max(1, ...HW.sensitivity.map((r) => Math.abs(r.delta_pp)));
    const grid = h("div", { class: "sensitivity-chart" });
    for (const factor of factors) {
      const pts = HW.sensitivity.filter((r) => r.factor === factor);
      const left = pts[0], mid = pts[1], right = pts[2];
      const endpoint = (r, side) => h("div", { class: `tornado-end ${side}` },
        h("span", { class: "tornado-label" }, `${r.value}${factor === "Speech error rate" ? "%" : ""} · ${Math.round(r.success[0] * 100)}%`),
        h("span", { class: "tornado-track" }, h("i", { style: { width: `${Math.abs(r.delta_pp) / maxDelta * 100}%`, background: r.delta_pp < 0 ? "#d95926" : "#199e70" } })));
      grid.append(h("div", { class: "tornado-row" }, h("b", {}, factor), endpoint(left, "left"),
        h("span", { class: "tornado-zero" }, `${Math.round(mid.success[0] * 100)}%`), endpoint(right, "right")));
    }
    root.append(h("div", { class: "card", style: { marginTop: "14px" }, id: "sensitivity-tornado" },
      h("h3", {}, "Which assumptions move success?", tag("ASSUMED")),
      h("div", { class: "sub" }, "One factor changes at a time across its own representative task. Bars show percentage-point change from the middle setting; 30 paired seeds per point. These are directional sensitivity checks, not causal estimates."),
      grid));
  }
  if (HW.prewarn?.points?.length) {
    const p = HW.prewarn;
    const bestPoint = p.points.find((x) => x.lead_s === p.selected_lead_s);
    const fallbackRecovered = bestPoint?.fallback_recovered || 0;
    const prewarnSummary = p.target_met
      ? `Modeled lead: ${p.selected_lead_s} s before estimated pickup; fallback recovered ${fallbackRecovered} missed first alerts.`
      : `No tested policy reaches 90%. Best observed: ${p.selected_lead_s} s early, ${Math.round(bestPoint.ready_by_pickup_plus_patience * 100)}% ready; fallback recovered ${fallbackRecovered} missed first alerts.`;
    root.append(h("div", { class: "card", style: { marginTop: "14px" }, id: "prewarn-policy" },
      h("h3", {}, "When should HoldForMe ring you?", tag("ASSUMED")),
      h("div", { class: "sub" }, `Pre-warn timing sweep uses 1,000 paired samples per lead. Queue prediction error has an assumed 25 s standard deviation. The model gives a 60 s app heads-up when possible and retries one missed alert after 12 s; both behaviors are assumptions. It selects the smallest early-ready time that meets 90% readiness, or reports the best observed readiness if no lead meets the target.`),
      h("div", { class: "callout" }, prewarnSummary),
      lines([{ name: "ready by pickup + patience", color: "#3987e5", points: p.points.map((x) => [x.lead_s, x.ready_by_pickup_plus_patience * 100]) }],
        { width: 780, height: 210, xfmt: (v) => `${Math.round(v)} s`, yfmt: (v) => `${Math.round(v)}%`, xlabel: "alert lead before estimated pickup", ylabel: "handoff readiness" })));
  }
  const paired = new Map();
  for (const row of HW.arm_rows || []) {
    if (row[0] !== "A" && row[0] !== "D") continue;
    const key = `${row[1]}|${row[2]}|${row[3]}`;
    const pair = paired.get(key) || {};
    pair[row[0]] = row; paired.set(key, pair);
  }
  const matched = [...paired.values()].filter((p) => p.A && p.D);
  const savedMinutes = matched.reduce((sum, p) => sum + (p.A[7] - p.D[7]), 0);
  const hfmRows = matched.map((p) => p.D), totalCost = hfmRows.reduce((sum, r) => sum + (r[10] || 0), 0);
  const resolved = hfmRows.filter((r) => r[4]).length;
  const savedHours = savedMinutes / 60;
  const avgCost = totalCost / Math.max(1, hfmRows.length);
  const costResolved = totalCost / Math.max(1, resolved);
  const perHourSaved = savedHours > 0 ? totalCost / savedHours : null;
  root.append(h("div", { class: "card", style: { marginTop: "14px" }, id: "unit-economics" },
    h("h3", {}, "Unit economics", tag("ASSUMED")),
    h("div", { class: "sub" }, `Matched human and HoldForMe rows (${matched.length} calls). Spend uses the current platform model; Indian telephony pricing is still a placeholder.`),
    h("div", { class: "economics-grid" },
      econ("Mean HoldForMe call cost", fmt.inr(avgCost)),
      econ("Cost per resolved call", fmt.inr(costResolved)),
      econ("Rupees per hour saved", perHourSaved === null ? "—" : fmt.inr(perHourSaved)),
      econ("Mean user time saved", `${fmt.num(savedMinutes / Math.max(1, matched.length), 2)} min`))));
  // by goal type
  const goals = HW.arms.by_goal;
  const gt = h("table", { class: "t" }, h("tr", {}, h("th", {}, "Goal type (Sierra's three)"), ...ARM_ORDER.map((a) => h("th", {}, ARMS[a].name))),
    ...Object.entries(goals).map(([g, v]) => h("tr", {}, h("td", {}, g.replace("_", " ")), ...ARM_ORDER.map((a) => h("td", {}, v[a] ? `${fmt.pct(v[a].success)} (n=${v[a].n})` : "–")))));
  // stress heat table
  const titles = Object.fromEntries(HW.stress.scenarios.map((x) => [x.id, x]));
  const arms = ["B", "C", "D", "O"];
  const heat = h("table", { class: "t heat", id: "ev-stress" }, h("tr", {}, h("th", {}, "Scenario"), h("th", {}, "Breaks"), ...arms.map((a) => h("th", { style: { textAlign: "center" } }, ARMS[a].name))));
  for (const [sid, cells] of Object.entries(HW.stress.table)) {
    const sc = titles[sid];
    heat.append(h("tr", {}, h("td", {}, h("b", {}, sid), " ", sc.title, h("div", { class: "muted", style: { fontSize: "11px" } }, sc.source)), h("td", { class: "muted" }, sc.breaks),
      ...arms.map((a) => {
        const w = cells[a]; const v = w ? w[0] : null;
        const bg = v === null ? "transparent" : `color-mix(in srgb, #3987e5 ${Math.round(v * 85)}%, #0a101b)`;
        const td = h("td", { class: "cell", style: { background: bg, color: v > 0.55 ? "#fff" : "var(--text-2)" } }, v === null ? "–" : `${Math.round(v * 100)}%`);
        td.addEventListener("click", () => { const r = HW.stress_rows.find((x) => x[0] === sid && x[1] === a && x[2] === 0); if (r) emit("open-trace", { id: r[4], play: true }); });
        td.addEventListener("mousemove", (e) => showTip(e, `<b>${sid} · ${ARMS[a].name}</b><br>pass ${fmt.pct(w)} · 95% ${fmt.ci(w)}<br><span class=muted>click to replay seed 0</span>`));
        td.addEventListener("mouseleave", hideTip);
        return td;
      })));
  }
  root.append(h("div", { class: "grid g2", style: { marginTop: "14px" } },
    h("div", { class: "card" }, h("h3", {}, "Stress suite: pass rate"), h("div", { class: "sub" }, "Darker = more calls passed. Each scenario names where it comes from."), h("div", { class: "scroll" }, heat)),
    h("div", { class: "col", style: { display: "flex", flexDirection: "column", gap: "14px" } },
      h("div", { class: "card" }, h("h3", {}, "By goal type"), gt),
      ablationCard(), memoryCard())));
  // platforms + city
  const P = HW.platforms;
  const prow = Object.entries(P.by_platform).map(([k, v]) => ({ label: P.platforms[k].label, value: v.success[0] * 100, lo: v.success[1] * 100, hi: v.success[2] * 100, color: "#3987e5", sub: P.platforms[k].note }));
  const pcost = Object.entries(P.by_platform).map(([k, v]) => ({ label: P.platforms[k].label, value: v.cost_inr_median, color: "#c98500", sub: P.platforms[k].note }));
  root.append(h("div", { class: "grid g2", style: { marginTop: "14px" } },
    h("div", { class: "card", id: "ev-platforms" }, h("h3", {}, "Same agent, different voice platforms ", tag("OFFICIAL")), h("div", { class: "sub" }, "Limits from each platform's docs: Bolna's 90 s default and 10 s silence hang-up, no way to press keys on Bolna or Exotel, Plivo's sendDTMF and 4 h limit."), barsH(prow, { max: 100, fmt: (v) => Math.round(v), unit: "%", width: 560, labelW: 190 })),
    h("div", { class: "card" }, h("h3", {}, "Cost per call (median) ", tag("OFFICIAL"), tag("ASSUMED")), h("div", { class: "sub" }, "Bolna ₹5.52/min is official. Telephony ₹0.60/min is a placeholder until Plivo's India price is checked. The hybrid runs a cheap classifier during hold and the full pipeline only while talking."), barsH(pcost, { fmt: (v) => `₹${v.toFixed(1)}`, width: 560, labelW: 190 }))));
  root.append(cityCurves());
}

function ablationCard() {
  const ab = HW.ablation, feats = HW.features;
  const scs = Object.keys(ab.full);
  const t = h("table", { class: "t heat", style: { fontSize: "11px" } }, h("tr", {}, h("th", {}, "Without…"), h("th", {}, "Product"), ...scs.map((s2) => h("th", { style: { textAlign: "center", padding: "4px" } }, s2))));
  for (const f of feats) {
    const row = ab.minus[f.key]; if (!row) continue;
    t.append(h("tr", {}, h("td", {}, f.key), h("td", { class: "muted" }, f.group.replace("Google Hold for Me", "Google")),
      ...scs.map((s2) => {
        const drop = (ab.full[s2] ?? 0) - (row[s2] ?? 0);
        const v = Math.max(0, drop);
        const td = h("td", { class: "cell", style: { background: v > 0.05 ? `color-mix(in srgb, #d95926 ${Math.round(Math.min(1, v) * 90)}%, #0a101b)` : "transparent", color: v > 0.4 ? "#fff" : "var(--muted)", padding: "3px" } }, v > 0.05 ? `−${Math.round(v * 100)}` : "·");
        td.addEventListener("mousemove", (e) => showTip(e, `<b>without ${f.key}</b> on ${s2}<br>pass ${(row[s2] * 100).toFixed(0)}% vs ${(ab.full[s2] * 100).toFixed(0)}% with everything<br><span class=muted>${f.text}</span>`));
        td.addEventListener("mouseleave", hideTip);
        return td;
      })));
  }
  return h("div", { class: "card", id: "ev-ablation" }, h("h3", {}, "Ablation: remove one component at a time"), h("div", { class: "sub" }, "Orange = pass-rate points lost on that scenario when the component is switched off (5 runs each, so small effects are noisy)."), h("div", { class: "scroll", style: { maxHeight: "300px" } }, t));
}

function memoryCard() {
  const m = HW.path_memory;
  return h("div", { class: "card" }, h("h3", {}, "Path memory (Sierra)"), h("div", { class: "callout", html: `Second call to the same line: menu time <b>${fmt.sec(m.second_call_ivr_s)}</b> vs <b>${fmt.sec(m.first_call_ivr_s)}</b> on the first (median of ${m.n}).` }));
}

function cityCurves() {
  const c = HW.city;
  const wrap = h("div", { class: "grid g3", style: { marginTop: "14px" }, id: "ev-city" });
  const col = { none: "#d95926", deadline_20min: "#3987e5", callback: "#9085e9", offpeak: "#c98500", handshake: "#199e70" };
  const name = { none: "Never hang up", deadline_20min: "20 min deadline", callback: "Scheduled callback", offpeak: "Join off-peak", handshake: "Bank voicebot handshake" };
  for (const [hid, d] of Object.entries(c)) {
    const policies = Object.entries(d).filter(([, rows]) => Array.isArray(rows));
    const series = policies.flatMap(([k, rows]) => [
      { name: `${name[k]} · sim`, color: col[k], points: rows.map((r) => [r.alpha * 100, r.hum_wait]) },
      ...(rows[0].erlang_a_wait == null ? [] : [{ name: `${name[k]} · Erlang-A`, color: col[k], dash: "4 3", points: rows.map((r) => [r.alpha * 100, r.erlang_a_wait]) }]),
    ]);
    const rec = d.recommendation;
    wrap.append(h("div", { class: "card" }, h("h3", {}, `${helplineName(hid)}: what happens at scale`), h("div", { class: "sub" }, "Human callers' average wait as more callers use an AI holder. Solid/dotted series compare three simulated days per point with a stationary Erlang-A approximation where its assumptions apply. Callback and off-peak arrivals are shifted in the day model; these are still modeled scenarios."),
      h("div", { class: "callout", style: { marginBottom: "10px" }, html: `At 25% adoption, the rule-based recommendation is <b>${name[rec.policy]}</b>: ${fmt.sec(rec.human_wait_delta_s)} added human wait, ${fmt.sec(rec.ai_wait_s)} mean AI queue wait (20 min cap).` }),
      lines(series, { width: 560, height: 220, xfmt: (v) => `${Math.round(v)}%`, yfmt: (v) => fmt.sec(v), xlabel: "share of callers using an AI holder", ylabel: "human wait" })));
  }
  if (HW.disruption?.none) {
    const d = HW.disruption, pol = ["none", "deadline_20min", "handshake"];
    wrap.append(h("div", { class: "card" }, h("h3", {}, "Airline surge: 3x incoming demand", tag("ASSUMED")),
      h("div", { class: "sub" }, "An illustrative disruption scenario with volume tripled and staffing held fixed. It is an assumption sweep, not a claim about a specific airline event."),
      lines(pol.map((k) => ({ name: name[k], color: col[k], points: d[k].map((r) => [r.alpha * 100, r.hum_wait]) })),
        { width: 560, height: 220, xfmt: (v) => `${Math.round(v)}%`, yfmt: (v) => fmt.sec(v), xlabel: "AI-holder share", ylabel: "human wait" })));
  }
  if (HW.calendar?.weekday) {
    const cal = HW.calendar;
    wrap.append(h("div", { class: "card" }, h("h3", {}, "Calendar and seasonal demand"),
      h("div", { class: "sub" }, "Weekday index is measured from the 1999 source centre and is not India-specific. The festive peak multipliers are assumed; this chart shows the bank queue response with staffing held fixed."),
      h("h4", {}, "Observed weekday arrivals (weekly mean = 1.0)"),
      columns(cal.weekday.map((x) => x.index), { width: 520, height: 130, color: "#3987e5", fmt: (x) => `${x.toFixed(2)}x`, xlab: (i) => cal.weekday[i].label, labelEvery: 1 }),
      h("h4", {}, "Assumed festive volume peak"),
      lines([{ name: "bank human wait", color: "#d95926", points: cal.peak_sweep.map((x) => [x.volume_multiplier, x.mean_human_wait_s]) }],
        { width: 520, height: 190, xfmt: (v) => `${v.toFixed(2)}x`, yfmt: (v) => fmt.sec(v), xlabel: "arrival volume multiplier", ylabel: "human wait" })));
  }
  return wrap;
}

// ---------------------------------------------------------------------------------- parity
export function renderParity(root) {
  root.append(header("8 · Feature parity", "Everything Google Hold for Me, Pine and Sierra do, and where HoldWorld tests it",
    "Each row is a capability a reference product has. The middle column says which HoldWorld component reproduces it; the right column is the measured evidence from this run."));
  const A = HW.arms.summary, ST = HW.stress.table;
  const ev = (key) => {
    const [k, a, b, c2] = key.split(":");
    if (k === "stress") { const w = ST[a]?.D; return w ? [`${a}: ${fmt.pct(w)} pass`, w[0] >= 0.7 ? "pass" : w[0] >= 0.4 ? "part" : "fail"] : ["–", "part"]; }
    if (k === "arms" && b) { const v = A[a]?.[b]; return [b.includes("minutes") ? `${fmt.num(v, 1)} min` : b.includes("latency") ? `${fmt.num(v, 1)} s` : fmt.sec(v), "pass"]; }
    if (k === "arms" && a) { return [`${ARMS[a].name}: ${fmt.pct(A[a]?.success)}`, "pass"]; }
    if (k === "arms") return [`${HW.arm_rows.length} calls`, "pass"];
    if (k === "feature") return ["component switchable, in ablation", "pass"];
    if (k === "task") { const rows = HW.arm_rows.filter((r) => r[0] === "D" && r[2] === a); const ok = rows.filter((r) => r[4]).length; return [`${ok}/${rows.length} calls`, rows.length && ok / rows.length >= 0.6 ? "pass" : "part"]; }
    if (k === "goal") { const rows = HW.arm_rows.filter((r) => r[0] === "D"); return [`${Object.keys(HW.arms.by_goal).length} goal types`, "pass"]; }
    if (k === "waits") return [`${Object.keys(HW.waits).length} lines × 24 h`, "pass"];
    if (k === "path_memory") return [`${fmt.sec(HW.path_memory.second_call_ivr_s)} vs ${fmt.sec(HW.path_memory.first_call_ivr_s)}`, HW.path_memory.second_call_ivr_s <= HW.path_memory.first_call_ivr_s ? "pass" : "part"];
    if (k === "helplines") return [`${Object.keys(HW.helplines).length} lines`, "pass"];
    if (k === "real") return [`r = ${HW.holdout.corr_wait.toFixed(3)} on held-out days`, "pass"];
    if (k === "modes") return [Object.entries(HW.modes).map(([m, w]) => `${m.split("|")[0]} ${fmt.pct(w)}`).slice(0, 3).join(" · "), "pass"];
    if (k === "city") return ["curves in Evidence", "pass"];
    return ["–", "part"];
  };
  const prodColor = { "Google Hold for Me": "#3987e5", Pine: "#199e70", Sierra: "#9085e9", Ours: "#c98500" };
  const t = h("table", { class: "t", id: "parity-table" }, h("tr", {}, h("th", {}, "Product"), h("th", {}, "Capability"), h("th", {}, "HoldWorld component"), h("th", {}, "Evidence this run"), h("th", {}, "")));
  for (const [prod, feat, comp, key] of HW.parity) {
    const [txt, st] = ev(key);
    t.append(h("tr", {}, h("td", {}, h("span", { class: "chip", style: { borderColor: prodColor[prod], color: "var(--text)" } }, prod)), h("td", {}, feat), h("td", { class: "muted" }, comp), h("td", {}, txt), h("td", {}, h("span", { class: `pill ${st}` }, st === "pass" ? "covered" : st === "part" ? "partial" : "gap"))));
  }
  root.append(h("div", { class: "card" }, t),
    h("div", { class: "note", style: { marginTop: "12px" } }, "Audio tooling is scaffolded: a Sarvam cache script, optional YAMNet classifier, and authenticated Plivo stream adapter are in the repo. No provider audio or live call is included until credentials, public WSS, and licensed assets are supplied. Asterisk/SIPp infrastructure is still pending."));
}

// ---------------------------------------------------------------------------------- provenance
export function renderData(root) {
  const pv = HW.provenance;
  root.append(header("9 · Where every number comes from", "Provenance",
    `Every parameter the simulation uses is registered with one of five tags. <b>DATA</b>: measured in a real dataset. <b>OFFICIAL</b>: published by the company, regulator or platform. <b>STD</b>: a technical standard. <b>ATLAS</b>: to be measured by calling real Indian helplines. <b>ASSUMED</b>: nothing published exists, so the value is swept over a range. This table is generated from the code, so the screen and the model cannot disagree.`));
  const counts = h("div", { class: "row" }, ...Object.entries(pv.counts).map(([t, n]) => h("button", { class: "btn", onclick: () => filt(t) }, tag(t), ` ${n}`)), h("button", { class: "btn", onclick: () => filt(null) }, "all"));
  const atlas = HW.atlas || { calls: 0, by_helpline: {} };
  const atlasCovered = Object.values(atlas.by_helpline).filter((x) => x.n >= 3).length;
  const tbody = h("tbody");
  const table = h("table", { class: "t", id: "prov-table" }, h("thead", {}, h("tr", {}, h("th", {}, "Parameter"), h("th", {}, "Value"), h("th", {}, "Tag"), h("th", {}, "Source"), h("th", {}, "Note / sweep"))), tbody);
  const filt = (t) => {
    tbody.innerHTML = "";
    for (const p of pv.params) {
      if (t && p.tag !== t) continue;
      const src = pv.sources[p.source] || {};
      const val = typeof p.value === "object" ? JSON.stringify(p.value) : String(p.value);
      tbody.append(h("tr", {}, h("td", {}, h("code", {}, p.key)), h("td", {}, h("code", {}, val.length > 60 ? val.slice(0, 60) + "…" : val), p.unit ? h("span", { class: "muted" }, ` ${p.unit}`) : null), h("td", {}, tag(p.tag)),
        h("td", {}, src.url ? h("a", { href: src.url, target: "_blank", rel: "noopener" }, src.title) : h("span", { class: "muted" }, src.title || p.source)),
        h("td", { class: "muted" }, p.note || "", p.sweep ? h("div", {}, `sweep ${JSON.stringify(p.sweep)}`) : null)));
    }
  };
  filt(null);
  root.append(h("div", { class: "callout", style: { marginBottom: "12px" }, html: `India Hold Atlas: <b>${atlas.calls || 0}</b> recorded calls across <b>${atlasCovered}</b> helplines with at least three measurements. Put field observations in <code>data/atlas/measurements.csv</code>, then rerun the simulation to replace supported assumptions.` }), h("div", { class: "card" }, counts, h("div", { class: "scroll", style: { marginTop: "10px" } }, table)));
  const hls = h("div", { class: "grid g3", style: { marginTop: "14px" } });
  for (const hl of Object.values(HW.helplines)) {
    const src = pv.sources[hl.source] || {};
    hls.append(h("div", { class: "card tight" }, h("h3", {}, hl.name, h("span", { class: "sp" }), tag(hl.tag)), h("div", { class: "sub" }, `${hl.brand} · ${Object.keys(hl.nodes).length} menu nodes · ${hl.languages.length} language options`),
      src.url ? h("a", { href: src.url, target: "_blank", rel: "noopener", style: { fontSize: "12px" } }, src.title) : h("span", { class: "muted", style: { fontSize: "12px" } }, "structure assumed until the Atlas"),
      ...hl.notes.map((n) => h("div", { class: "muted", style: { fontSize: "12px", marginTop: "6px" } }, n))));
  }
  root.append(h("h3", { style: { marginTop: "18px" } }, "The helplines"), hls);
}

// ---------------------------------------------------------------------------------- proof
export function renderProof(root) {
  const p = HW.proof || {};
  root.append(header("10 · Proof", "Tests, run on the real data",
    `The test suite checks the real dataset (exact record count, the hang-up spikes, a held-out replay), the official menu structures, the phone standards, the queue engine against the Erlang-C formula, and every caller's behaviour. Reproduce it with <code>python -m holdworld test</code>; the report below is that command's output.`));
  if (!p.total) { root.append(h("div", { class: "note" }, "No test report bundled. Run python -m holdworld test, then python -m holdworld run.")); return; }
  const mods = {};
  for (const t of p.tests) (mods[t.module] = mods[t.module] || []).push(t);
  root.append(h("div", { class: "kpis", style: { gridTemplateColumns: "repeat(4, minmax(0,1fr))" } },
    h("div", { class: "kpi" }, h("div", { class: "v", style: { color: p.failed ? "var(--crit)" : "#5ef0b4" } }, `${p.passed}/${p.total}`), h("div", { class: "l" }, "tests passed")),
    h("div", { class: "kpi" }, h("div", { class: "v" }, String((mods.test_real_data || []).length)), h("div", { class: "l" }, "on the 440,837 real calls")),
    h("div", { class: "kpi" }, h("div", { class: "v" }, `${p.seconds}s`), h("div", { class: "l" }, "suite runtime")),
    h("div", { class: "kpi" }, h("div", { class: "v", style: { fontSize: "16px" } }, p.ran_at), h("div", { class: "l" }, `Python ${p.python}`))));
  const nice = { test_real_data: "Real call-centre data", test_queue: "Queue engine", test_line: "Call environment & standards", test_callers: "Callers & stress scenarios", test_sources: "Sources & official structures" };
  const grid = h("div", { class: "grid g2", style: { marginTop: "14px" }, id: "proof-tests" });
  for (const [m, ts] of Object.entries(mods)) {
    grid.append(h("div", { class: "card" }, h("h3", {}, nice[m] || m, h("span", { class: "sp" }), h("span", { class: "pill pass" }, `${ts.filter((t) => t.status === "passed").length}/${ts.length}`)),
      h("table", { class: "t" }, ...ts.map((t) => h("tr", {}, h("td", {}, h("span", { class: `pill ${t.status === "passed" ? "pass" : "fail"}` }, t.status === "passed" ? "✓" : "✗")), h("td", {}, t.name.replace(/^test_/, "").replace(/_/g, " ")), h("td", { class: "muted", style: { textAlign: "right" } }, `${t.time.toFixed(2)}s`))))));
  }
  root.append(grid);
}

function econ(label, value) {
  return h("div", { class: "econ" }, h("small", {}, label), h("strong", {}, value));
}
