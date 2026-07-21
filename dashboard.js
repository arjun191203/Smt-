let charts = {}; // keep refs so we can destroy/redraw on refresh
let currentTab = "overview";
let lineNames = [];

const datePicker = document.getElementById("datePicker");
datePicker.value = new Date().toISOString().slice(0, 10);
datePicker.addEventListener("change", refreshAll);

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function pillClass(pct) {
  if (pct >= 95) return "good";
  if (pct >= 80) return "warn";
  return "bad";
}

function fmt(n) {
  return (n === null || n === undefined || isNaN(n)) ? "-" : Number(n).toLocaleString();
}

// ---------- Tabs ----------
function buildTabs(lines) {
  lineNames = lines.map(l => l.Line_Name);
  const tabbar = document.getElementById("tabbar");
  const lineViews = document.getElementById("lineViews");
  // clear previously injected tabs/views
  tabbar.querySelectorAll(".tab:not([data-tab='overview'])").forEach(el => el.remove());
  lineViews.innerHTML = "";

  lineNames.forEach(line => {
    const btn = document.createElement("button");
    btn.className = "tab";
    btn.dataset.tab = line;
    btn.textContent = line;
    btn.onclick = () => switchTab(line);
    tabbar.appendChild(btn);

    const section = document.createElement("section");
    section.className = "view";
    section.id = "view-" + line;
    section.innerHTML = lineViewTemplate(line);
    lineViews.appendChild(section);
  });

  document.querySelector('[data-tab="overview"]').onclick = () => switchTab("overview");
}

function lineViewTemplate(line) {
  return `
    <div class="line-header">
      <h2>${line}</h2>
      <span class="model-tag" id="model-${cssId(line)}"></span>
    </div>

    <div class="card">
      <div class="card-title">Hourly UPH — Target vs Actual</div>
      <div class="chart-box"><canvas id="uph-${cssId(line)}"></canvas></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Mounter Details</div>
        <div class="table-wrap"><table id="mounter-${cssId(line)}">
          <thead><tr><th>Machine</th><th>Model</th><th>Placed</th><th>CPH Tgt</th><th>CPH Act</th><th>Pickup Err</th><th>Downtime</th></tr></thead>
          <tbody></tbody></table></div>
      </div>
      <div class="card">
        <div class="card-title">AOI Details</div>
        <div class="table-wrap"><table id="aoi-${cssId(line)}">
          <thead><tr><th>AOI</th><th>Inspected</th><th>Pass</th><th>NG</th><th>False Call</th><th>FPY %</th></tr></thead>
          <tbody></tbody></table></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Solder Paste Timing</div>
        <div class="table-wrap"><table id="paste-${cssId(line)}">
          <thead><tr><th>Batch</th><th>Print Start</th><th>Print End</th><th>Out of Fridge</th><th>Expiry</th><th>Viscosity Chk</th></tr></thead>
          <tbody></tbody></table></div>
      </div>
      <div class="card">
        <div class="card-title">Stencil Cleaning Timing</div>
        <div class="table-wrap"><table id="stencil-${cssId(line)}">
          <thead><tr><th>Stencil ID</th><th>Last Clean</th><th>Next Due</th><th>Cycles</th><th>Method</th></tr></thead>
          <tbody></tbody></table></div>
      </div>
    </div>
  `;
}

function cssId(line) { return line.replace(/[^a-zA-Z0-9]/g, "_"); }

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById("view-" + tab).classList.add("active");
  loadTabData(tab);
}

// ---------- Data loading ----------
async function loadMeta() {
  const res = await fetch("/api/meta");
  const data = await res.json();
  buildTabs(data.lines);
}

async function loadTabData(tab) {
  const date = datePicker.value;
  if (tab === "overview") {
    const res = await fetch(`/api/overview?date=${date}`);
    renderOverview(await res.json());
  } else {
    const res = await fetch(`/api/line/${encodeURIComponent(tab)}?date=${date}`);
    renderLine(tab, await res.json());
  }
}

async function refreshAll() {
  try {
    await loadMeta();
    await loadTabData(currentTab);
    document.getElementById("lastUpdated").textContent =
      "Last updated: " + new Date().toLocaleTimeString();
  } catch (err) {
    console.error("Refresh failed:", err);
    document.getElementById("lastUpdated").textContent =
      "⚠ Could not load data - check the server terminal for errors";
  }
}

// ---------- Renderers ----------
function renderOverview(d) {
  document.getElementById("kpiPlan").textContent = fmt(d.totals.plan_qty);
  document.getElementById("kpiActual").textContent = fmt(d.totals.actual_qty);
  document.getElementById("kpiAch").textContent = d.totals.achievement_pct + "%";
  document.getElementById("kpiLines").textContent = d.by_line.length;

  const tbody = document.querySelector("#planTable tbody");
  tbody.innerHTML = d.by_line.map(r => `
    <tr>
      <td><strong>${r.line}</strong></td>
      <td>${r.model || "-"}</td>
      <td>${r.shift || "-"}</td>
      <td>${fmt(r.plan_qty)}</td>
      <td>${fmt(r.actual_qty)}</td>
      <td><span class="pill ${pillClass(r.achievement_pct)}">${r.achievement_pct}%</span></td>
    </tr>`).join("") || `<tr><td colspan="6">No data for this date</td></tr>`;

  destroyChart("hourlyAll");
  drawChart(() => {
    const ctx = document.getElementById("hourlyAllChart");
    const colors = ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];
    charts.hourlyAll = new Chart(ctx, {
      type: "line",
      data: {
        labels: d.hourly.hour_slots,
        datasets: d.hourly.series.map((s, i) => ({
          label: s.line,
          data: s.actual,
          borderColor: colors[i % colors.length],
          backgroundColor: colors[i % colors.length] + "22",
          tension: 0.35,
          fill: false,
          pointRadius: 3,
        })),
      },
      options: chartOpts("Qty"),
    });
  }, "hourlyAllChart");
}

// Runs a chart-drawing function safely: if Chart.js isn't loaded (e.g. no
// internet reaching the CDN) or the draw throws for any reason, show a
// clear message in that chart's box instead of leaving it silently blank
// and instead of blocking any other part of the page from rendering.
function drawChart(fn, canvasId) {
  try {
    if (typeof Chart === "undefined") throw new Error("Chart.js not loaded");
    fn();
  } catch (err) {
    console.error("Chart render failed:", err);
    const canvas = document.getElementById(canvasId);
    if (canvas && canvas.parentElement) {
      canvas.parentElement.innerHTML =
        '<div class="chart-error">⚠ Chart library did not load (no internet reaching the CDN). Tables still work. See setup note in README.</div>';
    }
    document.getElementById("cdnWarning")?.classList.remove("hidden");
  }
}

function renderLine(line, d) {
  const id = cssId(line);
  const meta = (lineNames.length && document.getElementById("model-" + id));
  if (meta) meta.textContent = "";

  // Tables first - these must always show even if charting fails.
  fillTable(`mounter-${id}`, d.mounters, m => `
    <tr><td>${m.Machine_No}</td><td>${m.Model_Placed}</td><td>${fmt(m.Placement_Qty)}</td>
    <td>${fmt(m.CPH_Target)}</td><td>${fmt(m.CPH_Actual)}</td>
    <td>${fmt(m.Pickup_Error_Qty)}</td><td>${fmt(m.Downtime_Min)} min</td></tr>`);

  fillTable(`aoi-${id}`, d.aoi, a => `
    <tr><td>${a.AOI_No}</td><td>${fmt(a.Inspected_Qty)}</td><td>${fmt(a.Pass_Qty)}</td>
    <td>${fmt(a.NG_Qty)}</td><td>${fmt(a.FalseCall_Qty)}</td>
    <td><span class="pill ${pillClass(a.FPY_pct)}">${a.FPY_pct}%</span></td></tr>`);

  fillTable(`paste-${id}`, d.solder_paste, p => `
    <tr><td>${p.Paste_Batch_No}</td><td>${p.Print_Start_Time}</td><td>${p.Print_End_Time}</td>
    <td>${p.Room_Temp_Out_Time}</td><td>${p.Expiry_Time}</td><td>${p.Viscosity_Check_Time}</td></tr>`);

  fillTable(`stencil-${id}`, d.stencil_cleaning, s => `
    <tr><td>${s.Stencil_ID}</td><td>${s.Last_Clean_Time}</td><td>${s.Next_Due_Time}</td>
    <td>${fmt(s.Cycles_Since_Clean)}</td><td>${s.Cleaning_Method}</td></tr>`);

  // Chart last, and never allowed to break the tables above if it fails.
  drawChart(() => {
    destroyChart("uph-" + id);
    charts["uph-" + id] = new Chart(document.getElementById("uph-" + id), {
      type: "bar",
      data: {
        labels: d.uph.hour_slots,
        datasets: [
          { label: "UPH Target", data: d.uph.target, backgroundColor: "#cbd5e1" },
          { label: "UPH Actual", data: d.uph.actual, backgroundColor: "#2563eb" },
        ],
      },
      options: chartOpts("UPH"),
    });
  }, "uph-" + id);
}

function fillTable(tableId, rows, rowFn) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  if (!tbody) return;
  tbody.innerHTML = rows.length ? rows.map(rowFn).join("") :
    `<tr><td colspan="8">No data for this date</td></tr>`;
}

function chartOpts(yLabel) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
    scales: {
      y: { title: { display: true, text: yLabel, font: { size: 10 } }, ticks: { font: { size: 10 } } },
      x: { ticks: { font: { size: 9 } } },
    },
  };
}

// ---------- Clock + boot ----------
function tickClock() {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString();
}
setInterval(tickClock, 1000);
tickClock();

refreshAll();
setInterval(refreshAll, 60000);
