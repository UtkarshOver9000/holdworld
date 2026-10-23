// Chapter 6: Hold City (three.js). Tower height = median wait at the chosen hour; people outside = callers
// waiting (Little's law: arrivals per second x mean wait). Drag the clock; add AI holders.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { HW, h, fmt, header, tag, helplineName, visible } from "./core.js";

const C = { hour: 11, playing: true, speed: 0.12, alpha: 0, sel: null };

export function render(root) {
  root.append(header("6 · Hold City", `${Object.keys(HW.waits).length} helplines, one city, a whole day`,
    `Each tower is a helpline. Height tracks its modeled median wait; the caller dots are estimated from arrivals × wait (Little’s law). The 24-hour view follows the historical queue shape, with current assumptions tagged; it is not a live Indian-bank feed. Change the AI-holder share to see people remain in queues when they no longer hang up. Select any tower for waits, agents, hourly demand and the evidence tag.`));
  if (!C.sel && HW.waits.psu_bank) C.sel = "psu_bank";
  const box = h("div", { class: "citybox", id: "city-box" });
  const clock = h("div", { class: "cityclock" }, "11:00");
  const hour = h("input", { type: "range", min: 0, max: 23.9, step: 0.1, value: C.hour, style: { width: "220px" }, oninput: (e) => { C.hour = +e.target.value; C.playing = false; playB.textContent = "▶"; } });
  const playB = h("button", { class: "btn", onclick: () => { C.playing = !C.playing; playB.textContent = C.playing ? "❚❚" : "▶"; } }, "❚❚");
  const pace = h("select", { "aria-label": "City simulation playback speed", title: "Time simulated per real second", onchange: (e) => { C.speed = +e.target.value; } },
    [[0.06, "Slow · 1h / 17s"], [0.12, "Normal · 1h / 8s"], [0.3, "Fast · 1h / 3s"]].map(([value, label]) => h("option", { value, selected: value === C.speed }, label)));
  const alpha = h("input", { type: "range", min: 0, max: 0.5, step: 0.05, value: 0, style: { width: "160px" }, oninput: (e) => { C.alpha = +e.target.value; aL.textContent = `${Math.round(C.alpha * 100)}% AI holders`; } });
  const aL = h("span", { class: "chip" }, "0% AI holders");
  const info = h("div", { class: "card tight", style: { position: "absolute", right: "12px", bottom: "12px", width: "280px" }, id: "city-info" }, h("div", { class: "muted" }, "Click a tower"));
  box.append(h("div", { class: "cityhud" }, clock, playB, hour, pace, alpha, aL), info);
  root.append(box, h("div", { class: "row", style: { marginTop: "8px" } }, h("span", { class: "muted" }, "Tower outline: "), tag("OFFICIAL"), h("span", { class: "muted" }, "menu from an official page ·"), tag("ASSUMED"), h("span", { class: "muted" }, "assumed until the Atlas · gold people = AI holders")));
  requestAnimationFrame(() => {
    try { build(box, clock, hour, info); }
    catch (error) {
      console.error("Hold City initialization failed", error);
      renderFallback(box, clock, hour, info, error);
    }
  });
}

function build(box, clock, hourInput, info) {
  const W = () => box.clientWidth, Hh = () => box.clientHeight;
  // Explore mode is hidden while Watch mode starts. Never create a zero-sized renderer/camera,
  // and resize again when the chapter becomes visible.
  const initialW = Math.max(1, W()), initialH = Math.max(1, Hh());
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(initialW, initialH);
  Object.assign(renderer.domElement.style, { position: "absolute", inset: "0", zIndex: "0" });
  box.prepend(renderer.domElement);
  const labels = new CSS2DRenderer();
  labels.setSize(initialW, initialH);
  Object.assign(labels.domElement.style, { position: "absolute", inset: "0", zIndex: "1", pointerEvents: "none" });
  box.prepend(labels.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x05080e, 60, 150);
  const cam = new THREE.PerspectiveCamera(42, initialW / initialH, 0.1, 400);
  cam.position.set(0, 48, 78);
  const resizeScene = () => {
    const width = W(), height = Hh();
    if (width < 1 || height < 1) return;
    cam.aspect = width / height;
    cam.updateProjectionMatrix();
    renderer.setSize(width, height);
    labels.setSize(width, height);
  };
  if ("ResizeObserver" in window) new ResizeObserver(resizeScene).observe(box);
  addEventListener("resize", resizeScene, { passive: true });
  resizeScene();
  const ctl = new OrbitControls(cam, renderer.domElement);
  ctl.target.set(0, 4, 0); ctl.enableDamping = true; ctl.autoRotate = true; ctl.autoRotateSpeed = 0.35; ctl.maxPolarAngle = Math.PI * 0.47;
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
    towers.push({ hid, x, z, ang, index: i, body, cap, people, lab, div, curH: 1 });
  });

  // One visible HoldForMe routing hub ties the helplines together; moving light pulses
  // make the simulated call paths legible even before a tower is selected.
  const hubMat = new THREE.MeshStandardMaterial({ color: 0x17365d, metalness: 0.45, roughness: 0.35, emissive: 0x0c2b55, emissiveIntensity: 0.9 });
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 6, 15, 8), hubMat);
  hub.position.y = 7.5; scene.add(hub);
  const hubRoof = new THREE.Mesh(new THREE.CylinderGeometry(5.5, 4.6, 1.2, 8), new THREE.MeshStandardMaterial({ color: 0x3987e5, emissive: 0x174d91, emissiveIntensity: 1.2 }));
  hubRoof.position.y = 15.2; scene.add(hubRoof);
  const hubAntenna = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.22, 4, 8), hubMat);
  hubAntenna.position.y = 17.8; scene.add(hubAntenna);
  const hubBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.55, 12, 8), new THREE.MeshBasicMaterial({ color: 0x76c5ff }));
  hubBeacon.position.y = 20; scene.add(hubBeacon);
  const hubRing = new THREE.Mesh(new THREE.TorusGeometry(7.2, 0.13, 8, 64), new THREE.MeshBasicMaterial({ color: 0x3987e5, transparent: true, opacity: 0.7 }));
  hubRing.rotation.x = Math.PI / 2; hubRing.position.y = 0.2; scene.add(hubRing);
  const hubLabel = new CSS2DObject(h("div", { class: "lab hub-label" }, "HOLDFORME", h("small", {}, "AI call-routing hub")));
  hubLabel.position.set(0, 24, 0); scene.add(hubLabel);
  const routes = towers.map((tower, index) => {
    const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0.16, 0), new THREE.Vector3(tower.x, 0.16, tower.z)]);
    scene.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0x28548a, transparent: true, opacity: 0.42 })));
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.22, 8, 6), new THREE.MeshBasicMaterial({ color: 0x8fd4ff }));
    scene.add(dot);
    return { tower, dot, index };
  });
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  renderer.domElement.addEventListener("click", (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, cam);
    const hit = ray.intersectObjects(towers.map((t) => t.body))[0];
    if (hit) { C.sel = hit.object.userData.hid; ctl.autoRotate = false; }
  });
  const m4 = new THREE.Matrix4(), col = new THREE.Color();
  const cityFactor = (hid) => {
    const c = HW.city[hid] || HW.city.psu_bank;
    const rows = c.none; const base = rows[0].hum_wait || 1;
    let lo = rows[0], hi = rows[rows.length - 1];
    for (let i = 0; i < rows.length - 1; i++) if (C.alpha >= rows[i].alpha && C.alpha <= rows[i + 1].alpha) { lo = rows[i]; hi = rows[i + 1]; }
    const f = hi.alpha === lo.alpha ? 0 : (C.alpha - lo.alpha) / (hi.alpha - lo.alpha);
    return (lo.hum_wait + (hi.hum_wait - lo.hum_wait) * f) / base;
  };
  let last = 0, stopped = false;
  function frame(now) {
    if (stopped) return;
    requestAnimationFrame(frame);
    try {
    if (!visible(box)) { last = now; return; }
    const dt = last ? (now - last) / 1000 : 0; last = now;
    if (C.playing) { C.hour = (C.hour + dt * C.speed) % 24; hourInput.value = C.hour; }
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
      const rearLabelLift = t.z < 0 ? Math.max(0, t.index - Math.floor(towers.length / 2)) * 2.6 : 0;
      t.lab.position.set(t.x * 1.12, Math.max(8, t.curH + 2.2) + rearLabelLift, t.z * 1.12);
      t.div.querySelector("small").textContent = open ? `${fmt.sec(med)} · ${waiting} waiting` : "closed";
      if (C.sel === t.hid) renderCityInfo(info, t.hid, hr, open, med, waiting, w);
    }
    routes.forEach(({ tower, dot, index }) => {
      const progress = (now / 2400 + index / routes.length) % 1;
      dot.position.set(tower.x * progress, 0.45 + Math.sin(now / 300 + index) * 0.12, tower.z * progress);
    });
    hubBeacon.material.color.setHSL(0.56, 0.85, 0.58 + Math.sin(now / 260) * 0.12);
    hubRing.scale.setScalar(1 + (Math.sin(now / 950) + 1) * 0.035);
    ctl.update();
    renderer.render(scene, cam);
    labels.render(scene, cam);
    } catch (error) {
      stopped = true;
      console.error("Hold City frame failed; switching to the interactive fallback", error);
      renderFallback(box, clock, hourInput, info, error);
    }
  }
  requestAnimationFrame(frame);
}

function renderCityInfo(info, hid, hour, open, waitSeconds, waiting, data) {
  const helpline = HW.helplines[hid];
  if (!helpline) return;
  const aiWaiting = Math.round(waiting * C.alpha);
  const signature = [hid, hour, open, Math.round(waitSeconds), waiting, aiWaiting, data.agents[hour], data.arrivals[hour], data.answered_90s].join("|");
  if (info.dataset.signature === signature) return;
  info.dataset.signature = signature;
  const children = [
    h("h3", {}, helpline.name, h("span", { class: "sp" }), tag(helpline.tag)),
    h("div", { class: "sub" }, helpline.brand),
    cityStat("Clock hour", `${String(hour).padStart(2, "0")}:00`),
    cityStat("Median wait now", open ? fmt.sec(waitSeconds) : "closed"),
    cityStat("Callers waiting", String(waiting)),
    cityStat("AI holders in queue", String(aiWaiting)),
    cityStat("Agents on duty", String(data.agents[hour] || 0)),
    cityStat("Calls per hour", fmt.int(data.arrivals[hour] || 0))];
  if (data.answered_90s) children.push(h("div", { class: "muted city-sla" }, `TRAI reference: ${(data.answered_90s * 100).toFixed(1)}% answered within 90 s`));
  info.replaceChildren(...children);
}

function cityStat(label, value) {
  return h("div", { class: "stat" }, h("span", {}, label), h("b", {}, value));
}

function renderFallback(box, clock, hourInput, info, reason) {
  for (const child of [...box.children]) {
    if (!child.classList.contains("cityhud") && child.id !== "city-info") child.remove();
  }
  const canvas = h("canvas", { class: "city-fallback", "aria-label": "Interactive animated call-centre city" });
  const status = h("div", { class: "city-fallback-status" }, "Interactive 2D city · graphics fallback");
  box.prepend(canvas);
  box.append(status);
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    status.textContent = `City renderer unavailable: ${reason?.message || "2D canvas is not supported"}`;
    return;
  }
  let last = 0, layout = [], width = 0, height = 0, ratio = 1;
  const ids = Object.keys(HW.waits || {});
  const resize = () => {
    width = box.clientWidth; height = box.clientHeight;
    if (!width || !height) return;
    ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
  };
  if ("ResizeObserver" in window) new ResizeObserver(resize).observe(box);
  addEventListener("resize", resize, { passive: true });
  resize();
  canvas.addEventListener("click", (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    const nearest = layout.map((tower) => ({ tower, distance: Math.hypot(x - tower.x, y - tower.y) }))
      .filter((hit) => hit.distance < hit.tower.hitRadius).sort((a, b) => a.distance - b.distance)[0];
    if (nearest) C.sel = nearest.tower.hid;
  });

  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible(box)) { last = now; return; }
    if (width !== box.clientWidth || height !== box.clientHeight) resize();
    if (!width || !height) return;
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 0; last = now;
    if (C.playing) { C.hour = (C.hour + dt * C.speed) % 24; hourInput.value = C.hour; }
    clock.textContent = fmt.hhmm(C.hour * 3600);
    const hr = Math.floor(C.hour), cx = width / 2, cy = height * 0.72;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const sky = ctx.createLinearGradient(0, 0, 0, height);
    sky.addColorStop(0, "#08101e"); sky.addColorStop(0.62, "#0a1423"); sky.addColorStop(1, "#05080e");
    ctx.fillStyle = sky; ctx.fillRect(0, 0, width, height);
    const glow = ctx.createRadialGradient(cx, cy, 20, cx, cy, Math.max(width, height) * 0.62);
    glow.addColorStop(0, "rgba(43,110,185,.19)"); glow.addColorStop(1, "rgba(5,8,14,0)");
    ctx.fillStyle = glow; ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(72,123,184,.13)"; ctx.lineWidth = 1;
    for (let i = 1; i <= 8; i++) {
      ctx.beginPath(); ctx.ellipse(cx, cy + i * 15, width * (0.09 + i * 0.055), i * 10 + 6, 0, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.beginPath(); ctx.ellipse(cx, cy, Math.min(width * 0.37, 450), Math.min(height * 0.22, 150), 0, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(57,135,229,.45)"; ctx.lineWidth = 1.5; ctx.stroke();
    layout = ids.map((hid, index) => {
      const data = HW.waits[hid], stat = data.stats.find((row) => row.hour === hr);
      const open = data.agents[hr] > 0, points = HW.city?.[hid]?.none || HW.city?.psu_bank?.none || [];
      const baseline = points[0]?.hum_wait || 1;
      let lo = points[0], hi = points[points.length - 1];
      for (let i = 0; i < points.length - 1; i++) if (C.alpha >= points[i].alpha && C.alpha <= points[i + 1].alpha) { lo = points[i]; hi = points[i + 1]; break; }
      const fraction = lo && hi && hi.alpha !== lo.alpha ? (C.alpha - lo.alpha) / (hi.alpha - lo.alpha) : 0;
      const factor = lo && hi ? (lo.hum_wait + (hi.hum_wait - lo.hum_wait) * fraction) / baseline : 1;
      const wait = stat ? stat.median * factor : 0;
      const waiting = open && stat ? Math.min(80, Math.round((data.arrivals[hr] / 3600) * wait)) : 0;
      const angle = (index / ids.length) * Math.PI * 2;
      const radius = Math.min(width * 0.31, 380), depth = 0.68 + (Math.sin(angle) + 1) * 0.16;
      const x = cx + Math.cos(angle) * radius * depth, y = cy + Math.sin(angle) * radius * 0.24;
      const towerHeight = open ? 54 + Math.min(125, Math.sqrt(Math.max(0, wait)) * 5.2) : 40;
      return { hid, data, open, wait, waiting, x, y, depth, towerHeight, hitRadius: Math.max(42, 36 * depth) };
    }).sort((a, b) => a.y - b.y);
    for (const tower of layout) drawFallbackTower(ctx, tower, hr, now);
    ctx.textAlign = "center"; ctx.font = "600 10px IBM Plex Mono, monospace"; ctx.fillStyle = "#9bc7ff";
    ctx.fillText("HOLDFORME · LIVE QUEUE MODEL", cx, height - 22);
    if (C.sel) {
      const t = layout.find((tower) => tower.hid === C.sel);
      if (t) renderCityInfo(info, C.sel, hr, t.open, t.wait, t.waiting, t.data);
    }
  }
  requestAnimationFrame(frame);
}

function drawFallbackTower(ctx, tower, hour, now) {
  const { hid, x, y, depth, towerHeight: height, wait, waiting, data } = tower;
  const width = 43 * depth, top = y - height, hl = HW.helplines[hid];
  const outline = hl?.tag === "OFFICIAL" ? "#199e70" : "#ec835a";
  const load = Math.min(1, wait / 600), hue = Math.round(210 - 210 * load);
  const roof = `hsl(${hue} 82% 58%)`;
  ctx.fillStyle = "rgba(0,0,0,.38)"; ctx.beginPath(); ctx.ellipse(x + 10, y + 8, width * 0.85, 8 * depth, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(x - width / 2, top); ctx.lineTo(x - width / 2 + 12 * depth, top - 8 * depth); ctx.lineTo(x + width / 2 + 12 * depth, top - 8 * depth); ctx.lineTo(x + width / 2, top); ctx.closePath();
  ctx.fillStyle = "#173253"; ctx.fill(); ctx.strokeStyle = roof; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x + width / 2, top); ctx.lineTo(x + width / 2 + 12 * depth, top - 8 * depth); ctx.lineTo(x + width / 2 + 12 * depth, y - 8 * depth); ctx.lineTo(x + width / 2, y); ctx.closePath();
  ctx.fillStyle = "#091321"; ctx.fill(); ctx.strokeStyle = outline; ctx.stroke();
  ctx.beginPath(); ctx.rect(x - width / 2, top, width, height); ctx.fillStyle = "#10223a"; ctx.fill(); ctx.strokeStyle = outline; ctx.stroke();
  ctx.save(); ctx.shadowBlur = 16; ctx.shadowColor = roof; ctx.strokeStyle = roof; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x - width / 2, top); ctx.lineTo(x + width / 2, top); ctx.stroke(); ctx.restore();
  const floors = Math.max(2, Math.floor(height / 17));
  for (let floor = 0; floor < floors; floor++) {
    for (let col = 0; col < 3; col++) {
      const wx = x - width * 0.34 + col * width * 0.31, wy = y - 9 - floor * (height - 14) / floors;
      ctx.fillStyle = (floor + col + hour) % 4 === 0 ? "#90c8ff" : "#315b82";
      ctx.fillRect(wx, wy, 4 * depth, 5 * depth);
    }
  }
  const dots = Math.min(18, Math.ceil(waiting / 3));
  for (let i = 0; i < dots; i++) {
    const row = Math.floor(i / 6), col = i % 6;
    const px = x + width / 2 + 14 * depth + col * 8 * depth, py = y - 4 + row * 9 * depth;
    ctx.beginPath(); ctx.arc(px, py + Math.sin(now / 420 + i) * 1.5, 2.8 * depth, 0, Math.PI * 2);
    ctx.fillStyle = i < Math.round(dots * C.alpha) ? "#e3a21a" : "#a8d2ff"; ctx.fill();
  }
  ctx.textAlign = "center"; ctx.font = `600 ${Math.max(9, 10 * depth)}px IBM Plex Sans, sans-serif`;
  ctx.fillStyle = "#e6edf7"; ctx.fillText(hl?.name || hid, x + 3 * depth, top - 18 * depth);
  ctx.font = "10px IBM Plex Mono, monospace"; ctx.fillStyle = "#92a7c0";
  ctx.fillText(`${tower.open ? fmt.sec(wait) : "closed"} · ${waiting} waiting`, x + 3 * depth, top - 6 * depth);
}
