"""
recommender.py  —  Product Recommender (Phase 1)
=================================================
Run:
    python recommender.py
"""

import os
import re
import praw
import requests
from anthropic import Anthropic
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

# ─── Check all keys are present before doing anything ────────────────────────

REQUIRED_KEYS = [
    "ANTHROPIC_API_KEY",
    "SERPER_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
]

missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print("\n❌  Missing keys in your .env file:")
    for k in missing:
        print(f"    - {k}")
    print("\nCopy .env.example → .env and fill in the values.\n")
    exit(1)

# ─── Clients ─────────────────────────────────────────────────────────────────

claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)


# ─── Step 1: Google Shopping via Serper ──────────────────────────────────────

def fetch_products(query: str, budget: float) -> list[dict]:
    print(f"\n🔍  Searching Google Shopping for: '{query}'  |  Budget: ₹{budget:,.0f}")

    try:
        response = requests.post(
            "https://google.serper.dev/shopping",
            headers={
                "X-API-KEY": os.getenv("SERPER_API_KEY"),
                "Content-Type": "application/json",
            },
            json={"q": query, "gl": "in", "hl": "en"},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("shopping", [])
    except Exception as e:
        print(f"⚠️  Serper fetch failed: {e}")
        return []

    products = []
    for item in items:
        # Serper returns price as string like "₹45,999" — strip non-numeric chars
        price_str = item.get("price", "")
        price_clean = re.sub(r"[^\d.]", "", price_str)
        if not price_clean:
            continue
        price = float(price_clean)
        if price <= budget:
            products.append({
                "title": item.get("title", "Unknown"),
                "price": price,
                "source": item.get("source", "Unknown"),
                "rating": item.get("rating"),
                "link": item.get("link", ""),
            })

    # Best rated first, then cheapest
    products.sort(key=lambda x: (-(x["rating"] or 0), x["price"]))

    print(f"✅  Found {len(products)} products within budget")
    return products[:5]


# ─── Step 2: Reddit opinions ─────────────────────────────────────────────────

def fetch_reddit_opinions(product_name: str) -> str:
    print(f"\n💬  Fetching Reddit opinions for: '{product_name}'")

    try:
        posts = reddit.subreddit("all").search(
            query=f"{product_name} review",
            sort="relevance",
            limit=5,
            time_filter="year",
        )

        snippets = []
        for post in posts:
            post.comments.replace_more(limit=0)
            comments = [
                c.body[:250]
                for c in post.comments.list()[:2]
                if hasattr(c, "body") and len(c.body) > 30
            ]
            if comments:
                snippets.append(f"• {post.title}\n  {' | '.join(comments)}")

        if not snippets:
            return "No Reddit opinions found."

        print(f"✅  Got {len(snippets)} Reddit threads")
        return "\n\n".join(snippets)[:2000]

    except Exception as e:
        print(f"⚠️  Reddit fetch failed: {e}")
        return "Reddit opinions unavailable."


# ─── Step 3: YouTube transcript ──────────────────────────────────────────────

def fetch_youtube_transcript(product_name: str) -> str:
    print(f"\n▶️   Fetching YouTube transcript for: '{product_name} review'")

    try:
        # Use Serper to find YouTube video IDs (uses your Serper quota)
        response = requests.post(
            "https://google.serper.dev/videos",
            headers={
                "X-API-KEY": os.getenv("SERPER_API_KEY"),
                "Content-Type": "application/json",
            },
            json={"q": f"{product_name} review", "gl": "in"},
            timeout=10,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
    except Exception as e:
        print(f"⚠️  YouTube search failed: {e}")
        return "YouTube transcript unavailable."

    for video in videos[:4]:
        link = video.get("link", "")
        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", link)
        if not match:
            continue
        video_id = match.group(1)
        try:
            data = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join(entry["text"] for entry in data)
            print(f"✅  Got transcript: {video.get('title', video_id)[:60]}")
            return text[:2000]
        except Exception:
            continue  # no transcript for this video, try next

    return "No YouTube transcript available."


# ─── Step 4: Claude recommendation ──────────────────────────────────────────

def get_recommendation(
    user_query: str,
    budget: float,
    products: list[dict],
    reddit_opinions: str,
    youtube_transcript: str,
) -> str:
    print("\n🤖  Asking Claude for recommendation...")

    product_list = "\n".join(
        f"  {i+1}. {p['title']} | ₹{p['price']:,.0f} | "
        f"Rating: {p['rating'] or 'N/A'} | Store: {p['source']}"
        for i, p in enumerate(products)
    )

    prompt = f"""You are a sharp, no-nonsense product advisor for Indian consumers.

USER'S NEED: {user_query}
BUDGET: ₹{budget:,.0f}

PRODUCTS FOUND (within budget, sorted by rating):
{product_list}

REDDIT USER OPINIONS:
{reddit_opinions}

YOUTUBE REVIEW SNIPPET:
{youtube_transcript}

Give me a clean, structured recommendation:

**BEST PICK**
Name + price. In 2-3 sentences explain exactly why this is the best choice for the user's specific need.

**PROS**
- (3 specific pros, not generic)

**CONS**
- (2 honest cons)

**STRETCH OPTION**
If the user increased their budget by 20% to ₹{budget * 1.20:,.0f}, what should they buy instead and what concrete benefit does it add? Use your knowledge if needed.

**VERDICT**
One punchy sentence.

Keep it practical. Use ₹ for prices. No fluff."""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


# ─── Orchestrator ────────────────────────────────────────────────────────────

def recommend(user_query: str, budget: float):
    print("\n" + "=" * 60)
    print("  🛍️   PRODUCT RECOMMENDER")
    print(f"  Query  : {user_query}")
    print(f"  Budget : ₹{budget:,.0f}")
    print("=" * 60)

    # 1. Prices
    products = fetch_products(user_query, budget)
    if not products:
        print("\n❌  No products found within budget.")
        print("    Try: rephrasing the query, or increasing the budget.\n")
        return

    top_product = products[0]["title"]

    # 2. Reddit
    reddit_opinions = fetch_reddit_opinions(top_product)

    # 3. YouTube
    youtube_transcript = fetch_youtube_transcript(top_product)

    # 4. Claude
    result = get_recommendation(
        user_query=user_query,
        budget=budget,
        products=products,
        reddit_opinions=reddit_opinions,
        youtube_transcript=youtube_transcript,
    )

    print("\n" + "=" * 60)
    print("  📋  RECOMMENDATION")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ✏️  Change these two lines to test
    recommend(
        user_query="laptop for video editing and coding",
        budget=70000,
    )
