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

> 使用 $project-interview-dossier，根据这份简历的指定项目，补齐完整项目与具体工作，按六个学习板块写成自然连贯的手册。没有单独 JD，直接开始。

六个学习板块为：

1. 项目背景与目标
2. 业务流程与产品全貌
3. 整体方案与基础知识
4. 项目推进与核心工作
5. 验证、迭代与交付
6. 项目复盘与学习巩固

每个板块可包含多个项目专属章节。先让读者看懂项目形态、用户任务与具体成果，再解释运行机制、个人工作与取舍；代码、公式和记录用于解释相应判断，不要求每章都做操作复现。

启动时会提供一次可跳过的输入步骤：可以粘贴 JD，没有也可用自然语言描述岗位或求职方向；已有 JD 或明确跳过时不重复询问。

默认先完成作者自查；用户要求独立审查，或主要工作的操作、判断、交接仍存在具体缺口时，按需启用内部 interview 模块。教学补建内容会集中说明，不代表经核实的企业内部记录。

## 文件

- [验证范围与结论](VALIDATION.md)
- [主 Skill](skills/project-interview-dossier/SKILL.md)
- [教材结构](skills/project-interview-dossier/references/document-guide.md)
- [教学方法](skills/project-interview-dossier/references/teaching-method.md)
- [深度标准](skills/project-interview-dossier/references/depth-standard.md)
- [内部 interview](skills/project-interview-dossier/internal/interview-auditor/SKILL.md)

仓库只包含 Skill 及其配套参考资料、模板和检查脚本，不包含真实简历、生成教材或私人记录。内部 interview 模块的改编来源见其 [来源说明](skills/project-interview-dossier/internal/interview-auditor/references/sources.md) 与 [许可证](skills/project-interview-dossier/internal/interview-auditor/LICENSE)。
