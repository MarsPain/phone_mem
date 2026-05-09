# phone-mem

语言：[English](README.md) | 中文

`phone-mem` 是智能手机 Agent Memory 的架构与原型仓库。项目目标是在手机上构建一个以 Agent 方式管理用户 memory 的本地优先系统：它理解并维护用户在手机场景中的长期偏好、事件、上下文和操作习惯，并把这些受控 memory 能力提供给更广泛的 Agent 应用。

仓库现在包含已完成的确定性 Python 参考版 Personal Memory Service、已完成的 Stage 1.5 Python LLM Agent runtime spike、已完成的 Stage 1.6 本地 Python Web Lab，以及正在进行的 Stage 1.7 Python-only agentic memory lifecycle maturation 计划。Stage 1.5 用真实 provider-backed chat 验证受治理 memory API 上的 Agent 体验；Stage 1.6 在浏览器里提供 chat、memory inspection 和 turn debugging；Stage 2 移动端实现会等 Python oracle 稳定并且单独移动端计划被接受后再启动，旧的 mobile TypeScript boundary files 不再保留。

## 现在已有能力

- `phone_mem.personal_memory_service`：canonical event 构造、SQLite 存储、受治理搜索、修正、删除、审计、生命周期解释和指标。
- `phone_mem.context`：runtime-neutral context bundle 组装和 token/budget 统计。
- `phone_mem.governance`：permission scope、memory view、audit record 和访问检查。
- `phone_mem.agent_runtime`：provider-neutral Agent runtime contract、memory tools、prompt assembly 和 OpenAI-compatible client adapter。
- `phone_mem.web_lab`：本地浏览器实验台，支持 chat、memory inspection、context preview、修正、删除、审计、指标和 turn debugging。
- `docs/exec-plans/active/`：当前 Stage 1.7 Python Agentic Memory Lifecycle Maturation 计划。

## 快速开始

先用 `uv` 安装依赖，然后运行确定性检查：

```bash
uv run python main.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

运行不调用 LLM provider 的确定性 demo：

```bash
uv run python examples/agent_memory_demo.py
uv run python examples/agent_memory_repl.py
uv run python examples/python_reference_walkthrough.py
uv run python examples/file_backed_sqlite_walkthrough.py
uv run python examples/retrieval_selector_walkthrough.py
```

运行 provider-backed Agent 体验：

```bash
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/llm_agent_chat.py
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/web_lab.py --reload
```

Web Lab 默认把本地开发 memory 存在 `.phone-mem-lab/memory.sqlite3`。Python reference 保持 local-first 和 deterministic；provider 调用只存在于 Agent runtime/demo 边界。

## 架构速览

Python reference 是未来移动端对齐的 executable oracle。`PersonalMemoryService` 负责 durable memory events、permissions、audit、tombstones、retrieval 和 lifecycle operations。`context` 把受治理 retrieval 结果转换成 runtime-neutral bundles。`agent_runtime` 让 chat Agent 通过 scoped tools 使用 memory，同时避免 memory core 依赖任何 provider。`web_lab` 用本地开发 UI 暴露同一套 service 和 runtime。

外部 Agent 应消费 governed views 和 context bundles，而不是 raw global memory store。未来 phone runtime 应保留这条边界，并把 Python infrastructure 替换为 mobile-native storage、permissions 和 runtime integration。

## 文档入口

- [ARCHITECTURE.md](ARCHITECTURE.md)：顶层架构地图。
- [AGENTS.md](AGENTS.md)：面向代码 Agent 的工作导航。
- [docs/README.md](docs/README.md)：详细文档索引。
- [docs/PYTHON_REFERENCE.md](docs/PYTHON_REFERENCE.md)：Python 参考服务使用与维护指南。
- [docs/design-docs/python-llm-agent-runtime.md](docs/design-docs/python-llm-agent-runtime.md)：Python LLM Agent runtime 设计。
- [docs/design-docs/python-web-lab.md](docs/design-docs/python-web-lab.md)：Stage 1.6 本地 Web Lab 设计。
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md)：智能手机 Agent Memory 开发设计。
- [docs/references/source-review.md](docs/references/source-review.md)：原 PDF 的深度 review、精华提炼和漏洞澄清。
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md)：结合论文与 Apple/Android 平台资料的 v2 调研依据。

## 当前阶段

Stage 1、Python reference maturation track、Stage 1.5 Python LLM Agent runtime spike 和 Stage 1.6 Python Web Lab 已完成。Stage 1.7 Python Agentic Memory Lifecycle Maturation 当前处于 active 状态。`phone_mem/` 下的 Python 代码仍是未来移动端对齐的 executable oracle；active plan 会先深化 runtime memory protocol、governed session capture、hot capsules、hybrid retrieval、relation projections、maintenance workflows、quality metrics 和 future-mobile fixtures。

Stage 2 移动端实现仍处于 deferred 状态。仓库目前不保留 mobile TypeScript boundary、React Native app、移动端 SQLite adapter 或 TypeScript 测试工具链。未来移动端工作应基于 Stage 1.7 完成后的稳定 Python oracle 重新创建这些边界。

当前 active、completed 和 deferred 的计划见 [docs/PLANS.md](docs/PLANS.md)。
