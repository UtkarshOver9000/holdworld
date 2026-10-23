// The guided tour: a spotlight walks through every chapter and drives the animations.
import { emit, $, HW, fmt } from "./core.js";
import { theatre, featuredList } from "./theatre.js";
import { queue } from "./queue.js";

const feat = () => featuredList();
const fid = (i) => (feat()[i] || feat()[0])[1];
const findFeat = (txt) => (feat().find((f) => f[0].includes(txt)) || feat()[0])[1];

export function steps() {
  return [
    { sel: "#overview header", title: "Welcome to HoldWorld", text: "A simulated India of customer-care phone lines. An AI agent (HoldForMe) calls them, gets through the menu, waits on hold and connects you when a real person answers. Everything here is replayed from recorded simulation runs." },
    { sel: "#hero-cv", title: "One call, end to end", text: "This is a real simulated call travelling through the system: keys pressed in the menu, the hold, the moment a person answers, the stall line, and your phone ringing." },
    { sel: ".kpis", title: "Built on real data", text: `${fmt.int(HW.real.records)} real call-centre records drive the queue, menus come from official bank pages, and ${HW.proof?.passed || "all"} tests check it.` },
    { sel: "#call-transport", title: "The Call Theatre", text: "Pick any call, from featured ones to every stress scenario and task, and replay it frame by frame. We'll play the featured bank complaint at 16×.", run: () => { theatre.open(fid(0), true); theatre.setSpeed(16); } },
    { sel: "#call-tree", title: "The menu reveals itself", text: "HoldForMe never sees this tree. It hears the prompts through speech-to-text, with errors, and picks by meaning. The tree fills in as it explores; the dashed node is the goal." },
    { sel: "#call-ear-card", title: "What the agent hears", text: "Top band: what was really playing (ground truth, every half-second). Lines: what a sound classifier reports. Bottom: HoldForMe's belief that a live person is speaking. It crosses the green line only for a real human.", run: () => theatre.skipHold() },
    { sel: "#call-status", title: "The race is on", text: "When a person answers, their patience with silence starts draining. HoldForMe stalls ('one moment please') while your phone rings, then hands over." },
    { sel: "#call-transport", title: "A recording that sounds human", text: "Hold lines play 'Hi, I'm Priya, your call is valuable to us'. Here a scripted bot falls for it and rings you for nothing. Google Hold for Me's core problem.", run: () => { theatre.open(findFeat("scripted bot falls"), true); theatre.setSpeed(16); } },
    { sel: "#call-ear-card", title: "…and HoldForMe doesn't", text: "Same scenario. Known phrases, repetition, studio-clean audio and a quick 'hello?' probe keep its belief below the line until a real person speaks.", run: () => { theatre.open(findFeat("HoldForMe doesn't"), true); theatre.setSpeed(16); } },
    { sel: "#pine-chat", title: "Pine mode", text: "Sometimes HoldForMe finishes the job itself: verification, the OTP relayed from your phone, refusing retention offers, and reading the reference number back until the executive confirms it." },
    { sel: "#queue-cv", title: "A real day of a real call centre", text: "2 November 1999, replayed from the records: real arrival times, real waits, real hang-ups, real agents at their desks.", run: () => { document.getElementById("queue").scrollIntoView(); queue.set({ t: 9 * 3600, speed: 240 }); queue.play(); } },
    { sel: "#queue-hazard", title: "When people hang up", text: "Measured from the records: hang-ups spike right after the first 'please hold' message and again when it replays near 60 s. HoldWorld's human callers give up exactly like this." },
    { sel: "#queue-holdout", title: "Proof the replay is right", text: `On ${HW.holdout.days.length} days the fit never saw, re-simulated waits track reality (r = ${HW.holdout.corr_wait.toFixed(3)}) and hang-up rates match (${(HW.holdout.mean_real_abandon * 100).toFixed(1)}% real vs ${(HW.holdout.mean_sim_abandon * 100).toFixed(1)}% simulated).` },
    { sel: "#waits-grid", title: "Wait time by hour", text: "Google's wait-times feature, for every line. The telecom line is staffed to TRAI's 90-second rule." },
    { sel: "#race-controls", title: "The handoff race", text: "Run handoffs yourself. Your answer time follows a large real call log; executive patience is swept because no one has published it. Try stall off, then merge mode (M2)." },
    { sel: "#city-box", title: "Hold City", text: "Nine helplines through a whole day. Drag the AI-holder slider: queues swell where callers stop hanging up, the side effect the City experiment measures." },
    { sel: "#ev-arms", title: "The evidence", text: "Five callers on every task, with 95% intervals: Human, Scripted bot, Basic agent, HoldForMe, and a perfect-knowledge Oracle." },
    { sel: "#ev-stress", title: "20 stress tests, every cell replayable", text: "Each scenario breaks one thing real calls break. Click any cell to watch that exact call in the theatre." },
    { sel: "#parity-table", title: "Google, Pine and Sierra, feature by feature", text: "Every capability of the three reference products, the HoldWorld component that reproduces it, and the measured evidence." },
    { sel: "#prov-table", title: "Every number has a source", text: "DATA, OFFICIAL, STD, ATLAS or ASSUMED. Assumptions are labelled and swept, never hidden. The India Hold Atlas will turn ASSUMED rows into measured ones." },
    { sel: "#proof-tests", title: "Proof", text: "The test suite runs on the real data and the official structures. Reproduce everything with two commands: python -m holdworld test and python -m holdworld run." },
  ];
}

export function startTour() {
  const S = steps();
  const box = $("#tour"), hole = $(".tour-hole", box), card = $(".tour-card", box);
  let i = 0;
  const show = () => {
    const st = S[i];
    const el = document.querySelector(st.sel);
    if (!el) { i = Math.min(S.length - 1, i + 1); return show(); }
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    try { st.run && st.run(); } catch (e) { console.warn(e); }
    $(".tour-step", card).textContent = `STEP ${i + 1} OF ${S.length}`;
    $("h3", card).textContent = st.title;
    $("p", card).textContent = st.text;
    $('[data-act="next"]', card).textContent = i === S.length - 1 ? "Finish" : "Next";
    setTimeout(place, 450);
    function place() {
      const r = el.getBoundingClientRect(), pad = 8;
      Object.assign(hole.style, { left: r.left - pad + "px", top: Math.max(4, r.top - pad) + "px", width: r.width + pad * 2 + "px", height: Math.min(innerHeight - 8, r.height + pad * 2) + "px" });
      const cw = 380, chh = card.offsetHeight || 190;
      let x = r.right + 18, y = r.top;
      if (x + cw > innerWidth - 12) x = Math.max(12, Math.min(innerWidth - cw - 12, r.left));
      if (x === r.right + 18) y = Math.max(12, Math.min(innerHeight - chh - 12, r.top));
      else y = r.bottom + 14 + chh < innerHeight ? r.bottom + 14 : Math.max(12, r.top - chh - 14);
      Object.assign(card.style, { left: x + "px", top: y + "px" });
    }
  };
  const close = () => { box.hidden = true; document.removeEventListener("keydown", key); };
  const key = (e) => { if (e.key === "Escape") close(); if (e.key === "ArrowRight") next(); if (e.key === "ArrowLeft") prev(); };
  const next = () => { if (i >= S.length - 1) return close(); i++; show(); };
  const prev = () => { if (i > 0) { i--; show(); } };
  card.onclick = (e) => { const a = e.target.dataset.act; if (a === "next") next(); if (a === "prev") prev(); if (a === "close") close(); };
  document.addEventListener("keydown", key);
  box.hidden = false;
  show();
}
