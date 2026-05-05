# phone-mem

语言：[English](README.md) | 中文

`phone-mem` 是智能手机 Agent Memory 的架构与原型仓库。项目目标是在手机上构建一个以 Agent 方式管理用户 memory 的本地优先系统：它理解并维护用户在手机场景中的长期偏好、事件、上下文和操作习惯，并把这些受控 memory 能力提供给更广泛的 Agent 应用。

仓库现在包含已完成的确定性 Python 参考版 Personal Memory Service，以及未来移动端 runtime 所需的架构上下文。当前 active track 是 Stage 1.5 Python LLM Agent runtime spike，用真实 provider-backed chat 验证受治理 memory API 上的 Agent 体验；Stage 2 移动端实现会等单独计划被接受后再启动。

## 快速开始

```bash
uv run python main.py
uv run python examples/agent_memory_demo.py
uv run python examples/agent_memory_repl.py
OPENAI_API_KEY=... PHONE_MEM_LLM_MODEL=gpt-4.1 uv run python examples/llm_agent_chat.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

## 文档入口

- [ARCHITECTURE.md](ARCHITECTURE.md)：顶层架构地图。
- [AGENTS.md](AGENTS.md)：面向代码 Agent 的工作导航。
- [docs/README.md](docs/README.md)：详细文档索引。
- [docs/PYTHON_REFERENCE.md](docs/PYTHON_REFERENCE.md)：Python 参考服务使用与维护指南。
- [docs/design-docs/python-llm-agent-runtime.md](docs/design-docs/python-llm-agent-runtime.md)：Python LLM Agent runtime 设计。
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md)：智能手机 Agent Memory 开发设计。
- [docs/references/source-review.md](docs/references/source-review.md)：原 PDF 的深度 review、精华提炼和漏洞澄清。
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md)：结合论文与 Apple/Android 平台资料的 v2 调研依据。

## 当前阶段

Stage 1 和 Python reference maturation track 已完成。`phone_mem/` 下的 Python 代码现在是未来移动端对齐的 executable oracle。当前 Stage 1.5 实现新增了独立的 `phone_mem.agent_runtime` 边界，用于真实 LLM API demo，同时保持 memory core 不依赖 provider。

Stage 2 移动端实现仍处于 deferred 状态。仓库目前只有 TypeScript boundary files 和由 Python reference 支撑的 contract fixtures，还没有 React Native app、移动端 SQLite adapter 或 TypeScript 测试工具链。
