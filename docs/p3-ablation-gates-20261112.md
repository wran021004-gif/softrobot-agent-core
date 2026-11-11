# P3 消融能力准备

基线：`codex/m1-ablation-gates-20261111` / `78e1c8535597f67c365f6a94b4a522a58d5a1e52`。开发分支：`codex/p3-ablation-gates-20261112`。复用既有 M1 Direct 和初始化白名单，没有重做权限框架。本轮没有创建 Study/Store/Agent、发送 Provider 请求、启动 Worker 或执行 MuJoCo。

## 方法和 operation 门禁

新增可选 `mechanism_operations`，合法集合为 `inspect`、`differentiate`、`optimize`、`compare`、`interact`。省略时保留旧行为；设置时拒绝空列表、未知项和重复项。该字段进入冻结 spec 和身份摘要。

`structure_research.allowed_operations` 统一投影方法授权与 operation 白名单。`analysis.dispatch` 在候选准备/Worker 前拒绝未授权 operation；科学问题编译入口也提前拒绝。Main 的科学问题 Schema、原始 MechanismStudy Schema、方法发现和 operation 列表均同步许可。No-Math 使用已有 `mechanism_structure_v1: null`，不关闭整个 analysis、物理后端或结构生成。

No-Interact 保留 `family_search.coupled_block_enabled=true`。核对发现当前 Coupled Block 包装器实际生成 `MechanismStudy(operation='interact')`，并非另一个独立耦合优化器；因此同一 operation 门禁也拦截这个包装入口。普通坐标搜索、联合参数编辑和其他四种数学 operation 保留。

## No-Math 的必要搜索适配

旧 P3 的 ordinary FamilySearch 动态候选评价借道数学 inspect，受数学方法 grant 和数学额度约束。直接撤销 grant 会把搜索一起关闭。

对具有有限 `physical_launches` 的普通 `family_mixed_search_v1 / passive_task_response`，复用现有 `physical_replay.dispatch` 完成冻结物理程序；三个新 Pilot 配置采用同一路径。搜索准入按双方向 episode 折算，不占可选数学评价额度。旧 Full 的无限物理预算路径保持原来的数学适配语义。

此路径只接受完整冻结程序，不接受 `execution_profile` 覆盖；Main 搜索 Schema 和编译器同步允许省略 profile。它使用原任务诊断约束中的 normalized violation 排序，包含接触和腱约束；排除用户本轮不要求的 paired causal proof。结果明确标为 `task_acceptance='unmeasured'`，不把诊断得分写成正式验收。物理模型、阈值、Evaluator 和 `structure_research.calculate` 均未修改。

No-Math 的静态 equilibrium 数学诊断仍不可用；保留的是普通结构生成和完整被动物理响应搜索，不是绕开授权继续数学 inspect。独立确认、半步长、扰动、重复通过检查和正式 SELECT 均不是新增配置的研究义务。

## No-Knowledge

沿用 `KnowledgePolicy(mode='off')`，Main/Reporter 检索、catalogue 和提示条目均为空。另在 Reporter 缓存收据读取之前增加相同的冻结策略检查，避免缓存入口绕过 off。基础 System Prompt、任务定义、接口 Schema 和物理说明保留。

存在一个已核实的迁移差异：原 Research 启动 manifest 有 **45 条记录、17 个 entry ID**，指定独立 Core 基线按同一 Full policy 只解析出 **4 条通用条目**。No-Math/No-Interact 保留该 policy 与 Core 当前实际 4 条；No-Knowledge 为 0。没有私自迁移历史知识包或向 Main 注入 Full 成功结构。后续论文必须记录这个差异，不能把 4→0 的 Pilot 描述成对历史 45 条知识的严格单因素移除。

## 配置与预算合同

三份配置和计划在 Research 配套分支 [codex/p3-ablation-configs-20261112](https://github.com/wran021004-gif/softrobot-agent/tree/codex/p3-ablation-configs-20261112)。Core 先提交后，三份配置的 `base_commit` 绑定该新 Core SHA。

| 合同 | No-Math | No-Knowledge | No-Interact |
|---|---:|---:|---:|
| Provider / protected requests | 48 / 4 | 48 / 4 | 48 / 4 |
| Mathematical evaluations | 0 | 24 | 24 |
| Physical launches | 32 | 32 | 32 |
| Search proposals / evaluations | 24 / 16 | 24 / 16 | 24 / 16 |
| Public operations | 160 | 160 | 160 |

所有执行计数额度为有限硬上限，关闭旧 `request_budget_only` 的“只记数学/物理使用量、不限次数”模式。禁用的 NMPC/RL/local/offline/BDF 计数为 0。没有新增预算字段或自动扩展。

现有合同的必要区分：

- `family_search.max_proposals/max_evaluations` 是**每次搜索请求**上限，不是全 Study 累计提案/候选额度。Study 仍受共享 Provider、公共操作和物理计数限制；不将其伪称累计 24/16。
- `physical_launches` 限制登记的 backend episode；完整双方向普通响应消耗 2，因此新适配路径最多得到 16 次这样的新响应，并与其他物理请求共享。可选数学 Worker 内部积分另计数学评价，不能把 32 宣称为全 Study 所有物理轨迹的总上限。
- `numerical_s/activity_s/local_solve_s/delivery_reserve_s` 的 null 是旧 count-mode 中未设累计时间额度；它们不是这张表的执行次数预算。保留有限单 Worker watchdog，不伪造不被执行的时间上限。

## 离线验证

```powershell
$env:P3_ABLATION_CONFIG_DIR='D:\softrobot-agent\.worktrees\passive-research-capabilities-20261107\configs\research'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe' -m unittest discover -s tests -p test_p3_ablation_gates.py -v
```

**11 项 P3 定向测试通过**：三配置/Full 解析与共同科学配置比较；有限计数；No-Math 五种原始请求拒绝与 Main 可用目录；No-Interact 拒绝、其余四种 operation 和旧默认；两种 Schema 及发现列表；Main/Reporter/缓存/预载隔离；普通物理搜索准入和双方向预算；物理适配及检查点复用；Main 搜索 Schema/编译器；Coupled 包装器；非法 operation 列表。

另运行既有 **9 项 M1 方法门禁定向回归，全部通过**，因为本次修改了共享解析和 Schema。没有运行全量套件。测试阻止网络、子进程与 MuJoCo 导入；允许的执行停在 Mock 边界，假数值明确为测试 fixture，不是研究结果。

提交前 `git diff --check` 通过。没有改写 Full、任务、FamilySpace、Runtime、Phase 0 文档、历史 Store 或物理/数学计算算法。下一步只等待用户授权首个 Pilot；本轮不执行。
