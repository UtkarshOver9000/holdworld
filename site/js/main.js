// Boot: build the chapters, the navigation, the tour.
import { HW, h, $ } from "./core.js";
import * as overview from "./overview.js";
import * as theatre from "./theatre.js";
import * as queue from "./queue.js";
import * as S from "./sections.js";
import { startTour } from "./tour.js";

const CHAPTERS = [
  ["overview", "Overview", overview.render], ["call", "Call theatre", theatre.render], ["queue", "Real queue", queue.render],
  ["waits", "Wait times", S.renderWaits], ["handoff", "Handoff race", S.renderHandoff], ["pine", "Pine mode", S.renderPine],
  ["city", "Hold City (3D)", null], ["evidence", "Evidence", S.renderEvidence], ["parity", "Feature parity", S.renderParity],
  ["data", "Provenance", S.renderData], ["proof", "Proof", S.renderProof],
];

function boot() {
  if (!HW) { document.body.innerHTML = "<p style='padding:40px'>Missing data/world.js. Run: python -m holdworld run</p>"; return; }
  const nav = $("#chapters");
  CHAPTERS.forEach(([id, name, fn], i) => {
    nav.append(h("a", { href: `#${id}`, "data-id": id }, h("span", { class: "n" }, String(i).padStart(2, "0")), name));
    const root = document.getElementById(id);
    try { if (fn) fn(root); } catch (e) { console.error(id, e); root.append(h("div", { class: "note" }, `This chapter failed to render: ${e.message}`)); }
  });
  import("./city.js").then((m) => m.render(document.getElementById("city"))).catch((e) => {
    console.warn("3D city unavailable", e);
    document.getElementById("city").append(h("div", { class: "note" }, "The 3D city needs WebGL and the three.js CDN. The rest of the page works without it."));
  });
  const main = $("#main");
  const links = [...nav.querySelectorAll("a")];
  main.addEventListener("scroll", () => {
    let cur = CHAPTERS[0][0];
    for (const [id] of CHAPTERS) { const el = document.getElementById(id); if (el.getBoundingClientRect().top < innerHeight * 0.35) cur = id; }
    links.forEach((a) => a.classList.toggle("on", a.dataset.id === cur));
  }, { passive: true });
  links[0].classList.add("on");
  $("#tour-btn").addEventListener("click", startTour);
  if (location.hash === "#tour") setTimeout(startTour, 1200);
}
boot();
