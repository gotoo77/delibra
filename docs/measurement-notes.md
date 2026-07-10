# Measurement Notes

Measurement notes record lessons about how to interpret Delibra observations.
They are not backlog items, runtime requirements, or protocol recommendations by
themselves.

## M001 - Prefer Direct Trace Measures Over Whole-Run Proxies

Observation:
- In observation 0002, the first comparison used `analyze-run` whole-run context
  upper bounds.
- That proxy suggested context pressure had increased.
- The hypothesis, however, was about the context received by the final synthesis
  call, not about total run pressure.

Lesson:
- Whenever trace data exposes the variable under test directly, prefer it over
  whole-run proxy metrics.
- Proxy metrics should be explicitly labeled as proxies.

Example:
- Whole-run context upper bounds are useful indicators of total run pressure.
- They are not suitable for validating a hypothesis about one specific call
  when trace data records that call's declared inputs and resolved artifact ids.

Implication:
- Observation notes should state which variable is being tested.
- Metrics should be tied to that variable as directly as the trace allows.
- When only a proxy is available, the conclusion should remain provisional.
