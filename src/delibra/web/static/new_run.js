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
    modelInput.placeholder = placeholder;
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
