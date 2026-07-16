(function () {
  const presetSelect = document.querySelector('[data-preset-select]');
  const presetDetails = Array.from(document.querySelectorAll('[data-preset-detail]'));
  if (!(presetSelect instanceof HTMLSelectElement) || presetDetails.length === 0) {
    return;
  }

  function syncPresetDetail() {
    const selected = presetSelect.value;
    for (const detail of presetDetails) {
      if (!(detail instanceof HTMLDetailsElement)) {
        continue;
      }
      const isSelected = detail.dataset.presetDetail === selected;
      detail.open = isSelected && selected !== "";
    }
  }

  presetSelect.addEventListener("change", syncPresetDetail);
  syncPresetDetail();
})();
