# P3 No-Math 第三账号启动修复

原 Core 基线：`ac4065f27edb357876c18c290ae3983a5bae5793`。
用户在确认默认8787与第三账号8789的绑定差异后，明确要求“直接修复，然后我们重新开始这个消融实验的study”。

## 最小代码修复

- `provider.transition_transport`：原接口只允许 OpenAI API 与 Gateway 互转，现允许经过同样明确授权的 Gateway 实例之间迁移。仍要求 IPv4 loopback `/v1`、同模型/研究设置、精确原身份授权和已结算边界；不扩展远程端点、预算或自动换账号能力。
- `session_handoff.trusted_history`：首个请求若是已结算的 `subscription_sharing_usage_limit_exceeded` 429，并且之后已有授权传输修正及实现绑定，可在没有任何模型输出/工具执行且SDK初始消息与原wire严格一致时复用原始初始提示。保留失败与请求消耗；不跳过成功响应、未知结果或已执行工具。
- `agent.converse`：上述原始初始提示恢复时，不要求构造一个并不存在的已完成assistant交接边界；停止接续授权仍需核实原封存状态和原处置引用。

物理模型、任务、设计空间、数学算法、No-Math方法/operation门禁、Knowledge和预算算法均未修改。没有伪造模型输出或关闭原执行门禁。

## 离线验证

5项新增定向Mock测试通过：本地Gateway实例修正、任务/数学授权及已用请求保留、远端/换模型拒绝、精确首个429恢复，以及缺授权/缺绑定/已成功/已执行工具/提示变化拒绝。测试阻断网络、Worker和MuJoCo，无真实Host/Study。

原11项P3离线门禁及9项M1权限回归全部通过，合计25项。未运行全量套件。Python：`D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`；配置来自Research已提交的P3三配置和原M1夹具。`git diff --check`通过。

## 本次实际重启范围

用户选择重新开始，因此旧 `p3-ablation-no-math-20261112` 保持封存，其错误8787请求1次和429证据不删除、不重置。Research新增独立配置与第三账号Runtime，新Study为 `p3-ablation-no-math-20261112-account3-restart1`；新Store为空，预算沿用200请求（含4保护）、数学0、物理150、公共操作800，FamilySearch每请求24/16。旧1次错误启动成本单独报告，不作为新实验的科学结果。

运行前先提交本修复，Research新配置绑定修复后的精确Core SHA。新配置直接选择8789与第三账号独立凭据，不需对新Store做传输迁移；恢复兼容修复仅在今后明确授权接续且满足全部原始证据检查时生效。本次不再启动其他消融或第二次自动重试。
