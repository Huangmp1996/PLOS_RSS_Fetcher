import json
import os
import feedparser
from openai import OpenAI
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# 定义多订阅源列表
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
    """针对宏观生态学、群落构建、生物地理与保护科学进行严格垂直筛选"""
    if not client:
        return None

    system_prompt = "你是一个深耕宏观生态学、群落生态学、生物地理学与保护生物学的资深学者。请严格基于特定生态学问题评估论文，绝不进行微观层面的生硬泛化类比，并严格返回 JSON 格式。"
    
    user_prompt = f"""请分析以下发表在《{journal_title}》上的学术论文：

标题：{title}
摘要：{summary}

【核心筛选与评估准则】
一、 领域准入（仅关注真实的中宏观生态学与环境科学问题）：
1. 目标核心领域：
   - 群落生态学与群落构建（如：物种共存、环境过滤、扩散限制、功能性状与系统发育多样性、营养级网络/食物网、深度/纬度/环境梯度多样性格局）；
   - 动物行为学与行为生态学（如：鸣声通讯/生物声学/语言学定律、社会结构与群体决策、移动生态学/觅食/栖息地选择、反捕食与繁殖策略、行为适应性演化）；
   - 生物地理学与宏观生态学（如：大尺度多样性格局、物种分化与演化历史）；
   - 海洋与水生生态学（如：珊瑚礁生态系统、鱼类群落动态、热带化、底栖生态、海洋保护优先区评估）；
   - 全球变化与保护科学（如：生态系统弹性/临界慢化/转折点、保护区规划、eDNA/被动声学/水下影像监测方法）；
   - 理论生态学（如：种群动态模型、空间自组织、物种丰富度与稳定性理论）。

2. 【强制排除清单（直接判为无关，is_relevant 设为 false）】：
   - 严格排除分子进化/细胞/生化机制（如：遗传密码子起源、密码子偏好性、蛋白质折叠、酶动力学、RNA/DNA突变机制等）；
   - 严格排除生物物理/细胞动力学算法（如：细胞内因子运输、肌纤维/细胞单层变形、微流控生物反应器等）；
   - 严格排除将纯微观/分子算法强行“比喻”或“类比”为生态适应度景观或冗余性的文章。

二、 处理要求：
1. 确定性分类：必须严格依据上述准入与排除规则，判断是否属于目标生态学领域的真实研究或直接适用的宏观方法。
2. 中文翻译：将标题翻译为准确的中文标题；若英文摘要存在且包含实际科研内容，将其翻译为通顺专业的中文摘要；若无有效摘要或摘要过短，"summary_zh" 务必填空字符串 ""。
3. 核心价值与启发：若相关（is_relevant=true），用 2-3 句话指出该研究对上述生态学具体科学问题（如群落构建机制、多样性格局、保护规划等）的明确推进或方法学借鉴；若判定为无关，填“无”。

必须严格按照以下 JSON 格式输出，不要包含任何 markdown 标记或其他文本：
{{
  "is_relevant": true或false,
  "relevance_score": 1到5的整数,
  "title_zh": "中文标题",
  "summary_zh": "中文摘要翻译（无摘要时填空字符串 \"\"）",
  "inspiration": "核心价值与生态学启发（中文）"
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
            temperature=0.1  # 降低温度以提高分类确定性，减少幻觉和过度联想
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print(f"调用 DeepSeek API 失败: {e}")
        return None
        
def generate_rss_feed(articles):
    """生成排版优化后的聚合 RSS 订阅源"""
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
            fe.title(f"[{art['relevance_score']}分][{art.get('source_journal', '期刊')}] {art['title_zh']}")
            fe.link(href=art['link'])
            
            # 排版顺序调整：英文标题 -> 中文标题 -> 英文摘要 -> 中文摘要 -> 借鉴价值与启发
            content_html = f"""
            <p><strong>来源期刊：</strong> {art.get('source_journal', '未知期刊')}</p>
            <p><a href="{art['link']}">查看论文原文网页</a></p>
            <hr/>
            <h3>【英文原标题】</h3>
            <p>{art['title_en']}</p>
            <h3>【中文标题】</h3>
            <p>{art['title_zh']}</p>
            <hr/>
            <h3>【英文原文摘要】</h3>
            <p>{art['summary_en']}</p>
            <h3>【中文摘要翻译】</h3>
            <p>{art.get('summary_zh', '暂无中文摘要')}</p>
            <hr/>
            <h3>【生态学借鉴价值与启发】</h3>
            <p><strong>相关度评分：</strong> {art['relevance_score']} / 5</p>
            <p>{art['inspiration']}</p>
            """
            fe.description(content_html)
            fe.pubDate(datetime.now(timezone.utc))

    fg.rss_file(RSS_OUTPUT_FILE)
    print(f"\n成功更新并生成 RSS 文件: {RSS_OUTPUT_FILE}")

def main():
    history = set(load_json(HISTORY_FILE, []))
    processed_articles = load_json(OUTPUT_FILE, [])
    new_filtered_articles = []

    for feed_url in FEED_URLS:
        print(f"\n======== 开始解析订阅源: {feed_url} ========")
        feed = feedparser.parse(feed_url)
        journal_title = getattr(feed.feed, 'title', 'Academic Journal')

        for entry in feed.entries:
            article_id = getattr(entry, 'id', entry.link)
            
            if article_id not in history:
                title = entry.title
                link = entry.link
                
                # 1. 提取原始 description/summary
                raw_summary = getattr(entry, 'description', getattr(entry, 'summary', ''))
                
                # 2. 清理其中的 HTML 标签（如 <span class="paragraphSection">），还原为纯文本 Abstract
                clean_summary = ""
                if raw_summary:
                    soup = BeautifulSoup(raw_summary, "html.parser")
                    clean_summary = soup.get_text(separator=' ', strip=True)

                print(f"正在分析新文章: {title}")
                
                # 3. 将干净的摘要直接送入 DeepSeek API 分析
                analysis = analyze_article_with_llm(title, clean_summary, journal_title)
                
                if analysis and analysis.get("is_relevant"):
                    article_data = {
                        "id": article_id,
                        "source_journal": journal_title,
                        "title_en": title,
                        "title_zh": analysis.get("title_zh", title),
                        "summary_zh": analysis.get("summary_zh", ""),
                        "link": link,
                        "summary_en": clean_summary,
                        "relevance_score": analysis.get("relevance_score", 0),
                        "inspiration": analysis.get("inspiration", ""),
                        "published": getattr(entry, 'published', '')
                    }
                    new_filtered_articles.append(article_data)
                    print(f" -> [匹配成功] 得分: {analysis.get('relevance_score')} | 中文标题: {analysis.get('title_zh')}")
                else:
                    print(" -> [过滤剔除] 判定与生态学无关。")

                history.add(article_id)

    if new_filtered_articles:
        processed_articles = (new_filtered_articles + processed_articles)[:150]
        save_json(OUTPUT_FILE, processed_articles)
        print(f"\n新增 {len(new_filtered_articles)} 篇符合要求的论文。")

    save_json(HISTORY_FILE, list(history))
    generate_rss_feed(processed_articles)
    
if __name__ == "__main__":
    main()
