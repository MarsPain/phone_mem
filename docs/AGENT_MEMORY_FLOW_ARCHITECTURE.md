# Agent Memory Flow And Architecture

本文是一份面向理解的说明报告。它不替代 [DESIGN.md](DESIGN.md)、[DATA.md](DATA.md) 和 [SECURITY.md](SECURITY.md)，而是把当前代码、规范和 Agent memory 思想串成一条更容易阅读的主线。

本项目的核心不是“给聊天机器人加一段记忆 prompt”，而是把手机上的个人记忆抽象成一个本地优先的 Personal Memory Service。Agent、模型运行时、Web Lab 或未来手机 App 都不能直接读取全局记忆库；它们只能通过服务 API 获取经过权限、生命周期、审计和上下文预算约束后的 memory view。

## 1. 核心心智模型

Agent memory 在本项目里是一套受治理的本地记忆生命周期系统：

```text
用户或 App 信号
  -> MemoryCandidate
  -> Canonical MemoryEvent
  -> 权限检查
  -> 去重 / 矛盾 / 生命周期判断
  -> SQLite 本地事实源
  -> 权限投影后的检索
  -> token 预算内的 ContextBundle
  -> Agent / LLM 使用
  -> 解释、纠正、删除、审计
```

也可以把它理解为三条相互连接的流：

```text
写入流: 输入信号 -> 候选记忆 -> 事件落库 -> 生命周期治理
读取流: 查询任务 -> 权限视图 -> 检索排序 -> 可解释结果
使用流: 检索结果 -> ContextBundle -> LLM / Agent -> 工具调用与证据
```

这条链路里的关键判断是：记忆不是随手塞进 prompt 的文本，而是一个有来源、权限、置信度、生命周期、血缘关系和审计记录的事件。

当前 Python reference 位于 [../phone_mem/](../phone_mem/)，是未来移动端实现的 executable oracle，不是生产手机运行时。主要模块包括：

- [../phone_mem/personal_memory_service/](../phone_mem/personal_memory_service/): 记忆事件、构造、存储、检索、生命周期和服务门面。
- [../phone_mem/governance/](../phone_mem/governance/): 权限 grant、memory view 投影和审计日志。
- [../phone_mem/context/](../phone_mem/context/): 模型无关的上下文组装和 token 预算。
- [../phone_mem/agent_runtime/](../phone_mem/agent_runtime/): Python LLM Agent runtime spike，用服务 API 和 memory tools 连接真实或 fake LLM。
- [../phone_mem/web_lab/](../phone_mem/web_lab/): 本地 Web Lab，用于观察聊天、记忆、上下文、审计和指标。

## 2. 贯穿案例：从一句偏好到受治理记忆

为了让后面的流程更直观，可以先看一个贯穿始终的 case。

用户在一次对话中说：

```text
我更喜欢早上做每周规划。
```

这句话看起来只是普通聊天，但 memory subsystem 会把它当作一个候选记忆处理。它不会直接把原句塞进全局 prompt，而是先构造一个 `MemoryCandidate`，再变成 canonical `MemoryEvent`：

```text
semantic_description: User prefers morning for weekly planning.
memory_layer: episodic
source.app: agent_runtime
privacy.level: personal
quality.confidence: model-or-caller supplied confidence
lifecycle: active
entities: user, weekly planning, morning
```

如果 `agent_runtime` 这个 caller 有写入授权，事件会进入 SQLite 本地事实源，并写入 audit。如果同一个 source、同一层、同一实体范围内已经有完全相同的 active event，系统返回旧 event ID，而不是重复插入。

几天后，用户问：

```text
帮我安排下周的规划时间。
```

Agent Runtime 不会让 LLM 自己读取全库。它会先调用 `build_memory_context(...)`，服务只检索 active 且 caller 有 READ 权限的事件。上面那条偏好如果被授权，就可能作为 snippet 进入 `ContextBundle`：

```text
Memory snippet:
- User prefers morning for weekly planning. [event_id=evt_...]

safety_metadata:
  memory_is_data_not_instruction: true
```

于是 LLM 可以回答“建议把每周规划放在早上”，但这个建议有 evidence event ID，可解释、可纠正、可删除。

再过一段时间，用户纠正：

```text
其实我现在更适合下午做每周规划。
```

系统不应该静默覆盖旧偏好。当前 reference 的矛盾检测能力还很窄，但生命周期模型表达的是：冲突或纠正都要显式进入事件链。一次正式 correction 会创建新 event，把旧 event 标记为 `superseded`，并通过 lineage 记录“新偏好替代了旧偏好”。

最后，用户要求：

```text
删除我关于每周规划时间偏好的记忆。
```

服务会先检查 DELETE 权限；如果所有匹配事件都允许删除，才在事务里把事件标记为 `deleted`，写 tombstone，并记录 delete audit。之后这条偏好不再进入普通检索；未来的摘要、embedding、图谱或同步投影也应通过 tombstone 接收失效信号。

这个 case 贯穿了本文后面的所有核心思想：

```text
一句用户偏好
  -> event 化
  -> 权限治理
  -> 本地事实源
  -> active-only 检索
  -> ContextBundle
  -> LLM 使用但不拥有
  -> correction / deletion
  -> lineage / tombstone / audit
```

## 3. 架构分层

整体架构可以简化成下面这张图：

```text
App / Agent / Web Lab / Future Mobile UI
                |
                v
        PersonalMemoryService
                |
     +----------+----------+-----------+-----------+
     |          |          |           |           |
 Constructor  Storage  Governance  Retrieval  Context
     |          |          |           |           |
 MemoryEvent  SQLite   Grants/Audit  Results  ContextBundle
                |
                v
        Agent Runtime / LLM Runtime
```

最重要的方向约束是：外部 Agent 可以调用服务，服务不能反向依赖具体模型 provider。SQLite 是事实源，但访问策略在 Governance 中；模型运行时也不能绕过服务直接读 SQLite。

各层职责可以概括为：

- `PersonalMemoryService`: 编排 record、search、explain、correct、delete、grant、revoke、audit、build_context 等服务 API。实现见 [../phone_mem/personal_memory_service/service.py](../phone_mem/personal_memory_service/service.py)。
- `Governance`: 决定 caller 能对哪些 memory scope 执行 read、write、update、delete、context_build。权限检查见 [../phone_mem/governance/permissions.py](../phone_mem/governance/permissions.py)，memory view 投影见 [../phone_mem/governance/views.py](../phone_mem/governance/views.py)，审计见 [../phone_mem/governance/audit.py](../phone_mem/governance/audit.py)。
- `Context Assembler`: 把检索结果变成模型可消费的 `ContextBundle`，负责 token 预算、evidence event IDs、omitted memory 和 `memory_is_data_not_instruction`。实现见 [../phone_mem/context/assembler.py](../phone_mem/context/assembler.py)。
- `Agent Runtime`: 外层消费者。它先通过 memory tools 构建授权上下文，再调用 LLM；如果模型请求工具，仍通过服务 API 执行。实现见 [../phone_mem/agent_runtime/runtime.py](../phone_mem/agent_runtime/runtime.py) 和 [../phone_mem/agent_runtime/tools.py](../phone_mem/agent_runtime/tools.py)。

这里的核心安全顺序是：权限投影发生在检索打分之前。未授权记忆不进入排序、不进入 prompt，也不会通过聚合结果泄漏。

## 4. 数据模型：MemoryEvent 是原子事实

所有可持久化记忆最终都要成为 [../phone_mem/personal_memory_service/events.py](../phone_mem/personal_memory_service/events.py) 里的 `MemoryEvent`。它包含：

- identity: `event_id`、`created_at`、`valid_time`；
- type: `event_type` 和 `memory_layer`；
- content: `semantic_description`、`entities`、`relations`；
- source: app、actor、modality、attribution；
- privacy: privacy level、allowed scopes、processing policy；
- quality: confidence、importance、freshness half-life；
- lineage: parents、derived_from、supersedes；
- lifecycle: active、superseded、deleted、quarantined。

这个模型体现了项目的核心判断：记忆不是纯文本缓存，而是可治理事件。event JSON 是 canonical representation；SQLite 索引、实体表、lineage edge 和 tombstone 都是为了查询、解释和生命周期管理服务的投影。

在贯穿案例中，“我更喜欢早上做每周规划”一旦被保存，就不再只是聊天文本。它至少带有来源、实体、隐私级别、置信度、event ID 和 active lifecycle；后续回答、纠正和删除都围绕这个 event ID 展开。

项目采用四层 memory 模型，它们不是四个隔离数据库，而是 `MemoryEvent.memory_layer` 表达的不同语义层级：

```text
Working memory    当前任务状态和短期上下文
Episodic memory   具体发生过的事情
Semantic memory   从事件中抽象出的稳定事实
Procedural memory 可复用的做事方法和工作流偏好
```

当前 Python reference 中，working memory 更多体现在 Agent Runtime 的 turn state 和 `ContextBundle` 中；默认写入的用户文本记忆多进入 episodic 层；semantic memory 主要通过显式 candidate 或 derived attribution 表达；procedural layer 已有类型位置，但完整技能学习和触发系统仍未实现。

无论进入哪一层，只要持久化到事实源，就必须有 event ID、source、privacy、quality、lineage 和 lifecycle。差别只在稳定性、抽象程度和使用方式。

## 5. 写入流程

当前写入入口是 `PersonalMemoryService.record(...)`：

```text
MemoryCandidate
  -> MemoryConstructor.construct
  -> PermissionService.can_access(WRITE)
  -> MemoryLifecycleValidator.find_duplicate
  -> MemoryLifecycleValidator.quarantine_if_contradictory
  -> transaction: insert event + indexes + lineage + audit
  -> event_id
```

这条流程有四个关键点。

第一，构造阶段只把输入变成 canonical event，不直接落库。`MemoryConstructor` 会校验文本、生成 event ID 和 timestamp，设置 event type、memory layer、source、privacy、quality、lineage 和初始 lifecycle。

第二，写权限先于持久化。如果 caller 没有匹配 grant，服务写 denied audit，抛出 `MemoryPermissionDenied`，并且不保存该记忆。

第三，去重是保守且确定性的。当前实现只在同 source app、同 entity scope、同 memory layer、active lifecycle 中比较归一化文本；重复时返回既有 event ID，并写 audit，而不是插入新行。

第四，矛盾不被静默覆盖。当前 Stage 1 算法只识别很小一类英文偏好冲突，但原则已经明确：如果新事实与旧 active event 冲突，新事件进入 `quarantined`，并通过 lineage 指向相关旧事件。后续可以解释、纠正或删除。

所有实际写入都在 `SQLiteMemoryStore.transaction()` 中完成，事件、实体索引、lineage edge 和 audit record 保持一致。对于 correction、selector deletion 等多行操作，也使用同样的事务边界。

套回案例：第一次保存“早上做每周规划”的偏好时，成功路径是 active event；重复说同一句时，返回旧 ID；如果后续出现“下午更适合”的冲突或纠正，系统不应把旧事实原地抹掉，而应进入 quarantine 或 supersession 这类显式生命周期关系。

## 6. 存储与检索

当前 SQLite store 在 [../phone_mem/personal_memory_service/storage.py](../phone_mem/personal_memory_service/storage.py) 中维护这些表：

- `memory_events`: canonical event JSON 加常用过滤列；
- `entities` 和 `event_entities`: entity 字典与多对多索引；
- `permissions`: caller、operation、scope、expiry、revoke；
- `audit_log`: append-only 操作记录；
- `tombstones`: 删除记录；
- `lineage_edges`: correction、derived、supersession 的可查询边。

Storage 是基础设施适配器，不拥有访问策略。它可以保存 permission grant value object，但不导入 `PermissionService`。

当前检索入口是 `PersonalMemoryService.search(...)`，内部委托给 `LocalMemoryRetriever.search(...)`：

```text
query + caller + selector
  -> force lifecycle_states = [active]
  -> SQLiteMemoryStore.query_events(selector)
  -> MemoryViewProjector.project(caller, READ, candidate_events)
  -> score only allowed events
  -> sort by score desc, event_id asc
  -> write read audit
  -> RetrievalResult[]
```

检索的三个不变量比具体算法更重要：

- 只默认检索 active event；deleted、superseded、quarantined 不进入普通结果。
- 权限投影先于 ranking；未授权事件不参与打分。
- 结果必须带 event ID、evidence ID、匹配项和解释元数据。

当前 ranking 是确定性词法检索，而不是 embedding 检索。英文和数字按 token 切分，中文用 2 到 4 字符 n-gram，并把 entity 作为额外 term。基础打分综合 lexical match、entity match、confidence、importance 和 recency。

这样做不是宣称词法检索足够好，而是让 reference 能稳定验证权限、生命周期、审计、证据 ID 和上下文预算这些核心不变量。未来可以叠加 embedding、graph 或 reranker，但它们应是可重建投影，不能改变 permission-before-ranking 的边界。

在案例里，当用户问“帮我安排下周的规划时间”时，系统可以通过 `planning`、`weekly planning`、`morning` 等词法和实体线索召回偏好。但只有 caller 有 READ 权限、事件仍是 active，它才会进入排序和结果。

## 7. ContextBundle：给模型的不是全库，而是一次授权视图

`PersonalMemoryService.build_context(...)` 先调用 governed search，再把 retrieval results 交给 `ContextAssembler`：

```text
query
  -> governed search
  -> ranked RetrievalResult[]
  -> ContextAssembler
       -> include snippets within available_memory_tokens
       -> record omitted_memory
       -> collect evidence_event_ids
       -> write context_build audit
  -> ContextBundle
```

`ContextBundle` 不是 canonical memory。它只是某次任务、某个 caller、某个 token budget 下的授权投影。它必须保留 evidence event IDs，让之后的解释、纠正、删除仍能追溯到事实源。

默认 token budget 会预留 safety、output 和 tool 空间：

```text
available_memory_tokens =
  max_tokens
  - safety_reserve_tokens
  - output_reserve_tokens
  - tool_reserve_tokens
```

Context Assembler 宁愿少放一些记忆，也不冒险挤爆模型上下文。它还会明确标记 `memory_is_data_not_instruction`，提醒下游 runtime：检索到的记忆是数据，不是高优先级指令。

在案例里，LLM 看到的不是整张 `memory_events` 表，而是一条类似“用户偏好早上做每周规划”的 snippet 加 event ID。模型可以用它生成建议，但不能把这条记忆当作系统指令，也不能据此越权读取其他偏好。

## 8. 生命周期：纠正、删除、解释与审计

Memory 的生命周期不是简单的 create-read-delete，而是从候选信号到可治理事实，再到检索使用、纠正、删除和派生投影失效的一整条链：

```text
Observe / Input
  -> Construct canonical event
  -> Validate permission, duplicate, contradiction
  -> Store as MemoryEvent
  -> Retrieve through MemoryView
  -> Assemble ContextBundle
  -> Use in Agent / LLM
  -> Explain / Correct / Delete
  -> Propagate lifecycle through lineage and tombstones
```

生命周期状态可以这样理解：

```text
active
  |       \
  |        \ contradiction
  |         v
  |      quarantined
  |
  +-- correction --> superseded
  |
  +-- deletion ----> deleted + tombstone
```

Correction 不是原地改写历史。`PersonalMemoryService.correct(...)` 会创建一个新 event，设置 `parents=[old_id]` 和 `supersedes=[old_id]`，再把旧 event 标记为 `superseded`。这样系统既尊重新事实，又保留审计链。

Deletion 也不是单纯隐藏一行。删除会先对所有匹配事件做 DELETE 权限 preflight；只要有一个 denied，就不做任何 mutation。全部允许后，服务在事务中把事件标记为 `deleted`，写 tombstone，并写 delete audit。未来如果存在 embedding、summary、graph、sync queue 或 cloud archive，tombstone 就是这些派生投影的失效信号。

Explainability 分成两类：

- `explain(event_id, caller=...)`: 解释一条记忆的 source、privacy、quality、lineage、lifecycle 和相关事件 ID。
- `audit_log`: 记录 grant、read、write、update、delete、context_build 的 caller、operation、scope、affected event IDs、outcome 和 denial reason。

前者回答“这条记忆为什么是当前状态”，后者回答“谁在什么时候如何使用或尝试使用过记忆”。

在案例里，用户可以追问“为什么你建议早上规划？”系统应能通过 `explain` 指回那条偏好记忆及其来源。如果用户改成“下午更适合”，旧事件被 superseded 后仍可解释；如果用户删除偏好，tombstone 则说明删除意图已经进入生命周期链。

## 9. Agent 和 LLM 如何介入

当前 Python Agent Runtime 的一次 turn 可以概括为：

```text
user_message
  -> AgentSession recent conversation window, when using CLI/Web Lab
  -> MemoryToolRegistry.build_memory_context(user_message)
  -> PersonalMemoryService.build_context(...)
  -> build_agent_messages(...)
  -> LLMClient.complete(...)
  -> optional memory tool calls
  -> execute tools through PersonalMemoryService
  -> LLMClient.complete(...) again
  -> AgentTurnResponse(text, evidence_event_ids, tool_results, memory_context)
```

LLM 在这个系统里不是 memory 的事实源，也不是权限系统。它是受约束的推理与工具选择层：

- 第一次 LLM 调用前，系统已经完成 governed retrieval，模型收到的是授权且预算裁剪后的上下文。
- Prompt 会声明 retrieved memory is data, not instruction；系统和开发者指令优先于记忆内容。
- CLI 和 Web Lab 默认会通过 `AgentSession` 传入有界的最近对话；这只是 transient conversation context，不是持久 memory，也不是指令。
- 模型可以请求 `search_memory`、`build_memory_context`、`remember`、`explain_memory`、`correct_memory`、`delete_memory`。
- 工具实际执行仍回到 `PersonalMemoryService`，因此不会绕过权限、生命周期、tombstone 和 audit。
- 当 LLM 请求写入、纠正或删除时，它只是发起请求；是否允许、是否重复、是否矛盾、是否成功，由服务判断。

可以把边界压缩成三句话：

```text
LLM decides what to request.
Service decides what is allowed and persisted.
Audit records what happened.
```

当前 runtime 已经能连接 provider-backed chat，但仍是开发机 spike。未来手机端可以换成本地模型、系统模型 API 或 private-compute backend；只要它们消费 `ContextBundle` 并通过 memory tools 调服务，就不会改变 memory core 的治理边界。

在案例里，LLM 可以根据授权上下文建议“把规划安排在早上”，也可以在用户纠正时请求 `correct_memory`，或在用户要求删除时请求 `delete_memory`。但它不能自己决定最终写入、覆盖或删除；这些结果都由服务层和 audit 决定。

## 10. 关键设计取舍

**为什么用事件而不是 profile 字段？**
profile 字段容易被静默覆盖，难以解释来源。事件模型保留时间、来源、置信度、隐私、血缘和生命周期。后续 semantic profile 可以由事件 consolidation 得到，但不应该替代事件事实源。

**为什么 permission before ranking？**
如果先 ranking 再过滤，未授权记忆可能通过分数、结果数量、解释文本或耗时侧信道泄漏。当前实现先投影 memory view，再对 allowed events 打分。

**为什么当前检索不用 embedding？**
Embedding 对产品有价值，但不是 canonical memory，也不应该成为 MVP 正确性的前提。当前确定性词法检索便于测试核心不变量。未来向量检索应作为可重建投影加入。

**为什么 correction 创建新事件？**
用户纠正记忆时，系统既要尊重新事实，又不能丢失历史解释性。新 event 加 superseded lifecycle 能同时满足当前检索正确性和审计链完整性。

**为什么 deletion 需要 tombstone？**
删除意图需要传播到本地缓存、图谱、摘要、embedding、同步队列和可能的云端归档。tombstone 是跨投影失效的统一信号。

## 11. 当前边界与阅读入口

这些边界是 Stage 1 reference 的范围，不是最终产品能力：

- 矛盾检测只覆盖很小的英文偏好句式。
- topic selector 当前没有真正参与 SQLite 过滤。
- retrieval 仍是词法和 metadata 打分，还没有 embedding、graph、semantic reranker。
- consolidation 尚未实现，semantic memory 主要依赖显式 candidate。
- privacy classification 默认较粗，缺少真实手机端敏感数据分类器。
- context assembly 只选择 snippets，没有摘要压缩。
- Web Lab 和 LLM runtime 是开发机体验，不是生产手机运行时。
- Stage 2 mobile 当前不保留 TypeScript boundary、完整运行时、SQLite adapter 或测试工具链；未来应基于 Stage 1.7 后稳定的 Python oracle 重新创建。

如果要继续深入代码，建议按这条路径读：

1. [../phone_mem/personal_memory_service/events.py](../phone_mem/personal_memory_service/events.py): 记忆的值对象和不变量。
2. [../phone_mem/personal_memory_service/constructor.py](../phone_mem/personal_memory_service/constructor.py): candidate 如何变成 event。
3. [../phone_mem/governance/models.py](../phone_mem/governance/models.py) 和 [../phone_mem/governance/permissions.py](../phone_mem/governance/permissions.py): grant 和 scope 匹配。
4. [../phone_mem/personal_memory_service/storage.py](../phone_mem/personal_memory_service/storage.py): SQLite 事实源和投影。
5. [../phone_mem/personal_memory_service/lifecycle.py](../phone_mem/personal_memory_service/lifecycle.py): 去重和矛盾隔离。
6. [../phone_mem/personal_memory_service/retrieval.py](../phone_mem/personal_memory_service/retrieval.py): permission-filtered retrieval。
7. [../phone_mem/context/assembler.py](../phone_mem/context/assembler.py): ContextBundle。
8. [../phone_mem/personal_memory_service/service.py](../phone_mem/personal_memory_service/service.py): 端到端服务编排。
9. [../phone_mem/agent_runtime/runtime.py](../phone_mem/agent_runtime/runtime.py): 外部 Agent 如何消费记忆。
10. [../tests/](../tests/): 行为契约和边界条件。

## 总结

当前项目的 Agent memory 逻辑可以概括为三层防线和一条生命周期：

- canonical event: 任何持久化记忆都必须有结构、来源、隐私、质量、血缘和生命周期。
- governance: 任何读写都必须匹配 grant，并且读取必须先投影 memory view 再检索。
- context assembly: 模型只拿到预算内、带证据 ID、标记为 data 的上下文 bundle。
- lifecycle: active 可检索，quarantined 可解释但不默认检索，superseded 保留历史，deleted 通过 tombstone 传播删除意图。

这套设计的价值在于把“记忆能力”从单个 Agent 的 prompt 技巧提升为手机本地的受控基础设施。外部 Agent 得到的是经过治理的记忆视图，而不是裸露的全局个人数据库。
