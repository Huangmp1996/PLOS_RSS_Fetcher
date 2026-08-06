import json
import os
import feedparser
from openai import OpenAI

FEED_URL = "https://journals.plos.org/ploscompbiol/feed/atom"
HISTORY_FILE = "history.json"
OUTPUT_FILE = "processed_articles.json"

# 初始化 DeepSeek 客户端
api_key = os.getenv("LLM_API_KEY")
# DeepSeek 官方 Base URL 为 https://api.deepseek.com
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

def analyze_article_with_llm(title, summary):
    """调用 DeepSeek API 进行筛选、翻译与灵感提炼"""
    if not client:
        print("警告: 未检测到 LLM_API_KEY，跳过大模型筛选。")
        return None

    system_prompt = "你是一个专业科研助手，负责评估学术论文并严格按照指定的 JSON 格式返回数据。"
    
    user_prompt = f"""你是一名生态学与计算科学交叉领域的专家。请分析以下发表在《PLOS Computational Biology》上的论文信息：

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
            model="deepseek-chat",  # 指定 DeepSeek-V3 模型
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

def main():
    history = set(load_json(HISTORY_FILE, []))
    processed_articles = load_json(OUTPUT_FILE, [])
    
    feed = feedparser.parse(FEED_URL)
    new_filtered_articles = []

    print(f"拉取订阅源完成，共获得 {len(feed.entries)} 条目。")

    for entry in feed.entries:
        article_id = getattr(entry, 'id', entry.link)
        
        # 仅处理未读文章
        if article_id not in history:
            title = entry.title
            link = entry.link
            summary = getattr(entry, 'summary', '')
            published = getattr(entry, 'published', '')

            print(f"\n正在分析新文章: {title}")
            
            analysis = analyze_article_with_llm(title, summary)
            
            # 筛选符合条件（is_relevant == True）的文章
            if analysis and analysis.get("is_relevant"):
                article_data = {
                    "id": article_id,
                    "title_en": title,
                    "title_zh": analysis.get("title_zh", title),
                    "link": link,
                    "summary_en": summary,
                    "relevance_score": analysis.get("relevance_score", 0),
                    "inspiration": analysis.get("inspiration", ""),
                    "published": published
                }
                new_filtered_articles.append(article_data)
                print(f" -> [匹配成功] 相关度评分: {analysis.get('relevance_score')} | 中文标题: {analysis.get('title_zh')}")
            else:
                print(" -> [过滤剔除] 判定与生态学无关。")

            # 标记为已处理
            history.add(article_id)

    # 追加新文章并保留最近 100 条记录
    if new_filtered_articles:
        updated_articles = (new_filtered_articles + processed_articles)[:100]
        save_json(OUTPUT_FILE, updated_articles)
        print(f"\n成功保留 {len(new_filtered_articles)} 篇新论文。")

    # 更新已读记录
    save_json(HISTORY_FILE, list(history))

if __name__ == "__main__":
    main()
