# Phase 1A：M1 方法级消融开关

从 M1 Full 实际 Core 提交 `7f034a60f1ea0be5ac3174c5b6c8908a8f56dd40` 创建 `codex/m1-ablation-gates-20261111`。本轮只实现权限、Schema 和配置验证；没有创建 Study/Store/Agent，没有 Provider 请求、数学 Worker 或 MuJoCo 执行。

## 修改范围

| 文件 | 修改 |
|---|---|
| `tools/research/config.py` | 解析、冻结 Direct 方法授权及可选初始化方法白名单；验证方法名和重复项；显式 null 表示撤销数学方法授权 |
| `tools/research/nonlinear_capability.py` | 在既有方法授权映射注册 Direct，并保留旧冻结配置省略 Direct 时的默认语义 |
| `tools/research/analysis.py` | 在候选准备和 Worker 前对 Direct 复用 Native 的方法授权检查 |
| `tools/research/physical_replay.py` | `seed_control` 在条件克隆、基线创建和 guided_seed 前检查初始化方法许可；未改 Replay、Evaluator 或探针算法 |
| `tools/research/agent.py` | 初始化 Schema 仅展示许可方法；若 baseline 未授权，则要求显式方法选择 |
| `tools/research/task_constraints.py` | Direct 方法目录/可选状态反映授权；不影响单独授权的 Native T1 |
| `tools/research/research_context.py` | 初始化帮助信息同步白名单 |
| `tests/test_m1_ablation_gates.py` | 9 项离线 Mock 测试 |

## 配置语义与兼容

Direct 授权 key 为 `mathematical_methods.mujoco_direct_control_v1`：非空说明字符串表示授权，**显式 null 表示撤销**。Native T1 同样可用 null 撤销；其 key 仍为 `mujoco-nonlinear-task-capability-v1`。整个 `analysis` 能力保持启用，其他已授权数学方法不被一并关闭。

为保留历史 Full 默认行为，省略 Direct key 时沿用旧 Direct 权限；新解析的配置会将该默认授权明确冻结。旧冻结 spec 未带该 key 时也保持原默认语义。因此关闭 Direct 必须显式写 null，不能通过删除 key 关闭。没有改写原 Full 配置、冻结 Store 或历史授权事件。

`control_initialization_methods` 为可选、非空、无重复的方法名列表，合法方法来自现有 `ControlSeedRequest`。省略该字段时保留旧行为；设置后仅允许名单内方法。No-Automated-Physical-Probe 使用：

```json
"control_initialization_methods": [
  "baseline",
  "mathematical_response",
  "capability_sequence"
]
```

拒绝不是只发生在 Schema：原始初始化请求也在 `seed_control` 最先被拒绝。Native/Direct 原始请求则在 `analysis.dispatch` 方法准入处被拒绝。

## 两份研究配置

配置属于研究仓库 `wran021004-gif/softrobot-agent`，没有移入独立 Core 仓库。配套分支同为 `codex/m1-ablation-gates-20261111`，文件留在原 Full 引用目录：

- [No-Model-Based-Control](https://github.com/wran021004-gif/softrobot-agent/blob/codex/m1-ablation-gates-20261111/paper_experiments/configs/m1_core_full_v1/ablation_m1_no_model_based_control.json)
- [No-Automated-Physical-Probe](https://github.com/wran021004-gif/softrobot-agent/blob/codex/m1-ablation-gates-20261111/paper_experiments/configs/m1_core_full_v1/ablation_m1_no_automated_physical_probe.json)

两份配置复用指定 Full 叶配置的 defaults、FamilySpace、三任务、control、runtime 与知识引用。科学参数和预算逐项相等；各有独立 Study ID、证据目录、权限说明及新实现绑定，且标为离线配置草案，不提供 Pilot 执行授权。

**预算基线严格采用用户指定的原叶文件：Provider 48、数学评价 16、物理评价 18，Native 结点上限 4。** 历史 Full 运行时用户追加到 Provider 73、结点 30 的授权没有自动扩展到新实验。两份配置的这些值一致；本轮没有擅自提高任何控制限制。后续 Pilot 若要对齐历史最终运行额度，需要统一其新实验授权与对照方案。

历史 Full 引用资源继续保留在原目录；本次配置提交只包含两个新叶文件，没有复制或修改历史依赖，也没有把私人 Store/日志上传。

| Capability | Full 默认 | No-Model-Based-Control | No-Automated-Physical-Probe |
|---|---|---|---|
| Native T1 | ON | OFF | ON |
| Direct | ON | OFF | ON |
| Automated Physical Probe | ON | ON | OFF |
| 普通 baseline 初始化 | ON | ON | ON |
| 其他已授权分析 | ON | ON | ON |
| Task Evaluator | ON | ON | ON |
| 独立 Physical Replay | ON | ON | ON |
| Joint SELECT | ON | ON | ON |

## 离线验证

在指定 Core 工作树执行：

```powershell
$env:M1_ABLATION_CONFIG_DIR='D:\softrobot-agent\paper_experiments\configs\m1_core_full_v1'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe' -m unittest discover -s tests -p test_m1_ablation_gates.py -v
```

结果：**9 项通过**。覆盖两配置和 Full 的真实解析、共同科学配置相等、Native/Direct 分别撤销和原始入口拒绝、Probe 在克隆/评价前拒绝、允许初始化的分派、方法目录/科学问题 Schema、历史默认兼容、非法白名单，以及共同 Replay/SELECT 权限路径。Full 原叶文件 SHA256 前后不变：`ed09d64f45297b8237d9a549fe2b4fc4b1c41fbd90195237b35275ec54ff5a84`。

测试阻止网络、子进程和 MuJoCo 导入。允许的分析停在 Mock 候选边界，初始化停在 Mock 委托边界，Replay 停在 Mock 物理预检边界；联合选择的收据评估为 Mock。Evaluator 仅解析原注册函数，不计算新的任务结果。这里的 ON 指权限链路保留，不是新增物理通过证据。没有运行全量测试。

`git diff --check` 通过。没有修改 Native/Direct 搜索、局部拟合、物理后端、Evaluator、任务阈值、P3 或历史 Full。实现允许后续安排 Pilot，本轮不启动。

No-Automated-Physical-Probe 只移除自动 helper。保留显式 baseline 时序与独立 Replay，意味着 Main 仍可组织手工物理实验；本实现不宣称禁止所有语义上的有限差分探测，也未增加行为分类器。
