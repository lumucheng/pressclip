import streamlit as st
import sqlite3
from datetime import datetime
import hashlib

# Database setup
conn = sqlite3.connect('news_articles.db', check_same_thread=False)
c = conn.cursor()

# Simple user authentication (for demo purposes)
users = {
    "user1": "password1",
    "user2": "password2"
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

hashed_users = {user: hash_password(pw) for user, pw in users.items()}

def login(username, password):
    if username in hashed_users and hash_password(password) == hashed_users[username]:
        return True
    return False

def search_articles(query):
    if query.strip() == "":
        # Return all articles when no search term is provided
        c.execute('''
            SELECT title, author, source, content, date_created, date_updated, mp_mentioned, categories, summary
            FROM articles
            ORDER BY date_created DESC
        ''')
    else:
        query = f"%{query}%"
        c.execute('''
            SELECT title, author, source, content, date_created, date_updated, mp_mentioned, categories, summary
            FROM articles
            WHERE mp_mentioned LIKE ?
            ORDER BY date_created DESC
        ''', (query,))
    return c.fetchall()

# Dialog for article details
@st.dialog("Article Details", width="large")
def show_article_dialog(article):
    st.markdown(f"### {article['title']}")
    st.write(f"**Summary by GENAI:** {article['summary'] if article['summary'] else 'No summary available'}")
    st.write(f"**Author:** {article['author']}")
    st.write(f"**Source:** {article['source']}")
    st.write(f"**Date Created:** {article['date_created']}")
    st.write(f"**Date Updated:** {article['date_updated']}")
    st.write(f"**Categories:** {article['categories'] if article['categories'] else 'No categories'}")
    st.write(f"**MP Mentioned:** {article['mp_mentioned']}")
    st.markdown("---")
    st.markdown(f"<div style='white-space: pre-wrap; max-height: 60vh; overflow-y: auto;'>{article['content']}</div>", unsafe_allow_html=True)

def main():
    st.title("Press Clipping")

    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False

    if not st.session_state.logged_in:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        else:
            st.info("Please log in to access the app.")
        return

    # Main search functionality
    st.subheader("Search News Articles")
    
    # Create columns for inline search box and button
    col1, col2 = st.columns([4, 1])
    
    with col1:
        search_query = st.text_input("Enter search term (MP mentioned)", label_visibility="collapsed", placeholder="Enter search term (MP mentioned)")
    
    with col2:
        search_button = st.button("Search", use_container_width=True)

    # Perform search when button is clicked
    if search_button:
        st.session_state.search_results = search_articles(search_query)
        st.session_state.search_performed = True

    # Display search results
    if st.session_state.search_performed:
        if st.session_state.search_results:
            if search_query.strip() == "":
                st.info(f"Showing all articles ({len(st.session_state.search_results)} results)")
            else:
                st.info(f"Found {len(st.session_state.search_results)} articles matching '{search_query}'")
            
            cols = st.columns(3)
            for idx, result in enumerate(st.session_state.search_results):
                title, author, source, content, date_created, date_updated, mp_mentioned, categories, summary = result
                col = cols[idx % 3]
                with col:
                    card_key = f"view_article_{idx}"
                    if st.button(
                        f"📰 **{title}**\n\nMP(s): {mp_mentioned if mp_mentioned else 'None'}",
                        key=card_key,
                        help=f"Source: {source}\nClick to view full article",
                        use_container_width=True
                    ):
                        article_data = {
                            "title": title,
                            "author": author,
                            "source": source,
                            "content": content,
                            "date_created": date_created,
                            "date_updated": date_updated,
                            "mp_mentioned": mp_mentioned,
                            "categories": categories,
                            "summary": summary
                        }
                        show_article_dialog(article_data)
        else:
            if search_query.strip() == "":
                st.info("No articles found in the database.")
            else:
                st.info(f"No articles found matching '{search_query}'.")
    else:
        st.info("Welcome! Click Search to view all articles, or enter a search term to filter results.")

if __name__ == "__main__":
    main()