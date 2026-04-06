# LLM-wiki

这仓库不是又一个“知识管理理念帖”，它是可落地的模板。

基线范式来自 Karpathy 那套思路，但这里把它收成了可复用的工程化做法：

- `compile-first`
- `writeback` 必做
- 中等规模先 `wiki`，不先上重 `RAG`
- Obsidian 可替换，范式不可替换
- `Idea / Intent` 优先于 `Code`

## 这仓库放什么

- [docs/knowledge-system-playbook.md](./docs/knowledge-system-playbook.md)
- [skills/knowledge-system-bootstrap](./skills/knowledge-system-bootstrap)

## 你该怎么用

### 1. 读 playbook

先看：

- [docs/knowledge-system-playbook.md](./docs/knowledge-system-playbook.md)

它讲清楚：

- 为什么 raw 不该全塞 Git
- 为什么中等规模项目先上 wiki，不先上重 RAG
- 什么叫 `raw -> wiki -> code`

### 2. 安装 skill

把这个目录复制到你本机 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R skills/knowledge-system-bootstrap ~/.codex/skills/knowledge-system-bootstrap
```

### 3. 用 skill 起一个新项目

skill 里的脚手架会帮你生成：

- `AGENTS.md`
- `docs/wiki/*`
- `manifests/raw_sources.csv`
- `scripts/wiki_check.py`
- `scripts/raw_manifest_check.py`
- `scripts/init_raw_root.py`
- `scripts/export_memory_repo.py`

核心命令在 skill 里：

```bash
python3 scripts/bootstrap_knowledge_system.py /path/to/new-repo "My New Project"
```

### 4. 真正的默认结构

- GitHub private repo：`code + wiki + manifests + verified cases`
- 本地 raw 仓：`pdf/xlsx/xls/rar/图片/客户原件`
- memory repo：只放编译后的长期记忆，不放 raw 本体

## 别干的蠢事

- 别把全量 PDF/XLSX 当成 Git 主仓
- 别把聊天上下文当长期记忆
- 别还没编译 raw 就先上重 RAG
- 别只改代码不回写 wiki

## 结论

这不是 Obsidian 教程，也不是 RAG 教程。

这是把项目知识变成生产线的办法。
