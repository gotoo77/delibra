(function () {
  const root = document.querySelector("[data-events-url]");
  if (!root || !window.EventSource) {
    return;
  }

  const statusEl = document.getElementById("execution-status");
  const elapsedEl = document.getElementById("execution-elapsed");
  const artifactsEl = document.getElementById("execution-artifacts");
  const logEl = document.getElementById("progress-log");
  const source = new EventSource(root.dataset.eventsUrl);

  source.addEventListener("progress", function (event) {
    const data = JSON.parse(event.data);
    const li = document.createElement("li");
    const time = document.createElement("span");
    time.textContent = "+" + data.elapsed_seconds.toFixed(2) + "s";
    li.appendChild(time);
    li.appendChild(document.createTextNode(renderProgress(data)));
    logEl.appendChild(li);
  });

  source.addEventListener("status", function (event) {
    const data = JSON.parse(event.data);
    statusEl.textContent = data.status;
    elapsedEl.textContent = data.elapsed_seconds.toFixed(2) + "s";
    artifactsEl.textContent =
      data.artifact_count === null ? "unknown" : String(data.artifact_count);
    if (data.status === "completed" || data.status === "failed") {
      source.close();
      window.setTimeout(function () {
        window.location.reload();
      }, 500);
    }
  });

  source.addEventListener("missing", function () {
    source.close();
  });

  function renderProgress(data) {
    let text = data.type;
    if (data.step_id) text += " step=" + data.step_id;
    if (data.role_id) text += " role=" + data.role_id;
    if (data.artifact_id) text += " artifact=" + data.artifact_id;
    return text;
  }
})();
