# PLOS & Cross-disciplinary Ecology Inspiration RSS

本项目是一个自动化的学术文献监控与二次加工工具。系统定期拉取计算生物学及相关交叉学科期刊的 RSS/Atom 订阅源，利用大语言模型（DeepSeek API）自动筛选出与生态学直接相关或其方法论（算法、模型、模式识别等）可为生态学研究提供启发的论文，并生成带有中文翻译与借鉴价值点评的专属 RSS 订阅源。

## 核心功能

* **自动数据抓取**：定时解析目标期刊的 Atom/RSS 订阅源，自动去重并识别新发表论文。
* **智能语义筛选**：利用 DeepSeek API 对论文标题与摘要进行评估，识别可迁移至生态学领域的方法论。
* **双语与排版优化**：自动生成准确的中文标题与中文摘要翻译（针对完整摘要），并提炼 2–3 句话的“生态学借鉴价值与启发”。若论文无摘要，则自动跳过摘要区块，保持界面整洁。
* **RSS 聚合输出**：自动将处理后的结构化数据重新打包为标准的 RSS 2.0 XML 格式，支持直接导入各类 RSS 阅读器（如 Inoreader, Feedly 等）。

## 实现路径

1. **数据拉取（Data Ingestion）**：通过 Python 的 `feedparser` 模块提取 RSS/Atom Feed 中的条目，使用本地 `history.json` 记录已处理文章 DOI，避免重复分析。
2. **AI 过滤与提炼（LLM Processing）**：结合 `BeautifulSoup` 提取干净文本，向 DeepSeek API 传入结构化 Prompt，请求返回 JSON 格式的分类判定、中文翻译与灵感点分析。
3. **订阅生成与发布（Feed Generation & Deployment）**：基于 `feedgen` 模块生成 `feed.xml` 文件，借由 GitHub Actions 的 `cron` 定时任务自动提交并利用 GitHub Pages 进行托管展示。

## 订阅链接

* **GitHub Pages 链接（推荐）**：
  `https://huangmp1996.github.io/PLOS_RSS_Fetcher/feed.xml`
