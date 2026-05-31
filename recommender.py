



"""
recommender.py  —  Product Recommender (Phase 1)
=================================================
Run:
    python recommender.py
"""

import os
import re
import sys
import requests
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

# Force stdout/stderr to use UTF-8 to prevent UnicodeEncodeError with emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

# ─── Check all keys are present before doing anything ────────────────────────

REQUIRED_KEYS = [
    "GEMINI_API_KEY",
    "SERPER_API_KEY"
]

missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
if missing:
    print("\n❌  Missing keys in your .env file:")
    for k in missing:
        print(f"    - {k}")
    print("\nCopy .env.example → .env and fill in the values.\n")
    exit(1)

# ─── Clients ─────────────────────────────────────────────────────────────────

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ─── Step 1: Google Shopping via Serper ──────────────────────────────────────

def fetch_products(query: str, budget: float) -> list[dict]:
    print(f"\n🔍  Searching Google Shopping for: '{query}'  |  Budget: ₹{budget:,.0f}")

    items = []
    for attempt in range(1, 3):
        try:
            response = requests.post(
                "https://google.serper.dev/shopping",
                headers={
                    "X-API-KEY": os.getenv("SERPER_API_KEY"),
                    "Content-Type": "application/json",
                },
                json={"q": query, "gl": "in", "hl": "en"},
                timeout=20,
            )
            response.raise_for_status()
            items = response.json().get("shopping", [])
            break
        except Exception as e:
            if attempt == 2:
                print(f"⚠️  Serper fetch failed (Attempt {attempt}/2): {e}")
                return []
            print(f"⚠️  Serper fetch timed out or failed. Retrying (Attempt {attempt}/2)...")

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
    return products

# ─── Step 3: YouTube transcript ──────────────────────────────────────────────

def fetch_youtube_transcript(product_name: str) -> str:
    print(f"\n▶️   Fetching YouTube transcript for: '{product_name} review'")

    videos = []
    for attempt in range(1, 3):
        try:
            # Use Serper to find YouTube video IDs (uses your Serper quota)
            response = requests.post(
                "https://google.serper.dev/videos",
                headers={
                    "X-API-KEY": os.getenv("SERPER_API_KEY"),
                    "Content-Type": "application/json",
                },
                json={"q": f"{product_name} review", "gl": "in"},
                timeout=20,
            )
            response.raise_for_status()
            videos = response.json().get("videos", [])
            break
        except Exception as e:
            if attempt == 2:
                print(f"⚠️  YouTube search failed (Attempt {attempt}/2): {e}")
                return "YouTube transcript unavailable."
            print(f"⚠️  YouTube search timed out or failed. Retrying (Attempt {attempt}/2)...")

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


# ─── Step 4: Gemini recommendation ──────────────────────────────────────────

def get_recommendation(
    user_query: str,
    budget: float,
    products: list[dict],
    youtube_transcript: str,
) -> str:
    print("\n🤖  Asking Gemini for recommendation...")

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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text


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

    # 3. YouTube
    youtube_transcript = fetch_youtube_transcript(top_product)

    # 4. Gemini
    result = get_recommendation(
        user_query=user_query,
        budget=budget,
        products=products,
        youtube_transcript=youtube_transcript,
    )

    print("\n" + "=" * 60)
    print("  📋  RECOMMENDATION")
    print("=" * 60)
    print(result)
    print("=" * 60 + "\n")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  👋  Welcome to the AI Product Recommender!")
    print("=" * 60)

    # Get user query
    user_query = ""
    while not user_query.strip():
        user_query = input("\n💬 What are you looking to buy?\n👉 ")
        if not user_query.strip():
            print("⚠️  Please enter a valid product description.")

    # Get budget
    budget = 0.0
    while True:
        budget_str = input("\n💰 What is your maximum budget in ₹ (INR)?\n👉 ")
        # Strip currency symbols and commas to be user friendly
        budget_clean = re.sub(r"[^\d.]", "", budget_str)
        if not budget_clean:
            print("⚠️  Please enter a valid number for the budget.")
            continue
        try:
            budget = float(budget_clean)
            if budget <= 0:
                print("⚠️  Budget must be greater than 0.")
                continue
            break
        except ValueError:
            print("⚠️  Please enter a valid number for the budget.")

    recommend(
        user_query=user_query.strip(),
        budget=budget,
    )
