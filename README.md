# 完整项目学习手册

根据简历与可选 JD，补建完整统一的项目情境，按六个学习板块生成从浅到深的项目教材，讲清业务、产品、原理、具体工作与结果。

## 安装

克隆仓库后，将 `skills/project-interview-dossier` 文件夹复制到你的 Codex Skills 目录（通常为 `~/.codex/skills/`）。

```bash
git clone https://github.com/xiaomoixuan/project_learner.git
mkdir -p ~/.codex/skills
cp -R project_learner/skills/project-interview-dossier ~/.codex/skills/
```

如果已有同名 Skill，请先备份或比较现有版本。

## 使用

提供简历并指定项目，可选提供岗位 JD：

> 使用 $project-interview-dossier，根据这份简历的指定项目和岗位方向，让我从头认识项目，学懂功能怎样实现、方案怎样选择，以及我的工作和结果。按六个板块写成连贯的面试准备手册。没有单独 JD，直接开始。

六个学习板块为：

1. 项目背景与目标
2. 业务流程与产品全貌
3. 整体方案与基础知识
4. 项目推进与核心工作
5. 验证、迭代与交付
6. 项目复盘与学习巩固

每个板块可包含多个项目专属章节。先跟着使用者完成一次任务，再进入系统理解功能怎样实现，以及开发者怎样作选择、处理难点、验证结果。默认用自然语言、流程和有内容的例子教学，不用代码、函数名或字段回放代替解释。实际 JD 决定哪些设计与机制需要讲深。

启动时会提供一次可跳过的输入步骤：可以粘贴 JD，没有也可用自然语言描述岗位或求职方向；已有 JD 或明确跳过时不重复询问。

默认先完成作者自查；用户要求独立审查，或主要功能、设计和个人工作仍讲不清时，按需启用内部 interview 模块。通常使用三个独立视角，用户明确要求节省时间时可用一个新实例合并审查，并保留实际模式和复验记录。维护迭代另用全新读者顺序学习全文，评价深度、可理解性、语言、岗位适配与连贯性。教学补建内容会集中说明，不代表经核实的企业内部记录。

## 文件

- [验证范围与结论](VALIDATION.md)
- [主 Skill](skills/project-interview-dossier/SKILL.md)
- [教材结构](skills/project-interview-dossier/references/document-guide.md)
- [教学方法](skills/project-interview-dossier/references/teaching-method.md)
- [深度标准](skills/project-interview-dossier/references/depth-standard.md)
- [内部 interview](skills/project-interview-dossier/internal/interview-auditor/SKILL.md)

仓库包含 Skill、配套参考资料、模板、检查脚本和通用回归测试，不包含真实简历、生成教材或私人记录。内部 interview 模块的改编来源见其 [来源说明](skills/project-interview-dossier/internal/interview-auditor/references/sources.md) 与 [许可证](skills/project-interview-dossier/internal/interview-auditor/LICENSE)。
