/**
 * POLARIS — Lunar Rover Path Planning Visualizer
 * Client-side Controller & Canvas Renderer
 */

const ALGORITHM_METADATA = {
  astar: {
    name: "Weighted A*",
    tag: "HEURISTIC OPTIMAL",
    description: "Balances traversal cost against Euclidean distance heuristic for fast, safe navigation.",
    headerBadge: "WEIGHTED A* & SOLAR TELEMETRY",
    supportsWeight: true,
    supportsDls: false,
  },
  dijkstra: {
    name: "Dijkstra's Algorithm",
    tag: "UNIFORM-COST OPTIMAL",
    description: "Exhaustive uniform-cost search. Guarantees strictly lowest cost path across terrain.",
    headerBadge: "DIJKSTRA SEARCH & SOLAR TELEMETRY",
    supportsWeight: false,
    supportsDls: false,
  },
  bfs: {
    name: "Breadth-First Search (BFS)",
    tag: "MINIMUM HOP COUNT",
    description: "Unweighted FIFO search. Finds path with minimal step transitions regardless of cost.",
    headerBadge: "BFS GRAPH SEARCH & SOLAR TELEMETRY",
    supportsWeight: false,
    supportsDls: false,
  },
  dls: {
    name: "Depth-Limited Search (DLS)",
    tag: "BOUNDED EXPLORATION",
    description: "Depth-bounded DFS. Explores branch paths up to a specified maximum depth limit.",
    headerBadge: "DLS SEARCH & SOLAR TELEMETRY",
    supportsWeight: false,
    supportsDls: true,
  },
  dfs: {
    name: "Depth-First Search (DFS)",
    tag: "UNINFORMED DEEP SEARCH",
    description: "Explores deep into navigable terrain branches. Non-optimal, sensitive to exploration order.",
    headerBadge: "DFS SEARCH & SOLAR TELEMETRY",
    supportsWeight: false,
    supportsDls: false,
  },
};

const state = {
  terrainData: null,
  activeLayer: "ohrc",
  clickMode: "start", // 'start' or 'goal'
  algorithm: "astar",
  startPt: [46, 51],
  goalPt: [158, 130],
  plan: null,
  currentStep: 0,
  isPlaying: false,
  playbackSpeed: 2,
  animationTimer: null,
};

// DOM Elements
const terrainCanvas = document.getElementById("terrain-canvas");
const overlayCanvas = document.getElementById("overlay-canvas");
const tCtx = terrainCanvas.getContext("2d");
const oCtx = overlayCanvas.getContext("2d");

const chartCanvas = document.getElementById("chart-canvas");
const chartCtx = chartCanvas.getContext("2d");

const layerButtons = document.querySelectorAll(".layer-btn");
const modeButtons = document.querySelectorAll(".mode-btn");
const btnCompute = document.getElementById("btn-compute");
const btnPlay = document.getElementById("btn-play");
const btnReset = document.getElementById("btn-reset");
const timelineSlider = document.getElementById("timeline-slider");
const playbackSpeedSelect = document.getElementById("playback-speed");

const landingSelect = document.getElementById("landing-site-select");
const scienceSelect = document.getElementById("science-target-select");
const algorithmSelect = document.getElementById("algorithm-select");

// Layer images cache
const layerImages = {
  ohrc: new Image(),
  elevation: new Image(),
  slope: new Image(),
  psr: new Image(),
};

// ---------------------------------------------------------------------------
// 1. Initialization
// ---------------------------------------------------------------------------
async function init() {
  setupEventListeners();
  await fetchTerrain();
  await computeRoute();
}

async function fetchTerrain() {
  try {
    const res = await fetch("/api/terrain");
    if (!res.ok) throw new Error("Failed to load terrain metadata");
    const data = await res.json();
    state.terrainData = data;

    // Load layer images
    layerImages.ohrc.src = data.layers.ohrc;
    layerImages.elevation.src = data.layers.elevation;
    layerImages.slope.src = data.layers.slope;
    layerImages.psr.src = data.layers.psr;

    layerImages.ohrc.onload = () => drawTerrainLayer();

    const sourceBadge = document.getElementById("ohrc-source-badge");
    if (sourceBadge) {
      if (data.is_real_ohrc) {
        sourceBadge.textContent = "REAL CHANDRAYAAN-2 OHRC";
        sourceBadge.style.color = "#10b981";
        sourceBadge.style.borderColor = "#10b981";
      } else {
        sourceBadge.textContent = "OHRC LUNAR REFLECTANCE";
        sourceBadge.style.color = "#38bdf8";
      }
    }

    // Populate dropdowns
    populateLandmarks(data.landmarks);
  } catch (err) {
    console.error("Error loading terrain:", err);
    document.getElementById("connection-status").textContent = "OFFLINE (API ERROR)";
    document.getElementById("connection-status").style.color = "#ef4444";
  }
}

function populateLandmarks(landmarks) {
  landingSelect.innerHTML = '<option value="custom">Custom Point</option>';
  scienceSelect.innerHTML = '<option value="custom">Custom Point</option>';

  landmarks.landing_sites.forEach((site) => {
    const opt = document.createElement("option");
    opt.value = `${site.r},${site.c}`;
    opt.textContent = `${site.name} [${site.r}, ${site.c}]`;
    landingSelect.appendChild(opt);
  });

  landmarks.science_targets.forEach((target) => {
    const opt = document.createElement("option");
    opt.value = `${target.r},${target.c}`;
    opt.textContent = `${target.name} [${target.r}, ${target.c}]`;
    scienceSelect.appendChild(opt);
  });

  // Select first items
  if (landmarks.landing_sites.length > 0) {
    landingSelect.selectedIndex = 1;
    const [r, c] = landingSelect.value.split(",").map(Number);
    state.startPt = [r, c];
    updateCoordLabels();
  }
  if (landmarks.science_targets.length > 0) {
    scienceSelect.selectedIndex = 1;
    const [r, c] = scienceSelect.value.split(",").map(Number);
    state.goalPt = [r, c];
    updateCoordLabels();
  }
}

// ---------------------------------------------------------------------------
// 2. Map Rendering
// ---------------------------------------------------------------------------
function drawTerrainLayer() {
  const img = layerImages[state.activeLayer];
  tCtx.clearRect(0, 0, terrainCanvas.width, terrainCanvas.height);
  if (img && img.complete) {
    tCtx.drawImage(img, 0, 0, terrainCanvas.width, terrainCanvas.height);
  }

  // If hazard overlay is enabled and viewing OHRC or DEM, blend translucent slope hazard
  const chkHazard = document.getElementById("chk-hazard-overlay");
  if (chkHazard && chkHazard.checked && (state.activeLayer === "ohrc" || state.activeLayer === "elevation")) {
    const slopeImg = layerImages.slope;
    if (slopeImg && slopeImg.complete) {
      tCtx.save();
      tCtx.globalAlpha = 0.28;
      tCtx.drawImage(slopeImg, 0, 0, terrainCanvas.width, terrainCanvas.height);
      tCtx.restore();
    }
  }
}

function drawOverlay() {
  oCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  const scaleX = overlayCanvas.width / 256.0;
  const scaleY = overlayCanvas.height / 256.0;

  // 1. Draw Planned Path
  if (state.plan && state.plan.raw_path && state.plan.raw_path.length > 0) {
    const path = state.plan.raw_path;

    // Glowing path line
    oCtx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    oCtx.lineWidth = 6;
    oCtx.lineCap = "round";
    oCtx.lineJoin = "round";
    oCtx.beginPath();
    oCtx.moveTo(path[0][1] * scaleX, path[0][0] * scaleY);
    for (let i = 1; i < path.length; i++) {
      oCtx.lineTo(path[i][1] * scaleX, path[i][0] * scaleY);
    }
    oCtx.stroke();

    oCtx.strokeStyle = "#38bdf8";
    oCtx.lineWidth = 2.5;
    oCtx.beginPath();
    oCtx.moveTo(path[0][1] * scaleX, path[0][0] * scaleY);
    for (let i = 1; i < path.length; i++) {
      oCtx.lineTo(path[i][1] * scaleX, path[i][0] * scaleY);
    }
    oCtx.stroke();

    // Primary RDP Waypoints
    if (state.plan.smooth_path) {
      oCtx.fillStyle = "#ffffff";
      state.plan.smooth_path.forEach((pt) => {
        oCtx.beginPath();
        oCtx.arc(pt[1] * scaleX, pt[0] * scaleY, 3, 0, Math.PI * 2);
        oCtx.fill();
      });
    }

    // 2. Animated Rover Position
    if (state.plan.telemetry && state.plan.telemetry.length > 0) {
      const stepIdx = Math.min(state.currentStep, state.plan.telemetry.length - 1);
      const cur = state.plan.telemetry[stepIdx];
      const rx = cur.grid_c * scaleX;
      const ry = cur.grid_r * scaleY;

      // Rover halo
      oCtx.fillStyle = cur.status === "RECHARGE_STOP" ? "rgba(245, 158, 11, 0.3)" : "rgba(16, 185, 129, 0.3)";
      oCtx.beginPath();
      oCtx.arc(rx, ry, 12, 0, Math.PI * 2);
      oCtx.fill();

      // Rover core
      oCtx.fillStyle = cur.status === "RECHARGE_STOP" ? "#f59e0b" : "#10b981";
      oCtx.strokeStyle = "#ffffff";
      oCtx.lineWidth = 2;
      oCtx.beginPath();
      oCtx.arc(rx, ry, 6, 0, Math.PI * 2);
      oCtx.fill();
      oCtx.stroke();
    }
  }

  // 3. Start Marker (Green Ring)
  const sx = state.startPt[1] * scaleX;
  const sy = state.startPt[0] * scaleY;
  oCtx.fillStyle = "#10b981";
  oCtx.strokeStyle = "#ffffff";
  oCtx.lineWidth = 2;
  oCtx.beginPath();
  oCtx.arc(sx, sy, 7, 0, Math.PI * 2);
  oCtx.fill();
  oCtx.stroke();

  // 4. Goal Marker (Red Star / Target)
  const gx = state.goalPt[1] * scaleX;
  const gy = state.goalPt[0] * scaleY;
  oCtx.fillStyle = "#ef4444";
  oCtx.strokeStyle = "#ffffff";
  oCtx.lineWidth = 2;
  oCtx.beginPath();
  oCtx.arc(gx, gy, 7, 0, Math.PI * 2);
  oCtx.fill();
  oCtx.stroke();
}

// ---------------------------------------------------------------------------
// 3. Path Planning API Call
// ---------------------------------------------------------------------------
async function computeRoute() {
  btnCompute.disabled = true;
  btnCompute.innerHTML = `<span class="btn-icon">⏳</span> PLANNING ROUTE...`;

  const dlsInput = document.getElementById("param-dls-limit");
  const payload = {
    start: state.startPt,
    goal: state.goalPt,
    algorithm: state.algorithm,
    dls_limit: dlsInput ? parseInt(dlsInput.value, 10) : 200,
    w: parseFloat(document.getElementById("param-w").value),
    max_slope: parseFloat(document.getElementById("param-max-slope").value),
    rover_spec: {
      battery_wh: parseFloat(document.getElementById("spec-battery").value),
      solar_panel_w: parseFloat(document.getElementById("spec-solar").value),
      drive_power_w: parseFloat(document.getElementById("spec-drive").value),
      speed_m_per_s: parseFloat(document.getElementById("spec-speed").value),
    },
  };

  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      alert("Path Planning Alert: " + (err.detail || "Route could not be solved."));
      return;
    }

    const plan = await res.json();
    state.plan = plan;
    state.currentStep = 0;

    // Update KPI panels
    document.getElementById("kpi-distance").textContent = `${plan.total_distance_m.toFixed(0)} m`;
    document.getElementById("kpi-time").textContent = `${plan.total_time_hours.toFixed(2)} hrs`;
    document.getElementById("kpi-max-slope").textContent = `${plan.max_slope_deg.toFixed(1)}°`;
    document.getElementById("kpi-min-soc").textContent = `${plan.min_battery_pct.toFixed(1)}%`;

    // Search algorithm metrics
    const nodesEl = document.getElementById("kpi-nodes-expanded");
    if (nodesEl) {
      nodesEl.textContent = plan.search_stats ? `${plan.search_stats.expanded_nodes.toLocaleString()}` : "--";
    }
    const execTimeEl = document.getElementById("kpi-exec-time");
    if (execTimeEl) {
      execTimeEl.textContent = plan.search_stats ? `${plan.search_stats.execution_time_ms.toFixed(1)} ms` : "--";
    }

    // Configure timeline slider
    const totalSteps = plan.telemetry.length;
    timelineSlider.max = Math.max(0, totalSteps - 1);
    timelineSlider.value = 0;
    document.getElementById("total-steps").textContent = totalSteps;

    // Render chart & map
    drawOverlay();
    renderProfileChart(plan.telemetry);
    updateLiveTelemetry(0);
  } catch (err) {
    console.error("Compute route failed:", err);
  } finally {
    btnCompute.disabled = false;
    btnCompute.innerHTML = `<span class="btn-icon">⚡</span> COMPUTE TRAVERSE`;
  }
}

// ---------------------------------------------------------------------------
// 4. Telemetry & Chart Rendering
// ---------------------------------------------------------------------------
function updateLiveTelemetry(stepIdx) {
  if (!state.plan || !state.plan.telemetry || state.plan.telemetry.length === 0) return;
  const t = state.plan.telemetry[stepIdx];
  if (!t) return;

  document.getElementById("current-step").textContent = stepIdx;
  timelineSlider.value = stepIdx;

  // Battery SoC
  document.getElementById("live-soc").textContent = `${t.battery_pct.toFixed(1)}%`;
  const socBar = document.getElementById("soc-bar");
  socBar.style.width = `${t.battery_pct}%`;
  if (t.battery_pct < 20) {
    socBar.style.background = "#ef4444";
  } else if (t.battery_pct < 50) {
    socBar.style.background = "#f59e0b";
  } else {
    socBar.style.background = "#10b981";
  }

  // Solar & Drive
  document.getElementById("live-solar").textContent = `${t.solar_in_w.toFixed(1)} W`;
  document.getElementById("live-sunlit").textContent = t.is_sunlit ? "IN DIRECT SUNLIGHT" : "SHADOWED (PSR)";
  document.getElementById("live-sunlit").style.color = t.is_sunlit ? "#10b981" : "#ef4444";

  document.getElementById("live-drive").textContent = `${t.drive_w.toFixed(1)} W`;
  document.getElementById("live-slope").textContent = `${t.slope_deg.toFixed(1)}°`;

  const netPrefix = t.net_w >= 0 ? "+" : "";
  document.getElementById("live-net").textContent = `${netPrefix}${t.net_w.toFixed(1)} W`;
  document.getElementById("live-net").style.color = t.net_w >= 0 ? "#10b981" : "#ef4444";

  document.getElementById("live-dist").textContent = `${t.distance_m.toFixed(0)} m`;
  document.getElementById("live-time").textContent = `${t.elapsed_hours.toFixed(2)} h`;

  // Status Badge
  const badge = document.getElementById("badge-status");
  badge.className = "status-badge";
  if (t.status === "DRIVING") {
    badge.classList.add("driving");
    badge.textContent = "DRIVING";
  } else if (t.status === "RECHARGE_STOP") {
    badge.classList.add("recharge");
    badge.textContent = "SOLAR RECHARGE STOP";
  } else {
    badge.classList.add("standby");
    badge.textContent = t.status;
  }
}

function renderProfileChart(telemetry) {
  if (!telemetry || telemetry.length === 0) return;

  const w = chartCanvas.width;
  const h = chartCanvas.height;
  chartCtx.clearRect(0, 0, w, h);

  const padL = 30, padR = 10, padT = 15, padB = 25;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  // Grid lines
  chartCtx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  chartCtx.lineWidth = 1;
  chartCtx.beginPath();
  for (let i = 0; i <= 4; i++) {
    const y = padT + (plotH / 4) * i;
    chartCtx.moveTo(padL, y);
    chartCtx.lineTo(w - padR, y);
  }
  chartCtx.stroke();

  const n = telemetry.length;

  // Draw Battery SoC (%)
  chartCtx.strokeStyle = "#10b981";
  chartCtx.lineWidth = 2;
  chartCtx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padL + (i / (n - 1)) * plotW;
    const y = padT + plotH * (1.0 - telemetry[i].battery_pct / 100.0);
    if (i === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  }
  chartCtx.stroke();

  // Draw Solar Power (scaled to max 200W)
  chartCtx.strokeStyle = "#f59e0b";
  chartCtx.lineWidth = 1.5;
  chartCtx.setLineDash([4, 2]);
  chartCtx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padL + (i / (n - 1)) * plotW;
    const y = padT + plotH * (1.0 - Math.min(200, telemetry[i].solar_in_w) / 200.0);
    if (i === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  }
  chartCtx.stroke();

  // Draw Drive Draw (scaled to max 200W)
  chartCtx.strokeStyle = "#ef4444";
  chartCtx.lineWidth = 1.5;
  chartCtx.setLineDash([2, 2]);
  chartCtx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = padL + (i / (n - 1)) * plotW;
    const y = padT + plotH * (1.0 - Math.min(200, telemetry[i].drive_w) / 200.0);
    if (i === 0) chartCtx.moveTo(x, y);
    else chartCtx.lineTo(x, y);
  }
  chartCtx.stroke();
  chartCtx.setLineDash([]);
}

// ---------------------------------------------------------------------------
// 5. Playback Controller
// ---------------------------------------------------------------------------
function togglePlay() {
  state.isPlaying = !state.isPlaying;
  btnPlay.textContent = state.isPlaying ? "⏸" : "▶";

  if (state.isPlaying) {
    const delay = Math.max(30, 200 / state.playbackSpeed);
    state.animationTimer = setInterval(() => {
      if (!state.plan || !state.plan.telemetry) return;
      if (state.currentStep >= state.plan.telemetry.length - 1) {
        togglePlay();
        return;
      }
      state.currentStep++;
      updateLiveTelemetry(state.currentStep);
      drawOverlay();
    }, delay);
  } else {
    clearInterval(state.animationTimer);
  }
}

function resetPlayback() {
  if (state.isPlaying) togglePlay();
  state.currentStep = 0;
  updateLiveTelemetry(0);
  drawOverlay();
}

// ---------------------------------------------------------------------------
// 6. Event Listeners
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Layer toggles
  layerButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      layerButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeLayer = btn.dataset.layer;
      drawTerrainLayer();
    });
  });

  // Click mode toggles
  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      modeButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.clickMode = btn.id === "mode-start" ? "start" : "goal";
    });
  });

  // Map canvas click for point placement
  overlayCanvas.addEventListener("click", (e) => {
    const rect = overlayCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const gridCol = Math.round((clickX / overlayCanvas.width) * 256.0);
    const gridRow = Math.round((clickY / overlayCanvas.height) * 256.0);

    const boundedRow = Math.min(255, Math.max(0, gridRow));
    const boundedCol = Math.min(255, Math.max(0, gridCol));

    if (state.clickMode === "start") {
      state.startPt = [boundedRow, boundedCol];
      landingSelect.value = "custom";
    } else {
      state.goalPt = [boundedRow, boundedCol];
      scienceSelect.value = "custom";
    }

    updateCoordLabels();
    drawOverlay();
  });

  // Right click places goal directly
  overlayCanvas.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const rect = overlayCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    const gridCol = Math.min(255, Math.max(0, Math.round((clickX / overlayCanvas.width) * 256.0)));
    const gridRow = Math.min(255, Math.max(0, Math.round((clickY / overlayCanvas.height) * 256.0)));
    state.goalPt = [gridRow, gridCol];
    scienceSelect.value = "custom";
    updateCoordLabels();
    drawOverlay();
  });

  // Dropdown selections
  landingSelect.addEventListener("change", (e) => {
    if (e.target.value !== "custom") {
      const [r, c] = e.target.value.split(",").map(Number);
      state.startPt = [r, c];
      updateCoordLabels();
      drawOverlay();
    }
  });

  scienceSelect.addEventListener("change", (e) => {
    if (e.target.value !== "custom") {
      const [r, c] = e.target.value.split(",").map(Number);
      state.goalPt = [r, c];
      updateCoordLabels();
      drawOverlay();
    }
  });

  // Algorithm selection change
  if (algorithmSelect) {
    algorithmSelect.addEventListener("change", (e) => {
      const algoKey = e.target.value;
      state.algorithm = algoKey;
      const meta = ALGORITHM_METADATA[algoKey];
      if (meta) {
        const infoTag = document.getElementById("algo-info-tag");
        const infoDesc = document.getElementById("algo-description");
        const headerBadge = document.getElementById("header-algo-badge");
        if (infoTag) infoTag.textContent = meta.tag;
        if (infoDesc) infoDesc.textContent = meta.description;
        if (headerBadge) headerBadge.textContent = meta.headerBadge;

        // Toggle heuristic weight slider
        const wContainer = document.getElementById("param-w-container");
        if (wContainer) {
          wContainer.style.display = meta.supportsWeight ? "block" : "none";
        }

        // Toggle DLS depth limit slider
        const dlsContainer = document.getElementById("param-dls-container");
        if (dlsContainer) {
          dlsContainer.style.display = meta.supportsDls ? "block" : "none";
        }
      }
      // Recompute route immediately so the new algorithm's path is drawn instantly
      computeRoute();
    });
  }

  // DLS depth limit slider
  const dlsSlider = document.getElementById("param-dls-limit");
  if (dlsSlider) {
    dlsSlider.addEventListener("input", (e) => {
      document.getElementById("val-dls-limit").textContent = `${e.target.value} steps`;
    });
    dlsSlider.addEventListener("change", () => {
      computeRoute();
    });
  }

  // Slider value badges & recompute on release
  const paramWInput = document.getElementById("param-w");
  paramWInput.addEventListener("input", (e) => {
    document.getElementById("val-weight").textContent = e.target.value;
  });
  paramWInput.addEventListener("change", () => {
    computeRoute();
  });

  const paramSlopeInput = document.getElementById("param-max-slope");
  paramSlopeInput.addEventListener("input", (e) => {
    document.getElementById("val-slope").textContent = `${e.target.value}°`;
  });
  paramSlopeInput.addEventListener("change", () => {
    computeRoute();
  });

  // Hazard overlay toggle
  const chkHazard = document.getElementById("chk-hazard-overlay");
  if (chkHazard) {
    chkHazard.addEventListener("change", () => drawTerrainLayer());
  }

  // Compute button
  btnCompute.addEventListener("click", computeRoute);

  // Playback controls
  btnPlay.addEventListener("click", togglePlay);
  btnReset.addEventListener("click", resetPlayback);

  timelineSlider.addEventListener("input", (e) => {
    state.currentStep = parseInt(e.target.value, 10);
    updateLiveTelemetry(state.currentStep);
    drawOverlay();
  });

  playbackSpeedSelect.addEventListener("change", (e) => {
    state.playbackSpeed = parseFloat(e.target.value);
    if (state.isPlaying) {
      clearInterval(state.animationTimer);
      state.isPlaying = false;
      togglePlay();
    }
  });
}

function updateCoordLabels() {
  document.getElementById("lbl-start").textContent = `[${state.startPt[0]}, ${state.startPt[1]}]`;
  document.getElementById("lbl-goal").textContent = `[${state.goalPt[0]}, ${state.goalPt[1]}]`;
}

// Launch application on DOM ready
document.addEventListener("DOMContentLoaded", init);
