// Chapter 2: a real day of a real call centre, replayed call by call, and the same day with AI holders.
import { HW, h, fmt, fitCanvas, visible, header, tag } from "./core.js";
import { lines, scatter, columns } from "./charts.js";

const Q = { t: 7 * 3600, playing: false, speed: 16, mode: "real", last: 0 };

export function render(root) {
  const rd = HW.real_day, real = HW.real, ho = HW.holdout;
  const d = rd.date;
  const dateTxt = `${d.slice(4, 6)} ${["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+d.slice(2, 4)]} 19${d.slice(0, 2)}`;
  root.append(header("2 · Recent queue evidence", "What public call-centre data shows in 2026",
    `A recent view of helpline demand comes first: California DHCS county reports from January–June 2026 include call volume, wait by language and abandonment. These are monthly aggregates, not individual call records, and they are not Indian bank measurements. The event-by-event playback below remains a separately labelled historical validation set.`));
  renderModernQueueData(root);
  root.append(header("Historical event replay · 1999", "A real call centre, replayed call by call",
    `This is <b>${dateTxt}</b>, the busiest weekday in November 1999 at the "Anonymous Bank" call centre (${fmt.int(rd.events.length)} regular-service calls). Each dot arrives at its recorded time, waits for its recorded duration, then reaches the recorded agent or hangs up. Change the playback speed or switch to the clearly labelled simulated AI-holder scenarios. This historical Israeli call log validates queue behaviour; it does not describe today's Indian bank waits.`));
  const cv = h("canvas", { class: "queuecv", id: "queue-cv" });
  const play = h("button", { class: "btn primary", id: "queue-play", onclick: () => { Q.playing = !Q.playing; play.textContent = Q.playing ? "❚❚ Pause" : "▶ Play the day"; } }, "▶ Play the day");
  const scrub = h("input", { type: "range", min: 7 * 3600, max: 24 * 3600, step: 30, value: Q.t, oninput: (e) => { Q.t = +e.target.value; clock.textContent = fmt.hhmm(Q.t); draw(cv, stats); } });
  const clock = h("span", { class: "clock" }, "07:00");
  const speed = h("div", { class: "seg", title: "1× is real time; slower playback makes individual arrivals easier to follow." }, [1, 4, 16, 60].map((v) => h("button", { class: v === Q.speed ? "on" : "", "aria-label": `Play at ${v} times real time`, onclick: (e) => { Q.speed = v; [...speed.children].forEach((b) => b.classList.toggle("on", b === e.target)); } }, `${v}×`)));
  const mode = h("div", { class: "seg", id: "queue-mode" }, [["real", "Real records"], ["0.0", "Re-simulated"], ["0.25", "+25% AI holders"], ["0.5", "+50% AI holders"]].map(([k, l]) => h("button", { class: k === Q.mode ? "on" : "", onclick: (e) => { Q.mode = k; [...mode.children].forEach((b) => b.classList.toggle("on", b === e.target)); } }, l)));
  const stats = h("div", { id: "queue-stats" });
  root.append(h("div", { class: "transport" }, play, speed, mode, scrub, clock));
  root.append(h("div", { class: "grid", style: { gridTemplateColumns: "minmax(0,1fr) 280px" } }, cv, h("div", { class: "card" }, h("h3", {}, "Right now"), stats)));
  // the science panels
  const hz = real.patience.hazard.filter((r) => r[0] <= 240);
  const spikes = real.patience.spikes_s.filter((x) => x <= 240);
  const hazard = lines([{ name: "hang-up hazard", color: "#d95926", points: hz.map((r) => [r[0], r[1] * 1000]) }],
    { width: 520, height: 210, xfmt: (v) => `${Math.round(v)} s`, yfmt: (v) => v.toFixed(1), xlabel: "seconds on hold", ylabel: "hang-ups per 1000 waiting callers per second", marks: spikes.map((x, i) => ({ x, text: `spike at ${x} s`, dy: i * 12 })) });
  const pts = ho.days.map((r) => ({ x: r.real_mean_wait, y: r.sim_mean_wait, tip: `<b>${r.date}</b><br>real mean wait ${r.real_mean_wait.toFixed(0)} s<br>re-simulated ${r.sim_mean_wait.toFixed(0)} s<br>abandon ${(r.real_abandon * 100).toFixed(1)}% vs ${(r.sim_abandon * 100).toFixed(1)}%` }));
  const sc = scatter(pts, { xlabel: "real mean wait (s)", ylabel: "re-simulated (s)", fmt: (v) => Math.round(v) });
  const hourly = real.hourly;
  root.append(h("div", { class: "grid g3", style: { marginTop: "14px" } },
    h("div", { class: "card", id: "queue-hazard" }, h("h3", {}, "When people hang up ", tag("DATA")), h("div", { class: "sub" }, `Kaplan–Meier hazard over ${fmt.int(real.queued)} callers who waited. Two spikes: right after the first "please hold" message, and when it replays around 60 s. Brown et al. (2005) found the same.`), hazard),
    h("div", { class: "card", id: "queue-holdout" }, h("h3", {}, "Is the replay right? ", tag("DATA")), h("div", { class: "sub" }, `${ho.days.length} July–December days the fit never saw. Only after-call work (${HW.wrapup_s.toFixed(0)} s) was fitted, on January–June. Correlation ${ho.corr_wait.toFixed(3)} (wait), ${ho.corr_abandon.toFixed(3)} (hang-ups); mean error ${ho.mae_wait.toFixed(1)} s.`), sc),
    h("div", { class: "card" }, h("h3", {}, "The whole year, by hour ", tag("DATA")), h("div", { class: "sub" }, "Average weekday: callers asking for an agent (bars) and how many hang up."),
      columns(hourly.map((r) => r.hour >= 7 ? r.arrivals_per_day : null), { width: 320, height: 120, fmt: (v) => `${v.toFixed(0)} calls`, xlab: (i) => `${i}:00`, labelEvery: 4 }),
      columns(hourly.map((r) => r.hour >= 7 ? r.abandon_frac * 100 : null), { width: 320, height: 90, color: "#d95926", fmt: (v) => `${v.toFixed(1)}% hang up`, xlab: (i) => `${i}:00`, labelEvery: 4 }),
      h("div", { class: "muted", style: { fontSize: "12px", marginTop: "6px" } }, `${fmt.int(real.records)} records · ${(real.abandon_frac * 100).toFixed(1)}% hang up · median service ${real.service.median_s} s · ${(real.p_wait_zero * 100).toFixed(0)}% answered at once`))));
  prepare();
  setTimeout(() => draw(cv, stats), 0);
  const loop = (now) => {
    requestAnimationFrame(loop);
    const dt = Q.last ? Math.min(0.1, (now - Q.last) / 1000) : 0; Q.last = now;
    if (Q.playing) { Q.t += dt * Q.speed; if (Q.t >= 24 * 3600) { Q.t = 24 * 3600; Q.playing = false; play.textContent = "▶ Play the day"; } }
    if (!visible(cv)) return;
    scrub.value = Q.t; clock.textContent = fmt.hhmm(Q.t);
    draw(cv, stats);
  };
  requestAnimationFrame(loop);
}
export const queue = { play: () => { Q.playing = true; const b = document.getElementById("queue-play"); if (b) b.textContent = "❚❚ Pause"; }, set: (o) => Object.assign(Q, o) };

function renderModernQueueData(root) {
  const body = h("div", { class: "recent-data-body" }, "Loading the saved 2026 county dataset…");
  const panel = h("section", { class: "card recent-data", id: "queue-2026" },
    h("div", { class: "row" }, h("div", { class: "kicker" }, "CONTEMPORARY PUBLIC DATA · 2026"), h("span", { class: "sp" }), tag("DATA")),
    h("h3", {}, "California Medi-Cal call-centre reports, January–June 2026"),
    h("p", { class: "recent-intro" }, "A six-month, county-by-county view with actual call totals, average wait by language, and abandonment. Choose a month to inspect the county data and language waits."),
    body);
  root.append(panel);

  fetch(new URL("../data/medi_cal_2026.json", import.meta.url))
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((payload) => {
      const months = payload.months;
      body.replaceChildren();
      const monthSelect = h("select", { "aria-label": "Select a reporting month" }, months.map((month) => h("option", { value: month.month }, month.label)));
      const metrics = h("div", { class: "recent-kpis" });
      const trend = h("div", { class: "recent-table-wrap" });
      const countyTable = h("div", { class: "recent-table-wrap" });
      const countySelect = h("select", { "aria-label": "Select a county for language wait details" });
      const languageTable = h("div", { class: "recent-table-wrap" });
      const detailHeading = h("h4", {}, "Language wait times");
      const detailScope = h("p", { class: "muted recent-note" });
      const source = h("p", { class: "recent-note" },
        h("a", { href: payload.source.dataset_url, target: "_blank", rel: "noreferrer" }, "California DHCS · source, definitions and license ↗"),
        ` · Data updated ${payload.source.data_updated}; snapshot saved ${payload.source.snapshot_retrieved}.`);
      body.append(
        h("div", { class: "row recent-filter" }, h("label", {}, "Reporting month ", monthSelect)),
        metrics,
        h("div", { class: "recent-subhead" }, h("h4", {}, "Six-month trend"), h("span", { class: "muted" }, "County medians are unweighted; volume includes IVR and after-hours calls.")),
        trend,
        h("div", { class: "recent-subhead" }, h("h4", {}, "County detail"), h("span", { class: "muted" }, "Sorted by average all-language wait, longest first.")),
        countyTable,
        h("div", { class: "recent-subhead" }, detailHeading, h("label", {}, "County ", countySelect)),
        detailScope,
        languageTable,
        h("p", { class: "recent-note" }, "A blank is not zero: some values were suppressed or not reported. Abandonment is for callers who entered a live-agent queue; it excludes IVR self-service."),
        source);

      const cell = (value) => h("td", {}, value);
      const table = (heads, rows) => h("table", { class: "t" },
        h("thead", {}, h("tr", {}, heads.map((label) => h("th", {}, label)))),
        h("tbody", {}, rows));
      const metric = (label, value, note) => h("div", { class: "recent-metric" },
        h("span", {}, label), h("b", {}, value), h("small", {}, note));
      const formatAbandon = (value) => value === null || value === undefined ? "—" : `${(value * 100).toFixed(0)}%`;

      function renderMonth() {
        const selected = months.find((month) => month.month === monthSelect.value) || months[0];
        metrics.replaceChildren(
          metric("Calls received", fmt.int(selected.total_calls), `${selected.counties_with_volume} counties · includes IVR and after-hours`),
          metric("Median county average wait", fmt.sec(selected.county_median_wait_seconds), `${selected.counties_with_wait} county averages · all languages`),
          metric("Median county abandonment", formatAbandon(selected.county_median_abandonment_rate), `${selected.counties_with_abandonment} reporting counties · unweighted median`));

        trend.replaceChildren(table(
          ["Month", "Total calls received", "Median county average wait", "Median county abandonment"],
          months.map((month) => h("tr", { class: month.month === selected.month ? "selected-row" : "" },
            cell(month.label), cell(fmt.int(month.total_calls)),
            cell(`${fmt.sec(month.county_median_wait_seconds)} · ${month.counties_with_wait} counties`),
            cell(`${formatAbandon(month.county_median_abandonment_rate)} · ${month.counties_with_abandonment} counties`)))));

        const records = selected.counties;
        countyTable.replaceChildren(table(
          ["County", "Calls", "Working hours", "After hours", "Avg wait · all languages", "Abandonment"],
          records.map((county) => h("tr", {},
            cell(county.county), cell(fmt.int(county.total_calls)), cell(fmt.int(county.calls_working_hours)),
            cell(fmt.int(county.calls_after_hours)), cell(fmt.sec(county.average_wait_seconds)),
            cell(formatAbandon(county.abandonment_rate))))));

        const options = [...records].sort((a, b) => a.county.localeCompare(b.county));
        countySelect.replaceChildren(options.map((county) => h("option", { value: county.county }, county.county)));
        const defaultCounty = records.find((county) => county.average_wait_seconds !== null)?.county || options[0]?.county;
        if (defaultCounty) countySelect.value = defaultCounty;
        renderLanguages();
      }

      function renderLanguages() {
        const selected = months.find((month) => month.month === monthSelect.value) || months[0];
        const county = selected.counties.find((row) => row.county === countySelect.value);
        const languages = Object.entries(county?.language_wait_seconds || {}).sort((a, b) => a[0].localeCompare(b[0]));
        detailHeading.textContent = `Language wait times · ${county?.county || "select a county"}`;
        detailScope.textContent = `Monthly average time from entering the queue to an agent pickup. ${languages.length} language measurements were published for this county.`;
        languageTable.replaceChildren(table(["Language", "Average wait"], languages.map(([language, wait]) => h("tr", {}, cell(language), cell(fmt.sec(wait))))));
        if (!languages.length) languageTable.textContent = "No language-level values were published for this county and month.";
      }

      monthSelect.addEventListener("change", renderMonth);
      countySelect.addEventListener("change", renderLanguages);
      monthSelect.value = months[months.length - 1].month;
      renderMonth();
    })
    .catch((error) => {
      body.textContent = `The saved 2026 dataset could not be loaded (${error.message}). The source files and rebuild script are included in the repository.`;
      console.warn("2026 queue dataset failed to load", error);
    });
}

let REAL = [], SIMS = {}, servers = [], staffing = {};
function prepare() {
  const rd = HW.real_day;
  servers = rd.servers || [...new Set(rd.events.map((e) => e[5]).filter((x) => x && x !== "NO_SERVER"))].sort();
  const sidx = Object.fromEntries(servers.map((s, i) => [s, i]));
  REAL = rd.events.map(([a, q, o, s2, p, srv]) => ({ a, w: q, srv: o === "A", desk: sidx[srv] ?? -1, s: s2, k: p === 2 ? "p" : "h" }));
  if (!servers.length) servers = Array.from({ length: 12 }, (_, i) => `agent ${i + 1}`);
  for (const [al, sim] of Object.entries(rd.sims)) SIMS[al] = sim.callers.map(([a, w, srv, k, d, s2]) => ({ a, w: w ?? 0, srv: !!srv, desk: d ?? -1, s: s2, k: k === "a" ? "ai" : "h" }));
  staffing = rd.staffing;
}

function draw(cv, stats) {
  const { ctx, w, h: H } = fitCanvas(cv);
  ctx.clearRect(0, 0, w, H);
  const data = Q.mode === "real" ? REAL : SIMS[Q.mode] || REAL;
  const t = Q.t;
  const deskN = Q.mode === "real" ? servers.length : Math.max(8, ...data.map((c) => (c.desk ?? 0) + 1));
  const staffNow = staffing[String(Math.floor(t / 900) * 900)] || 0;
  const waiting = [], serving = [], gone = [], done = [];
  let served = 0, ab = 0, waitSum = 0, nW = 0, aiWait = 0;
  for (const c of data) {
    if (c.a > t) break;
    const endQ = c.a + c.w;
    if (t < endQ) { waiting.push(c); if (c.k === "ai") aiWait++; continue; }
    if (c.srv) { served++; waitSum += c.w; nW++; if (t < endQ + c.s) serving.push(c); }
    else { ab++; if (t - endQ < 120) gone.push([c, (t - endQ) / 120]); }
  }
  // layout: queue lane on the left, desks on the right
  const laneX = 30, laneW = w * 0.42, deskX = laneX + laneW + 50, cols = Math.ceil(Math.sqrt(deskN * 1.6)), dw = (w - deskX - 30) / cols, rows = Math.ceil(deskN / cols), dh = Math.min(64, (H - 70) / rows);
  ctx.font = "600 12px IBM Plex Sans"; ctx.fillStyle = "#a9b6cb";
  ctx.fillText(`Waiting (${waiting.length})`, laneX, 22);
  ctx.fillText(Q.mode === "real" ? `Agents (real names) · ${staffNow} on duty now` : `Agents · ${staffNow} on duty now`, deskX, 22);
  // queue dots in arrival order (snake)
  const per = Math.max(6, Math.floor(laneW / 16));
  waiting.sort((a, b) => a.a - b.a).forEach((c, i) => {
    const r = Math.floor(i / per), col = r % 2 ? per - 1 - (i % per) : i % per;
    const x = laneX + 8 + col * 16, y = 46 + r * 18;
    if (y > H - 20) return;
    const waited = t - c.a;
    ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fillStyle = c.k === "ai" ? "#c98500" : waited > 120 ? "#d95926" : waited > 45 ? "#9085e9" : "#3987e5";
    ctx.fill();
  });
  // abandoned callers float away
  for (const [c, f] of gone) {
    const x = laneX + 20 + (c.a % 97) / 97 * (laneW - 40), y = H - 20 - f * 60;
    ctx.globalAlpha = 1 - f; ctx.fillStyle = "#e66767"; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
    ctx.font = "10px IBM Plex Mono"; ctx.fillText("hung up", x + 8, y + 3); ctx.globalAlpha = 1;
  }
  // desks
  const busy = new Map(serving.map((c) => [c.desk, c]));
  for (let d = 0; d < deskN; d++) {
    const x = deskX + (d % cols) * dw, y = 36 + Math.floor(d / cols) * dh;
    const c = busy.get(d);
    ctx.fillStyle = c ? (c.k === "ai" ? "#2a2108" : "#0d2a22") : "#0d1524";
    ctx.strokeStyle = c ? (c.k === "ai" ? "#c98500" : "#199e70") : "#1c2740";
    ctx.lineWidth = 1.5; ctx.beginPath(); ctx.roundRect(x + 3, y + 3, dw - 6, dh - 6, 6); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#6c7a92"; ctx.font = "10px IBM Plex Mono";
    ctx.fillText(Q.mode === "real" ? (servers[d] || "").slice(0, 8) : `desk ${d + 1}`, x + 9, y + 16);
    if (c) {
      const f = Math.min(1, (t - c.a - c.w) / Math.max(1, c.s));
      ctx.strokeStyle = c.k === "ai" ? "#c98500" : "#199e70"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(x + dw / 2, y + dh / 2 + 6, 9, -Math.PI / 2, -Math.PI / 2 + f * Math.PI * 2); ctx.stroke();
    }
  }
  // legend
  const lg = [["#3987e5", "waiting < 45 s"], ["#9085e9", "45–120 s"], ["#d95926", "> 2 min"], ["#c98500", "AI holder (never hangs up)"], ["#199e70", "being served"], ["#e66767", "hung up"]];
  ctx.font = "11px IBM Plex Sans"; let lx = laneX;
  for (const [c, l] of lg) { ctx.fillStyle = c; ctx.fillRect(lx, H - 12, 10, 8); ctx.fillStyle = "#a9b6cb"; ctx.fillText(l, lx + 14, H - 4); lx += ctx.measureText(l).width + 34; }
  stats.innerHTML = "";
  const row = (k, v) => h("div", { class: "stat" }, h("span", {}, k), h("b", {}, v));
  const sim = Q.mode === "real" ? null : HW.real_day.sims[Q.mode];
  stats.append(row("Clock", fmt.hhmm(t)), row("Waiting now", String(waiting.length)), row("AI holders waiting", String(aiWait)),
    row("Served so far", fmt.int(served)), row("Hung up so far", fmt.int(ab)),
    row("Hang-up rate so far", served + ab ? `${(ab / (served + ab) * 100).toFixed(1)}%` : "–"),
    row("Mean wait so far", nW ? fmt.sec(waitSum / nW) : "–"));
  if (sim) stats.append(h("div", { class: "note", style: { marginTop: "10px" } }, `Whole day, this setting: humans wait ${fmt.sec(sim.human_wait)} on average and ${(sim.human_abandon * 100).toFixed(1)}% hang up${sim.ai_wait !== null ? `; AI holders wait ${fmt.sec(sim.ai_wait)}` : ""}.`));
  else stats.append(h("div", { class: "note", style: { marginTop: "10px" } }, "These are the real records: real arrival times, real waits, real hang-ups, real agents."));
}
