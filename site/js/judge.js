// Judge Mode: an autoplaying comparison built from a matched pair of recorded traces.
import { HW, h, loadTraces, decodeTrace, fmt, emit } from "./core.js";

const SCENE_SECONDS = 15;
const END_CARD_SECONDS = 9;
const FILM_SCENES = [
  ["The problem at scale", "Real queue arrivals. Red marks show callers who gave up."],
  ["The menu maze", "Official bank menu. Each choice appears as HoldForMe navigates."],
  ["The human-sounding trap", "A recorded greeting fools the scripted bot. HoldForMe waits."],
  ["The handoff race", "Same helpline, task, and seed. Human versus HoldForMe."],
  ["Doing the job", "HoldForMe completes verification and records the result."],
  ["At scale", "Unrestricted AI holders stretch waits. A voicebot handshake helps."],
];
const PHASES = [
  { at: 0, human: ["OUTGOING CALL", "Dialling the helpline…", "The same queue and time of day"], agent: ["NAVIGATING MENU", "Finding the right team…", "Keys selected from the spoken menu"], caption: "Two callers. One helpline. One shared simulation seed." },
  { at: .12, human: ["PHONE MENU", "Listening for the right option", "Language, service, then the complaint team"], agent: ["MENU NAVIGATED", "Complaint team selected", "Meaning mapped to the menu options"], caption: "The menu takes time before either caller reaches a person." },
  { at: .32, human: ["IN THE QUEUE", "“Your call is important to us”", "Hold music, then another announcement"], agent: ["HOLDING FOR YOU", "Still listening. Still holding.", "Recordings do not trigger a false alarm"], caption: "Hold time is compressed here; the recorded trace keeps the actual duration." },
  { at: .68, human: ["STILL WAITING", "The queue is moving slowly", "Real callers abandon in measured bursts"], agent: ["LIVE VOICE DETECTED", "A person has answered", "Belief crosses the live-person threshold"], caption: "HoldForMe waits for a live person before ringing you." },
  { at: .82, human: ["BACK ON THE LINE", "You return after the hold", "The caller's time includes the call and retries"], agent: ["HANDOFF", "Your phone rings", "The executive is asked to wait"], caption: "The human caller spends the wait on the phone. HoldForMe absorbs it." },
  { at: .94, human: ["CALL COMPLETE", "The call took your afternoon", "Recorded human caller run"], agent: ["CONNECTED", "You join the live executive", "Recorded HoldForMe run"], caption: "Race complete. Open either trace to inspect every half-second." },
];

const byPair = () => {
  const ids = new Set(HW.trace_ids || []), rows = HW.arm_rows || [];
  const paired = new Map();
  for (const row of rows) {
    const [arm, hl, task, seed, ok, tid] = row;
    if (!ids.has(tid) || !["A", "D"].includes(arm)) continue;
    const key = `${hl}|${task}|${seed}`;
    if (!paired.has(key)) paired.set(key, {});
    const pair = paired.get(key);
    if (!pair[arm] || (arm === "D" && ok)) pair[arm] = tid;
  }
  const featured = paired.get("psu_bank|psu_complaint|0");
  if (featured?.A && featured?.D) return featured;
  for (const pair of paired.values()) if (pair.A && pair.D) return pair;
  return null;
};

function clock(sec) { return fmt.clock(Math.max(0, sec || 0)); }
function totalDuration(seconds) {
  const s = Math.max(0, Math.round(seconds || 0)), hours = Math.floor(s / 3600), minutes = Math.floor((s % 3600) / 60);
  return hours ? `${hours}h ${String(minutes).padStart(2, "0")}m` : `${minutes}m`;
}
function outcome(r) { return (r.end_reason || "completed").replace(/_/g, " "); }

export async function bootJudge() {
  const pairs = await loadTraces();
  const pair = byPair();
  if (!pair || !pairs[pair.A] || !pairs[pair.D]) {
    document.getElementById("judge-context").textContent = "Recorded traces are unavailable. Open Explore to inspect the dashboard.";
    return;
  }
  const human = decodeTrace(pairs[pair.A]), agent = decodeTrace(pairs[pair.D]);
  const byArm = (arm, pred = () => true) => {
    const row = (HW.arm_rows || []).find((r) => r[0] === arm && pairs[r[5]] && pred({ hl: r[1], task: r[2], ok: r[4], tid: r[5] }));
    return row ? decodeTrace(pairs[row[5]]) : null;
  };
  const stressTrace = (scenario, arm) => {
    const row = (HW.stress_rows || []).find((r) => r[0] === scenario && r[1] === arm && r[2] === 0 && pairs[r[4]]);
    return row ? decodeTrace(pairs[row[4]]) : null;
  };
  const filmTraces = {
    menu: byArm("D", (r) => r.hl === "psu_bank" && r.task === "psu_complaint"),
    trapBot: stressTrace("S6", "B"), trapHold: stressTrace("S6", "D"),
    task: byArm("D", (r) => r.task === "psu_dispute" && r.ok) || byArm("D", (r) => r.task === "ecom_refund" && r.ok) || agent,
  };
  const hR = human.r, aR = agent.r, hl = HW.helplines[aR.helpline];
  document.querySelector("#race-human .race-head h1").textContent = `Calling ${hl.name}`;
  document.querySelector("#race-agent .race-head h1").textContent = `HoldForMe calls ${hl.name}`;
  document.getElementById("judge-context").textContent = `${hl.name} · ${aR.task.replace(/_/g, " ")} · ${fmt.hhmm(aR.hour * 3600)} simulation time`;
  document.getElementById("judge-seed").textContent = `SEED ${aR.seed} · ${aR.scenario === "base" ? "BASE RUN" : aR.scenario}`;
  document.getElementById("human-attempts").textContent = String(hR.attempts || 1);
  document.getElementById("human-outcome").textContent = outcome(hR);
  document.getElementById("human-cost").textContent = fmt.inr(hR.cost_inr);
  document.getElementById("agent-hold").textContent = clock(aR.t_hold);
  document.getElementById("agent-false").textContent = String(aR.false_alerts ?? 0);
  document.getElementById("agent-cost").textContent = fmt.inr(aR.cost_inr);
  const summary = HW.arms?.summary || {}, humanMean = summary.A?.user_minutes_mean, agentMean = summary.D?.user_minutes_mean;
  const pairedCalls = summary.D?.n || 192;
  document.getElementById("endcard-saved").textContent = humanMean != null && agentMean != null ? totalDuration((humanMean - agentMean) * pairedCalls * 60) : "—";
  document.getElementById("endcard-success").textContent = summary.D?.success ? `${Math.round(summary.D.success[0] * 100)}%` : "—";
  document.getElementById("endcard-false").textContent = summary.D?.false_alerts_per_call != null ? summary.D.false_alerts_per_call.toFixed(2) : "—";
  document.getElementById("endcard-copy").textContent = `Estimated from mean caller time across ${pairedCalls} simulated calls (${fmt.num(humanMean, 2)} min human vs ${fmt.num(agentMean, 2)} min HoldForMe).`;
  document.getElementById("endcard-explore").onclick = () => explore("call");
  document.getElementById("human-trace").onclick = () => inspectTrace(human.id, false);
  document.getElementById("agent-trace").onclick = () => inspectTrace(agent.id, false);
  document.getElementById("judge-proof").onclick = openProof;
  document.getElementById("proof-close").onclick = closeProof;
  document.getElementById("proof-backdrop").onclick = closeProof;
  document.getElementById("proof-all").onclick = () => explore("evidence");
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeProof(); });
  document.getElementById("judge-explore").onclick = () => explore("evidence");
  document.querySelector('[data-mode="explore"]').onclick = () => explore("overview");
  document.querySelector('[data-mode="watch"]').onclick = () => {
    document.body.classList.remove("explore-mode", "try-mode");
    document.getElementById("try-yourself").hidden = true;
    document.body.classList.add("judge-mode");
    document.querySelectorAll(".judge-modes button").forEach((button) => button.classList.toggle("on", button.dataset.mode === "watch"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  document.querySelector('[data-mode="try"]').onclick = () => openTryYourself(agent, filmTraces.menu || agent);

  const humanEvents = ["Dial the helpline", "Navigate the menu", "Wait in the queue", "Call again / reconnect"];
  const agentEvents = ["Read the menu", "Hold through the queue", "Confirm a live person", "Ring your phone"];
  const eventList = (el, items) => items.forEach((label, i) => el.append(h("span", { class: "race-event", "data-step": i }, h("i", {}, String(i + 1).padStart(2, "0")), label)));
  eventList(document.getElementById("human-events"), humanEvents);
  eventList(document.getElementById("agent-events"), agentEvents);

  const canvas = document.getElementById("film-canvas"), stage = document.getElementById("film-stage"), race = document.querySelector(".race-grid");
  const filmDots = document.getElementById("film-dots");
  FILM_SCENES.forEach((scene, index) => filmDots.append(h("button", { type: "button", "aria-label": `Play scene ${index + 1}: ${scene[0]}`, title: scene[0], onclick: () => { started = performance.now() - index * SCENE_SECONDS * 1000; } })));
  document.getElementById("film-replay").onclick = () => { started = performance.now(); };
  document.getElementById("film-skip").onclick = () => {
    const t = (performance.now() - started) / 1000, sceneRun = SCENE_SECONDS * FILM_SCENES.length;
    if (t >= sceneRun) started = performance.now();
    else started = performance.now() - ((Math.floor(t / SCENE_SECONDS) + 1) * SCENE_SECONDS) * 1000;
  };
  let started = performance.now(), lastFrame = 0;
  const progress = document.getElementById("race-progress"), replay = document.getElementById("race-replay");
  replay.onclick = () => { started = performance.now(); document.getElementById("race-caption").textContent = "Same helpline. Same task. Same simulation seed."; };
  function frame(now) {
    requestAnimationFrame(frame);
    if (document.body.classList.contains("explore-mode") || document.body.classList.contains("try-mode") || now - lastFrame < 100) return;
    lastFrame = now;
    const total = SCENE_SECONDS * FILM_SCENES.length + END_CARD_SECONDS;
    const elapsed = ((now - started) / 1000) % total;
    const isEndCard = elapsed >= SCENE_SECONDS * FILM_SCENES.length;
    const sceneIndex = Math.min(FILM_SCENES.length - 1, Math.floor(elapsed / SCENE_SECONDS));
    const sceneElapsed = elapsed - sceneIndex * SCENE_SECONDS, f = isEndCard ? 1 : sceneElapsed / SCENE_SECONDS;
    stage.hidden = !isEndCard && sceneIndex === 3;
    race.hidden = isEndCard || sceneIndex !== 3;
    document.getElementById("film-copy").hidden = isEndCard;
    canvas.hidden = isEndCard;
    document.getElementById("film-endcard").hidden = !isEndCard;
    document.getElementById("film-scene-number").textContent = isEndCard ? "END CARD" : `SCENE ${String(sceneIndex + 1).padStart(2, "0")} / 06`;
    document.getElementById("film-title").textContent = isEndCard ? "Your time, returned" : FILM_SCENES[sceneIndex][0];
    document.getElementById("film-caption").textContent = isEndCard ? "Estimated user time saved across the full simulation set." : FILM_SCENES[sceneIndex][1];
    [...filmDots.children].forEach((button, i) => button.classList.toggle("on", i === sceneIndex));
    if (!isEndCard && sceneIndex !== 3) drawFilm(canvas, sceneIndex, sceneElapsed, filmTraces);
    let phase = PHASES[0];
    for (const p of PHASES) if (f >= p.at) phase = p;
    const index = PHASES.indexOf(phase);
    ["human", "agent"].forEach((side) => {
      const copy = phase[side];
      document.getElementById(`${side}-kicker`).textContent = copy[0];
      document.getElementById(`${side}-line`).textContent = copy[1];
      document.getElementById(`${side}-sub`).textContent = copy[2];
      const panel = document.getElementById(`race-${side}`);
      panel.classList.toggle("complete", phase.at >= .94);
      document.getElementById(`${side}-state`).textContent = phase.at >= .94 ? (side === "agent" ? (aR.success ? "CONNECTED" : "CALL COMPLETE") : "CALL COMPLETE") : copy[0];
      document.querySelectorAll(`#${side}-events .race-event`).forEach((el, i) => el.classList.toggle("done", i < Math.max(0, index - 1)));
    });
    const humanSeconds = (hR.user_minutes || hR.phone_busy_minutes || 0) * 60;
    const agentSeconds = aR.user_minutes || 0;
    const ratio = Math.min(1, f / .94);
    document.getElementById("human-time").textContent = clock(humanSeconds * ratio);
    document.getElementById("agent-time").textContent = clock(agentSeconds * ratio);
    progress.style.width = `${elapsed / total * 100}%`;
    document.getElementById("race-caption").textContent = isEndCard ? "Six recorded scenes · aggregate results · replay or explore a call trace." : sceneIndex === 3 ? phase.caption : FILM_SCENES[sceneIndex][1];
    if (f > .94) {
      document.getElementById("human-kicker").textContent = "YOUR TIME ON THE PHONE";
      document.getElementById("human-line").textContent = `${fmt.num(hR.user_minutes || hR.phone_busy_minutes || 0, 1)} minutes across ${hR.attempts || 1} attempt${(hR.attempts || 1) === 1 ? "" : "s"}`;
      document.getElementById("agent-kicker").textContent = "YOUR TIME WITH HOLDFORME";
      document.getElementById("agent-line").textContent = `${fmt.num(aR.user_minutes || 0, 1)} minutes of your time`;
      document.getElementById("agent-sub").textContent = `HoldForMe spent ${fmt.sec(aR.t_total)} on the call.`;
    }
  }
  replay.textContent = "Replay race ↻";
  replay.onclick = () => { started = performance.now() - 3 * SCENE_SECONDS * 1000; };
  requestAnimationFrame(frame);
}

function drawFilm(canvas, scene, elapsed, traces) {
  const { ctx, w, h: height } = fitCanvas(canvas);
  ctx.clearRect(0, 0, w, height);
  const pad = Math.min(54, w * .07), mid = height * .56, progress = Math.min(1, elapsed / SCENE_SECONDS);
  ctx.strokeStyle = "#18253a"; ctx.lineWidth = 1;
  for (let y = 35; y < height - 24; y += 32) { ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(w - pad, y); ctx.stroke(); }
  const text = (value, x, y, size = 12, color = "#a9b6cb", font = "IBM Plex Mono") => { ctx.font = `${size}px ${font}`; ctx.fillStyle = color; ctx.fillText(value, x, y); };
  if (scene === 0) {
    const calls = HW.real_day?.events || [], shown = Math.floor(Math.min(1, progress * 1.6) * Math.min(calls.length, 900));
    const cols = Math.max(12, Math.floor((w - 2 * pad) / 13)), rows = Math.ceil(shown / cols), startY = Math.max(54, mid - Math.min(rows * 10, height * .42));
    for (let i = 0; i < shown; i++) {
      const e = calls[i], x = pad + (i % cols) * 13, y = startY + Math.floor(i / cols) * 10;
      if (y > height - 22) continue;
      const abandon = e[2] !== "A";
      ctx.globalAlpha = .55 + .45 * ((i % 7) / 7); ctx.fillStyle = abandon ? "#e66767" : "#3987e5";
      ctx.beginPath(); ctx.arc(x, y, abandon ? 2.6 : 2, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    text(`${shown.toLocaleString("en-IN")} calls in one recorded day`, pad, 30, 12, "#dce6f4");
    text("RED DOTS  ·  callers who abandoned after waiting", pad, height - 16, 11, "#e58a8a");
    return;
  }
  if (scene === 1) {
    const tr = traces.menu, hl = tr && HW.helplines[tr.r.helpline], visited = tr?.visited || [];
    const nodes = visited.slice(0, 6), y0 = 62, step = Math.min(55, (height - 105) / Math.max(1, nodes.length));
    text("OFFICIAL MENU STRUCTURE · RECORDED HOLDForMe RUN", pad, 30, 11, "#91bfff");
    nodes.forEach((id, i) => {
      const node = hl?.nodes[id], y = y0 + i * step, x = pad + i * 23;
      if (i) { ctx.strokeStyle = "#3987e5"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x - 8, y - step + 16); ctx.lineTo(x + 8, y); ctx.stroke(); }
      ctx.fillStyle = i < Math.max(1, Math.floor(progress * nodes.length)) ? "#17365c" : "#121a2a"; ctx.strokeStyle = "#3987e5";
      ctx.beginPath(); ctx.roundRect(x, y, Math.min(360, w - x - pad), 34, 7); ctx.fill(); ctx.stroke();
      text(`${String(i + 1).padStart(2, "0")}  ${node?.type || "menu"}  ·  ${id}`, x + 12, y + 22, 11, "#e0e9f7");
    });
    const sample = tr?.tx?.find((x) => x.who === "ivr" && x.text)?.text || "Spoken menu prompt from the trace";
    text(sample.slice(0, Math.max(24, Math.floor((w - pad * 2) / 7))), pad, height - 18, 10, "#9aa9bf", "IBM Plex Sans");
    return;
  }
  if (scene === 2) {
    const bot = traces.trapBot, hold = traces.trapHold, cardW = (w - pad * 2 - 20) / 2;
    [[bot, "SCRIPTED BOT", "#c98500", pad], [hold, "HOLDFORME", "#3987e5", pad + cardW + 20]].forEach(([tr, label, color, x]) => {
      ctx.fillStyle = "#0d1524"; ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.roundRect(x, 52, cardW, height - 85, 10); ctx.fill(); ctx.stroke();
      text(label, x + 14, 76, 10, color);
      text(tr ? (tr.r.success ? "Outcome: stayed on the right path" : `Outcome: ${outcome(tr.r)}`) : "Recorded run unavailable", x + 14, 102, 11, "#dbe5f4", "IBM Plex Sans");
      const line = tr?.tx?.find((x) => x.who !== "agent" && x.text)?.text || "Hi, I'm Priya. Your call is valuable to us.";
      const wrapped = line.slice(0, 78); text(`“${wrapped}”`, x + 14, 132, 11, "#aab8cb", "IBM Plex Sans");
      const baseY = height - 48, bx = x + 16, bw = cardW - 32;
      if (tr?.r.arm === "D") {
        const belief = tr.belief || [], toY = (value) => baseY - (Math.max(-8, Math.min(4, value)) + 8) / 12 * 58;
        const threshold = toY(1.2);
        ctx.strokeStyle = "#50607b"; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(bx, threshold); ctx.lineTo(bx + bw, threshold); ctx.stroke(); ctx.setLineDash([]);
        ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
        const shownBelief = belief.filter((point) => point[0] <= progress * (tr?.dur || 1));
        shownBelief.forEach((point, i) => { const xx = bx + Math.min(1, point[0] / (tr?.dur || 1)) * bw, yy = toY(point[1]); i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); });
        ctx.stroke(); text("HOLDFORME DETECTION SCORE · ALERT THRESHOLD 1.2", bx, baseY + 17, 8, "#718099");
      } else {
        text(`FALSE ALERTS IN THIS TRACE  ·  ${tr?.r.false_alerts ?? 0}`, bx, baseY + 4, 9, "#e5b85c");
      }
    });
    return;
  }
  if (scene === 4) {
    const tr = traces.task, events = (tr?.tx || []).filter((x) => x.text && x.who !== "network").slice(0, 6);
    const count = Math.min(events.length, Math.ceil(progress * events.length));
    text(`RECORDED RUN  ·  ${tr ? HW.helplines[tr.r.helpline]?.name : "HoldForMe"}`, pad, 30, 11, "#91bfff");
    events.slice(0, count).forEach((ev, i) => {
      const y = 54 + i * 38;
      ctx.fillStyle = ev.who === "agent" ? "#17365c" : "#101c2c"; ctx.beginPath(); ctx.roundRect(pad + (ev.who === "agent" ? w * .22 : 0), y, w * .65, 29, 7); ctx.fill();
      const safe = ev.text.replace(/\b\d{4,}\b/g, "••••").replace(/(otp|pin|cvv|password)\s*[:=]?\s*[A-Z0-9-]+/gi, "$1 [withheld]");
      text(`${ev.who.toUpperCase()}  ·  ${safe.slice(0, 78)}`, pad + 10 + (ev.who === "agent" ? w * .22 : 0), y + 19, 10, ev.who === "agent" ? "#b8d7ff" : "#c4cede", "IBM Plex Sans");
    });
    text("SECRETS ARE NEVER SPOKEN BY THE AGENT", pad, height - 16, 9, "#76cfae");
    return;
  }
  if (scene === 5) {
    const city = HW.city?.psu_bank, normal = city?.none || [], handshake = city?.handshake || [];
    const x0 = pad + 30, y0 = height - 35, chartW = w - 2 * pad - 55, chartH = height - 100;
    text("MEAN HUMAN WAIT · SAME BANK QUEUE MODEL", pad, 28, 11, "#dce6f4");
    for (const value of [0, 30, 60, 90]) { const y = y0 - value / 90 * chartH; ctx.strokeStyle = "#1c2940"; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x0 + chartW, y); ctx.stroke(); text(`${value}s`, pad, y + 4, 9, "#718099"); }
    const plot = (data, color) => {
      if (!data.length) return;
      ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.beginPath();
      const n = Math.max(2, Math.floor(progress * data.length));
      data.slice(0, n).forEach((r, i) => { const x = x0 + r.alpha * 2 * chartW, y = y0 - r.hum_wait / 90 * chartH; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke();
      const r = data[n - 1], x = x0 + r.alpha * 2 * chartW, y = y0 - r.hum_wait / 90 * chartH;
      ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
      text(`${Math.round(r.hum_wait)}s`, x + 8, y - 7, 10, color);
    };
    plot(normal, "#e66767"); plot(handshake, "#38c991");
    text("AI-holder share →", x0 + chartW - 110, height - 12, 9, "#8795aa");
    text("UNRESTRICTED", pad + 4, height - 52, 8, "#e66767"); text("VOICEBOT HANDSHAKE", pad + 4, height - 39, 8, "#38c991");
  }
}

function explore(chapter) {
  closeProof();
  document.body.classList.remove("try-mode");
  document.getElementById("try-yourself").hidden = true;
  document.body.classList.remove("judge-mode");
  document.body.classList.add("explore-mode");
  document.querySelectorAll(".judge-modes button").forEach((button) => button.classList.toggle("on", button.dataset.mode === (chapter === "call" ? "try" : "explore")));
  document.getElementById("main").scrollTop = 0;
  document.getElementById(chapter)?.scrollIntoView({ behavior: "smooth" });
}

function openProof() {
  const drawer = document.getElementById("proof-drawer"), backdrop = document.getElementById("proof-backdrop"), content = document.getElementById("proof-content");
  content.innerHTML = "";
  const s14 = HW.stress_rows?.find((r) => r[0] === "S14" && r[1] === "D" && r[2] === 0);
  const s18 = HW.stress_rows?.find((r) => r[0] === "S18" && r[1] === "D" && r[2] === 0);
  const s12 = HW.stress_rows?.find((r) => r[0] === "S12" && r[1] === "D" && r[2] === 0);
  const rows = [
    ["Queue replay", `${fmt.int(HW.real.records)} recorded calls`, `Held-out wait correlation ${HW.holdout.corr_wait.toFixed(3)} · ${HW.holdout.days.length} days`, null, "queue"],
    ["HoldForMe", `${Math.round(HW.arms.summary.D.success[0] * 100)}% task success`, `${HW.arms.summary.D.n} runs · 95% interval ${fmt.ci(HW.arms.summary.D.success)}`, HW.trace_ids.find((id) => id.startsWith("D-psu_bank-psu_complaint")), null],
    ["False alarms", HW.arms.summary.D.false_alerts_per_call.toFixed(2), "Average false alerts per call in the full run", HW.trace_ids.find((id) => id.startsWith("D-psu_bank-psu_complaint")), null],
    ["Transfer · S14", s14 ? (s14[3] ? "Pass" : "Fail") : "Not recorded", "Second hold after a team transfer", s14?.[4], null],
    ["Voicebot · S18", s18 ? (s18[3] ? "Pass" : "Fail") : "Not recorded", "Bank voicebot handshake scenario", s18?.[4], null],
    ["Bad line · S12", s12 ? (s12[3] ? "Pass" : "Fail") : "Not recorded", "Poor channel grounded at 34.8% WER", s12?.[4], null],
  ];
  rows.forEach(([title, value, detail, traceId, chapter]) => {
    const button = h("button", { class: "proof-row", onclick: () => { closeProof(); if (traceId) inspectTrace(traceId, true); else explore(chapter || "evidence"); } },
      h("span", { class: "proof-row-copy" }, h("small", {}, title), h("b", {}, value), h("span", {}, detail)), h("span", { class: "proof-row-arrow" }, "↗"));
    content.append(button);
  });
  drawer.hidden = false; backdrop.hidden = false;
}

function closeProof() {
  const drawer = document.getElementById("proof-drawer"), backdrop = document.getElementById("proof-backdrop");
  if (drawer) drawer.hidden = true;
  if (backdrop) backdrop.hidden = true;
}

function inspectTrace(id, play) {
  document.body.classList.remove("judge-mode", "try-mode");
  document.body.classList.add("explore-mode");
  document.getElementById("try-yourself").hidden = true;
  document.querySelectorAll(".judge-modes button").forEach((button) => button.classList.toggle("on", button.dataset.mode === "try"));
  emit("open-trace", { id, play });
}

function openTryYourself(trace, menuTrace) {
  document.body.classList.remove("explore-mode");
  document.body.classList.add("judge-mode", "try-mode");
  document.querySelectorAll(".judge-modes button").forEach((button) => button.classList.toggle("on", button.dataset.mode === "try"));
  const root = document.getElementById("try-yourself"); root.hidden = false; root.innerHTML = "";
  document.getElementById("film-stage").hidden = true;
  document.querySelector(".race-grid").hidden = true;
  document.getElementById("judge-context").textContent = "Browser trial · official bank menu · no phone call is placed";
  document.getElementById("judge-seed").textContent = "LIVE MENU EXERCISE";
  const hl = HW.helplines[menuTrace.r.helpline], langs = hl.languages || [], task = hl.tasks.find((x) => x.id === "psu_complaint") || hl.tasks[0];
  const view = {
    lang: langs.some((x) => x[1] === "en") ? "en" : "hi", node: hl.root, input: "", inHold: false,
    holdAt: 0, gaveUp: false, joined: false, finished: false, timer: 0, audio: null,
  };
  const langButton = h("button", { class: "btn ghost", onclick: () => { view.lang = view.lang === "en" ? "hi" : "en"; renderNode(); } }, "English / हिन्दी");
  const voiceSample = h("button", { class: "btn ghost", hidden: true, onclick: () => {
    const audio = new Audio(`/audio/${view.lang}_main_menu.wav`); audio.play().catch(() => { voiceSample.hidden = true; });
  } }, "Play generated voice sample");
  fetch(`/audio/${view.lang}_main_menu.wav`, { method: "HEAD" }).then((r) => { voiceSample.hidden = !r.ok; }).catch(() => {});
  langButton.addEventListener("click", () => {
    voiceSample.hidden = true;
    fetch(`/audio/${view.lang}_main_menu.wav`, { method: "HEAD" }).then((r) => { voiceSample.hidden = !r.ok; }).catch(() => {});
  });
  const reset = h("button", { class: "btn ghost", onclick: () => { clearTimeout(view.timer); view.node = hl.root; view.input = ""; view.inHold = false; view.gaveUp = false; view.joined = false; view.finished = false; hang.disabled = false; hang.textContent = "I would give up"; renderNode(); } }, "Restart");
  const body = h("div", { class: "try-layout" });
  const screen = h("div", { class: "try-phone-screen" });
  const options = h("div", { class: "try-options" });
  const keypad = h("div", { class: "try-keypad" });
  const stat = h("div", { class: "try-status" });
  stat.append(h("span", {}, "HoldForMe status"), h("strong", {}, "Dialling the helpline…"));
  const hang = h("button", { class: "btn", onclick: giveUp }, "I would give up");
  const controls = h("div", { class: "try-control-row" }, langButton, voiceSample, h("span", { class: "sp" }), hang, reset);
  const phone = h("div", { class: "try-phone" }, h("div", { class: "try-notch" }), h("div", { class: "try-phone-brand" }, hl.name), screen, options, keypad, controls);
  const side = h("aside", { class: "try-side" },
    h("div", { class: "race-eyebrow" }, "HOLDFORME · PICTURE IN PICTURE"),
    h("h2", {}, "Still on the line for you"),
    h("div", { class: "try-agent-orbit" }, h("span", {}, "✳")),
    stat,
    h("div", { class: "note" }, "This browser exercise uses the published menu structure. Hold timing and handoff are illustrative; inspect the recorded paired run for measured values."));
  body.append(phone, side);
  root.append(h("div", { class: "try-heading" }, h("div", {}, h("span", { class: "race-eyebrow" }, "TRY IT YOURSELF"), h("h2", {}, `Get to ${task.goal.toLowerCase()}`)), h("span", { class: "badge" }, `${hl.tag} MENU`)), body);
  const keys = "123456789*0#";
  keys.split("").forEach((k) => keypad.append(h("button", { type: "button", onclick: () => press(k) }, k)));

  function promptFor(n) {
    const language = view.lang === "hi" ? 2 : 1;
    if (n.type === "menu") return `${hl.brand}: ${n.opts.map((o) => `for ${o[language] || o[1]}, press ${o[0]}`).join(". ")}`;
    if (n.type === "queue") return "All our executives are busy helping other customers. Please hold; your call is important to us.";
    if (n.type === "collect") return `Please enter your ${n.field.replace(/_/g, " ")}. Use the demo digits 1234 only; do not enter a real secret.`;
    if (n.type === "fact") return n.fact || "Here is the requested account information.";
    if (n.type === "action") return n.action || "Your request has been recorded.";
    return n.message || "Please listen to the options again.";
  }
  function renderNode() {
    const n = hl.nodes[view.node]; if (!n) return;
    options.innerHTML = ""; screen.innerHTML = "";
    if (n.type === "queue") { beginHold(); return; }
    if (["fact", "action"].includes(n.type)) {
      view.finished = true;
      screen.append(h("span", { class: "try-call-label" }, "SIMULATED OUTCOME"), h("strong", {}, n.fact || n.action || "Menu task complete"), h("span", { class: "try-sub" }, "No live call was made. Restart to explore another menu path."));
      return;
    }
    const prompt = promptFor(n);
    screen.append(h("span", { class: "try-call-label" }, `CALL MENU · ${n.type.toUpperCase()}`), h("strong", { lang: view.lang === "hi" ? "hi" : "en" }, prompt), h("span", { class: "try-sub" }, view.input ? `Digits entered: ${view.input}` : "Tap a menu option or use the keypad"));
    if (view.input) { const enter = h("button", { class: "try-option", onclick: () => advanceInput(n) }, h("b", {}, "#"), "Continue with entered digits"); options.append(enter); }
    n.opts.forEach((o) => options.append(h("button", { class: "try-option", onclick: () => { tone(o[0]); select(o[0], o[3]); } }, h("b", {}, o[0]), h("span", {}, o[view.lang === "hi" ? 2 : 1] || o[1]))));
    if (n.next) options.append(h("button", { class: "try-option", onclick: () => { view.node = n.next; renderNode(); } }, h("b", {}, "#"), h("span", {}, "Continue")));
    if (n.agent) options.append(h("button", { class: "try-option", onclick: () => { view.node = n.agent; renderNode(); } }, h("b", {}, "9"), h("span", {}, "Talk to an executive")));
    if (n.extras?.["*"]) options.append(h("button", { class: "try-option", onclick: () => speak(prompt) }, h("b", {}, "*"), h("span", {}, "Repeat the menu")));
    stat.innerHTML = ""; stat.append(h("span", {}, "HoldForMe status"), h("strong", {}, "Ready to follow the same menu"));
    speak(prompt);
  }
  function select(key, target) {
    view.input = "";
    if (!target || !hl.nodes[target]) { invalid(); return; }
    view.node = target; renderNode();
  }
  function press(key) {
    tone(key);
    if (view.inHold) return;
    if (view.finished) return;
    const n = hl.nodes[view.node];
    if (n.opts.some((o) => o[0] === key)) { select(key, n.opts.find((o) => o[0] === key)[3]); return; }
    if (n.type === "collect" && /\d/.test(key) && view.input.length < 8) { view.input += key; renderNode(); return; }
    if (n.type === "collect" && key === "#") { advanceInput(n); return; }
    if (n.next && key === "#") { view.node = n.next; view.input = ""; renderNode(); return; }
    if (n.agent && key === "9") { view.node = n.agent; renderNode(); return; }
    if (key === "*" && n.extras?.["*"]) { view.input = ""; renderNode(); return; }
    invalid();
  }
  function advanceInput(n) {
    if (!view.input) { invalid("Enter the demo digits 1234 to continue."); return; }
    if (n.next && hl.nodes[n.next]) view.node = n.next;
    else { view.finished = true; screen.innerHTML = ""; screen.append(h("strong", {}, "Demo entry accepted"), h("span", { class: "try-sub" }, "No real account information was entered.")); }
    view.input = ""; renderNode();
  }
  function invalid(message = "That key is not available in this menu. Try one of the shown options.") {
    options.prepend(h("div", { class: "try-invalid" }, message));
  }
  function giveUp() {
    if (!view.inHold || view.gaveUp || view.joined) return;
    view.gaveUp = true; hang.disabled = true; hang.textContent = "You gave up";
    screen.innerHTML = ""; screen.append(h("span", { class: "try-call-label" }, "YOU HUNG UP"), h("strong", {}, `You stayed ${Math.max(1, Math.round((Date.now() - view.holdAt) / 1000))} seconds in this compressed hold.`), h("span", { class: "try-sub" }, "HoldForMe keeps waiting for you."));
  }
  function beginHold() {
    if (view.inHold) return;
    clearTimeout(view.timer);
    view.inHold = true; view.holdAt = Date.now(); hang.disabled = false;
    screen.innerHTML = ""; screen.append(h("span", { class: "try-call-label" }, "IN THE QUEUE · HOLD MUSIC"), h("strong", {}, "Your call is important to us."), h("span", { class: "try-sub" }, "Hold is compressed. This is a browser simulation."));
    stat.innerHTML = ""; const status = h("strong", {}, "Listening to hold music…"), absorbed = h("b", {}, "Hold absorbed: 00:00"); stat.append(h("span", {}, "HoldForMe status"), status, absorbed);
    const start = Date.now();
    const tick = () => {
      if (!view.inHold || !document.body.classList.contains("try-mode")) return;
      const elapsed = (Date.now() - start) / 1000;
      absorbed.textContent = `Hold absorbed: ${clock(Math.min(trace.r.t_hold || 0, elapsed * 60))}`;
      if (elapsed >= 4 && elapsed < 9) status.textContent = "Recording detected. Still holding…";
      if (elapsed >= 9 && !view.joined) {
        status.textContent = view.gaveUp ? "Your phone is ringing." : "A live person answered. Your phone is ringing.";
        if (!options.querySelector(".try-join")) options.append(h("button", { class: "btn primary try-join", onclick: join }, "Join HoldForMe's call →"));
      }
      if (elapsed >= 12) { status.textContent = view.joined ? "Connected to the executive." : "HoldForMe connected; your call is ready."; }
      view.timer = window.setTimeout(tick, 200);
    };
    tick();
  }
  function join() {
    view.joined = true; view.gaveUp = true; hang.disabled = true;
    statusText("Connected to the executive.");
    screen.innerHTML = ""; screen.append(h("span", { class: "try-call-label" }, "CONNECTED"), h("strong", {}, "You joined the executive."), h("span", { class: "try-sub" }, `The real recorded HoldForMe trace absorbed ${fmt.sec(trace.r.t_hold)} of hold.`));
  }
  function statusText(message) { const strong = stat.querySelector("strong"); if (strong) strong.textContent = message; }
  function speak(text) {
    if (!window.speechSynthesis || !text) return;
    speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.lang = view.lang === "hi" ? "hi-IN" : "en-IN"; u.rate = 1.05; speechSynthesis.speak(u);
  }
  function tone(key) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      view.audio ||= new AudioCtx(); if (view.audio.state === "suspended") view.audio.resume();
      const grid = ["123", "456", "789", "*0#"], rows = [697, 770, 852, 941], cols = [1209, 1336, 1477];
      for (let r = 0; r < 4; r++) { const c = grid[r].indexOf(key); if (c < 0) continue; for (const f of [rows[r], cols[c]]) { const osc = view.audio.createOscillator(), gain = view.audio.createGain(); osc.frequency.value = f; gain.gain.value = .045; osc.connect(gain); gain.connect(view.audio.destination); osc.start(); osc.stop(view.audio.currentTime + .1); } }
    } catch { /* audio may be unavailable */ }
  }
  function ringback() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      view.audio ||= new AudioCtx(); if (view.audio.state === "suspended") view.audio.resume();
      const now = view.audio.currentTime, carrier = view.audio.createOscillator(), modulation = view.audio.createOscillator();
      const volume = view.audio.createGain(), depth = view.audio.createGain(), envelope = view.audio.createGain();
      carrier.frequency.value = 400; modulation.frequency.value = 25; volume.gain.value = .04; depth.gain.value = .025; envelope.gain.value = 0;
      carrier.connect(volume); modulation.connect(depth); depth.connect(volume.gain); volume.connect(envelope); envelope.connect(view.audio.destination);
      envelope.gain.setValueAtTime(0, now); envelope.gain.setValueAtTime(.8, now + .01); envelope.gain.setValueAtTime(0, now + .41);
      envelope.gain.setValueAtTime(.8, now + .61); envelope.gain.setValueAtTime(0, now + 1.01);
      carrier.start(now); modulation.start(now); carrier.stop(now + 1.1); modulation.stop(now + 1.1);
    } catch { /* audio may be unavailable */ }
  }
  const keyHandler = (event) => { if (document.body.classList.contains("try-mode") && /^[0-9*#]$/.test(event.key)) press(event.key); if (event.key === "Escape") { document.body.classList.remove("try-mode"); root.hidden = true; } };
  if (openTryYourself.keyHandler) document.removeEventListener("keydown", openTryYourself.keyHandler);
  openTryYourself.keyHandler = keyHandler;
  document.addEventListener("keydown", keyHandler);
  ringback();
  view.timer = window.setTimeout(renderNode, 1700);
}
