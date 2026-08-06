import json
import os
import feedparser
from openai import OpenAI
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

# 1. 定义多订阅源列表（可继续追加其他期刊 RSS）
FEED_URLS = [
    "https://journals.plos.org/ploscompbiol/feed/atom",
    "https://royalsocietypublishing.org/rss/site_1000019/1000012.xml"
]

HISTORY_FILE = "history.json"
OUTPUT_FILE = "processed_articles.json"
RSS_OUTPUT_FILE = "feed.xml"

# 初始化 DeepSeek 客户端
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def analyze_article_with_llm(title, summary, journal_title=""):
    """调用 DeepSeek API 进行筛选、翻译与灵感提炼"""
    if not client:
        print("警告: 未检测到 LLM_API_KEY，跳过大模型筛选。")
        return None

    system_prompt = "你是一个专业科研助手，负责评估学术论文并严格按照指定的 JSON 格式返回数据。"
    
    user_prompt = f"""你是一名生态学与计算科学交叉领域的专家。请分析以下发表在学术期刊《{journal_title}》上的论文信息：

标题：{title}
摘要：{summary}

请进行以下评估与处理：
1. 确定性分类：判断该研究是否属于“生态学/环境科学直接研究”，或者是否包含“可迁移至生态学领域的方法论（如种群动态建模、空间模式识别、复杂网络分析、遥感与图像识别算法等）”？
2. 中文翻译：将标题翻译为准确、专业的中文标题。
3. 灵感与应用点：若相关，用 2-3 句话解释该方法或结论对生态学研究的具体借鉴价值与潜在应用场景；若完全无关，填“无”。

必须严格按照以下 JSON 格式输出，不要包含任何 markdown 标记或其他文本：
{{
  "is_relevant": true或false,
  "relevance_score": 1到5的整数,
  "title_zh": "中文标题",
  "inspiration": "灵感与应用点分析（中文）"
}}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print(f"调用 DeepSeek API 失败: {e}")
        return None

def generate_rss_feed(articles):
    """生成聚合 RSS 订阅源"""
    fg = FeedGenerator()
    fg.title('生态学与计算交叉科学 - 灵感筛选源')
    fg.link(href='https://github.com/', rel='alternate')
    fg.description('基于 DeepSeek API 自动从多本顶级期刊筛选的生态学及交叉学科启发文献')
    fg.language('zh-CN')

    if not articles:
        fe = fg.add_entry()
        fe.id('system-notice-empty')
        fe.title('【系统通知】订阅源运行正常，本次未发现匹配文章')
        fe.link(href='https://github.com/')
        fe.description('系统已运行并扫描所有目标订阅源，本次扫描未发现生态学强相关文章。')
        fe.pubDate(datetime.now(timezone.utc))
    else:
        for art in articles:
            fe = fg.add_entry()
            fe.id(art['id'])
            # 标题中标明来源期刊
            fe.title(f"[{art['relevance_score']}分][{art.get('source_journal', '期刊')}] {art['title_zh']}")
            fe.link(href=art['link'])
            
            content_html = f"""
            <h3>【生态学借鉴价值与启发】</h3>
            <p><strong>来源期刊：</strong> {art.get('source_journal', '未知期刊')}</p>
            <p><strong>相关度评分：</strong> {art['relevance_score']} / 5</p>
            <p>{art['inspiration']}</p>
            <hr/>
            <h3>【英文原标题】</h3>
            <p>{art['title_en']}</p>
            <h3>【英文原文摘要】</h3>
            <p>{art['summary_en']}</p>
            <hr/>
            <p><a href="{art['link']}">查看论文原文网页</a></p>
            """
            fe.description(content_html)
            fe.pubDate(datetime.now(timezone.utc))

    fg.rss_file(RSS_OUTPUT_FILE)
    print(f"\n成功更新并生成 RSS 文件: {RSS_OUTPUT_FILE}")

def main():
    history = set(load_json(HISTORY_FILE, []))
    processed_articles = load_json(OUTPUT_FILE, [])
    new_filtered_articles = []

    # 2. 循环遍历每一个订阅源
    for feed_url in FEED_URLS:
        print(f"\n======== 开始解析订阅源: {feed_url} ========")
        feed = feedparser.parse(feed_url)
        # 获取期刊名称（若获取不到则赋予默认名称）
        journal_title = getattr(feed.feed, 'title', 'Academic Journal')

        for entry in feed.entries:
            article_id = getattr(entry, 'id', entry.link)
            
            if article_id not in history:
                title = entry.title
                link = entry.link
                # 兼容 Atom 的 summary/content 以及 RSS 2.0 的 description
                summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                published = getattr(entry, 'published', '')

                print(f"正在分析新文章: {title}")
                
                analysis = analyze_article_with_llm(title, summary, journal_title)
                
                if analysis and analysis.get("is_relevant"):
                    article_data = {
                        "id": article_id,
                        "source_journal": journal_title,
                        "title_en": title,
                        "title_zh": analysis.get("title_zh", title),
                        "link": link,
                        "summary_en": summary,
                        "relevance_score": analysis.get("relevance_score", 0),
                        "inspiration": analysis.get("inspiration", ""),
                        "published": published
                    }
                    new_filtered_articles.append(article_data)
                    print(f" -> [匹配成功] 得分: {analysis.get('relevance_score')} | 中文标题: {analysis.get('title_zh')}")
                else:
                    print(" -> [过滤剔除] 判定与生态学无关。")

                history.add(article_id)

    # 3. 汇总合并新旧记录（保留最新的 150 条）
    if new_filtered_articles:
        processed_articles = (new_filtered_articles + processed_articles)[:150]
        save_json(OUTPUT_FILE, processed_articles)
        print(f"\n新增 {len(new_filtered_articles)} 篇符合要求的论文。")

    save_json(HISTORY_FILE, list(history))
    
    # 重新生成聚合 RSS 文件
    generate_rss_feed(processed_articles)

if __name__ == "__main__":
    main()
