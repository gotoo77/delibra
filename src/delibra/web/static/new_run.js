(function () {
  const presetSelect = document.querySelector('[data-preset-select]');
  const presetDetails = Array.from(document.querySelectorAll('[data-preset-detail]'));

  function syncPresetDetail() {
    if (!(presetSelect instanceof HTMLSelectElement)) {
      return;
    }
    const selected = presetSelect.value;
    for (const detail of presetDetails) {
      if (!(detail instanceof HTMLDetailsElement)) {
        continue;
      }
      const isSelected = detail.dataset.presetDetail === selected;
      detail.open = isSelected && selected !== "";
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
  const modelInput = modelField?.querySelector('input[name="model"]');
  if (!(providerSelect instanceof HTMLSelectElement) || !(modelInput instanceof HTMLInputElement)) {
    return;
  }

  function syncModelField() {
    const selected = providerSelect.selectedOptions[0];
    const modelRequired = selected?.dataset.modelRequired === "true";
    if (modelField instanceof HTMLElement) {
      modelField.hidden = !modelRequired;
    }
    modelInput.disabled = !modelRequired;
  }

  providerSelect.addEventListener("change", syncModelField);
  syncModelField();
})();
