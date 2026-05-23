# 架构概念详解

本文档收集 phone memory 框架中算法与架构层面的核心概念，以教学导向的详细解释帮助理解代码背后的设计意图与实现边界。

与 [retrieval-and-context-assembly.md](retrieval-and-context-assembly.md) 和 [AGENT_MEMORY_FLOW_ARCHITECTURE.md](../AGENT_MEMORY_FLOW_ARCHITECTURE.md) 不同，本文档不追求覆盖全部设计，而是聚焦于那些**容易混淆、需要反复回顾的特定知识点**。

## 如何撰写一个 Explainer

每个 explainer 应当回答以下问题：

- 这个概念是什么。
- 为什么对本框架重要。
- 它涉及哪些组件或契约。
- 与更简单或相邻的方案有何区别。
- 它在当前实现中的映射与已知 gap。

---

## Context Window 预算与压缩

### 概念

当 LLM 的上下文窗口接近上限时，系统不能无限制地把检索到的记忆全部塞进 prompt。`ContextBudget` + `ContextAssembler` 构成了一个**显式预算管理**机制，在记忆进入模型前进行分层截断与压缩。

### 为什么重要

手机 Agent 的本地模型通常上下文窗口有限（例如 4K–32K tokens）。如果不做预算管理：
- 检索到的长记忆可能挤爆 prompt，导致模型无法输出或截断系统指令；
- 简单的"全部拼接"策略会让高优先级记忆和低优先级记忆混在一起；
- 开发者无法观测"哪些记忆因为预算被丢弃了"。

本框架采用**宁可少放、不可溢出**的保守策略，让压缩过程可观测、可审计。

### 核心组件

```text
ContextBudget
  max_tokens                    ← 总窗口上限
  - safety_reserve_tokens       ← 系统/安全指令预留
  - output_reserve_tokens       ← 模型输出预留
  - tool_reserve_tokens         ← 工具调用响应预留
  = available_memory_tokens     ← 记忆可用的剩余配额
```

`ContextAssembler` 的工作流程：

1. 遍历 `RetrievalResult`，按检索排名（score 从高到低）依次处理；
2. 用 `TokenCounter` 估算每条 `MemorySnippet` 的 token 成本；
3. 如果 `used_tokens + snippet_tokens > available_memory_tokens`，则**整条丢弃**，记录 `omitted_memory` 及原因 `"budget_exhausted"`；
4. 对**已被选中的 snippets**，额外构建 `HotMemoryCapsule`，使用**独立的 capsule 预算**（默认 64 tokens）；
5. 输出 `ContextBundle`，包含 snippets、capsules、relation paths、token 预算账目和丢弃记录。

### 与相邻方案的区别

| 方案 | 做法 | 本框架的选择 |
|---|---|---|
| **无预算管理** | 全部拼接 | ❌ 不可接受，会溢出 |
| **尾部截断** | 按字符数从末尾切掉 | ❌ 丢失了优先级信息；高排名记忆也可能被截断成半截句子 |
| **动态摘要** | 用 LLM 把长记忆压缩成摘要 | 尚未实现；当前用规则化 capsules 作为占位 |
| **本框架：硬截断 + 分级投影** | 高排名 snippet 保留全文，低排名整段丢弃，capsule 提供存在性信号 | ✅ 确定性、可审计、预算透明 |

### 当前实现映射与已知 Gap

**已实现：**
- `ContextBudget` 的显式预留计算（`phone_mem/context/budgets.py`）
- `ContextAssembler` 的排名遍历与硬截断（`phone_mem/context/assembler.py`）
- `ConservativeTokenCounter` 的保守估算（ASCII 3.5 chars/token，CJK 1.0 char/token，安全系数 1.3）（`phone_mem/context/token_counter.py`）
- Capsule 的独立预算与丢弃记录（`phone_mem/context/capsules.py`）
- Metrics 观测压缩比和丢弃原因（`phone_mem/personal_memory_service/metrics.py`）

**已知 Gap：**
- 当前默认使用字符估算，没有接入 tiktoken 等 provider-specific tokenizer；
- 没有 LLM 动态摘要器，长 episodic 记忆只能被整条丢弃，不能被段落级压缩；
- 对话历史只有固定条数截断（`max_history_messages=8`），没有滚动摘要。

---

## Memory Snippet 与 Hot Memory Capsule 的区别

这是本框架中最容易混淆的一对概念。它们不是"同一事物的两种格式"，而是**同一批记忆在 context 组装流程中的两个不同投影层**。

### Memory Snippet（记忆片段）

**是什么：** 从检索层返回的**原始完整记忆文本**。

```python
@dataclass(frozen=True)
class MemorySnippet:
    event_id: str
    text: str              # ← 原始完整文本，例如 "User prefers morning planning sessions."
    source_app: str
    attribution: str
    confidence: float
    memory_layer: str
    privacy_level: str
    evidence_event_ids: list[str]
```

**角色：** 是 LLM 能直接阅读并据此生成回复的**可消费内容**。在 prompt 中会以完整文本呈现：
```
- event-1: User prefers morning planning sessions. | evidence=['event-1']
```

**预算行为：** 按 `available_memory_tokens` 预算逐一评估；超预算时**整条 omitted**。

### Hot Memory Capsule（热记忆胶囊）

**是什么：** 对**已被选中的 snippets** 进行的**二次压缩投影**。

```python
@dataclass(frozen=True)
class HotMemoryCapsule:
    category: str          # 分类标签
    text: str              # ← 极度压缩后的标签，例如 "Fact." / "Decision."
    evidence_event_ids: list[str]
    confidence: float
    attribution: str
    lifecycle_state: str
    omitted_memory: list[dict[str, str]]
```

**角色：** 设计意图是 **"compact startup projection"**——在对话启动或 snippets 被截断时，给模型一个极简的"记忆类型速览"，同时保留证据链和元数据。

**预算行为：** 拥有**独立的 capsule 预算**（默认 64 tokens），与 snippets 预算隔离。

### 为什么要有两个层

**Snippet 解决"能读到什么"，Capsule 试图解决"还遗漏了什么类型"。**

设想一个场景：
- Token budget 只能容纳 2 条完整 snippet；
- 检索结果有 10 条相关记忆；
- 模型只读了 2 条，但不知道还有 8 条被丢了。

Capsule 的设计意图是告诉模型："除了你读到的 2 条，用户还有若干个 Fact、Decision、Constraint 类的记忆被预算截断了。如果你需要，可以通过工具去查。"

### 关键区别对比

| | **Snippet** | **Capsule** |
|---|---|---|
| **内容** | 原始完整文本 | 分类标签（"Fact." / "Decision." 等） |
| **来源** | 检索层直接产出 | ContextAssembler 对选中 snippets 二次加工 |
| **Token 预算** | 共享 `available_memory_tokens` | 独立预算（默认 64 tokens） |
| **是否可被 LLM 直接用于回复** | ✅ 是 | ⚠️ 仅有标签时难以直接用于回复 |
| **携带 omitted_memory** | ❌ 不携带 | ✅ 携带（记录被预算丢弃的记忆） |
| **当前是否被 prompt builder 消费** | ✅ 是 | ❌ 否（`_serialize_context_bundle` 序列化了它，但 `prompts.py` 未读取） |

### 当前实现中的 Gap 与建议

**最核心的问题：** Capsule 的 `text` 字段当前只有单个词标签，丢失了原始 snippet 的关键词信息，导致 LLM 即使看到 capsule 也无法构造有效查询或做出准确判断。

```python
# 当前实现（capsules.py）
def _capsule_text(self, category: str, snippet: MemorySnippet) -> str:
    if category == "stable_user_confirmed_fact":
        return "Fact."
    if category == "recent_decision":
        return "Decision."
    ...
```

**改进方向：**

1. **关键词保留式摘要**：把 `text` 从 `"Fact."` 改为保留核心名词短语，例如 `"Fact: morning planning preference."`，让 LLM 知道具体内容方向。
2. **分场景消费**：在 prompt builder 中增加 capsule 渲染逻辑——当 `snippets` 非空时，capsules 作为补充元数据；当 `snippets` 为空时，capsules 作为兜底信号。
3. **工具联动**：如果模型支持 function calling，可以设计 prompt 让模型看到 capsule 后主动调用 `retrieve_memory(event_id=...)` 获取完整内容。

### 数据流图示

```text
检索结果 RetrievalResult[]
  │
  ▼
MemorySnippet（原始完整文本）
  │
  ▼
ContextAssembler.build_context()
  │
  ├──► Token Budget 筛选 → ContextBundle.snippets（保留完整文本）
  │      │
  │      └──► 进入 LLM prompt（实际被消费）✅
  │
  └──► HotMemoryCapsuleBuilder 二次压缩 → ContextBundle.hot_memory_capsules
         │
         ├──► text = "Fact." / "Decision."（丢失了具体内容）
         ├──► 保留 evidence_event_ids、confidence、attribution
         └──► 序列化到 ContextBundle，但 prompt builder 未读取 ⚠️
```

---

## ContextBundle 的三类模型可消费材料

### 概念

`ContextBundle` 不是记忆的全集，而是**某次任务、某个 caller、某个 token budget 下的授权投影**。它包含三类互补的材料：

1. **Snippets**：具体可读的完整记忆文本（当预算充足时最有价值）。
2. **Hot Memory Capsules**：从已选 snippets 压缩出的类型标签与元数据（试图提供存在性信号，但目前内容过度压缩）。
3. **Relation Paths**：从关系图投影中选出的有界路径（如 `Person --assigned_to--> Project --solved_by--> Task`），把多跳关系压缩为单条上下文。

### 为什么分三类

记忆不只是"一段段文本"。它还有：
- **事实内容**（snippets）
- **类型与重要性信号**（capsules 试图承载）
- **实体间关系**（relation paths）

例如：
> "Mira 负责 Project Atlas，该项目通过刷新凭证解决了同步失败问题。"

这句话如果拆成三条 snippets，模型需要自行推理关联。而 relation path 可以直接给出：
```
nodes: ["Mira", "Project Atlas", "credential refresh"]
edges: ["person_assigned_to_project", "solved_by"]
```

### 统一契约

无论哪一类材料，都必须保留 `evidence_event_ids`，保证：
- **可解释**：能回答"你为什么这么说？"
- **可纠正**：用户说"不对，是下午不是早上"时，能定位到具体 event。
- **可删除**：删除请求能精确命中事实源，并触发 tombstone 传播。

### 当前实现映射

| 材料 | 实现状态 | 备注 |
|---|---|---|
| Snippets | ✅ 完整实现 | 含 budget 硬截断、omitted_memory 记录 |
| Capsules | ⚠️ 骨架实现 | 分类与预算逻辑已就绪，但 text 过度压缩，且 prompt builder 未消费 |
| Relation Paths | ✅ 已实现 | 含 compression_score 和 evidence_event_ids，作为 auditable context 接受 |

---

## 保守 Token 估算策略

### 概念

`ConservativeTokenCounter` 是一个**故意高估**的 token 计数器，用来在无法获取真实 tokenizer 时做安全兜底。

```python
class ConservativeTokenCounter:
    ascii_chars_per_token: float = 3.5      # 比真实值更保守
    non_ascii_chars_per_token: float = 1.0  # CJK 中文按 1 字符 1 token 算，极度保守
    safety_multiplier: float = 1.3          # 整体再乘 1.3
    overhead_tokens: int = 8                # 每条 snippet 额外加 8 token 开销
```

### 为什么故意高估

本框架的核心假设是：**宁可少放记忆，也不能挤爆上下文导致模型失败。**

高估的结果：
- 实际占用 10 tokens 的 snippet 可能被估算为 15 tokens；
- 系统会更早触发 `"budget_exhausted"`；
- 低排名记忆被丢弃，但高排名记忆保留完整且安全。

### 与精确 tokenizer 的关系

```text
运行时适配层
  ├── 有真实 tokenizer（如 tiktoken）→ 注入精确计数器
  └── 只有模型 URL 或未知 provider → 使用 ConservativeTokenCounter 兜底
```

当前 Python reference 中只实现了兜底版，真实 tokenizer 注入点是预留的（`TokenCounter` 接口），尚未有具体适配。
