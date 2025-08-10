import sqlite3
import os
import openai
from typing import List, Dict

# Set your OpenAI API key here or via environment variable OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-proj-")  # Replace with your key or set env var

DB_PATH = "news_articles.db"

PROMPT_TEMPLATE = """
You are an expert news analyst. Given the following news article, do the following:
1. Suggest 1-3 relevant categories for this article (e.g., "Politics", "Parliament", "Elections", "Policy", etc.).
2. Write a quick summary (2-3 sentences) of the article.
3. Extract all possible names of Members of Parliament (MPs) mentioned in the article. If none, say "None found".

Article:
"{content}"

Respond in this JSON format:
{{
  "categories": [ ... ],
  "summary": "...",
  "mp_names": [ ... ]
}}
"""

def fetch_articles(db_path: str) -> List[Dict]:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, title, content FROM articles")
    rows = c.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "content": row[2]} for row in rows]

def analyze_article_with_openai(article_content: str) -> Dict:
    prompt = PROMPT_TEMPLATE.format(content=article_content[:4000])  # Truncate if too long
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2,
        )
        # Extract JSON from response
        import json
        text = response.choices[0].message.content
        # Try to find the first JSON block in the response
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
        else:
            return {"categories": [], "summary": "No summary", "mp_names": []}
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {"categories": [], "summary": "API error", "mp_names": []}

def update_article_analysis(db_path: str, article_id: int, mp_names: List[str], categories: List[str], summary: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    mp_mentioned_str = ", ".join(mp_names) if mp_names else ""
    categories_str = ", ".join(categories) if categories else ""
    summary_str = summary if summary else ""
    c.execute(
        "UPDATE articles SET mp_mentioned = ?, categories = ?, summary = ? WHERE id = ?",
        (mp_mentioned_str, categories_str, summary_str, article_id)
    )
    conn.commit()
    conn.close()

def main():
    articles = fetch_articles(DB_PATH)
    for article in articles:
        print(f"Analyzing article ID {article['id']}: {article['title']}")
        ai_result = analyze_article_with_openai(article['content'])
        mp_names = ai_result.get("mp_names", [])
        categories = ai_result.get("categories", [])
        summary = ai_result.get("summary", "")
        # If the model says "None found", treat as empty
        if isinstance(mp_names, list):
            if len(mp_names) == 1 and mp_names[0].lower().strip() == "none found":
                mp_names = []
        elif isinstance(mp_names, str) and mp_names.lower().strip() == "none found":
            mp_names = []
        if isinstance(categories, str):
            categories = [categories]
        update_article_analysis(DB_PATH, article["id"], mp_names, categories, summary)
        print(f"  -> Updated mp_mentioned: {mp_names}, categories: {categories}, summary: {summary[:60]}...")

    print("Analysis complete. Database updated.")

if __name__ == "__main__":
    main()
