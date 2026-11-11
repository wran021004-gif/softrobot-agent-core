# Installation and runtime configuration

## Python and packages

Python **3.11+** is required; the migration smoke checks use Python 3.11. Base requirements are declared in `pyproject.toml`: Pydantic, NumPy, SciPy, HTTPX, OpenAI client, JSON Schema, PyYAML, Strands Agents and Strands Harness. The two Strands versions retain the production source pins.

```bash
python -m venv .venv
# Activate .venv with the normal command for your shell.
python -m pip install .
# Choose only the extras you use:
python -m pip install '.[physics]'       # MuJoCo
python -m pip install '.[optimization]'  # CasADi / IPOPT
python -m pip install '.[conic]'         # CVXPY / Clarabel
python -m pip install '.[rl]'            # PyTorch / Gymnasium / Stable-Baselines3 / MuJoCo
python -m pip install '.[deepseek]'      # optional tokenizer library, not tokenizer data
```

Missing optional runtimes do not block base CLI, Registry, task parsing or Store initialization. Registry exposes their dependency requirements. A method that requires an absent optional package remains unavailable; no substitute numerical result is manufactured.

## Directories and environment variables

| Variable | Meaning |
|---|---|
| `SOFTROBOT_AGENT_HOME` | Writable data home; default `~/.softrobot-agent` |
| `SOFTROBOT_RL_RUNS` | Optional explicit RL run directory; default under the data home |
| `SOFTROBOT_RL_PYTHON` | Optional separate RL interpreter; default current Python |
| `SOROSIM_ROOT` | Separately installed, pinned upstream SoRoSim checkout |
| `SOFTROBOT_AGENT_TOKENIZER` | Optional externally obtained, hash-matched DeepSeek tokenizer JSON |
| `DEEPSEEK_API_KEY` | Credential consumed only by the DeepSeek adapter |
| `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` | Numerical thread settings; use `1` for the supplied runtime template |

PowerShell example:

```powershell
$env:SOFTROBOT_AGENT_HOME = Join-Path $HOME '.softrobot-agent'
python -m tools.research init-store --run-id local-project
python -m tools.research validate --example reach
```

A Store is bound to its own absolute data directory. Moving/copying an existing live Store still requires the original explicit migration policy. An empty independent Store is initialized directly with `Store(path).create(ProjectConfig(...))`; the CLI `init-store` supplies a unique zero-execution-budget configuration and creates no Study or model session.

## Generic examples

`python -m tools.research examples` returns the installed configuration paths. Copy that entire directory before editing it; relative includes are resolved against configuration-file locations, not the working directory. The two task templates use fresh illustrative targets, a generic family domain and zero Provider/physical budgets. They are not benchmark results or accepted designs.

```bash
python -m tools.research validate --example reach
python -m tools.research validate --example tracking
python -m pip install '.[physics,optimization]'
python -m tools.research prepare --example reach
python -m tools.research status --run-id example-reach
```

`prepare` creates a configuration and ledger; it does not itself start Main or run a trajectory. Do not initialize an empty Store at the same location first: Study preparation creates its own configured Store.

## Provider setup

The runtime template selects `openai_api`, with `YOUR_MODEL_ID` as a placeholder. Its context limits are illustrative and must match the chosen model. The default credential reference `provider.json` resolves under the data home. Copy and edit the credential template there:

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "REPLACE_WITH_YOUR_API_KEY",
  "model": "YOUR_MODEL_ID"
}
```

The endpoint and optional model in the credential file must match the runtime. Runtime interpreter fields set to `python` resolve to the invoking interpreter; explicit interpreter paths remain supported. No credential is read during `--help`, `registry`, `validate` or `init-store`.

The external `chatgpt_gateway` adapter retains the production contract for an independently supplied IPv4 loopback service at `http://127.0.0.1:PORT/v1`, with explicit advertised model/tool/reasoning capabilities. The local Gateway and noncommercial DevKit are **not** redistributed or required for Core installation. No new Gateway is implemented.

DeepSeek uses its existing adapter and `DEEPSEEK_API_KEY`. Large-request refinement/token-based handoff additionally requires the pinned tokenizer file obtained separately: SHA-256 `89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`. Set `SOFTROBOT_AGENT_TOKENIZER` to that file. The conservative byte-bound fast path needs no tokenizer. Tokenizer JSON and its upstream license are not bundled.

## Starting Main with your own configuration

The original research authorization model is retained. Installation and examples do not authorize paid requests. A real configuration supplies nonzero finite budgets, an actual Provider/model, task and FamilySpace, allowed actions and operator authorization. Use `prepare(spec_path)` and `bind(host)` from `tools.research.core`; then save an explicit grant with `tools.research.state.save`, set `formal_study_authorization` through `update`, and invoke `converse(host)` or `python -m tools.research run --run-id YOUR_STUDY`. Grant scope must bind `study_id`, `resolved_identity`, and `implementation_freeze`; see the short authoritative contract in `tools.research.state.require_research_authorization` for the additional formal capability/continuation scope. Session handoff additionally uses the existing `session_handoff.admit_formal_study` admission; choose your conversation policy explicitly. No archived admission proof is shipped.

These are the existing APIs, not a new setup framework. `run --delivery-only --max-new-provider-requests N` retains final-answer delivery using existing evidence and reserves the last allocated request for the answer.

## External physics software

MuJoCo is provided by the `physics` extra. CasADi/IPOPT and CVXPY/Clarabel are separate extras. RL can use a separately managed interpreter and is never installed implicitly.

MATLAB, its Python Engine, toolboxes and SoRoSim must be installed under their respective terms. The adapter retains its supported SoRoSim revision `24d573a3e864ffda87c42ee462a6ed620133cc7b`; set `SOROSIM_ROOT` to your checkout and install the Engine appropriate to your MATLAB release. Only this project's 13 JSON gateway/control wrapper `.m` files are packaged. MATLAB, SoRoSim source, MEX files, external libraries and their licenses are not bundled. Their absence does not block base installation.
