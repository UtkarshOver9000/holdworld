// Small SVG chart kit: thin marks, recessive grid, hover tooltips, legends for 2+ series.
import { h, s, showTip, hideTip } from "./core.js";

const niceMax = (m) => { if (m <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(m))); for (const k of [1, 2, 2.5, 5, 10]) if (k * p >= m) return k * p; return 10 * p; };

export function legend(items) {
  return h("div", { class: "legend" }, items.map((i) => h("span", {}, h("i", { style: { background: i.color } }), i.name)));
}

// horizontal bars with optional 95% interval whiskers
export function barsH(rows, { max = null, fmt = (v) => v, width = 560, rowH = 30, labelW = 150, unit = "" } = {}) {
  const m = max ?? niceMax(Math.max(...rows.map((r) => r.hi ?? r.value ?? 0)));
  const H = rows.length * rowH + 26, W = width, x0 = labelW, x1 = W - 56;
  const X = (v) => x0 + (x1 - x0) * Math.max(0, v) / m;
  const g = s("svg", { viewBox: `0 0 ${W} ${H}` });
  for (let i = 0; i <= 4; i++) {
    const v = m * i / 4, x = X(v);
    g.append(s("line", { x1: x, x2: x, y1: 4, y2: H - 20, class: "gridline", stroke: "var(--line)" }));
    g.append(s("text", { x, y: H - 6, "text-anchor": "middle", class: "tick" }, fmt(v)));
  }
  rows.forEach((r, i) => {
    const y = 6 + i * rowH, bh = 12, cy = y + rowH / 2 - 2;
    g.append(s("text", { x: x0 - 10, y: cy + 4, "text-anchor": "end", class: "lbl" }, r.label));
    if (r.value === null || r.value === undefined) return;
    const bar = s("rect", { x: x0, y: cy - bh / 2, width: Math.max(2, X(r.value) - x0), height: bh, rx: 4, fill: r.color });
    g.append(bar);
    if (r.lo !== undefined && r.hi !== undefined && r.lo !== null) {
      g.append(s("line", { x1: X(r.lo), x2: X(r.hi), y1: cy, y2: cy, stroke: "var(--text-2)", "stroke-width": 1.5 }));
      for (const v of [r.lo, r.hi]) g.append(s("line", { x1: X(v), x2: X(v), y1: cy - 5, y2: cy + 5, stroke: "var(--text-2)", "stroke-width": 1.5 }));
    }
    g.append(s("text", { x: Math.max(X(r.value), r.hi !== undefined && r.hi !== null ? X(r.hi) : 0) + 6, y: cy + 4, class: "val" }, fmt(r.value) + unit));
    const hit = s("rect", { x: 0, y, width: W, height: rowH, fill: "transparent" });
    hit.addEventListener("mousemove", (e) => showTip(e, `<b>${r.label}</b><br>${fmt(r.value)}${unit}${r.lo !== undefined && r.lo !== null ? `<br><span class=muted>95% interval ${fmt(r.lo)}–${fmt(r.hi)}${unit}</span>` : ""}${r.sub ? `<br><span class=muted>${r.sub}</span>` : ""}`));
    hit.addEventListener("mouseleave", hideTip);
    g.append(hit);
  });
  return h("div", { class: "chart" }, g);
}

// line chart with a crosshair tooltip
export function lines(series, { width = 560, height = 220, xfmt = (v) => v, yfmt = (v) => v, ymax = null, xlabel = "", ylabel = "", marks = [] } = {}) {
  const W = width, H = height, L = 46, R = 14, T = 12, B = 30;
  const xs = series.flatMap((s2) => s2.points.map((p) => p[0]));
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ym = ymax ?? niceMax(Math.max(...series.flatMap((s2) => s2.points.map((p) => p[1])), 0.0001));
  const X = (v) => L + (W - L - R) * (v - xmin) / Math.max(1e-9, xmax - xmin);
  const Y = (v) => H - B - (H - B - T) * v / ym;
  const g = s("svg", { viewBox: `0 0 ${W} ${H}` });
  for (let i = 0; i <= 4; i++) {
    const v = ym * i / 4;
    g.append(s("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: "var(--line)" }));
    g.append(s("text", { x: L - 6, y: Y(v) + 3, "text-anchor": "end", class: "tick" }, yfmt(v)));
  }
  const ticks = 6;
  for (let i = 0; i <= ticks; i++) {
    const v = xmin + (xmax - xmin) * i / ticks;
    g.append(s("text", { x: X(v), y: H - 12, "text-anchor": "middle", class: "tick" }, xfmt(v)));
  }
  if (xlabel) g.append(s("text", { x: W - R, y: H - 1, "text-anchor": "end", class: "tick" }, xlabel));
  if (ylabel) g.append(s("text", { x: L, y: 9, class: "tick" }, ylabel));
  for (const m of marks) {
    g.append(s("line", { x1: X(m.x), x2: X(m.x), y1: T, y2: H - B, stroke: m.color || "var(--s4)", "stroke-dasharray": "3 3" }));
    g.append(s("text", { x: X(m.x) + 4, y: T + 10 + (m.dy || 0), class: "tick", fill: "var(--text-2)" }, m.text));
  }
  for (const se of series) {
    const d = se.points.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("");
    g.append(s("path", { d, fill: "none", stroke: se.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-dasharray": se.dash || null }));
  }
  const cross = s("line", { y1: T, y2: H - B, stroke: "var(--text-2)", "stroke-width": 1, opacity: 0 });
  g.append(cross);
  const dots = series.map((se) => { const c = s("circle", { r: 4, fill: se.color, stroke: "var(--panel)", "stroke-width": 2, opacity: 0 }); g.append(c); return c; });
  const hit = s("rect", { x: L, y: T, width: W - L - R, height: H - B - T, fill: "transparent" });
  hit.addEventListener("mousemove", (e) => {
    const r = g.getBoundingClientRect();
    const vx = xmin + ((e.clientX - r.left) * W / r.width - L) / (W - L - R) * (xmax - xmin);
    let html = "";
    series.forEach((se, i) => {
      let best = se.points[0];
      for (const p of se.points) if (Math.abs(p[0] - vx) < Math.abs(best[0] - vx)) best = p;
      dots[i].setAttribute("cx", X(best[0])); dots[i].setAttribute("cy", Y(best[1])); dots[i].setAttribute("opacity", 1);
      cross.setAttribute("x1", X(best[0])); cross.setAttribute("x2", X(best[0])); cross.setAttribute("opacity", 0.5);
      if (!html) html += `<b>${xfmt(best[0])}</b>`;
      html += `<br><span style="color:${se.color}">■</span> ${se.name}: <b>${yfmt(best[1])}</b>`;
    });
    showTip(e, html);
  });
  hit.addEventListener("mouseleave", () => { hideTip(); cross.setAttribute("opacity", 0); dots.forEach((d) => d.setAttribute("opacity", 0)); });
  g.append(hit);
  const wrap = h("div", { class: "chart" }, g);
  if (series.length > 1) wrap.append(legend(series));
  return wrap;
}

// vertical columns (e.g. by hour), optional whisker to a second value
export function columns(vals, { width = 300, height = 110, color = "var(--s1)", whisk = null, fmt = (v) => v, xlab = (i) => i, ymax = null, labelEvery = 6 } = {}) {
  const W = width, H = height, B = 16, T = 6;
  const m = ymax ?? niceMax(Math.max(...vals.map((v) => v ?? 0), ...(whisk || []).map((v) => v ?? 0), 0.001));
  const bw = W / vals.length;
  const g = s("svg", { viewBox: `0 0 ${W} ${H}` });
  g.append(s("line", { x1: 0, x2: W, y1: H - B, y2: H - B, stroke: "var(--line-2)" }));
  vals.forEach((v, i) => {
    const x = i * bw;
    if (v !== null && v !== undefined) {
      const hh = (H - B - T) * v / m;
      g.append(s("rect", { x: x + 1, y: H - B - hh, width: Math.max(1, bw - 2), height: Math.max(0, hh), rx: Math.min(3, bw / 3), fill: color }));
      if (whisk && whisk[i] !== null && whisk[i] !== undefined) {
        const hy = H - B - (H - B - T) * Math.min(whisk[i], m) / m;
        g.append(s("line", { x1: x + bw / 2, x2: x + bw / 2, y1: H - B - hh, y2: hy, stroke: "var(--text-2)", "stroke-width": 1 }));
      }
    }
    if (i % labelEvery === 0) g.append(s("text", { x: x + bw / 2, y: H - 3, "text-anchor": "middle", class: "tick" }, xlab(i)));
    const hit = s("rect", { x, y: 0, width: bw, height: H, fill: "transparent" });
    hit.addEventListener("mousemove", (e) => showTip(e, `<b>${xlab(i)}</b><br>${v === null || v === undefined ? "closed" : fmt(v)}${whisk && whisk[i] != null ? `<br><span class=muted>p90 ${fmt(whisk[i])}</span>` : ""}`));
    hit.addEventListener("mouseleave", hideTip);
    g.append(hit);
  });
  return h("div", { class: "chart" }, g);
}

export function scatter(pts, { width = 360, height = 260, max = null, fmt = (v) => v, xlabel = "", ylabel = "", color = "var(--s1)" } = {}) {
  const W = width, H = height, L = 40, B = 30, T = 10, R = 10;
  const m = max ?? niceMax(Math.max(...pts.flatMap((p) => [p.x, p.y])));
  const X = (v) => L + (W - L - R) * v / m, Y = (v) => H - B - (H - B - T) * v / m;
  const g = s("svg", { viewBox: `0 0 ${W} ${H}` });
  for (let i = 0; i <= 4; i++) {
    const v = m * i / 4;
    g.append(s("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: "var(--line)" }));
    g.append(s("text", { x: L - 6, y: Y(v) + 3, "text-anchor": "end", class: "tick" }, fmt(v)));
    g.append(s("text", { x: X(v), y: H - 14, "text-anchor": "middle", class: "tick" }, fmt(v)));
  }
  g.append(s("line", { x1: X(0), y1: Y(0), x2: X(m), y2: Y(m), stroke: "var(--muted)", "stroke-dasharray": "4 4" }));
  g.append(s("text", { x: X(m) - 4, y: Y(m) + 14, "text-anchor": "end", class: "tick" }, "perfect agreement"));
  if (xlabel) g.append(s("text", { x: W - R, y: H - 1, "text-anchor": "end", class: "tick" }, xlabel));
  if (ylabel) g.append(s("text", { x: L, y: 8, class: "tick" }, ylabel));
  for (const p of pts) {
    const c = s("circle", { cx: X(p.x), cy: Y(p.y), r: 6, fill: color, stroke: "var(--panel)", "stroke-width": 2 });
    c.addEventListener("mousemove", (e) => showTip(e, p.tip));
    c.addEventListener("mouseleave", hideTip);
    g.append(c);
  }
  return h("div", { class: "chart" }, g);
}
