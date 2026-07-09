# Preset Repository

## Status

Architecture note.

## Intent

Delibra presets are reusable deliberation recipes, not throwaway examples.

A preset is a named protocol that captures a useful pattern of structured
reasoning: roles, steps, artifact outputs, and synthesis shape. It should be
possible to run the same preset repeatedly across inputs, review changes to it,
compare versions, and share it as a stable recipe.

## Boundary

The preset repository is not a plugin system, package manager, marketplace, or
runtime registry.

For now, `presets/` is a plain directory of YAML protocols. The runtime still
executes a protocol by path. There is no preset discovery API, no dependency
resolution, no remote install mechanism, and no semantic version resolver.

## Principles

- Presets describe what should be derived, not how cheaply or where to run it.
- Execution policy remains separate from presets.
- Provider, model, token, and cost choices do not belong in presets.
- Presets may be opinionated recipes, but they must stay valid Delibra
  protocols.
- Preset changes should be reviewed like code because they change reasoning
  behavior.

## Minimal Repository Convention

Each preset file in `presets/` should:

- use a stable snake_case filename matching the protocol `id`;
- include a non-empty `version`;
- include a short `description` that explains the recipe purpose;
- use only supported runtime primitives;
- avoid provider-specific language;
- produce a final synthesis artifact when the recipe has a natural final answer;
- be covered by preset validation and mock execution tests.

Experimental presets may exist, but should be labeled in documentation until
their shape has seen real use.

## Future Extension Points

Possible future work belongs outside the MVP unless real usage requires it:

- preset metadata beyond the protocol YAML;
- preset indexes or manifests;
- compatibility ranges for Delibra versions;
- external recipe repositories;
- import/install commands;
- recipe quality signals from field notes.

These features should not be added until a plain directory of versioned YAML
recipes becomes insufficient.
