import requests
from bs4 import BeautifulSoup
import time
import sqlite3
from datetime import datetime

BASE_URL = "https://www.channelnewsasia.com/topic/singapore-politics?type%5Barticle%5D=article&sort_by=field_release_date_value&sort_order=DESC&page=0"

def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    print(f"DEBUG: GET {url} -> status {resp.status_code}")
    print("DEBUG: Response snippet:", resp.text[:500])
    resp.raise_for_status()
    # Save the first page's HTML for debugging
    if "singapore-politics" in url and not hasattr(get_soup, "saved"):
        with open("debug_requests_listing.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        get_soup.saved = True
    return BeautifulSoup(resp.text, "html.parser")

def get_article_links(soup):
    # Find all article links and their tags on the listing page
    articles = []
    for list_obj in soup.select(".list-object, .list-object--video"):
        a = list_obj.select_one("a.h6__link.list-object__heading-link")
        tag_elem = list_obj.select_one("p.list-object__category.category a")
        if a and tag_elem:
            href = a.get("href")
            tag = tag_elem.get_text(strip=True)
            if href and href.startswith("/"):
                articles.append({
                    "url": "https://www.channelnewsasia.com" + href,
                    "tag": tag
                })
    return articles

def get_next_page_url(soup):
    # Find the next page link
    next_btn = soup.select_one("a[rel='next']")
    if next_btn:
        href = next_btn.get("href")
        if href and href.startswith("/"):
            return "https://www.channelnewsasia.com" + href
    return None

def scrape_article(url):
    soup = get_soup(url)
    title = soup.find("h1")

    # Author extraction
    author = ""
    # Try meta tag first
    meta_author = soup.find("meta", attrs={"name": "cXenseParse:author"})
    if meta_author and meta_author.get("content"):
        author = meta_author["content"].strip()
    # Fallback: <a href="/author/...">
    if not author:
        author_link = soup.find("a", href=lambda x: x and x.startswith("/author/"))
        if author_link:
            author = author_link.get_text(strip=True)

    # Created date extraction
    created = ""
    meta_created = soup.find("meta", attrs={"property": "article:published_time"})
    if meta_created and meta_created.get("content"):
        created = meta_created["content"].strip()
    if not created:
        meta_created = soup.find("meta", attrs={"name": "cXenseParse:recs:publishtime"})
        if meta_created and meta_created.get("content"):
            created = meta_created["content"].strip()

    # Updated date extraction
    updated = ""
    meta_updated = soup.find("meta", attrs={"property": "article:modified_time"})
    if meta_updated and meta_updated.get("content"):
        updated = meta_updated["content"].strip()
    if not updated:
        meta_updated = soup.find("meta", attrs={"name": "cXenseParse:recs:mdc-changedtime"})
        if meta_updated and meta_updated.get("content"):
            updated = meta_updated["content"].strip()

    # Find all divs with class "text-long" and extract all text (including paragraphs, headings, etc.)
    content_blocks = soup.find_all("div", class_="text-long")
    content_texts = []
    for block in content_blocks:
        # Get all text, preserving paragraph and heading breaks
        for elem in block.find_all(["p", "h2", "h3", "h4", "h5", "h6"]):
            content_texts.append(elem.get_text(strip=True))
    return {
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "author": author,
        "created": created,
        "updated": updated,
        "content": "\n\n".join(content_texts)
    }

def scrape_all_articles(start_url, max_pages=5, delay=2):
    articles = []
    for page_num in range(max_pages):
        url = start_url.replace("page=0", f"page={page_num}")
        print(f"Scraping page: {url}")
        soup = get_soup(url)
        article_objs = get_article_links(soup)
        for obj in article_objs:
            link = obj["url"]
            print(f"  Scraping article: {link}")
            try:
                article = scrape_article(link)
                articles.append(article)
                time.sleep(delay)
            except Exception as e:
                print(f"    Failed to scrape {link}: {e}")
        time.sleep(delay)
    return articles

def save_to_db(articles, db_path="news_articles.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Ensure table exists (schema from streamlit_news_app.py)
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            source TEXT,
            content TEXT,
            date_created TEXT,
            date_updated TEXT,
            mp_mentioned TEXT,
            categories TEXT,
            summary TEXT
        )
    ''')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for article in articles:
        # Use scraped values if available, else fallback
        author = article.get("author", "") or ""
        created = article.get("created", "") or now
        updated = article.get("updated", "") or created
        c.execute('''
            INSERT INTO articles (title, author, source, content, date_created, date_updated, mp_mentioned)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            article["title"],
            author,
            "Channel NewsAsia",  # source
            article["content"],
            created,
            updated,
            ""  # mp_mentioned (not scraped)
        ))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    articles = scrape_all_articles(BASE_URL, max_pages=5, delay=2)
    save_to_db(articles)
    print(f"Scraped {len(articles)} articles. Saved to news_articles.db.")
