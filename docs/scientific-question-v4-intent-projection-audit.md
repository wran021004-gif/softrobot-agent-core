# scientific_question_v4 Research Intent Projection Audit

审计基线：Core `9a8a1fd3feee5d966a5981dd965c2a2ec5c681d5`。本轮只读历史 P3 Store；没有实例化 Host、创建 Study、调用 Provider 或执行数学/物理 Worker。

## 结论与五个问题

**Not independently ablatable in current implementation**

| 问题 | 实际结论 |
|---|---|
| 是否有独立的意图投影实现？ | 有真实的、可定位的确定性科学问题编译代码；没有与 Main 的结构化问题选择、必需的模型绑定/检查相分离的自适应投影模块。不能把“有编译器”直接写成“有可独立消融的自适应投影算法”。 |
| Main 是否决定研究目标、参数组和物理意图？ | 是。候选绑定的 diagnose Plan 记录假设、预期/削弱观测和下一步；V4 请求明确选择 operation、effect_semantics、target、parameter_group/paths、负载、局部范围和请求额度。P3 为 no_active_control；固定输入/重新优化控制的选择属于主动任务的对应分支。 |
| 程序怎样产生数学问题？ | 校验注册参数/观测，绑定冻结候选、任务、模型、负载和约束，将显式结构化选择编译成 MechanismStudy/AnalysisRequest；求导路由、适用性、预算和 Worker 仍由原入口确定。程序不从自由文本假设推断一个新的目标函数或求解问题。 |
| 能否独立关闭？ | 当前不能得到含义清晰的独立 OFF 行为。禁用 expand_v4 只移除冻结字段补全；禁用 compile_question/compile_mechanism 会同时移除合法数学请求的绑定与校验；切换原始请求接口会改变 Main 的输入负担。它们均不是单独移除自适应科研投影。 |
| Full Trace 是否证明实际参与？ | 是。历史 Store 有 25 份 scientific_intent_compilation_v1 收据，能连接 Main 输入、compiled_question、full_request、原 diagnose Plan；抽查首个 inspect 和两次 interact 均有实际完成结果。该数目不是 51 份分析结果或 67 次数学评价的替代计数。 |

因此本轮不增加 No-Intent 开关、模板框架、配置或 test_p3_intent_projection_gate.py，不修改生产 Python。固定模板相对自适应问题构造的比较保留为未来方法工作：先建立两种明确的问题构造行为，再验证只改变组合自由度、保留五种 operation 和相同检查。当前代码允许在注册语义内组合问题，这属于 Main 决策与确定性编译共同实现的系统能力；并非声称这一能力不存在，也不是因为历史使用证据缺失而暂缓。

## 必要调用链与职责

以下定位均针对审计基线；本轮未改这些代码。

| 环节 | 源码与确定性职责 | Main 的科研选择 |
|---|---|---|
| Schema | tools/research/contracts.py: ScientificQuestionV4、ScientificStructureV4、PhysicalMechanismTarget；scientific_intent.question_schema 按冻结任务和方法权限投影 Schema | 显式研究域、目标及效应语义；Schema 可见不代表发生过调用 |
| Main 入口 | tools/research/agent.py 中 research_analysis 入口调用 compile_question，ready 后交给 analysis.dispatch；completed_question_plan 要求已有候选绑定 diagnose | 假设、研究方向、候选、参数组、预期观测、继续/停止 |
| 语义转换 | scientific_intent.expand_v4、compile_question、compile_mechanism、compile_dynamic、compile_constrained；保存 raw_main_input、compiled_question、deterministic_field_sources、full_request | 自主选择目标、参数和已有语义的组合；程序只补全唯一确定字段 |
| 参数与观测注册 | structure_research.parameters 使用 optimal_capability.family_analysis_parameters；extensions/math_analysis/mechanism_registry.py 的注册观测及物理意义 | 选择合法连续路径、观测及输出投影；不能提交未注册任意表达式 |
| 冻结任务与内层问题 | task_constraints.mathematical_method_view / mathematical_research_view 从 TaskAdapter 编译约束和适用性；prepare_context 绑定参数边界、物理模型、相同条件和成本 | 固定输入或重新优化控制、局部机制或完整任务响应；P3 无主动控制内层优化 |
| 数学路由与执行 | differentiation_router.select_method；analysis.dispatch 再查方法与 operation 权限、数学/物理余量，事务预留后才进入 execution_worker；structure_research.calculate 生成数值证据 | Main 不指定 KKT 判定结果或数值有效性，不将方法名当作有效结果 |

expand_v4 的补全依赖显式 effect_semantics 和冻结物理事实，例如被动模式、no_active_control、对应 operating_point。它不重新解释假设文本，也不在参数—观测—求解问题空间自行规划。仅在这里加开关会测量冗余字段填写，而不是论文希望研究的自主问题构造。

## 历史 Trace：区分五个证据层级

来源：Research 基线的 docs/research/p3-autonomous-study-v1_2-launch-20261110/launch-receipt.json 定位到原 Store：

`D:/softrobot-agent/.worktrees/passive-research-capabilities-20261107/runs/research/p3-passive-progressive-stiffness-autonomous-20261110-v1_2/platform.sqlite`

数据库以 readOnly=true 打开，并设 PRAGMA query_only=ON。只检查意图编译、对应结果、直接后续 Plan 和既有 Knowledge 读取；未导入历史 Store 到任何新组。下面是原 artifacts.id，供原始证据追溯，不是新运行产物。

| 实际请求 | 意图编译 artifact | 完成结果 artifact |
|---|---|---|
| 卸载活动集 inspect，routing 参数组、constraint_active_set | 69ccad2986c9c7bf7fffb502c4d00d4c2e9b8e04f6f9e4221866b382b245d9f9 | 4e42818b908e3b28bb4e671dac8e5e7f216b118ac30b02ebe857432ee7c9a404 |
| payout_offsets_m.tendon_1 × spans.0.radius_m，有限时间 interact | 36fcd04a2cc5cb1e65fb495f4a443e9513b990ac8902a79877e34ccb0de0d9ba | c0b844d23ed27d8b9c077e6167f03ee886a040611cec61573f26beabf4e979e4 |
| segments.3.physical_parameters.density_kg_m3 × segments.3.sections.0.parameters.radius_m，有限时间 interact | 5090da90cbac846e8715ea69d27a8f02c36a6ff6ef54ef54e0a11020acf11eba | 5f1e0a3b7c320eb72d9d4849f6179006c609d54af9771a7852c1c0712ad1774f |

1. **代码存在**：上述函数形成真实调用链，而不是只有架构命名。
2. **Schema 暴露**：编译收据保存 provider_schema；这单独不证明执行。
3. **Main 实际提交**：raw_main_input 保存明确目标/参数/语义；两次 interact 的路径均由 Main 提交。
4. **固定程序实际执行**：三份结果均 status=computed，boundary.worker_started=true、termination_confirmed=true、returncode=0。首个 inspect 对应 events seq 108（编译）、109（预留）、111（结果）、112（完成）。编译收据自身 scientific_execution_started=false，不能拿该收据单独充当 Worker 执行证据。
5. **结果影响后续决策**：后续 generate Plan artifact a60ced35772b39bcd4f337af9172c5f20c08788be97009251a17e2447406c4ad 引用 payout/radius 结果，解释“局部 payout 效应小、测试尺度未记录 radius 效应”，转向近远段长度重分配。这支持过程层面的决策影响，不证明编译层或交互对最终成功有独立因果贡献。

两次 interact 均为 matched_two_parameter_four_point_v1、strict_derivative=false、diagnostic_comparison；interaction_effect 和 independent_effects 为 null。不能写成严格混合偏导或已获有效标量交互增益。固定算法确实运行与数学结论充分有效必须分别报告。

## Knowledge 原始资产恢复

Research 的历史 knowledge-manifest.json 记录 45 条、17 个 ID；原始目录中全部内容仅涉及 9 个文件、253081 bytes。原基线打包的 4 条通用方法不能替代该快照。本轮直接复制这 9 个原始文件到 tools/assets/memory/ 原相对位置，并以 Research memory/diagnostic_index.json 中的 45 条原始元数据恢复 catalogue；保留既有 generic_methods.json 文件。不重写正文，不开发新的加载器。原始文件混用 CRLF/LF；.gitattributes 对恢复资源禁用换行转换，保留原字节以避免跨平台 checkout 改变历史内容指纹。pyproject.toml 现有 assets/**/*.json 规则已经覆盖这些资源。

对 manifest 中 45 条 content_sha256 做一次原始内容核对（content_key 条目按既有规范对具体条目计算），全部一致。恢复范围是历史准入快照，不代表 Main 实际读取全部 45 条。新 No-Math/No-Interact 使用相同快照；No-Knowledge 沿用 mode=off，Main/Reporter 的检索、预载、缓存及正文入口均关闭，任务/系统/工具说明继续保留。配置解析验证实际 freeze_knowledge 结果等于历史 manifest，OFF 为 0。因原始内容可直接恢复，本轮无需采用 4→0 回退口径。

| 角色 | 历史实际 read（已对原 retrieval 核对） |
|---|---|
| Main：7 次 | passive-structure-mechanics@1；mechanism-research-process@2；skill-parameter-model@4；skill-witness-replay@3；skill-matched-comparison@4；skill-finite-search@3；skill-continue-or-stop@3 |
| Reporter：9 次 | general-routing@1,@2；passive-structure-mechanics@2,@3；validation-qualification@1,@2；general-material-inertia@1,@2；skill-local-to-experiment@4 |

没有 p3-case@3 的直接 read；配置准入和其他条目的历史引用不等于读取本体。历史源文件中的经验仍是带来源上下文，不是本轮或历史 P3 新取得的证据。资产恢复只对齐知识可见范围，不抹去新旧 Core、预算和搜索物理适配的版本差异。

## 预算核实与验证范围

现有 config.resolve 将 provider_requests/public_operations/physical_launches 分别映射到平台 model_calls/tool_calls/backend_solves。provider.LiveBoundary 在 Store 事务预留前检查 remaining model_calls>=1，Main/Reporter 共享此计数；last_requests_v2 的 4 次 closeout 额度包含于 200，不额外增加。第 200 次可正常结束，第 201 次在发送前拒绝。公共操作使用原 tool_calls 硬上限 800；数学额度通过 mathematics_fits/事务 charge 限制为 0 或 100。数学动态请求已有 dynamic_cost_bound.episodes 的同一 backend ledger 预留，普通双方向物理搜索同样占用 150 上限，每个完整响应占 2 episodes。单请求搜索 24/16 保留原语义。

报告停止值 budget_exhausted / incomplete_at_budget 是实验报告合同，不新增伪造的配置预算或内部状态枚举。保留有限 Worker watchdog 和原保护阶段，不为凑满 200 请求突破其他额度；任何额度先耗尽都应如实记录。禁止自动扩展或通过新 Study/Store/身份续跑。

只修改已有 P3 测试的预算断言并加入快照一致性断言；继续执行原 11 项 P3 离线测试及 9 项 M1 方法授权回归。测试内阻断网络、子进程和 MuJoCo，允许路径停在 Mock 边界。没有新增意图门禁，故没有条件性新增测试。完整测试套件不运行。

验证结果：11/11 P3 定向离线测试通过（P3_ABLATION_CONFIG_DIR 指向本轮 Research 工作树）；9/9 M1 方法权限回归通过（M1_ABLATION_CONFIG_DIR=D:/softrobot-agent/paper_experiments/configs/m1_core_full_v1）。执行器为 D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe，命令分别为 python -m unittest discover -s tests -p test_p3_ablation_gates.py -v 和对应 test_m1_ablation_gates.py；PYTHONDONTWRITEBYTECODE=1。没有跑全量套件。提交前 git diff --check 通过。
