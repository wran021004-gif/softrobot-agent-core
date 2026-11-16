# Historical 33-entry Knowledge migration

This directory preserves the historical Knowledge corpus from
`wran021004-gif/softrobot-agent@codex/u1-u2-general-task-adaptation` without rewriting the source bodies.

## Organization

- `procedures/`: 23 versioned procedure records, including the explicitly marked draft procedure.
- `success_cases/`: 9 historical success traces. All remain benchmark-sensitive and are denied by default.
- `drafts/`: the draft case and draft procedure. Both are archived but denied by default.
- `source_diagnostic_index.json`: byte-for-byte source index snapshot.
- `migration_manifest.json`: source commit, resource identities, source Git blob SHA-1 values, roles, categories and disclosure policy.

All 33 historical records are explicitly assigned `resource_role=knowledge`.
The existing Core Skill catalogue is retained separately as `resource_role=skill`.

## Retrieval categories

- `diagnostic`: mechanism diagnosis, competing explanations, model/solver interpretation and bounded continuation.
- `validation`: full-grid checks, independent evaluation, witness/cost separation and acceptance accounting.
- `case`: historical research traces; full successful traces remain restricted.

The category is retrieval metadata, not a scientific claim. The exact source body,
revision and provenance remain authoritative.

## Disclosure

- 22 non-draft procedures are marked `answer_isolated` and can be selected by the Knowledge-only condition.
- 9 benchmark-sensitive success cases are retained but not exposed by default.
- 2 drafts are retained but not exposed by default.

No successful benchmark trace is made available to K1S0. No resource can become
current scientific evidence, grant action permission or satisfy a Core acceptance gate.

## Integrity

Original resource files are copied without semantic rewriting. Each source
resource's Git blob SHA-1 is recorded in `migration_manifest.json`. During Study
preparation, Core's `freeze_knowledge()` computes a SHA256 content hash for each
authorized resource and binds it into the frozen manifest.
