# 完整项目学习手册

根据简历与可选 JD，补建完整统一的项目情境，按六个学习板块生成从浅到深的项目教材，讲清业务、产品、原理、具体工作与结果。也可直接围绕项目开展逐轮模拟面试，根据你的回答追问并给出复盘。

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

> 使用 $project-interview-dossier，根据这份简历的指定项目，补齐完整项目与具体工作，按六个学习板块写成自然连贯的手册。没有单独 JD，直接开始。

六个学习板块为：

1. 项目背景与目标
2. 业务流程与产品全貌
3. 整体方案与基础知识
4. 项目推进与核心工作
5. 验证、迭代与交付
6. 项目复盘与学习巩固

每个板块可包含多个项目专属章节。默认先完成作者自查；用户要求独立审查，或主要工作的操作、判断、交接仍存在具体缺口时，按需启用内部 interview 模块。教学补建内容会集中说明，不代表经核实的企业内部记录。

### 面试模拟与追问

不必先生成手册，提供简历、已有教材或一段项目描述即可开始，JD 可选：

> 使用 $project-interview-dossier，针对我的预约系统项目模拟后端面试。一次只问一道题，根据我的回答追问，结束后再统一点评。没有 JD，直接开始。

默认模拟模式不提前透露答案，完成五道主问题后复盘，也可以随时说“结束”。想边答边学时，可明确选择辅导模式：

> 使用 $project-interview-dossier，根据这份项目手册带我练面试，每次回答后指出最关键的缺口，再让我重答。手册中的补建部分按教学设定处理。

支持提示、跳过、换题、切换模式和继续练习。结束时根据实际回答整理表现、薄弱点、一道重答示范及下一次练习；跳过与未问到的能力保留为未验证。需要跨会话续练时，可要求生成续练摘要。回答记录不默认写入磁盘。

这里由你实际回答；内部 interview 模块则由代理独立检查教材。两条流程分别触发，面试练习不会自动启动三镜头审查，也不会把教学补建细节写成你的真实经历。详细流程见[面试模拟与追问](skills/project-interview-dossier/references/mock-interview.md)。

## 文件

- [主 Skill](skills/project-interview-dossier/SKILL.md)
- [教材结构](skills/project-interview-dossier/references/document-guide.md)
- [教学方法](skills/project-interview-dossier/references/teaching-method.md)
- [深度标准](skills/project-interview-dossier/references/depth-standard.md)
- [面试模拟与追问](skills/project-interview-dossier/references/mock-interview.md)
- [内部 interview](skills/project-interview-dossier/internal/interview-auditor/SKILL.md)

仓库只包含 Skill 及其配套参考资料、模板和检查脚本，不包含真实简历、生成教材或私人记录。内部 interview 模块的改编来源见其 [来源说明](skills/project-interview-dossier/internal/interview-auditor/references/sources.md) 与 [许可证](skills/project-interview-dossier/internal/interview-auditor/LICENSE)。
