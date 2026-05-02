# phone-mem

语言：[English](README.md) | 中文

`phone-mem` 是智能手机 Agent Memory 的架构与原型仓库。项目目标是在手机上构建一个以 Agent 方式管理用户 memory 的本地优先系统：它理解并维护用户在手机场景中的长期偏好、事件、上下文和操作习惯，并把这些受控 memory 能力提供给更广泛的 Agent 应用。

当前重点是把《手机端 Agent Memory 架构设计方案》沉淀为可执行的开发上下文：明确产品目标、系统边界、数据模型、安全约束、SDK 形态和阶段路线。

## 快速开始

```bash
uv run python main.py
uv run python scripts/validate_docs.py
uv run python -m unittest discover -s tests
```

## 文档入口

- [ARCHITECTURE.md](ARCHITECTURE.md)：顶层架构地图。
- [AGENTS.md](AGENTS.md)：面向代码 Agent 的工作导航。
- [docs/README.md](docs/README.md)：详细文档索引。
- [docs/design-docs/smartphone-agent-memory.md](docs/design-docs/smartphone-agent-memory.md)：智能手机 Agent Memory 开发设计。
- [docs/references/source-review.md](docs/references/source-review.md)：原 PDF 的深度 review、精华提炼和漏洞澄清。
- [docs/references/research-review-2026.md](docs/references/research-review-2026.md)：结合论文与 Apple/Android 平台资料的 v2 调研依据。

## 当前阶段

项目处于架构落地前的文档化阶段。短期目标是先实现 OS 级 Personal Memory Service 的本地 MVP：统一事件抽象、本地记忆服务、权限视图、审计/删除、基础检索，以及与端侧模型运行时解耦的上下文组装边界。
