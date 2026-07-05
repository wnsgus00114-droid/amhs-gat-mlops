import * as THREE from './vendor/three/three.module.js';
import { OrbitControls } from './vendor/three/OrbitControls.js';

const app = document.getElementById('app');
const statsEl = document.getElementById('stats');
const playBtn = document.getElementById('play');
const pauseBtn = document.getElementById('pause');
const resetBtn = document.getElementById('reset');
const speedRange = document.getElementById('speed');
const speedValue = document.getElementById('speed-value');
const timeRange = document.getElementById('time');

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x061018);
scene.fog = new THREE.Fog(0x061018, 140, 500);

const camera = new THREE.PerspectiveCamera(56, window.innerWidth / window.innerHeight, 0.1, 2000);
camera.position.set(120, 95, 185);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(70, 10, -16);

const hemi = new THREE.HemisphereLight(0xbddcff, 0x081018, 0.82);
scene.add(hemi);

const dir = new THREE.DirectionalLight(0xffffff, 1.05);
dir.position.set(80, 120, 90);
dir.castShadow = true;
dir.shadow.mapSize.width = 2048;
dir.shadow.mapSize.height = 2048;
dir.shadow.camera.near = 0.1;
dir.shadow.camera.far = 500;
dir.shadow.camera.left = -220;
dir.shadow.camera.right = 220;
dir.shadow.camera.top = 180;
dir.shadow.camera.bottom = -180;
scene.add(dir);

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(800, 360),
  new THREE.MeshStandardMaterial({ color: 0x0a141d, roughness: 0.98, metalness: 0.02 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = 0;
floor.receiveShadow = true;
scene.add(floor);

const grid = new THREE.GridHelper(800, 120, 0x2e5870, 0x163040);
grid.position.y = 0.02;
scene.add(grid);

let sceneData = null;
let railGroup = null;
let supportGroup = null;
let nodeGroup = null;
let ohtGroup = null;
let labelsGroup = null;
let ohtMeshes = [];

let simTime = 0;
let playing = true;
let speed = Number(speedRange.value);
let tMin = 0;
let tMax = 1;

function typeColor(type) {
  if (type === 'tool') return 0xf4a340;
  if (type === 'junction') return 0x63c7ff;
  if (type === 'station_s') return 0x78f59a;
  if (type === 'station_t') return 0x9fd7ff;
  if (type === 'main_m') return 0xf7709b;
  if (type === 'main_n') return 0xe65a7a;
  return 0xb8c5cf;
}

function buildStaticGeometry(data) {
  if (railGroup) scene.remove(railGroup);
  if (supportGroup) scene.remove(supportGroup);
  if (nodeGroup) scene.remove(nodeGroup);
  if (ohtGroup) scene.remove(ohtGroup);

  railGroup = new THREE.Group();
  supportGroup = new THREE.Group();
  nodeGroup = new THREE.Group();
  ohtGroup = new THREE.Group();

  const nodeMap = new Map(data.nodes.map((n) => [n.id, n]));

  const railMat = new THREE.MeshStandardMaterial({
    color: 0x5f90b0,
    metalness: 0.78,
    roughness: 0.3,
  });

  for (const e of data.edges) {
    const s = nodeMap.get(e.source);
    const t = nodeMap.get(e.target);
    if (!s || !t) continue;

    const start = new THREE.Vector3(s.x, s.y, s.z);
    const end = new THREE.Vector3(t.x, t.y, t.z);
    const dist = start.distanceTo(end);
    if (dist < 0.001) continue;

    const curve = new THREE.LineCurve3(start, end);
    const tube = new THREE.TubeGeometry(curve, 1, 0.18, 6, false);
    const mesh = new THREE.Mesh(tube, railMat);
    mesh.castShadow = true;
    railGroup.add(mesh);
  }

  const supportMat = new THREE.MeshStandardMaterial({ color: 0x274458, metalness: 0.35, roughness: 0.7 });
  const supportGeom = new THREE.CylinderGeometry(0.1, 0.18, 1, 8);

  for (const n of data.nodes) {
    const h = Math.max(0.5, n.y - 0.4);
    const m = new THREE.Mesh(supportGeom, supportMat);
    m.scale.y = h;
    m.position.set(n.x, h / 2, n.z);
    m.castShadow = true;
    supportGroup.add(m);
  }

  for (const n of data.nodes) {
    let geom;
    let y = n.y;
    if (n.type === 'tool') {
      geom = new THREE.BoxGeometry(0.95, 1.55, 0.95);
      y = n.y + 0.82;
    } else if (n.type === 'junction') {
      geom = new THREE.CylinderGeometry(0.34, 0.34, 0.32, 20);
      y = n.y + 0.16;
    } else {
      geom = new THREE.SphereGeometry(0.31, 14, 14);
      y = n.y + 0.32;
    }

    const mat = new THREE.MeshStandardMaterial({
      color: typeColor(n.type),
      metalness: 0.15,
      roughness: 0.55,
      emissive: typeColor(n.type),
      emissiveIntensity: 0.06,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(n.x, y, n.z);
    mesh.castShadow = true;
    nodeGroup.add(mesh);
  }

  const bayMat = new THREE.MeshStandardMaterial({ color: 0x123249, metalness: 0.12, roughness: 0.86 });
  const bayA = new THREE.Mesh(new THREE.BoxGeometry(230, 2.2, 20), bayMat);
  bayA.position.set(66, 1.1, -28);
  bayA.receiveShadow = true;
  bayA.castShadow = true;
  const bayB = new THREE.Mesh(new THREE.BoxGeometry(230, 2.2, 20), bayMat);
  bayB.position.set(66, 1.1, -4);
  bayB.receiveShadow = true;
  bayB.castShadow = true;
  const bayC = new THREE.Mesh(new THREE.BoxGeometry(230, 2.2, 20), bayMat);
  bayC.position.set(66, 1.1, 20);
  bayC.receiveShadow = true;
  bayC.castShadow = true;
  scene.add(bayA, bayB, bayC);

  const ohtGeom = new THREE.BoxGeometry(0.5, 0.32, 0.82);
  ohtMeshes = data.tracks.map((track, idx) => {
    const hue = (idx * 0.61803398875) % 1;
    const color = new THREE.Color().setHSL(hue, 0.68, 0.58);
    const mat = new THREE.MeshStandardMaterial({
      color,
      metalness: 0.52,
      roughness: 0.28,
      emissive: color,
      emissiveIntensity: 0.16,
    });
    const mesh = new THREE.Mesh(ohtGeom, mat);
    mesh.castShadow = true;
    mesh.userData.track = track;
    mesh.userData.cursor = 0;

    const k0 = track.keyframes[0];
    mesh.position.set(k0[1], k0[2] + 0.35, k0[3]);
    ohtGroup.add(mesh);
    return mesh;
  });

  scene.add(railGroup, supportGroup, nodeGroup, ohtGroup);
}

function interpolateAt(track, t, cursorHint = 0) {
  const k = track.keyframes;
  if (t <= k[0][0]) return { x: k[0][1], y: k[0][2], z: k[0][3], cursor: 0 };
  if (t >= k[k.length - 1][0]) {
    const last = k[k.length - 1];
    return { x: last[1], y: last[2], z: last[3], cursor: k.length - 2 };
  }

  let i = Math.max(0, Math.min(cursorHint, k.length - 2));

  while (i < k.length - 2 && t > k[i + 1][0]) i += 1;
  while (i > 0 && t < k[i][0]) i -= 1;

  const a = k[i];
  const b = k[i + 1];
  const span = Math.max(1e-6, b[0] - a[0]);
  const r = (t - a[0]) / span;

  return {
    x: a[1] + (b[1] - a[1]) * r,
    y: a[2] + (b[2] - a[2]) * r,
    z: a[3] + (b[3] - a[3]) * r,
    cursor: i,
    dx: b[1] - a[1],
    dz: b[3] - a[3],
  };
}

function updateOHTs(t) {
  for (const m of ohtMeshes) {
    const tr = m.userData.track;
    const res = interpolateAt(tr, t, m.userData.cursor || 0);
    m.userData.cursor = res.cursor;
    m.position.set(res.x, res.y + 0.35, res.z);

    if (Math.abs(res.dx || 0) + Math.abs(res.dz || 0) > 1e-6) {
      m.rotation.y = Math.atan2(-(res.dz || 0), res.dx || 1e-6);
    }
  }
}

function updateStats() {
  if (!sceneData) return;
  statsEl.textContent = [
    `Run: ${sceneData.metadata.run_id}`,
    `Nodes: ${sceneData.metadata.node_count}`,
    `Rails: ${sceneData.metadata.edge_count}`,
    `OHT: ${sceneData.metadata.oht_count}`,
    `Time: ${simTime.toFixed(0)} / ${tMax.toFixed(0)}`,
    `Speed: ${speed.toFixed(1)}x`,
    '',
    'Tip: mouse rotate / wheel zoom / right-drag pan',
  ].join('\n');
}

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}
window.addEventListener('resize', onResize);

playBtn.onclick = () => {
  playing = true;
};

pauseBtn.onclick = () => {
  playing = false;
};

resetBtn.onclick = () => {
  simTime = tMin;
  for (const m of ohtMeshes) m.userData.cursor = 0;
  updateOHTs(simTime);
  timeRange.value = '0';
  updateStats();
};

speedRange.oninput = () => {
  speed = Number(speedRange.value);
  speedValue.textContent = `${speed.toFixed(1)}x`;
  updateStats();
};

timeRange.oninput = () => {
  if (!sceneData) return;
  const r = Number(timeRange.value);
  simTime = tMin + (tMax - tMin) * r;
  updateOHTs(simTime);
  updateStats();
};

const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();

  if (sceneData && playing) {
    simTime += dt * 60.0 * speed;
    if (simTime > tMax) simTime = tMin;
    updateOHTs(simTime);

    const ratio = (simTime - tMin) / Math.max(1e-9, tMax - tMin);
    timeRange.value = String(Math.max(0, Math.min(1, ratio)));
  }

  controls.update();
  updateStats();
  renderer.render(scene, camera);
}

async function init() {
  const res = await fetch('./scene_data_run1.json');
  if (!res.ok) {
    throw new Error(`scene_data_run1.json load failed: ${res.status}`);
  }

  sceneData = await res.json();
  tMin = Number(sceneData.metadata.time_min || 0);
  tMax = Number(sceneData.metadata.time_max || 1);
  simTime = tMin;

  buildStaticGeometry(sceneData);
  updateOHTs(simTime);
  updateStats();
  animate();
}

init().catch((err) => {
  statsEl.textContent = `Load Error\n${String(err)}`;
  console.error(err);
});
