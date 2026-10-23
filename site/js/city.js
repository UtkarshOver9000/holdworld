// Chapter 6: Hold City (three.js). Tower height = median wait at the chosen hour; people outside = callers
// waiting (Little's law: arrivals per second x mean wait). Drag the clock; add AI holders.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { HW, h, fmt, header, tag, helplineName, visible } from "./core.js";

const C = { hour: 11, playing: true, alpha: 0, sel: null };

export function render(root) {
  root.append(header("6 · Hold City", "Nine helplines, one city, a whole day",
    "Each tower is a helpline. Its height is the median wait at the hour on the clock, and the people lined up outside are how many callers are waiting right now (arrivals × wait, by Little's law). Watch the morning and afternoon peaks from the real 1999 shape roll through. Drag the AI-holder slider to see queues swell where callers stop hanging up. Click a tower for details."));
  const box = h("div", { class: "citybox", id: "city-box" });
  const clock = h("div", { class: "cityclock" }, "11:00");
  const hour = h("input", { type: "range", min: 0, max: 23.9, step: 0.1, value: C.hour, style: { width: "220px" }, oninput: (e) => { C.hour = +e.target.value; C.playing = false; playB.textContent = "▶"; } });
  const playB = h("button", { class: "btn", onclick: () => { C.playing = !C.playing; playB.textContent = C.playing ? "❚❚" : "▶"; } }, "❚❚");
  const alpha = h("input", { type: "range", min: 0, max: 0.5, step: 0.05, value: 0, style: { width: "160px" }, oninput: (e) => { C.alpha = +e.target.value; aL.textContent = `${Math.round(C.alpha * 100)}% AI holders`; } });
  const aL = h("span", { class: "chip" }, "0% AI holders");
  const info = h("div", { class: "card tight", style: { position: "absolute", right: "12px", bottom: "12px", width: "280px" }, id: "city-info" }, h("div", { class: "muted" }, "Click a tower"));
  box.append(h("div", { class: "cityhud" }, clock, playB, hour, alpha, aL), info);
  root.append(box, h("div", { class: "row", style: { marginTop: "8px" } }, h("span", { class: "muted" }, "Tower outline: "), tag("OFFICIAL"), h("span", { class: "muted" }, "menu from an official page ·"), tag("ASSUMED"), h("span", { class: "muted" }, "assumed until the Atlas · gold people = AI holders")));
  requestAnimationFrame(() => build(box, clock, hour, info));
}

function build(box, clock, hourInput, info) {
  const W = () => box.clientWidth, Hh = () => box.clientHeight;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(W(), Hh());
  box.prepend(renderer.domElement);
  const labels = new CSS2DRenderer();
  labels.setSize(W(), Hh());
  Object.assign(labels.domElement.style, { position: "absolute", top: "0", left: "0", pointerEvents: "none" });
  box.prepend(labels.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x05080e, 60, 150);
  const cam = new THREE.PerspectiveCamera(42, W() / Hh(), 0.1, 400);
  cam.position.set(0, 42, 70);
  const ctl = new OrbitControls(cam, renderer.domElement);
  ctl.target.set(0, 6, 0); ctl.enableDamping = true; ctl.autoRotate = true; ctl.autoRotateSpeed = 0.35; ctl.maxPolarAngle = Math.PI * 0.47;
  scene.add(new THREE.AmbientLight(0x8899bb, 0.55));
  const sun = new THREE.DirectionalLight(0xffffff, 1.1); sun.position.set(30, 60, 20); scene.add(sun);
  const grid = new THREE.GridHelper(160, 64, 0x1c2740, 0x111a2a); scene.add(grid);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(80, 64), new THREE.MeshStandardMaterial({ color: 0x070b12, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.01; scene.add(ground);

  const ids = Object.keys(HW.waits);
  const towers = [];
  ids.forEach((hid, i) => {
    const ang = (i / ids.length) * Math.PI * 2, R = 30;
    const x = Math.cos(ang) * R, z = Math.sin(ang) * R;
    const hl = HW.helplines[hid];
    const off = hl.tag === "OFFICIAL";
    const mat = new THREE.MeshStandardMaterial({ color: 0x12203a, metalness: 0.3, roughness: 0.45, emissive: 0x0a1a33, emissiveIntensity: 0.6 });
    const body = new THREE.Mesh(new THREE.BoxGeometry(6, 1, 6), mat);
    body.position.set(x, 0.5, z); body.userData.hid = hid; scene.add(body);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(6, 1, 6)), new THREE.LineBasicMaterial({ color: off ? 0x199e70 : 0xec835a }));
    body.add(edges);
    const cap = new THREE.Mesh(new THREE.BoxGeometry(6.2, 0.35, 6.2), new THREE.MeshStandardMaterial({ color: 0x3987e5, emissive: 0x3987e5, emissiveIntensity: 0.9 }));
    scene.add(cap);
    const people = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.28, 0.6, 3, 6), new THREE.MeshStandardMaterial({ color: 0xffffff }), 80);
    people.instanceMatrix.setUsage(THREE.DynamicDrawUsage); scene.add(people);
    const div = h("div", { class: "lab" }, hl.name, h("small", {}, ""));
    const lab = new CSS2DObject(div); scene.add(lab);
    towers.push({ hid, x, z, ang, body, cap, people, lab, div, curH: 1 });
  });
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  renderer.domElement.addEventListener("click", (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, cam);
    const hit = ray.intersectObjects(towers.map((t) => t.body))[0];
    if (hit) { C.sel = hit.object.userData.hid; ctl.autoRotate = false; }
  });
  addEventListener("resize", () => { cam.aspect = W() / Hh(); cam.updateProjectionMatrix(); renderer.setSize(W(), Hh()); labels.setSize(W(), Hh()); });
  const m4 = new THREE.Matrix4(), col = new THREE.Color();
  const cityFactor = (hid) => {
    const c = HW.city[hid] || HW.city.psu_bank;
    const rows = c.none; const base = rows[0].hum_wait || 1;
    let lo = rows[0], hi = rows[rows.length - 1];
    for (let i = 0; i < rows.length - 1; i++) if (C.alpha >= rows[i].alpha && C.alpha <= rows[i + 1].alpha) { lo = rows[i]; hi = rows[i + 1]; }
    const f = hi.alpha === lo.alpha ? 0 : (C.alpha - lo.alpha) / (hi.alpha - lo.alpha);
    return (lo.hum_wait + (hi.hum_wait - lo.hum_wait) * f) / base;
  };
  let last = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible(box)) return;
    const dt = last ? (now - last) / 1000 : 0; last = now;
    if (C.playing) { C.hour = (C.hour + dt * 0.6) % 24; hourInput.value = C.hour; }
    clock.textContent = fmt.hhmm(C.hour * 3600);
    const hr = Math.floor(C.hour);
    for (const t of towers) {
      const w = HW.waits[t.hid];
      const st = w.stats.find((r) => r.hour === hr);
      const open = w.agents[hr] > 0;
      const factor = cityFactor(t.hid);
      const med = st ? st.median * factor : 0;
      const target = open ? 1 + Math.min(34, med / 18) : 0.6;
      t.curH += (target - t.curH) * Math.min(1, dt * 3);
      t.body.scale.y = t.curH; t.body.position.y = t.curH / 2;
      t.cap.position.set(t.x, t.curH + 0.2, t.z);
      const load = Math.min(1, med / 600);
      t.cap.material.color.setHSL(0.6 - 0.6 * load, 0.8, 0.5); t.cap.material.emissive.copy(t.cap.material.color);
      t.body.material.emissiveIntensity = open ? 0.6 : 0.1;
      const waiting = open && st ? Math.min(80, Math.round((w.arrivals[hr] / 3600) * med)) : 0;
      const ai = Math.round(waiting * C.alpha);
      const dir = new THREE.Vector3(-Math.cos(t.ang), 0, -Math.sin(t.ang));
      const side = new THREE.Vector3(-dir.z, 0, dir.x);
      for (let i = 0; i < 80; i++) {
        if (i < waiting) {
          const row = Math.floor(i / 10), k = i % 10;
          const p = new THREE.Vector3(t.x, 0.6, t.z).addScaledVector(dir, 4.6 + row * 1.0).addScaledVector(side, (k - 4.5) * 0.75);
          p.y = 0.6 + Math.abs(Math.sin(now / 400 + i)) * 0.05;
          m4.makeTranslation(p.x, p.y, p.z);
          t.people.setColorAt(i, col.set(i < ai ? 0xc98500 : 0x9cc6ff));
        } else m4.makeScale(0, 0, 0);
        t.people.setMatrixAt(i, m4);
      }
      t.people.instanceMatrix.needsUpdate = true; if (t.people.instanceColor) t.people.instanceColor.needsUpdate = true;
      t.lab.position.set(t.x, t.curH + 2.2, t.z);
      t.div.querySelector("small").textContent = open ? `${fmt.sec(med)} · ${waiting} waiting` : "closed";
      if (C.sel === t.hid) {
        const hl = HW.helplines[t.hid];
        info.innerHTML = "";
        info.append(h("h3", {}, hl.name, h("span", { class: "sp" }), tag(hl.tag)), h("div", { class: "sub" }, hl.brand),
          h("div", { class: "stat" }, h("span", {}, "Median wait now"), h("b", {}, open ? fmt.sec(med) : "closed")),
          h("div", { class: "stat" }, h("span", {}, "Callers waiting"), h("b", {}, String(waiting))),
          h("div", { class: "stat" }, h("span", {}, "Agents on duty"), h("b", {}, String(w.agents[hr]))),
          h("div", { class: "stat" }, h("span", {}, "Calls per hour"), h("b", {}, w.arrivals[hr].toFixed(0))),
          w.answered_90s ? h("div", { class: "muted", style: { fontSize: "12px", marginTop: "6px" } }, `TRAI: ${(w.answered_90s * 100).toFixed(1)}% answered within 90 s`) : null);
      }
    }
    ctl.update();
    renderer.render(scene, cam);
    labels.render(scene, cam);
  }
  requestAnimationFrame(frame);
}
