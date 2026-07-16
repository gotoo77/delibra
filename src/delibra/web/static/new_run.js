(function () {
  const presetSelect = document.querySelector('[data-preset-select]');
  const presetDetails = Array.from(document.querySelectorAll('[data-preset-detail]'));
  const presetEmpty = document.querySelector('[data-preset-empty]');
  let previousSelected = null;

  function syncPresetDetail() {
    if (!(presetSelect instanceof HTMLSelectElement)) {
      return;
    }
    const selected = presetSelect.value;
    const changed = selected !== previousSelected;
    previousSelected = selected;
    if (presetEmpty instanceof HTMLElement) {
      presetEmpty.hidden = selected !== "";
    }
    for (const detail of presetDetails) {
      if (!(detail instanceof HTMLDetailsElement)) {
        continue;
      }
      const isSelected = detail.dataset.presetDetail === selected;
      detail.hidden = !isSelected;
      if (isSelected && selected !== "" && changed) {
        detail.open = true;
      }
    }
  }

  if (presetDetails.length > 0) {
    presetSelect?.addEventListener("change", syncPresetDetail);
    syncPresetDetail();
  }
})();

(function () {
  const providerSelect = document.querySelector('[data-provider-select]');
  const modelField = document.querySelector('[data-model-field]');
  const modelInput = modelField?.querySelector('[data-model-input]');
  const modelRequiredMarker = modelField?.querySelector('[data-model-required-marker]');
  const modelHelps = Array.from(document.querySelectorAll('[data-model-help]'));
  const providerDetails = Array.from(document.querySelectorAll('[data-provider-detail]'));
  if (!(providerSelect instanceof HTMLSelectElement) || !(modelInput instanceof HTMLInputElement)) {
    return;
  }

  function syncModelField() {
    const selected = providerSelect.selectedOptions[0];
    const modelRequired = selected?.dataset.modelRequired === "true";
    const modelList = selected?.dataset.modelList || "";
    const placeholder = selected?.dataset.modelPlaceholder || "";
    if (modelField instanceof HTMLElement) {
      modelField.hidden = !modelRequired;
    }
    modelInput.disabled = !modelRequired;
    modelInput.required = modelRequired;
    modelInput.placeholder = placeholder;
    if (modelRequiredMarker instanceof HTMLElement) {
      modelRequiredMarker.hidden = !modelRequired;
    }
    if (modelRequired && modelList !== "") {
      modelInput.setAttribute("list", modelList);
    } else {
      modelInput.removeAttribute("list");
    }
    for (const help of modelHelps) {
      if (!(help instanceof HTMLElement)) {
        continue;
      }
      help.hidden = help.dataset.modelHelp !== selected?.value;
    }
    for (const detail of providerDetails) {
      if (!(detail instanceof HTMLElement)) {
        continue;
      }
      detail.hidden = detail.dataset.providerDetail !== selected?.value;
    }
  }

  providerSelect.addEventListener("change", syncModelField);
  syncModelField();
})();

(function () {
  const presetDetails = Array.from(document.querySelectorAll('[data-preset-detail]'));

  function selectTab(detail, selectedTab) {
    const tabs = Array.from(detail.querySelectorAll('[data-preset-tab]'));
    const panels = Array.from(detail.querySelectorAll('[data-preset-panel]'));
    for (const tab of tabs) {
      if (!(tab instanceof HTMLButtonElement)) {
        continue;
      }
      tab.setAttribute("aria-selected", String(tab.dataset.presetTab === selectedTab));
    }
    for (const panel of panels) {
      if (!(panel instanceof HTMLElement)) {
        continue;
      }
      panel.hidden = panel.dataset.presetPanel !== selectedTab;
    }
  }

  function escapeHtml(value) {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function highlightYaml(source) {
    return source
      .split("\n")
      .map((line) => {
        const escaped = escapeHtml(line);
        if (/^\s*#/.test(line)) {
          return `<span class="yaml-comment">${escaped}</span>`;
        }
        return escaped.replace(
          /^(\s*)([A-Za-z0-9_-]+)(\s*:)/,
          '$1<span class="yaml-key">$2</span>$3',
        );
      })
      .join("\n");
  }

  for (const detail of presetDetails) {
    if (!(detail instanceof HTMLElement)) {
      continue;
    }
    detail.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLButtonElement && target.dataset.presetTab) {
        selectTab(detail, target.dataset.presetTab);
      }
      if (target instanceof HTMLButtonElement && target.dataset.copyYaml !== undefined) {
        const source = detail.querySelector('[data-yaml-source]');
        if (source instanceof HTMLElement) {
          navigator.clipboard?.writeText(source.textContent || "");
        }
      }
    });
    const source = detail.querySelector('[data-yaml-source]');
    if (source instanceof HTMLElement) {
      source.innerHTML = highlightYaml(source.textContent || "");
    }
  }
})();
