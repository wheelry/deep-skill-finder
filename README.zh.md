<div align="center">

# deep-skill-finder : [deepskill.market](https://www.deepskill.market?ref=github)

**真测, 真评价, 找到真好用的技能**

*面向AIAgent真实场景的Skill Market。通过专业检索+理解，结合真实用户实际运行反馈，从200k+Skill生态中一键抵达「实测验证」过的技能*。

[![deep-skill-finder](assets/background.png)](https://www.deepskill.market/feedback?ref=github)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live in 40+ Agents](https://img.shields.io/badge/live%20in-40%2B%20AI%20Agents-8A2BE2.svg)](#生态支持情况)
[![Skills](https://img.shields.io/badge/skills-200k%2B-brightgreen.svg)](https://www.deepskill.market/skill)

[English](README.md) | 中文

</div>

---

## 🚀 在你的 Agent 中安装（30 秒）

复制下面的提示词，发送给你的 Agent（Claude Code / Codex / OpenClaw / Cursor / 其他 40+ 已支持的 Agent）：

```
请安装 deep-skill-finder Skill：从
https://www.deepskill.market/api/v1/skill-finder 下载安装包，解压到本地 Skills
目录并启用。
```

安装通常只需 15～30 秒。此后，当任务需要新的 Skill 时，DSF 会自动寻找候选项，并在安装前征得你的确认。不喜欢也可以随时用一条命令[卸载](#卸载与列表)。

### 使用方法

像平常一样自然地与 Agent 对话。当任务需要外部 Skill 时，DSF 会自动触发：

```
“帮我找一个能根据 CSV 构建交互式仪表盘的 Skill”
“有没有可以获取股票市场数据的 Skill？”
“推荐一个能把技术文档翻译成通俗英文的 Skill”
“搭建一套在每次 PR 时运行的 CI/CD 流水线”
```

DSF 会返回带有推荐理由的 TOP 5。推荐理由不仅说明能力是否匹配，也会呈现与当前任务相关的真实场景证据。确认序号后，安装将自动完成。

---

## 为什么选择 deep-skill-finder

Skill 生态正在快速增长。用户不再只是缺少工具，而是越来越难判断：**哪个 Skill 真正适合我的具体任务？**

传统 Skill 目录通常展示名称、作者描述、下载量和 Star。这些信息可以告诉你一个 Skill 是否容易被发现、是否受欢迎，却无法回答：

- 它是否在与你相似的任务中真正运行过？
- 它适合哪些 Agent、环境和工作流？
- 它是否需要额外凭证或复杂配置？
- 它的实际结果、耗时和 Token 消耗如何？
- 它在哪些情况下会失败？

Skill 都会介绍自己能做什么，但很少告诉你实际用起来怎么样。真正的问题不只是“能不能搜到”，而是找到之后仍然缺少足够的选择依据：

- **找到相关的，不等于找到适合的。** Skill 的名称和功能描述可以说明它“可能会做什么”，却无法告诉你它在特定 Agent、任务和环境中是否真正好用。
- **Skill 的真实表现，离不开具体场景。** 同一个 Skill 在不同任务、Agent 和运行环境下，可能呈现完全不同的结果。脱离场景的笼统评价，很难帮助你判断它是否适合当前需求。
- **流行程度，不等于真实表现。** 下载量和 Star 反映的是关注度，不能说明一个 Skill 是否跑得通、结果质量如何，或者曾在哪些真实场景中失败。

## deep-skill-finder vs Others
**deep-skill-finder 把专业检索与真实场景反馈结合起来。** 它先理解你的任务和约束，从全网 Skill 中找到真正相关的候选项；再结合相似任务中的真实使用反馈，帮助你做出最后的选择。

| 普通 Skill 目录 | deep-skill-finder |
| --- | --- |
| 根据名称、标签和关键词搜索 | 理解任务意图、能力方向与执行条件 |
| 主要展示作者对 Skill 的自我描述 | 补充真实使用反馈：实际表现、执行效果、关键信息 |
| 用下载量和 Star 衡量流行程度 | 呈现 Skill 在具体任务、Agent 和环境中的真实表现 |
| 很少呈现跑通、失败和结果质量 | 综合成功与失败记录、输出质量、耗时和使用成本 |
| 告诉你“大家在看什么” | **通过实际的应用案例**，告诉你“在相似场景中”这个 Skill 的执行结果如何 |

## 技能点评
deep-skill-finder 专门引入了**技能点评**这个模块，不是脱离上下文的简单评分，而一次反馈会围绕具体任务. 

[![deep-skill-finder](assets/cn/feedback.png)](https://www.deepskill.market/feedback?ref=github)

> 每一次`用户点评`都会完整记录使用场景、Skill 表现、评价，以及 Agent 类型、发生时间和预估 Token 消耗等上下文。
> 需要时还可以附加图片或视频：小文件直接内嵌在反馈 JSON 中，大文件通过服务端预签名 URL 上传到对象存储，上传时仅使用文件名、不会暴露本地路径。

```
usageScenario（使用场景）

在一个现有 Vue 3 + Vite 应用中新增技能点评与体验馆模块，要求复用既有导航、主题和响应式风格，同时使页面、展示组件、API、状态管理和数据访问保持独立，并完成类型检查、测试和生产构建验证。

skillPerformance（技能表现）

vue-patterns 提供了 feature-first 目录组织、Composition API、容器与展示组件分离、响应式状态选择、懒加载路由及测试方面的规范。实际实现据此拆分了路由页面、专用展示组件、服务端状态 composable、API、类型和本地 repository；服务端数据使用 Vue Query 管理，组件之间采用类型化 props/emit 通信。相关代码通过了 ESLint、类型检查、模块测试和生产构建，未观察到该 Skill 自身引起的异常、超时或重试。Skill 没有提供现有产品的视觉规范、业务交互设计或浏览器验收方法，这些部分仍需通过读取既有代码和人工判断补足

userFeedback（用户反馈）
9分，这个skill表现出较好的UI风格统一的能力，比较适合新增页面，新增模块的前端开发需求

附件（可选）
截图、录屏等图片/视频文件
```

通过上述**用户真实评测**所得到的信息，就能够帮助我们进一步甄别出更适合，更安全，更有效的skill，同时还能够帮助用户**提前规避风险**，请看以下3个真实的具体例子：

---

## 实际效果：3 个真实案例

**案例 1：搭建 GitHub Actions CI/CD**

> **仅看名称和描述：** `github-actions-gen` 与任务高度相关
>
> **真实运行反馈：** 文档简略，实际执行存在运行时 Bug
>
> DSF 推荐：`cicd-pipeline-generator`，文档完整，提供可直接使用的示例，并在任务中顺利运行

**案例 2：获取股票市场龙虎榜数据**

> **仅看关键词：** `pywencaistock` 覆盖股票数据能力
>
> **真实运行反馈：** 相关数据接口均已失效
>
> DSF 推荐：`lhb-api`，针对该数据源构建，3 个 API 调用全部通过

**案例 3：将 GPT-4o 博客翻译成通俗中文**

> **仅看功能匹配：** `translation-pro` 可以完成翻译
>
> **真实任务反馈：** 翻译正确，但表达生硬，不符合“通俗易懂”的风格要求
>
> DSF 推荐：`blog-polish-zhcn`，同时完成翻译、润色和术语保留，175 秒完成任务

这些案例中的差异并不只是“相关”与“不相关”。真正影响选择的，往往是接口是否仍然可用、运行环境是否兼容、输出风格是否符合要求，以及 Skill 能否完成端到端任务。

---

## 工作原理：专业检索 + 真实评价的 8 层排序

deep-skill-finder 的推荐不是一次简单的关键词排序，而是分为两个阶段：
> 1. **专业检索**：理解用户真正要完成的任务，从全网 Skill 中找到能力相关、方向正确、具备执行条件的候选项。
> 2. **真实评价排序**：将候选项放回具体使用场景，结合真实用户的执行过程、结果和评价，进一步判断哪个 Skill 更适合当前任务。

```
用户用自然语言描述具体任务
              │
              ▼
        任务理解与查询改写
 （目标 · 输入输出 · 方向 · 约束 · 环境）
              │
              ▼
┌──────────────────────────────────┐
│   专业检索（粗排）：多路召回          │
│                                  │
│ ① Skill 元信息相似度召回           │
│ ② SKILL.md / description        │
│    内容相似度召回                  │
│ ③ Feedback 真实反馈相似度召回      │
└──────────────┬───────────────────┘
               │
               ▼
      候选结果合并 · 去重 · 粗排
               │
               ▼
┌──────────────────────────────────┐
│       精排：Rerank + 评价甄别      │
│                                  │
│ 任务匹配：能力 · 方向 · 完整度       │
│ 执行判断：环境 · 依赖 · 可完成性     │
│                                  │
│ 真实评价甄别：                     │
│ usageScenario    相似使用场景      │
│ skillPerformance 执行过程与结果    │
│ userFeedback     用户评价与感受    │
│                                  │
│ 综合成功、失败、质量、风险与成本      │
└──────────────┬───────────────────┘
               │
               ▼
  TOP 5 + 推荐理由 + 场景证据 + 风险提示
               │
               ▼
       用户确认 → 安装 → 实际执行
                         │
                         ▼
                    用户主动评价
                         │
                         ▼
                      脱敏处理
                         │
                         ▼
                   新的真实评价证据
                         │
                         ├────→ Feedback 相似度召回
                         └────→ Rerank 评价甄别
```


### 第一阶段：通过专业检索找到相关候选

1. **任务意图理解** —— 识别用户真正想完成的目标，以及输入、输出、工作流方向和环境要求。
2. **能力与方向匹配** —— 优先分析结构化能力，区分“A → B”和“B → A”，避免只因关键词相似而错误命中。
3. **执行条件判断** —— 检查 Skill 是否依赖额外凭证、复杂配置或特定运行环境，并评估它能否覆盖完整任务。
4. **根本冲突过滤** —— 移除能力方向、使用条件或任务目标存在明显冲突的候选项。

### 第二阶段：通过真实评价重新判断排序

5. **相似场景优先** —— 对比评价中的 `usageScenario`。任务目标、Agent 类型和运行环境越接近当前需求，这条评价的参考价值越高。
6. **真实执行结果** —— 分析 `skillPerformance`，判断 Skill 是否真正跑通、完成了哪些步骤，以及是否通过测试、构建或结果验证。
7. **结果质量与用户感受** —— 结合 `userFeedback`，判断输出是否满足质量、风格和业务要求，而不只是“成功执行”。
8. **风险、限制与使用成本** —— 从评价中识别接口失效、异常、超时、额外依赖、能力边界、执行耗时和 Token 消耗，帮助高风险候选项降权。

### 真实评价如何影响最终推荐？

DSF 不会简单地按照评分高低排序。评价必须先与当前任务场景匹配，才能成为有效证据：

- 相似任务中的执行反馈，比无关场景里的高分更有价值；
- 有明确执行过程和结果验证的反馈，比笼统的“好用”更可信；
- 跑通记录、结果质量和用户认可会增强推荐依据；
- 接口失效、环境冲突和明确失败记录会使候选项降权或被过滤；
- 下载量只用于能力与真实表现接近时的辅助判断，不会覆盖真实执行证据。

最终，DSF 会综合专业检索结果与真实评价，输出最多 5 个高置信度推荐，并说明：

- 为什么它符合当前任务；
- 它曾在什么相似场景中运行；
- 实际表现和用户评价如何；
- 安装或执行前需要注意哪些风险。

**专业检索回答“哪些 Skill 可能适合”，真实评价回答“哪些 Skill 已经在相似场景中证明了自己”。**

真实评价会在推荐链路中发挥两次作用：

- **召回阶段：** Feedback 作为第三路数据源，可以召回那些仅凭名称或 Skill 描述不容易发现、但曾在相似任务中真实使用过的 Skill。
- **精排阶段：** Rerank 再利用评价中的使用场景、执行表现和用户反馈，验证候选项是否真正适合当前任务，并根据成功、失败、质量、风险和成本调整排序。

这形成了完整的推荐闭环：**任务理解 → 多路召回 → 合并粗排 → 精排甄别 → 用户确认 → 安装执行 → 真实评价回流**。

每一次用户愿意分享的真实使用，都不只是一个下载数字。它既能帮助系统发现更多适合相似任务的 Skill，也能成为下一次排序时判断真实表现的重要证据。

---

## 生态支持情况

deep-skill-finder 开箱即用地支持 **40+ Agent 运行环境**。无论你使用哪种 Agent，都能接入同一个 Skill 市场与真实场景反馈网络：

- Claude Code · Codex · Cursor · Windsurf · Cline
- WorkBuddy · OpenClaw · CatDesk · Hermes
- Copilot · Gemini · Antigravity · Amp
- 以及另外 28+ 种 Agent

**近 30 天活跃数据** *（2026-08 · 每月更新）*：

- 40+ 种不同的 `agentType` 客户端调用过 DSF
- **真实用户通过 DSF 安装次数最多的 Skills**（每个均经 10+ 个不同客户端安装验证）：
  - `desktop-pet`（116 个客户端）· `ppt-maker`（115）· `product-compare`（102）· `business-plan`（81）· `amazon-a-plus-content`（78）

这些数据不仅说明哪些 Skill 被发现，也记录哪些推荐最终转化成了真实用户的选择。随着更多任务被执行和评价，DSF 对不同场景的判断会持续获得新的证据。

---

## 项目结构

```
├── .gitignore                      # Git 忽略规则
├── README.md                       # 英文说明文档
├── README.zh.md                    # 中文说明文档
├── SKILL.md                        # Skill 定义与 Agent 完整工作流
├── assets/                         # README 视觉素材
├── references/
│   └── skill-evaluation.md         # 真实使用评价、确认与隐私规范
├── scripts/
│   ├── deep_skill_search.py        # 调用 Meyo 检索服务搜索并排序 Skills
│   ├── deep_skill_install.py       # 下载、安装与管理 Skills
│   └── skill_feedback.py           # 评价发现、脱敏、校验、保存与上传
└── tests/
    └── test_skill_feedback.py      # 真实评价链路与安全规则测试
```

其中，检索与真实评价分别由两组能力支撑：

- `deep_skill_search.py` 和 `deep_skill_install.py` 负责 Skill 的检索、选择与安装。
- `skill-evaluation.md`、`skill_feedback.py` 和对应测试共同负责真实使用评价的生成规范、用户确认、隐私保护与反馈提交。

## 脚本参考

通常你不需要直接调用这些脚本，Agent 会代为执行。不过，你也可以独立运行它们：

**搜索：**
```bash
python3 scripts/deep_skill_search.py "你的任务描述" [--agent-type openclaw]
```

搜索失败时脚本会返回非零退出码，并输出结构化的 `error.code`，例如
`search_timeout`、`search_network_error` 或 `search_service_error`。正常完成但没有匹配项时，
仍以成功状态退出，并返回空的 `community` 列表。

### 卸载与列表

**安装 / 卸载 / 列出：**
```bash
# 安装
python3 scripts/deep_skill_install.py <skill-name> --dir ~/.catpaw/skills

# 卸载
python3 scripts/deep_skill_install.py <skill-name> --dir ~/.catpaw/skills --uninstall

# 列出已安装的 Skills
python3 scripts/deep_skill_install.py --dir ~/.catpaw/skills --list
```

---

## 常见问题

**问：下载量和 Star 数难道不是足够好的指标吗？**

答：下载量和 Star 数只能说明什么更流行，不能说明什么能在你的具体任务中正常运行。DSF 优先考虑能力匹配、执行条件和相关场景中的真实表现，热度只用于候选项难分高下时的辅助判断。

**问：真实场景反馈和普通评分有什么不同？**

答：普通评分通常把不同用户、任务和环境下的体验压缩成一个数字。DSF 会保留与判断有关的场景信息，让 Agent 判断一条反馈是否与你当前的任务、环境和目标真正相关。

**问：真实场景反馈从哪里来？**

答：反馈来自用户通过 DSF 选择 Skill 后的实际执行与主动评价。它描述具体使用场景和 Skill 表现，并附带必要的运行上下文，而不是只对 Skill 给出笼统的好评或差评。

**问：评价会上传我的完整任务记录吗？**

答：不会。评价内容会先经过确定性脱敏处理，原始 trajectory 不会上传。只有在用户主动评价时，才会提交 `usageScenario`、`skillPerformance`、`rating`、`comment`，以及 `agentType`、`occurredAt`、`trajectoryIdHash` 和 `estimatedTokenUsage` 等上下文。

**问：“一个安装其他 Skills 的 Skill”——这算递归吗？安全吗？**

答：不算。DSF 负责推荐 Skills；在你的设备上执行任何安装前，都必须获得你的明确确认。每个推荐给你的 Skill 都会先通过安全审计和质量检查。

**问：如果我已经在使用 SkillHub / ClawHub / Vercel find-skills 呢？**

答：DSF 可以与它们协同使用，并不冲突。它会从 SkillHub、ClawHub、GitHub 和社区内容等来源召回候选项，再通过专业检索和真实场景反馈帮助你做出选择。

**问：我需要注册账号吗？**

答：不需要。DSF 可以独立运行，无需注册或提供邮箱。除用于跨会话保持状态的匿名本地 UUID 外，不收集额外的身份信息；只有在用户主动评价时，才会提交经过脱敏处理的反馈内容。

**问：它支持哪些 Agent？**

答：支持 40+ Agent 运行环境，包括 Claude Code、Codex、OpenClaw、Cursor、Windsurf、Cline、WorkBuddy、Hermes、CatDesk、Copilot 等。

---

## 参与贡献

欢迎提交 Issue 和 Pull Request，也欢迎用真实任务帮助整个 Skill 市场建立更可靠的场景口碑。

### 如果你是用户

- 如果某个 Skill 的推荐位置不准确，请在 [Meyo Community](https://www.deepskill.market/community/home) 留下真实运行记录。具体的任务、结果和使用条件，比单独的评分更能改善后续推荐。
- 通过 [Issues](https://github.com/wheelry/deep-skill-finder/issues) 报告问题，或申请覆盖特定任务和领域。

### 如果你是 Skill 创作者

- 我们索引全网 Skills，致力于构建兼具专业检索与真实场景反馈的 Skill Market。如果你的 Skill 没有出现在 DSF 结果中，请[提交 Issue](https://github.com/wheelry/deep-skill-finder/issues) 并附上 Skill URL，我们会进行排查。
- 真实任务反馈可以帮助你了解 Skill 在哪些场景中表现良好、哪里仍有改进空间。
- 有兴趣分享自己的 Skill 如何在真实任务中被使用？欢迎通过 Issues 联系我们。

---

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=wheelry/deep-skill-finder&type=Date)](https://star-history.com/#wheelry/deep-skill-finder&Date)

---

## 觉得有帮助？

- ⭐ **[给本仓库点个 Star](../../stargazers)** —— 帮助更多 Agent 用户发现 DSF
- 💬 **[分享一次真实使用](https://www.deepskill.market/community/home)** —— 让你的经验成为下一次推荐的依据
- 🐛 **[报告问题](../../issues)** —— 如果推荐结果看起来不准确，请告诉我们
- 📖 **[立即体验 DSF](#-在你的-agent-中安装30-秒)** —— 只需 30 秒即可安装

---

## 许可证

本项目采用 MIT 许可证，可在保留署名的前提下自由使用、修改和分发。详情请参阅 [LICENSE](LICENSE)。

---

## 相关链接

- **产品主页：** https://www.deepskill.market/skill
- **社区：** https://www.deepskill.market/community/skills
- **SkillHub 页面：** https://skillhub.cn/skills/deep-skill-finder
- **ClawHub 页面：** https://clawhub.ai/lintong123/skills/deep-skill-finder
