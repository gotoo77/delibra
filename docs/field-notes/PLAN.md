# Field Notes Plan

This plan proposes usage scenarios for field notes. It is not a roadmap.

Do not implement features because they appear in this plan. Run scenarios, observe friction, and only then decide whether the evidence justifies a fix, documentation update, preset issue, runtime issue, concept note, or waiting.

## Series A -- Real Code Review

1. `code_review` on commit `f076e17` with OpenAI.
   - Goal: exploit the first successful real-provider run.
   - Status: recorded in `0001-code-review-delibra-openai.md`.

2. `code_review` on a small Delibra commit with mock.
   - Goal: validate the scenario without provider cost.

3. `code_review` on a real personal or work diff.
   - Goal: test value on an external change.
   - Constraint: use OpenAI only if the code may be sent to the provider.

## Series B -- Design Review

4. `design_review` on `docs/adr/0001-core-identity.md`.
   - Goal: test whether the preset can critique Delibra's founding identity.

5. `design_review` on `docs/adr/0003-efficient-execution.md`.
   - Goal: test whether the preset can reason about runtime efficiency constraints.

6. `design_review` on `README.md`.
   - Goal: test whether the public explanation is coherent.

## Series C -- Decision Review

7. `decision_review` on whether to add `delibra plan` now or wait.
   - Goal: separate real pressure from attractive feature design.

8. `decision_review` on whether to create a `jeu_de_piste` preset now.
   - Goal: test product-layer expansion discipline.

## Series D -- Future Usage Shapes

9. `design_review` on a draft `jeu_de_piste` preset without implementing it.
   - Goal: see whether the existing DSL can express the idea conceptually.

10. `code_review` or `design_review` on `scripts/run_real_code_review.sh` after hardening.
    - Goal: compare before/after scenario maturity.
