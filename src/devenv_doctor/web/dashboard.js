const pageLabels = {
  overview: ["Overview", "Environment health and diagnostic summary"],
  diagnostics: ["Diagnostics", "Current findings from the diagnostic engine"],
  dependencies: ["Dependencies", "Declared packages with reported issues"],
  environment: ["Environment", "Referenced variable names and availability"],
  runtime: ["Runtime", "Interpreter and virtual-environment details"],
  reports: ["Reports", "Current report from the existing JSON output"],
};

const state = {
  page: "overview",
  filter: "all",
  report: null,
  health: { score: null, status: "Not available" },
  refreshing: false,
};

const content = document.querySelector("#page-content");
const toast = document.querySelector("#toast");

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = String(text);
  return item;
}

function findings() {
  return Array.isArray(state.report?.findings) ? state.report.findings : [];
}

function variableRecords() {
  return state.report?.environment_variables?.variables ?? [];
}

function statusFor(severity) {
  if (severity === "error") return ["Error", "status-error"];
  if (severity === "high" || severity === "warning") return ["Warning", "status-warning"];
  if (severity === "info") return ["Healthy", "status-healthy"];
  return ["Not available", "status-neutral"];
}

function categoryFindings(category) {
  return findings().filter((finding) => finding.category === category);
}

function evidenceMap(finding) {
  return Object.fromEntries((finding.evidence ?? []).map((line) => {
    const separator = line.indexOf(": ");
    return separator < 0 ? [line, ""] : [line.slice(0, separator), line.slice(separator + 2)];
  }));
}

function dependencyRows() {
  return categoryFindings("dependency").map((finding) => {
    const evidence = evidenceMap(finding);
    return {
      package: evidence["Required package"] ?? evidence.Package ?? "Not available",
      required: evidence.Requirement ?? evidence.Required ?? "Not available",
      installed: evidence.Installed ?? "Not available",
      status: finding.id === "DEPENDENCY_MISSING" ? "Missing" : "Mismatch",
      finding,
    };
  });
}

function addStatus(parent, label, className) {
  parent.append(node("span", `status-pill ${className}`, label));
}

function statCard(label, value, detail, statusLabel, statusClass) {
  const card = node("article", "stat-card");
  const top = node("div", "stat-top");
  top.append(node("span", "", label));
  addStatus(top, statusLabel, statusClass);
  card.append(top, node("div", "stat-value", value), node("div", "stat-detail", detail));
  return card;
}

function renderFinding(finding) {
  const card = node("article", "finding-card");
  const [label, statusClass] = statusFor(finding.severity);
  const bar = node("div", `finding-bar${finding.severity === "error" ? " error" : finding.severity === "info" ? " info" : ""}`);
  const body = node("div", "finding-body");
  const top = node("div", "finding-top");
  top.append(node("h3", "finding-title", finding.title));
  addStatus(top, label, statusClass);
  body.append(top, node("div", "finding-id", finding.id));
  const meta = node("div", "finding-meta");
  meta.append(node("span", "category-tag", finding.category));
  body.append(meta);
  if (finding.evidence?.length) {
    body.append(node("p", "evidence-copy", finding.evidence.join(" · ")));
  }
  if (finding.recommended_action) {
    const recommendation = node("p", "recommendation-copy");
    recommendation.append(node("span", "recommendation-label", "Recommended: "));
    recommendation.append(document.createTextNode(finding.recommended_action));
    body.append(recommendation);
  }
  card.append(bar, body);
  return card;
}

function emptyState(message) {
  return node("div", "empty-state", message);
}

function panel(title, subtitle) {
  const section = node("section", "panel");
  const heading = node("div", "panel-heading");
  const copy = node("div");
  copy.append(node("h2", "", title));
  if (subtitle) copy.append(node("p", "", subtitle));
  heading.append(copy);
  section.append(heading);
  return section;
}

function renderOverview() {
  const runtime = state.report?.environment_summary?.runtime ?? {};
  const virtualEnvironment = state.report?.environment_summary?.virtual_environment ?? {};
  const variables = variableRecords();
  const missingVariables = variables.filter((variable) => !variable.present).length;
  const dependencies = dependencyRows();
  const pythonIssue = categoryFindings("runtime").find((finding) => finding.severity !== "info");
  const venvIssue = categoryFindings("virtual-environment").find((finding) => finding.severity !== "info");
  const statGrid = node("div", "stat-grid");
  const pythonStatus = pythonIssue ? statusFor(pythonIssue.severity) : ["No mismatch", "status-healthy"];
  const venvStatus = venvIssue ? statusFor(venvIssue.severity) : [virtualEnvironment.active ? "Active" : "Not active", virtualEnvironment.active ? "status-healthy" : "status-warning"];
  const dependencyStatus = dependencies.length ? statusFor(dependencies[0].finding.severity) : ["No issues", "status-healthy"];
  const environmentStatus = !variables.length ? ["No references", "status-neutral"] : missingVariables ? ["Missing", "status-warning"] : ["Available", "status-healthy"];

  statGrid.append(
    statCard("Python", runtime.python_version ?? "Not available", pythonIssue?.title ?? "No version mismatch reported", pythonStatus[0], pythonStatus[1]),
    statCard("Virtual environment", virtualEnvironment.path ? virtualEnvironment.path.split(/[\\/]/).pop() : "Not active", virtualEnvironment.path ?? "No active environment path", venvStatus[0], venvStatus[1]),
    statCard("Dependencies", dependencies.length ? `${dependencies.length} issue${dependencies.length === 1 ? "" : "s"}` : "0 issues", "Issues reported by dependency analyzer", dependencyStatus[0], dependencyStatus[1]),
    statCard("Environment variables", variables.length ? `${variables.length} referenced` : "Not available", variables.length ? `${missingVariables} missing · values never shown` : "No supported references detected", environmentStatus[0], environmentStatus[1]),
  );

  const lower = node("div", "overview-grid");
  const healthPanel = panel("Environment health", "Calculated from current Finding severity values");
  const health = node("div", "health-layout");
  const score = node("div", "health-score");
  score.append(node("strong", "", state.health.score === null ? "—" : state.health.score), node("span", "", state.health.score === null ? "" : "/ 100"));
  const healthStatus = node("div", `health-state ${state.health.status === "Healthy" ? "healthy" : state.health.status === "Warning" ? "warning" : state.health.status === "Critical" ? "critical" : "unavailable"}`, state.health.status);
  score.append(healthStatus);
  const meter = node("div", "health-meter");
  const meterFill = node("span");
  meterFill.style.width = state.health.score === null ? "0%" : `${state.health.score}%`;
  meter.append(meterFill);
  health.append(score, meter);
  healthPanel.append(health);
  const severityCounts = state.report?.summary ?? {};
  const counts = node("div", "severity-counts");
  counts.append(
    severityRow("Healthy", severityCounts.info ?? 0, ""),
    severityRow("Warnings", severityCounts.warnings ?? 0, "warning"),
    severityRow("Errors", severityCounts.errors ?? 0, "error"),
  );
  healthPanel.append(counts);

  const recent = panel("Current findings", `${findings().length} finding${findings().length === 1 ? "" : "s"} from the diagnostic engine`);
  const list = node("div", "findings-list");
  if (findings().length) findings().forEach((finding) => list.append(renderFinding(finding)));
  else list.append(emptyState("No findings were returned."));
  recent.append(list);
  lower.append(healthPanel, recent);
  content.replaceChildren(statGrid, lower);
}

function severityRow(label, count, tone) {
  const row = node("div", "severity-row");
  row.append(node("span", `severity-dot ${tone}`, ""), node("span", "", label), node("strong", "", count));
  return row;
}

function table(headers, rows) {
  const wrap = node("div", "table-wrap");
  const element = node("table");
  const head = node("thead");
  const headerRow = node("tr");
  headers.forEach((label) => headerRow.append(node("th", "", label)));
  head.append(headerRow);
  const body = node("tbody");
  rows.forEach((row) => {
    const tr = node("tr");
    row.forEach((cell) => {
      const td = node("td");
      if (cell instanceof Node) td.append(cell);
      else td.textContent = String(cell);
      tr.append(td);
    });
    body.append(tr);
  });
  element.append(head, body);
  wrap.append(element);
  return wrap;
}

function renderDiagnostics() {
  const section = panel("Findings", "Each row is a Finding returned by the existing diagnostic engine");
  const filters = node("div", "filter-row");
  [["all", "All"], ["error", "Errors"], ["warning", "Warnings"], ["info", "Healthy"]].forEach(([key, label]) => {
    const button = node("button", `filter-button${state.filter === key ? " active" : ""}`, label);
    button.type = "button";
    button.addEventListener("click", () => { state.filter = key; renderPage(); });
    filters.append(button);
  });
  section.append(filters);
  const selected = findings().filter((finding) => {
    if (state.filter === "all") return true;
    if (state.filter === "warning") return finding.severity === "warning" || finding.severity === "high";
    return finding.severity === state.filter;
  });
  const rows = selected.map((finding) => {
    const [label, className] = statusFor(finding.severity);
    return [
      (() => { const pill = node("span", `status-pill ${className}`, label); return pill; })(),
      finding.category,
      (() => { const wrapper = node("div"); wrapper.append(node("strong", "", finding.title), node("div", "finding-id", finding.id)); return wrapper; })(),
      (finding.evidence ?? []).join(" · ") || "Not available",
      finding.recommended_action ?? "Not available",
    ];
  });
  section.append(rows.length ? table(["Severity", "Category", "Finding", "Evidence", "Recommendation"], rows) : emptyState("No findings match this filter."));
  content.replaceChildren(section);
}

function renderDependencies() {
  const issues = dependencyRows();
  const section = panel("Dependency findings", "Only issues returned by the existing dependency analyzer are listed");
  const rows = issues.map((item) => {
    const pill = node("span", "status-pill status-warning", item.status);
    return [
      node("strong", "", item.package),
      node("span", "mono", item.required),
      node("span", "mono", item.installed),
      pill,
    ];
  });
  section.append(rows.length ? table(["Package", "Required", "Installed", "Status"], rows) : emptyState("No dependency issues were reported. Compatible packages are not listed individually by the existing report."));
  content.replaceChildren(section);
}

function renderEnvironment() {
  const section = panel("Environment variables", "Names and presence only · values are never returned by the diagnostic report");
  const rows = variableRecords().map((variable) => {
    const label = variable.present ? "Present" : "Missing";
    const pill = node("span", `status-pill ${variable.present ? "status-healthy" : "status-warning"}`, label);
    const sources = Array.isArray(variable.sources) && variable.sources.length ? variable.sources.join(", ") : "Not available";
    return [node("strong", "", variable.name), node("span", "mono", sources), pill];
  });
  section.append(rows.length ? table(["Variable", "Source", "Status"], rows) : emptyState("No supported environment-variable references were detected."));
  content.replaceChildren(section);
}

function renderRuntime() {
  const report = state.report ?? {};
  const runtime = report.environment_summary?.runtime ?? {};
  const venv = report.environment_summary?.virtual_environment ?? {};
  const values = [
    ["Python version", runtime.python_version],
    ["Python executable", runtime.executable_path],
    ["Operating system", runtime.operating_system],
    ["Architecture", runtime.architecture],
    ["Virtual environment", venv.active === true ? "Active" : venv.active === false ? "Not active" : undefined],
    ["Virtual environment path", venv.path],
    ["Project path", undefined],
  ];
  const section = panel("Runtime details", "Collected from the interpreter running the diagnostic command");
  const grid = node("div", "runtime-grid");
  values.forEach(([label, value]) => {
    const item = node("div", "runtime-item");
    item.append(node("div", "runtime-label", label), node("div", "runtime-value mono", value ?? "Not available"));
    grid.append(item);
  });
  section.append(grid);
  content.replaceChildren(section);
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 1800);
}

function renderReports() {
  const section = panel("Diagnostic report", "The report body is the existing CLI JSON output");
  const toolbar = node("div", "report-toolbar");
  toolbar.append(node("p", "", "Raw report · environment-variable values are not included"));
  const actions = node("div", "report-actions");
  const copy = node("button", "button button-secondary", "Copy JSON");
  copy.type = "button";
  copy.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(JSON.stringify(state.report, null, 2)); showToast("JSON copied"); }
    catch { showToast("Clipboard access unavailable"); }
  });
  const download = node("a", "button button-primary", "Download JSON");
  download.href = "/api/report/download";
  download.download = "devenv-doctor-report.json";
  actions.append(copy, download);
  toolbar.append(actions);
  const reportView = node("pre", "json-view");
  reportView.textContent = JSON.stringify(state.report, null, 2);
  section.append(toolbar, reportView);
  content.replaceChildren(section);
}

function renderPage() {
  if (!state.report) return;
  const [title, subtitle] = pageLabels[state.page];
  document.querySelector("#page-title").textContent = title;
  document.querySelector("#breadcrumb-title").textContent = title;
  document.querySelector("#page-subtitle").textContent = subtitle;
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("active", button.dataset.page === state.page));
  const renderers = {
    overview: renderOverview,
    diagnostics: renderDiagnostics,
    dependencies: renderDependencies,
    environment: renderEnvironment,
    runtime: renderRuntime,
    reports: renderReports,
  };
  renderers[state.page]();
}

async function refreshReport() {
  if (state.refreshing) return;
  state.refreshing = true;
  const refreshButton = document.querySelector("#refresh-button");
  refreshButton.disabled = true;
  document.querySelector("#scan-state").textContent = "Scanning";
  try {
    const response = await fetch("/api/report", { cache: "no-store" });
    if (!response.ok) throw new Error("Diagnostic report unavailable");
    state.report = await response.json();
    const scoreHeader = response.headers.get("X-DevEnv-Health-Score");
    state.health.score = scoreHeader && scoreHeader !== "not-available" ? Number(scoreHeader) : null;
    state.health.status = response.headers.get("X-DevEnv-Health-Status") ?? "Not available";
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    document.querySelector("#updated-label").textContent = `Updated ${time}`;
    document.querySelector("#scan-state").textContent = "Ready";
    document.querySelector("#project-label").textContent = state.report.environment_summary?.project?.is_python_project ? "Python project detected" : "Project not detected";
    renderPage();
  } catch {
    document.querySelector("#scan-state").textContent = "Unavailable";
    content.replaceChildren(node("div", "error-state", "Unable to load diagnostics. Check that the local server is running, then refresh."));
  } finally {
    state.refreshing = false;
    refreshButton.disabled = false;
  }
}

document.querySelectorAll(".nav-link").forEach((button) => {
  button.addEventListener("click", () => { state.page = button.dataset.page; renderPage(); });
});
document.querySelector("#refresh-button").addEventListener("click", refreshReport);
refreshReport();