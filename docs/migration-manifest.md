# Production migration manifest

## Baseline

- Source repository: `wran021004-gif/softrobot-agent`.
- Source branch: `codex/passive-research-capabilities-20261107`.
- Exact source commit: `fd2c1694dbef225cc08a516d2249735c9c180053`.
- At extraction, the designated checkout was clean, HEAD equalled that commit, and the remote branch reported the same commit. No other branch was merged. The original checkout and Git history were not modified.
- New repository: `wran021004-gif/softrobot-agent-core`, fresh `main` history.

## Dependency closure and correspondence

The closure starts at `tools.research.__main__`, follows Python imports, trusted Registry bindings/capability hooks and declared sources/assets, and includes the runtime's own code fingerprint lists and optional worker entry points. `docs/source-inventory.json` lists every original production Python path and MATLAB wrapper. No folder-name-only bulk export is used.

| Source production area | Destination | Purpose |
|---|---|---|
| `tools/research/` | same module paths | Main, Reporter, scientific runtime, mathematics/search orchestration and evidence delivery |
| `tools/platform_*`, `tools/service_execution.py`, other reached `tools/` modules | same paths | Registry, Store implementation, host, task compilation, subprocess/work-order execution |
| `tools/rl/` | same paths | Optional production RL interface and contained workers |
| `schemas/` reached contracts | same paths | Tasks, scientific requests, physical structures, evidence, costs and policies |
| `extensions/math_analysis/`, `extensions/optimization/` | same paths | Generic mathematical kernels and optional solvers |
| `extensions/tendon_family/` | same paths | FamilySpace, structure generation, numerical models, control and physical adapters |
| `extensions/reference/`, `extensions/experiment_dynamics/` | same paths | Task adapters, evaluators and model contracts |
| `matlab/sorosim_control/*.m` | `tools/assets/matlab/sorosim_control/*.m` | 13 project-authored wrappers used by the external MATLAB/SoRoSim adapter |
| Selected generic Knowledge methods | `tools/assets/memory/` | Four procedure/skill cards; archived cases and candidate answers removed |
| General family/task/control contracts | `tools/assets/examples/` | Fresh illustrative Reach/Hold and tracking compositions, generic family prototypes and placeholder Provider configuration |

Existing generic production mathematics remains even when used in prior research. No PHS-2D independent branch, dedicated script, candidate or export is imported. Historical research results are not reattributed to Main in this repository.

## Necessary edits

- `tools/paths.py`: separates installed resources from `SOFTROBOT_AGENT_HOME` data, provides resource lookup and checkout/installed-source identity.
- `tools/research/__main__.py`: keeps the existing CLI, adds offline `examples`, `registry`, `validate` and `init-store` commands and explicit `--store` selection; defers research imports for basic CLI help.
- `tools/platform_store.py`, `tools/research/budget.py`, `core.py`, `experience.py`, `__main__.py`, `tools/rl/run.py`: route mutable ledgers, authority index, runs, private knowledge and exports to the data home.
- `tools/platform_host.py`, `tools/research/config.py`, `core.py`: preserve source provenance when installed without `.git`; configuration interpreters use current Python rather than personal paths. Relative credentials resolve under the data home.
- `tools/platform_registry.py`, `extensions/tendon_family/manifest.py`, `sorosim_session.py`: package and fingerprint MATLAB wrappers without creating a conflicting Python `matlab` namespace; remove example configuration files from executable source dependencies.
- `tools/research/diagnostic.py`: load CasADi/IPOPT diagnostic classes only when that numerical operation is requested, so the base Core imports without optimization extras.
- `tools/research/provider_context.py`: externalize the separately obtained tokenizer data while retaining its existing hash contract.
- `tools/research/runtime_capability.py`: remove a hardcoded private-machine failure archive; retain normal contained native probing and current-Study reuse.
- `candidate_portfolio.py`, `holding_diagnostic.py`, `feedback.py`, `numerics.py`: remove hardcoded historical-study enumerators and automatic archive discovery; retain generic explicit archive import and current-study analysis. Explicit archive paths resolve under the data home.

No new agent, mathematical algorithm, benchmark, P3 variant or acceptance definition is introduced. Existing scientific kernels and task acceptance semantics are retained.

## Excluded scripts, data and external software

- All `tests/`, `evidence/`, `runs/`, raw Stores, traces, trajectories, logs, caches, notebooks, historical Study configurations and experimental reports.
- Historical successful candidates, their exact parameters and success-case Knowledge. No default answer or archived admission proof is included.
- Unreached `tools/m3c2_diagnostic.py`, `tools/m3c3_verify.py`, `tools/task_intake.py` and `schemas/task_intake.py`; these do not belong to the selected production CLI/Registry dependency closure.
- One-off Shell/PowerShell/Node launch, quota/proxy/account-switch and export scripts; none is needed by the production Python entry point. Python contained workers and the 13 called MATLAB wrappers are retained.
- The complete local Gateway, noncommercial/restricted DevKit, third-party tokenizer data, MATLAB, SoRoSim, MEX binaries, scientific virtual environments and vendored third-party software.
- `.env`, real API keys, credential files, account metadata and personal absolute paths.

## Knowledge

Only generic material/inertia reasoning, parameter-to-model tracing, matched comparison and finite-search interpretation are packaged. Their procedural content is adapted from the source's method cards; standalone metadata removes references to archived cases, scientific result claims and unavailable cards. There are no historical successes, candidate vectors, task-specific winning controls or exact design recommendations. The example Knowledge mode is off; a user may explicitly enable the packaged typed procedural catalogue.

## Licensing

No explicit project LICENSE was present at the source commit. No license has been invented or applied by this migration. Public publication does not itself supply a new reuse license. Third-party runtimes and separately supplied software retain their own terms; restricted Gateway/DevKit code is excluded.

## Validation scope

Only compile/import smoke checks, CLI help, Registry discovery, two example parsers, independent empty Store initialization and standard wheel installation are performed. Results are recorded in `docs/migration-validation.json`. No Provider request, full Study, optimization, physical integration or historical regression suite is run.
