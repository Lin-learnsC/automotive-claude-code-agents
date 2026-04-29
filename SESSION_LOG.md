# Automotive Claude Code Agents — 学习进度日志

> **项目性质**: 汽车行业首个以 Agent 为主导的自动驾驶/新能源领域工具开源仓库  
> **项目来源**: 博世工程师整理发布，中国开发者补充 ADAS/新能源行业标准  
> **学习者**: [Lin]  
> **学习策略**: 分阶段模块化学习，子代理隔离，避免上下文爆炸

---

## 📋 学习路线图

| 阶段 | 主题 | 状态 | 关键产出 |
|------|------|------|---------|
| **P0** | 仓库框架层（建立地图） | ✅ 完成 | 仓库导航图、目录结构理解 |
| **P1** | 核心机制解剖 | ✅ 完成 | ToolRouter + Agent 编排四层模型 |
| **P2** | 领域按需深入 | 🔄 进行中 | AUTOSAR 生态深度分析 |
| **P3** | 工程实践强化 | 🔄 进行中 | 编译、测试、修复、扩展 |
| **P4** | 贡献与定制 | ⏳ 未开始 | 自定义 Agent、Skill、Adapter |

---

## 📝 会话日志

### Session 1 — 仓库地图建立 + 核心机制解剖

**日期**: 2026-04-21  
**时长**: ~2 小时  
**模式**: 探索 + 修复 + 深度分析

#### 完成内容

**1. 仓库架构全景扫描**
- 读取核心入口文件：`CLAUDE.md`、`Makefile`、`docs/DIRECTORY_MAP.md`
- 理解 Skills 双重结构：`skills/{domain}/` (YAML, ~4600个) vs `skills/automotive-{domain}/` (Markdown, ~70个)
- 子代理扫描确认：`agents/` (~32域)、`commands/` (~34类)、`workflows/` (~24种)、`tools/` (~15个Python模块)
- **关键认知**: 这不是传统程序，而是 Claude Code 的"扩展包"，通过 `./install.sh` 安装到 `~/.claude/`

**2. Examples 调研（Network Topology）**
- 目标: `./setup.sh` 一键启动 5 容器 ECU 网络拓扑
- **环境限制**: 当前云环境缺少 Docker + sudo，无法实际运行
- 完成 `setup.sh` 逐行推演（Dry Run），输出预期执行流程和拓扑图
- 提供本地运行指南（复制粘贴即可复现）
- **替代方案**: `test-virtual-network.py` 纯 Linux namespace 版本（需 sudo）

**3. ECU-BMS 编译修复与测试（核心工程实践）**
- 目标: 编译 `examples/ecu-bms/` 并运行单元测试
- **发现问题**: 原始代码存在 5 个编译/逻辑错误，无法通过 `-Werror` 编译
- **修复详情**:
  - `cell_monitor.c:36`: `int16_t` 溢出 → 改为 `int32_t`
  - `cell_monitor.c:250`/`cell_monitor.h:87`: 返回类型不一致 → 统一为 `CellFaultFlags_t`
  - `cell_monitor.c:68-75`: 枚举定义从 `.c` 移到 `.h`
  - `cell_monitor.c:286`: **运行时 int32 乘法溢出** (`3200 * 1000000` 溢出) → 使用 `int64_t` 中间计算（最关键修复）
  - `soc_estimator.c:29,33`: `uint16_t/int16_t` 赋值 1000000 溢出 → 改为 `uint32_t/int32_t`
  - `Rte_BMS.c`: `clock_gettime` 隐式声明 → 添加 `_POSIX_C_SOURCE 199309L`
  - `test_cell_monitor.c`: 测试函数缺少原型 → 添加 `static` 前向声明
  - `Makefile`: `build/test_unit` 目录未创建 → 添加 `mkdir`
- **新增 `src/main.c`**: 补充缺失的 ECU 入口程序，支持仿真运行
- **编译结果**:
  - `build/bms_ecu.elf` (83KB)
  - `build/bms_ecu.bin` (16KB)
  - `build/bms_ecu.hex` (19KB)
  - `build/bms_ecu.map` (44KB)
- **单元测试**: 8/8 全部通过

**4. SOC Estimator 单元测试补充**
- 目标: 为 `soc_estimator.c` 编写独立单元测试（原仓库仅 cell_monitor 有测试）
- **新增文件**: `tests/unit/test_soc_estimator.c` (7个测试用例)
- **Mock 技术**: `Rte_GetTimeMs()` 改为 `__attribute__((weak))`，测试文件覆盖为可控的 mock 时间
- **Makefile 改进**: 支持多测试可执行文件（`test_runner_cell_monitor`、`test_runner_soc_estimator`）
- **测试结果**: 7/7 全部通过
- **覆盖率**: `soc_estimator.c` 行覆盖率达到 **94.32%**

**5. 核心机制解剖（ToolRouter + Agent 编排）**
- 读取 `tools/tool_router.py` 完整源码 (322行)
- 子代理完成 `agents/` 架构报告和 `tools/` 层报告
- **输出四层运行时模型**:
  - Layer 1: 工具基础设施（ToolRouter Singleton + Adapter 模式）
  - Layer 2: Agent 执行层（声明式 YAML/Markdown）
  - Layer 3: 智能编排层（Skill Router → LLM Council → Workflow Orchestrator）
  - Layer 4: 用户交互层（Claude Code CLI）
- **关键发现**:
  - ToolRouter 策略: `auto` 优先商业工具 → fallback 开源工具
  - LLM Council: Claude vs GPT 辩论，5轮深度评审（Safety Critical场景）
  - 编排三层: Core Infrastructure → Orchestration Patterns → Workflow Orchestrators
  - 安全冲突裁决: `safety_always_wins`（ASIL 优先级 > 性能优化）
  - **无持久化 Agent Runtime**: 声明式配置，安装时激活，依赖 Claude Code CLI 消费
  - `automotive-claude-code-agents/agents/` 是嵌套生成的子集，与根目录 `agents/` 存在冗余

#### 深度问答

**Q: 为什么电压计算使用有符号整型（int64_t）而不是无符号整型？**  
A: 核心原则是"**存储用无符号（省空间），计算用有符号（保安全）**"。原因包括：
1. 校准偏移 `CAL_AdcOffset_mV` 可能为负数
2. 无符号溢出是定义行为（静默回绕），有符号溢出可被编译器捕获（`-Werror`）
3. MISRA C / ISO 26262 要求故障可检测，无符号静默回绕不符合安全原则
4. 中间变量生命周期极短，对 RAM 影响可忽略

#### 修改文件汇总

本次会话共修改/新增 **11 个文件**:

```
M  examples/ecu-bms/src/application/cell_monitor.c
M  examples/ecu-bms/src/application/cell_monitor.h
M  examples/ecu-bms/src/application/soc_estimator.c
M  examples/ecu-bms/src/rte/Rte_BMS.c
M  examples/ecu-bms/tests/unit/test_cell_monitor.c
M  examples/ecu-bms/Makefile
A  examples/ecu-bms/src/main.c
A  examples/ecu-bms/tests/unit/test_soc_estimator.c
A  SESSION_LOG.md (本文件)
```

---

## 🎯 下一步计划（待办）

### 近期（下一次会话）
- [ ] **P2 领域深入**: 选择 ADAS / AUTOSAR / Battery / Safety 之一，提取最小知识集
- [ ] **P3 工程强化**: 为 `soc_estimator.c` 补充 EKF 收敛测试、大电流放电测试
- [ ] **P3 工程强化**: 交叉编译到 ARM (`make TARGET=arm`)，需要安装 `gcc-arm-none-eabi`

### 中期（未来 2-3 次会话）
- [ ] **P3 工程强化**: 修复 `examples/automotive_protocols_demo.py` 的 `NameError`（缺少 `from typing import Dict`）
- [ ] **P4 贡献定制**: 基于 `skills/_templates/agent-template.yaml` 创建自定义 Agent（如"电池热管理工程师"）
- [ ] **P4 贡献定制**: 手写一个极简工具 Adapter（如 Vector CANoe Adapter），理解 BaseToolAdapter 模式
- [ ] **P1 核心深化**: 运行 `tests/llm-council/test_debate.py`，观察多模型辩论机制

### 长期
- [ ] 在本地 Docker 环境运行 `examples/network-topologies/setup.sh`
- [ ] 尝试 `./install.sh --project` 将框架安装到实际项目中体验
- [ ] 为这个仓库贡献 PR（修复已知问题或补充测试）

---

## 🔗 关键速查

### 常用命令
```bash
# BMS 编译与测试
cd examples/ecu-bms
make clean all        # 编译 ELF/BIN/HEX
make test             # 运行所有单元测试
./build/bms_ecu.elf   # 运行仿真

# 仓库结构速查
make help             # 查看所有 make 目标
python -m tools.tool_router --list    # 列出工具适配器
```

### 核心文件地图
| 目标 | 文件 |
|------|------|
| 理解项目总览 | `CLAUDE.md` |
| 理解目录结构 | `docs/DIRECTORY_MAP.md` |
| 理解技能双重结构 | `skills/` + `skills/automotive-*/` |
| 理解工具路由 | `tools/tool_router.py` |
| 理解 LLM 辩论 | `tools/llm_council.py` |
| 理解适配器模式 | `tools/adapters/base_adapter.py` |
| 理解 Agent 模板 | `skills/_templates/agent-template.yaml` |
| 理解编排模式 | `agents/orchestration/parallel-experts.yaml` |

### 学习原则
1. **子代理隔离**: 复杂调研用 `explore` 子代理，主上下文只保留结论
2. **显式限定范围**: 每次只聚焦一个目录或一个文件
3. **分块读取**: 大文件用行号限定，先读入口逻辑
4. **先问地图，再问细节**: 先列文件名，再决定深入哪个

---

### Session 2 — Claude Code 绑定性分析与跨平台迁移可行性

**日期**: 2026-04-21（Session 1 续接）  
**时长**: ~1 小时  
**模式**: 架构分析 + 源码验证

#### 完成内容

**1. 核心问题：此仓库是否与 Claude Code 强绑定？能否用 Codex/Kimi 替代？**
- **结论**: 与 Claude Code 是**"生态绑定"，不是"技术绑定"**
- 核心资产（YAML Agent、Markdown Skill、Python ToolRouter）是**平台无关的**

**2. 四层绑定分析（基于源码证据）**

| 层级 | 绑定强度 | 证据 | 迁移成本 |
|------|---------|------|---------|
| **安装层** | 🔴 强 | `install.sh` 硬编码 `~/.claude/` 目录 | 高（需重写安装脚本） |
| **Agent 格式层** | 🟢 弱 | 纯自定义 YAML/Markdown，无 Claude 特有 frontmatter | 低（直接复用） |
| **ToolRouter 层** | 🟢 无 | 纯 Python，不依赖任何 Claude API | 零（独立运行） |
| **LLM Council 层** | 🟡 中等 | 设计了 `ModelAdapter` 抽象基类，但只实现了 Claude/GPT | 低（新增 Adapter 约 50 行） |

**3. 关键源码验证**
- `.codex` 文件：**空文件（0 字节）**，说明有计划支持 Codex 但未实现
- `grep` 全仓库：**无任何对 Kimi/DeepSeek/Cursor IDE 的引用**
- `agents/autosar/architect.yaml`: 纯通用 YAML schema
- `agents/adas/adas-perception-engineer.md`: 纯 Markdown，无 Claude 特有语法
- `tools/llm_council.py`: `class ModelAdapter(ABC)` 已抽象，仅 `ClaudeAdapter` + `GPTAdapter` 有实现

**4. 迁移可行性矩阵**

| 目标平台 | 可行性 | 关键障碍 |
|---------|--------|---------|
| Claude Code | ✅ 原生 | 直接使用 |
| Kimi | 🟡 可行 | 需写 `KimiAdapter` + 适配安装目录 + Agent 加载机制 |
| Codex | 🟡 可行 | Codex 偏代码补全，缺乏 Agent 编排；需转 prompt 模板 |
| Cursor | 🟡 可行 | 可映射为 `.cursorrules` / system prompts |
| ChatGPT Plugin | 🟡 可行 | 需开发 Plugin，ToolRouter 可作 backend |
| 自研 IDE 插件 | ✅ 可行 | 工作量大，但技术完全独立 |

**5. 最小迁移路径（以 Kimi 为例）**
- Step 1: 写 `KimiAdapter(ModelAdapter)`（~50 行，Kimi 兼容 OpenAI API 格式）
- Step 2: 重写 `install-kimi.sh`（修改 `TARGET_DIR`）
- Step 3: Agent 调用适配（Kimi 无本地 Agent 目录，需用知识库/工具调用）
- Step 4: Skill 批量导入（Kimi 长上下文优势：可一次加载全部 70+ expert docs）

**6. 核心洞察**
> 仓库的真正价值不是 `install.sh` 或 `~/.claude/` 绑定，而是：
> 1. **4600+ YAML skills + 70+ expert docs**（汽车行业首个系统化 AI 知识库）
> 2. **ToolRouter + BaseToolAdapter**（商业/开源工具链统一接口）
> 3. **工程流程模板**（V-Model、SAFe、Scrum 的 YAML 定义）

#### 新增待办

- [ ] **P4 贡献定制**: 为 LLM Council 写 `KimiAdapter`（验证多模型扩展性）
- [ ] **P4 贡献定制**: 写 `install-kimi.sh` 安装脚本（验证跨平台安装）
- [ ] **P4 贡献定制**: 把 Agent Markdown 批量转成 Kimi 知识库格式

---

---

### Session 3 — 跨平台迁移 Kimi（Session 2 续接）

**日期**: 2026-04-25  
**模式**: 工程实现 + 验证

#### 完成内容

**1. `KimiAdapter` 集成到 LLM Council**
- 新增 `KimiAdapter(ModelAdapter)` 类（~95 行），使用标准 `openai.OpenAI` 客户端
- Endpoint: `https://api.moonshot.cn/v1`，环境变量 `KIMI_API_KEY`
- 支持 ResponseCache、token 统计、异常处理，与 `ClaudeAdapter`/`GPTAdapter` 保持接口一致
- 新增 `DEFAULT_KIMI_CONFIG`，模型名 `kimi-latest`，strengths 针对长上下文和中文技术文档优化

**2. `LLMCouncil` 动态 secondary provider 支持**
- 修改 `__init__`：根据 `gpt_config.provider` 自动选择 `GPTAdapter` 或 `KimiAdapter`
- 引入 `primary_label` / `secondary_label` 属性，替换所有硬编码的 "GPT-5.4" 和 "Claude Opus 4.6"
- 受影响的方法（全部完成替换）：
  - `debate()` 中的系统提示构建
  - `_build_messages()` 中的辩论上下文传递
  - `_synthesize_decision()` 中的合成提示
  - `_build_synthesis_prompt()` 中的历史记录渲染
- CLI 新增 `--secondary-provider {gpt,kimi}` 参数，默认 `gpt`
- **向后兼容**：不传参数时行为与之前完全一致（Claude vs GPT）

**3. `tools/convert_to_kimi.py` — 批量转换工具**
- Agent YAML → Kimi Skill 目录（`SKILL.md` + frontmatter）
- Agent Markdown → Kimi Skill 目录（保留内容，调整 frontmatter）
- `skills/automotive-*/` → Kimi Skill 目录（合并 expert docs）
- `--bundle-web` 模式：生成单文件知识库（~3.5 MB，115k 行），可直接上传 Kimi Web/App
- 测试结果：
  - Agents: **218** 个转换成功
  - Skills: **19** 个转换成功
  - Web Bundle: **3528 KB**

**4. `install-kimi.sh` — 跨平台安装脚本**
- 自动检测 Kimi Code CLI skills 目录（支持 VS Code 扩展路径、Python site-packages、~/.kimi/skills）
- 安装模式：
  - 本地安装：`~/.kimi/automotive-skills/`（默认）
  - IDE 集成：`--kimi-cli-dir <path>`（直接写入 Kimi Code CLI skills 目录）
  - 网页版：`--export-web`（生成 `kimi-web-kb.md`）
- 支持 `--dry-run`、`--status`、`--uninstall`
- Dry-run 验证通过，正确检测到 Kimi Code CLI 路径

**5. 源码验证**
- `python3 -m py_compile tools/llm_council.py` → **Syntax OK**
- `python3 tools/convert_to_kimi.py --dry-run`（逻辑验证）→ 输出结构正确
- `install-kimi.sh --dry-run` → 检测路径、计数、提示信息全部正确

#### 核心洞察

> 本次迁移验证了 Session 2 的结论：**生态绑定 ≠ 技术绑定**。
> 
> 实际工作量：
> - `KimiAdapter`：~95 行（Kimi 兼容 OpenAI API 格式，复用成本低）
> - `LLMCouncil` 动态化：~8 处修改（全部是最小侵入式标签替换，字段名保留兼容）
> - 转换工具：~280 行 Python
> - 安装脚本：~270 行 Bash
> 
> **总迁移成本远低于预期**，核心原因：
> 1. `ModelAdapter` 抽象基类设计良好，新增 provider 只需实现一个方法
> 2. Agent/Skill 内容纯 Markdown/YAML，无 Claude 特有语法
> 3. Kimi 的 OpenAI-compatible API 让 adapter 实现几乎零额外工作

#### 新增待办（已部分完成）

- [x] **P4 贡献定制**: 为 LLM Council 写 `KimiAdapter`（验证多模型扩展性）
- [x] **P4 贡献定制**: 写 `install-kimi.sh` 安装脚本（验证跨平台安装）
- [x] **P4 贡献定制**: 把 Agent Markdown 批量转成 Kimi 知识库格式
- [ ] **P3 工程强化**: 运行 `llm_council.py --secondary-provider kimi` 进行真实端到端辩论测试（需 Kimi 开放平台 `sk-...` API Key）
- [x] **P3 工程强化**: 为 `KimiAdapter` 补充单元测试（mock OpenAI client）

---

### Session 4 — KimiAdapter Mock 单元测试（Plan Mode 续接）

**日期**: 2026-04-25（Session 3 续接）  
**模式**: Plan Mode → 工程实现

#### 完成内容

**1. `tests/unit/test_kimi_adapter.py` — 完整 Mock 测试套件**
- 使用 `unittest.mock.patch("openai.OpenAI")` 模拟 OpenAI 客户端
- **12 个测试用例，全部通过**（`pytest -v` 验证）

| 测试类 | 用例数 | 覆盖场景 |
|--------|--------|---------|
| `TestKimiAdapterSuccess` | 2 | 正常返回文本/耗时、消息格式验证 |
| `TestKimiAdapterCache` | 3 | 缓存命中（duration=0）、miss→hit、无缓存模式 |
| `TestKimiAdapterErrorHandling` | 2 | API 错误日志+re-raise、OpenAI 初始化错误传播 |
| `TestKimiAdapterTokenTracking` | 3 | Token 累计、stats 字典、缺失 usage 属性 |
| `TestKimiAdapterConfiguration` | 2 | endpoint 配置、缺失 API Key 报错 |

**2. 测试关键发现**
- `KimiAdapter.client` 使用懒加载（lazy import），`patch("tools.llm_council.OpenAI")` 无效，必须 `patch("openai.OpenAI")`
- `client` property 初始化时会调用 `_get_api_key()`，测试中需通过 `patch.dict(os.environ, {"KIMI_API_KEY": "sk-dummy"})` 提供虚拟 Key
- 缓存逻辑验证：`ResponseCache` 的 hit/miss 行为与 `KimiAdapter` 正确集成

**3. Git 提交**
- Commit: `ece3655` — 为KimiAdapter补充Mock单元测试，验证消息格式、缓存、错误处理和Token统计

#### 待办状态更新

- [x] P4: `KimiAdapter`（验证多模型扩展性）
- [x] P4: `install-kimi.sh`（验证跨平台安装）
- [x] P4: Agent Markdown 批量转换
- [x] P3: `KimiAdapter` Mock 单元测试
- [ ] P3: 真实端到端辩论测试（需开放平台 API Key）

**额外完成（Session 3 续接）**

**6. Kimi Code CLI 实际部署**
- 目标：`install-kimi.sh --kimi-cli-dir <Kimi CLI skills 目录>`
- 结果：**286 个 skills/agents** 成功安装到 Kimi Code CLI
- 安装路径：`.../kimi_cli/skills/automotive/`
- 覆盖领域：ADAS、BMS、AUTOSAR、Cybersecurity、Functional Safety、SDV 等 32+ 域
- 验证：`ls` 确认 286 个目录全部写入，SKILL.md 格式正确
- **无需 API Key**，消耗 Token Plan 额度即可使用

**7. 网络问题排查记录**
- 初始错误：`SSL WRONG_VERSION_NUMBER` + `api.moonshot.cn` 解析到 `198.18.0.69`（保留测试 IP）
- 根因：代理软件劫持了 WSL2 DNS/流量
- 解决：关闭 VPN 后 DNS 恢复正常，curl 返回 `401 Unauthorized`（网络通，仅缺 Key）

**8. Token Plan vs 开放平台 API 区分**
- Token Plan：支持 Kimi 网页版 / App / Kimi Code CLI（官方产品，共享额度）
- 开放平台 API：独立计费，需 `sk-...` Key，用于程序化调用（如 `KimiAdapter`）
- 当前部署使用 Token Plan 路径，LLM Council API 路径代码已就绪，后续只需申请 Key

---

*最后更新: 2026-04-25*  
*本次会话结束。下次建议从 "P2 领域深入（ADAS/AUTOSAR/Battery 任选）" 或 "申请开放平台 API Key 跑端到端辩论测试" 开始*

