# Directory Map (Readable)

## 这份文档是干什么的

`docs/DIRECTORY_MAP.md` 的核心作用是解释一个常见疑问：

- 为什么 `skills/adas/` 和 `skills/automotive-adas/` 看起来像重复？
- 它们到底有什么分工？

一句话：**不重复，它们是两种不同层级的内容。**

---

## 先记住这个总图

仓库里 `skills/` 下面主要有两类内容：

1. `skills/{domain}/`  
   例如 `skills/adas/`、`skills/diagnostics/`
2. `skills/automotive-{domain}/`  
   例如 `skills/automotive-adas/`、`skills/automotive-safety/`

---

## 两类目录的区别（最重要）

### A. `skills/{domain}/`（基础技能层）

- 文件格式：主要是 `.yaml`
- 目标：覆盖面广（很多细分主题）
- 用途：快速检索、规则化、可被工具解析校验
- 适合谁：新人入门、需求梳理、标准条款对齐

你可以把它理解为：**技能索引库/能力卡片库**。

### B. `skills/automotive-{domain}/`（专家实践层）

- 文件格式：主要是 `.md`
- 目标：深度实践（实现思路、架构、示例代码）
- 用途：给工程实现提供参考模板
- 适合谁：需要落地方案的人（开发、架构、安全、测试）

你可以把它理解为：**专家指南库/实现参考库**。

---

## 常见目录怎么对应

| 基础目录 | 专家目录 | 如何配合使用 |
|---|---|---|
| `skills/adas/` | `skills/automotive-adas/` | 先看 YAML 明确任务，再看 MD 拿实现思路 |
| `skills/diagnostics/` | `skills/automotive-diagnostics/` | 先做协议/需求梳理，再看诊断流程与示例 |
| `skills/safety/` | `skills/automotive-safety/` | 先看术语与结构，再看 HARA/FMEA 等实操 |
| `skills/v2x/` | `skills/automotive-v2x/` | 先分场景，再看系统级方案 |

> 注意：不是每个基础目录都有 `automotive-*` 对应目录。

---

## 推荐阅读顺序（新人友好）

1. 先读 `skills/{domain}/xxx.yaml`  
   明确：这是在解决什么问题、约束和标准是什么。
2. 再读 `skills/automotive-{domain}/xxx.md`  
   看：可落地的设计思路、代码框架、测试方式。
3. 结合你们项目做裁剪  
   把示例改成你们真实 ECU、工具链、流程约束。

---

## 如何判断一个文件“值不值得直接用”

- 可以直接复用的：结构化模板、检查清单、通用流程骨架
- 需要验证后再用的：代码片段、性能指标、供应商/平台相关参数
- 必须二次确认的：安全、合规、认证相关结论（ISO 26262 / ISO 21434 / ASPICE 等）

---

## 原版文档和本版的关系

- 原版：`docs/DIRECTORY_MAP.md`（信息完整，细节多）
- 本版：`docs/DIRECTORY_MAP_READABLE.md`（快速理解，适合新人）

如果你是第一次接触这个仓库，先读本版，再回到原版查细节。
