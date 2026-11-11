# Softrobot-Agent Core

Softrobot-Agent is an evidence-driven software platform for soft-robot research. A Main agent chooses research actions; registered mathematical tools, structure generators and physical backends perform computations; a Reporter interprets saved results. A local SQLite Store preserves immutable evidence, candidate identities, costs and provenance.

This repository contains the production platform extracted from the research implementation. It contains **no historical Studies, accepted candidates, private Store, trajectories or experimental archives**. The examples are illustrative configurations, not known solutions. The research archive remains separate.

## Install

Python 3.11 or newer:

```bash
git clone https://github.com/wran021004-gif/softrobot-agent-core.git
cd softrobot-agent-core
python -m pip install .
# Optional numerical backends:
python -m pip install '.[physics,optimization,conic]'
```

Base installation supports CLI, configuration parsing, Registry, Store, Main and Reporter interfaces. MuJoCo, CasADi, conic solvers and reinforcement learning are optional. MATLAB/SoRoSim are installed separately. No Gateway or restricted DevKit is included.

## Start offline

```bash
python -m tools.research --help
python -m tools.research examples
python -m tools.research registry
python -m tools.research validate --example reach
python -m tools.research validate --example tracking
python -m tools.research init-store --run-id local-project
```

These commands do not contact a Provider or integrate physics. New data defaults to `~/.softrobot-agent`; set `SOFTROBOT_AGENT_HOME` before starting Python to use another directory. Code resources stay in the installation. `--store PATH` selects an explicit project Store. `init-store` initializes an empty, zero-execution-budget Store; `prepare` creates its own Study Store under a distinct run ID.

## Example tasks and research execution

The bundled Reach/Hold and timed-tracking templates illustrate the existing TaskAdapter and evaluator contracts. To prepare the default example without launching a Study:

```bash
python -m pip install '.[physics,optimization]'
python -m tools.research prepare --example reach
python -m tools.research status --run-id example-reach
```

The templates declare zero Provider and physical-launch budgets. They are configuration examples, with no successful candidate. For a research run, copy the example directory returned by `examples` into your own configuration folder, edit its task/domain/budgets and runtime, then use the existing `prepare`, `bind` and `run` commands. Formal model execution retains the original explicit, identity-bound research authorization and session-handoff admission; these are not automatically granted by installation. See [installation](docs/installation.md) for the authorization composition and optional environments. No full Study is started by installation or by the offline commands above.

## Provider configuration

Use the supplied `tools/assets/examples/runtime.json` and `provider.json` as templates. Select your actual model and its context limits; the example model identifier is a placeholder. Keep the credential file outside the checkout, normally at `$SOFTROBOT_AGENT_HOME/provider.json`. For the OpenAI-compatible official adapter, it contains `base_url`, `api_key` and optionally `model`, matching the runtime. Never commit real credentials.

The runtime retains the official API, DeepSeek and external local Gateway adapters. A Gateway endpoint is configured as an external service; obtain any separately licensed Gateway/DevKit independently. No Gateway implementation is bundled. DeepSeek tokenizer data is also external and optional; see the installation guide.

## Architecture and source

- `tools/research/`: CLI, Main, Reporter, scientific runtime and evidence interfaces.
- `tools/platform_*`: Registry, Store, host, workers and task compilation.
- `extensions/math_analysis/`, `extensions/optimization/`: mathematical and solver adapters.
- `extensions/tendon_family/`: FamilySpace, structure generation, model compilation and physical backends.
- `extensions/reference/`, `schemas/`: task adapters, evaluators and typed contracts.
- `tools/assets/`: generic examples, procedural Knowledge/Skill and project-authored MATLAB wrappers.

See [architecture](docs/architecture.md), [installation](docs/installation.md) and the [migration manifest](docs/migration-manifest.md). The source repository supplied no explicit project license; this extraction does not invent one or relicense third-party software. Public visibility alone is not an additional license grant.
