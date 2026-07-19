"""
app.py — Streamlit UI for the AI Product Recommender
======================================================
Runs:
    streamlit run app.py

Shows all intermediate outputs:
  • Google Shopping product table
  • YouTube search results + transcript preview
  • Gemini token usage & raw prompt
  • Final recommendation
"""

import os
import re
import time
import requests
import streamlit as st
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

from dotenv import load_dotenv

load_dotenv()

# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="🛍️ AI Product Recommender",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 40%, #16213e 100%);
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    border-right: 1px solid rgba(99,102,241,0.2);
}
[data-testid="stSidebar"] label {
    color: #a5b4fc !important;
    font-weight: 500;
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(168,85,247,0.2) 100%);
    border: 1px solid rgba(99,102,241,0.35);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(10px);
}
.hero-banner h1 {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem 0;
}
.hero-banner p {
    color: #94a3b8;
    font-size: 1rem;
    margin: 0;
}

/* Section card */
.section-card {
    background: rgba(30,27,75,0.55);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 30px rgba(0,0,0,0.3);
    animation: fadeIn 0.4s ease;
}
@keyframes fadeIn { from { opacity:0; transform:translateY(8px);} to { opacity:1; transform:translateY(0);} }

/* Section header label */
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #818cf8;
    margin-bottom: 0.6rem;
}

/* Metric pill */
.metric-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
    margin-top: 0.5rem;
}
.metric-pill {
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 50px;
    padding: 0.35rem 1rem;
    font-size: 0.82rem;
    color: #c7d2fe;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}
.metric-pill .val {
    font-weight: 700;
    color: #a5b4fc;
}

/* Token meter */
.token-bar-wrap {
    background: rgba(255,255,255,0.06);
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
    margin-top: 4px;
    margin-bottom: 2px;
}
.token-bar-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #6366f1, #a855f7);
}

/* Star rating */
.star { color: #fbbf24; }

/* Verdict box */
.verdict-box {
    background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(168,85,247,0.18));
    border: 1.5px solid rgba(168,85,247,0.45);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin-top: 1rem;
}
.verdict-box h2 {
    font-size: 1.35rem;
    color: #c084fc;
    margin-top: 0;
}

/* Badge */
.badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 10px;
    border-radius: 99px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-green  { background: rgba(34,197,94,0.2);  color: #86efac; border: 1px solid rgba(34,197,94,0.35); }
.badge-yellow { background: rgba(251,191,36,0.2); color: #fde68a; border: 1px solid rgba(251,191,36,0.35); }
.badge-red    { background: rgba(239,68,68,0.2);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.35); }
.badge-blue   { background: rgba(99,102,241,0.2); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.35); }

/* Dataframe tweaks */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Expander */
.streamlit-expanderHeader {
    background: rgba(99,102,241,0.1) !important;
    border-radius: 8px !important;
    color: #a5b4fc !important;
    font-weight: 500 !important;
}

/* Run button */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.4) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(99,102,241,0.6) !important;
}

/* Code block */
pre code { font-size: 0.78rem !important; }

/* Progress step */
.step-done  { color: #4ade80; font-weight: 600; }
.step-spin  { color: #fbbf24; font-weight: 600; }
.step-idle  { color: #475569; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def stars(rating):
    if rating is None:
        return "—"
    filled = round(rating)
    return '<span class="star">' + "★" * filled + "</span>" + "☆" * (5 - filled)

def rating_badge(rating):
    if rating is None:
        return '<span class="badge badge-blue">N/A</span>'
    if rating >= 4.0:
        return f'<span class="badge badge-green">⭐ {rating}</span>'
    if rating >= 3.0:
        return f'<span class="badge badge-yellow">⭐ {rating}</span>'
    return f'<span class="badge badge-red">⭐ {rating}</span>'

def check_keys():
    missing = [k for k in ["GEMINI_API_KEY", "SERPER_API_KEY"] if not os.getenv(k)]
    return missing

# ─── API functions (return rich metadata) ────────────────────────────────────

def fetch_products(query: str, budget: float):
    """Returns (products_within_budget, raw_items, attempt_count, elapsed_ms)"""
    t0 = time.time()
    raw_items = []
    attempts = 0
    error = None

    for attempt in range(1, 3):
        attempts = attempt
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
            raw_items = response.json().get("shopping", [])
            break
        except Exception as e:
            error = str(e)
            if attempt == 2:
                return [], [], attempts, int((time.time() - t0) * 1000), error

    products = []
    for item in raw_items:
        price_str = item.get("price", "")
        price_clean = re.sub(r"[^\d.]", "", price_str)
        if not price_clean:
            continue
        price = float(price_clean)
        if price <= budget:
            products.append({
                "Title": item.get("title", "Unknown"),
                "Price (₹)": price,
                "Store": item.get("source", "Unknown"),
                "Rating": item.get("rating"),
                "Reviews": item.get("ratingCount"),
                "Link": item.get("link", ""),
            })

    products.sort(key=lambda x: (-(x["Rating"] or 0), x["Price (₹)"]))
    elapsed = int((time.time() - t0) * 1000)
    return products, raw_items, attempts, elapsed, error


def fetch_youtube_data(product_name: str):
    """Returns (transcript_text, video_meta_list, selected_video, attempts, elapsed_ms, error)"""
    t0 = time.time()
    videos = []
    attempts = 0
    error = None

    for attempt in range(1, 3):
        attempts = attempt
        try:
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
            error = str(e)
            if attempt == 2:
                elapsed = int((time.time() - t0) * 1000)
                return "YouTube search failed.", [], None, attempts, elapsed, error

    video_meta = []
    selected_video = None
    transcript_text = "No transcript found."

    for video in videos[:6]:
        link = video.get("link", "")
        match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", link)
        vid_id = match.group(1) if match else None
        meta = {
            "title": video.get("title", "Unknown"),
            "channel": video.get("channel", "Unknown"),
            "date": video.get("date", "Unknown"),
            "link": link,
            "video_id": vid_id,
            "thumbnail": video.get("imageUrl", ""),
            "transcript_status": "not tried",
        }
        video_meta.append(meta)

        if vid_id and selected_video is None:
            try:
                data = YouTubeTranscriptApi.get_transcript(vid_id)
                full_text = " ".join(entry["text"] for entry in data)
                word_count = len(full_text.split())
                char_count = len(full_text)
                segment_count = len(data)
                transcript_text = full_text[:3000]
                meta["transcript_status"] = "✅ fetched"
                meta["word_count"] = word_count
                meta["char_count"] = char_count
                meta["segment_count"] = segment_count
                selected_video = meta
            except Exception as te:
                meta["transcript_status"] = f"❌ {str(te)[:80]}"

    elapsed = int((time.time() - t0) * 1000)
    return transcript_text, video_meta, selected_video, attempts, elapsed, error


def get_recommendation(user_query, budget, products, youtube_transcript, selected_video=None):
    """Returns (recommendation_text, prompt_text, usage_metadata, elapsed_ms, model_used)"""
    t0 = time.time()
    model_used = "gemini-2.5-flash"

    # ── Build conditional data sections ──────────────────────────────────────
    has_products   = bool(products)
    has_transcript = bool(youtube_transcript and youtube_transcript.strip()
                         and youtube_transcript not in (
                             "No transcript found.",
                             "No YouTube transcript available.",
                             "YouTube transcript unavailable.",
                             "YouTube search failed.",
                         ))

    products_section = (
        "\n".join(
            f"  [{i+1}] {p['Title']}\n"
            f"       Price : ₹{p['Price (₹)']:,.0f}\n"
            f"       Rating: {p['Rating'] or 'N/A'} "
            f"({int(p['Reviews']) if pd.notna(p.get('Reviews') or float('nan')) and p.get('Reviews') else 'N/A'} reviews)\n"
            f"       Store : {p['Store']}"
            for i, p in enumerate(products)
        )
        if has_products
        else "  ⚠️  No products were found in Google Shopping for this query."
    )

    transcript_section = (
        f"""YOUTUBE REVIEW TRANSCRIPT (excerpted from a real review video):
{youtube_transcript}"""
        if has_transcript
        else "YOUTUBE REVIEW: No transcript was available for any video found."
    )

    grounding_rules = """
┌────────────────────────────────────────────────────────────────┐
│  DATA-GROUNDING RULES — FOLLOW EXACTLY                           │
├────────────────────────────────────────────────────────────────┤
│ R1. BEST PICK should ideally be from the shopping list above.   │
│     However, if you know a strictly better alternative within   │
│     budget that isn't listed, you MAY recommend it instead.     │
│ R2. If you pick a listed item, copy its name and price exactly. │
│     If you suggest an unlisted alternative, state clearly that  │
│     it's an LLM-suggested alternative and estimate its price.   │
│ R3. PROS/CONS must be grounded in EITHER the list data OR the   │
│     YouTube transcript. Cite which source for each point.       │
│ R4. If the transcript is available, extract ≥1 concrete insight │
│     from it (e.g. a reviewer quote or observation).             │
│ R5. STRETCH OPTION may use your general knowledge for a model   │
│     not in the list, but MUST mention it is outside budget.     │
│ R6. If the shopping data is absent, say so and use knowledge.   │
│ R7. If the transcript is absent, skip transcript citations.     │
└────────────────────────────────────────────────────────────────┘"""

    prompt = f"""You are a data-grounded product advisor for Indian consumers.
Your job is to synthesise LIVE shopping data + real YouTube review insights
into a concrete recommendation. You must follow the grounding rules strictly.
{grounding_rules}

══ USER REQUEST ══
Need  : {user_query}
Budget: ₹{budget:,.0f}

══ LIVE GOOGLE SHOPPING DATA (fetched right now, prices are current) ══
{products_section}

══ {transcript_section}

══ OUTPUT FORMAT ══
Respond in exactly this structure:

**BEST PICK**
[Product name exactly as in list OR LLM-suggested alternative] — ₹[exact price from list OR estimated price]
2–3 sentences: why this product best fits the user’s specific need,
referencing at least one data point from the shopping list (rating/store)
{"and one insight from the YouTube transcript." if has_transcript else "."}

**BETTER ALTERNATIVES (IF ANY)**
If you picked a listed item but know a significantly better product for the same budget that wasn't listed, mention it here. Otherwise, omit this section.

**PROS** (label each with its source: [Shopping] or [YouTube] or [General knowledge])
- 
- 
- 

**CONS** (honest, specific)
- 
- 

**STRETCH OPTION**
If budget increases 20% to ₹{budget * 1.20:,.0f}: recommend a specific alternative
and state exactly what concrete improvement it provides.

**SOURCES USED**
- Google Shopping: {len(products)} products checked, prices as of today
- YouTube transcript: {"used — " + (selected_video.get("title","")[:60] if selected_video else "") if has_transcript else "not available"}
- Gemini knowledge: supplementary only

**VERDICT**
One punchy sentence. No fluff."""


    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model_used,
        contents=prompt,
    )

    usage = response.usage_metadata
    elapsed = int((time.time() - t0) * 1000)
    return response.text, prompt, usage, elapsed, model_used


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 1.5rem;">
        <div style="font-size: 2.8rem;">🛍️</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: #a5b4fc;">AI Product Recommender</div>
        <div style="font-size: 0.75rem; color: #64748b; margin-top:4px;">Powered by Gemini + YouTube</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-label">🎯 Your Query</div>', unsafe_allow_html=True)
    user_query = st.text_input(
        "What are you looking to buy?",
        placeholder="e.g. laptop for video editing",
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-label" style="margin-top:1rem;">💰 Budget (₹ INR)</div>', unsafe_allow_html=True)
    budget = st.number_input(
        "Budget",
        min_value=1000,
        max_value=10_000_000,
        value=70000,
        step=5000,
        label_visibility="collapsed",
    )

    st.markdown(f"""
    <div style="margin: 0.8rem 0; padding: 0.7rem 1rem;
         background: rgba(99,102,241,0.1); border-radius: 10px;
         border: 1px solid rgba(99,102,241,0.25); font-size: 0.85rem; color: #94a3b8;">
        Max stretch budget: <span style="color:#c084fc; font-weight:600;">₹{budget*1.2:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    run_btn = st.button("🚀  Find My Product", use_container_width=True)

    st.markdown("---")
    missing = check_keys()
    if missing:
        st.error(f"Missing API keys:\n" + "\n".join(f"• `{k}`" for k in missing))
    else:
        st.success("✅ API keys loaded")

    st.markdown("""
    <div style="margin-top: 1.5rem; font-size: 0.72rem; color: #475569; text-align:center;">
        Sources: Google Shopping · YouTube · Gemini AI
    </div>
    """, unsafe_allow_html=True)

# ─── Hero banner ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-banner">
    <h1>🛍️ AI Product Recommender</h1>
    <p>Searches Google Shopping · reads YouTube reviews · asks Gemini — then shows you everything under the hood.</p>
</div>
""", unsafe_allow_html=True)

# ─── Main content ─────────────────────────────────────────────────────────────

if not run_btn:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="section-card" style="text-align:center;">
            <div style="font-size:2.2rem;">🛒</div>
            <div style="font-weight:600; color:#a5b4fc; margin-top:0.5rem;">Google Shopping</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:0.3rem;">Live price search across Indian stores within your budget</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="section-card" style="text-align:center;">
            <div style="font-size:2.2rem;">▶️</div>
            <div style="font-weight:600; color:#a5b4fc; margin-top:0.5rem;">YouTube Reviews</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:0.3rem;">Fetches real transcript from the top review video</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="section-card" style="text-align:center;">
            <div style="font-size:2.2rem;">🤖</div>
            <div style="font-weight:600; color:#a5b4fc; margin-top:0.5rem;">Gemini 2.5 Flash</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:0.3rem;">Synthesises all data into a sharp, structured recommendation</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; color:#475569; font-size:0.9rem; margin-top: 2rem;">
        👈  Enter your query and budget in the sidebar, then hit <strong style="color:#a5b4fc;">Find My Product</strong>
    </div>
    """, unsafe_allow_html=True)

else:
    if not user_query.strip():
        st.error("⚠️ Please enter a product query in the sidebar.")
        st.stop()
    if check_keys():
        st.error("⚠️ Missing API keys. Check sidebar.")
        st.stop()

    # ── Step tracker ──────────────────────────────────────────────────────────

    step_col1, step_col2, step_col3, step_col4 = st.columns(4)
    with step_col1: shop_status = st.empty()
    with step_col2: yt_status   = st.empty()
    with step_col3: gem_status  = st.empty()
    with step_col4: done_status = st.empty()

    def set_step(s1="idle", s2="idle", s3="idle", s4="idle"):
        icons = {"idle": "⚪", "spin": "🟡", "done": "🟢", "err": "🔴"}
        shop_status.markdown(f"<div style='text-align:center'>{icons[s1]}<br><span style='font-size:0.78rem;color:#94a3b8;'>Shopping</span></div>", unsafe_allow_html=True)
        yt_status.markdown(  f"<div style='text-align:center'>{icons[s2]}<br><span style='font-size:0.78rem;color:#94a3b8;'>YouTube</span></div>",  unsafe_allow_html=True)
        gem_status.markdown( f"<div style='text-align:center'>{icons[s3]}<br><span style='font-size:0.78rem;color:#94a3b8;'>Gemini</span></div>",   unsafe_allow_html=True)
        done_status.markdown(f"<div style='text-align:center'>{icons[s4]}<br><span style='font-size:0.78rem;color:#94a3b8;'>Done</span></div>",      unsafe_allow_html=True)

    set_step("spin", "idle", "idle", "idle")

    # ════════════════════════════════════════════════════════════════════════════
    # STEP 1 — GOOGLE SHOPPING
    # ════════════════════════════════════════════════════════════════════════════

    with st.spinner("🔍 Searching Google Shopping..."):
        products, raw_items, shop_attempts, shop_ms, shop_err = fetch_products(user_query.strip(), budget)

    set_step("done", "spin", "idle", "idle")

    st.markdown('<div class="section-label" style="margin-top:1rem">🛒 STEP 1 — GOOGLE SHOPPING RESULTS</div>', unsafe_allow_html=True)

    # Metrics row
    within = len(products)
    total_raw = len(raw_items)
    filtered = total_raw - within

    st.markdown(f"""
    <div class="section-card">
      <div class="metric-row">
        <div class="metric-pill">🔎 Total results <span class="val">{total_raw}</span></div>
        <div class="metric-pill">✅ Within budget <span class="val">{within}</span></div>
        <div class="metric-pill">🚫 Over budget <span class="val">{filtered}</span></div>
        <div class="metric-pill">⏱️ Latency <span class="val">{shop_ms} ms</span></div>
        <div class="metric-pill">🔄 Attempts <span class="val">{shop_attempts}</span></div>
        <div class="metric-pill">🌐 Region <span class="val">India (gl=in)</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if shop_err:
        st.error(f"Serper error: {shop_err}")
        st.stop()

    if not products:
        st.warning("No products found within budget. Try a broader query or higher budget.")
        st.stop()

    # Product table
    import pandas as pd

    df = pd.DataFrame(products)
    df_display = df.copy()
    df_display["Price (₹)"] = df_display["Price (₹)"].apply(
        lambda x: f"₹{x:,.0f}" if pd.notna(x) else "N/A"
    )
    df_display["Rating"] = df_display["Rating"].apply(
        lambda x: f"⭐ {x}" if pd.notna(x) and x else "N/A"
    )
    df_display["Reviews"] = df_display["Reviews"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) and x else "N/A"
    )
    df_display["Link"] = df_display["Link"].apply(lambda x: f"[🔗 View]({x})" if x else "—")

    st.dataframe(
        df_display.drop(columns=["Link"]),
        use_container_width=True,
        hide_index=True,
    )

    # Clickable links in expander
    with st.expander("🔗 Product Links"):
        for p in products:
            if p["Link"]:
                st.markdown(f"- [{p['Title']}]({p['Link']}) — ₹{p['Price (₹)']:,.0f} on {p['Store']}")

    # Price distribution chart
    with st.expander("📊 Price Distribution Chart"):
        chart_df = pd.DataFrame({
            "Product": [p["Title"][:35] + "…" if len(p["Title"]) > 35 else p["Title"] for p in products],
            "Price (₹)": [p["Price (₹)"] for p in products],
        })
        st.bar_chart(chart_df.set_index("Product"))

    top_product = products[0]["Title"]

    # ════════════════════════════════════════════════════════════════════════════
    # STEP 2 — YOUTUBE
    # ════════════════════════════════════════════════════════════════════════════

    with st.spinner(f"▶️ Searching YouTube for '{top_product} review'..."):
        transcript, video_meta, selected_video, yt_attempts, yt_ms, yt_err = fetch_youtube_data(top_product)

    set_step("done", "done", "spin", "idle")

    st.markdown('<div class="section-label" style="margin-top:1.5rem">▶️ STEP 2 — YOUTUBE DATA</div>', unsafe_allow_html=True)

    # YouTube metadata pills
    word_count = selected_video.get("word_count", 0) if selected_video else 0
    char_count = selected_video.get("char_count", 0) if selected_video else 0
    seg_count  = selected_video.get("segment_count", 0) if selected_video else 0

    st.markdown(f"""
    <div class="section-card">
      <div class="metric-row">
        <div class="metric-pill">🎬 Videos found <span class="val">{len(video_meta)}</span></div>
        <div class="metric-pill">✅ Transcript fetched <span class="val">{"Yes" if selected_video else "No"}</span></div>
        <div class="metric-pill">📝 Words <span class="val">{word_count:,}</span></div>
        <div class="metric-pill">🔤 Characters <span class="val">{char_count:,}</span></div>
        <div class="metric-pill">🎙️ Segments <span class="val">{seg_count}</span></div>
        <div class="metric-pill">⏱️ Latency <span class="val">{yt_ms} ms</span></div>
        <div class="metric-pill">🔄 Attempts <span class="val">{yt_attempts}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Selected video info
    if selected_video:
        vid_link = selected_video.get("link", "")
        vid_thumb = selected_video.get("thumbnail", "")
        vid_title = selected_video.get("title", "")
        vid_channel = selected_video.get("channel", "")
        vid_date = selected_video.get("date", "")

        col_thumb, col_info = st.columns([1, 3])
        with col_thumb:
            if vid_thumb:
                st.image(vid_thumb, use_container_width=True)
        with col_info:
            st.markdown(f"""
            <div class="section-card" style="margin-bottom:0;">
              <div class="section-label">📌 Selected Video (transcript source)</div>
              <div style="font-size:1rem; font-weight:600; color:#e2e8f0;">{vid_title}</div>
              <div style="color:#64748b; font-size:0.82rem; margin-top:4px;">
                  📺 {vid_channel} &nbsp;·&nbsp; 📅 {vid_date}
              </div>
              <a href="{vid_link}" target="_blank"
                 style="display:inline-block; margin-top:0.6rem;
                        background: linear-gradient(135deg,#6366f1,#a855f7);
                        color:white; border-radius:8px; padding:4px 14px;
                        font-size:0.8rem; text-decoration:none; font-weight:600;">
                ▶ Watch on YouTube
              </a>
            </div>
            """, unsafe_allow_html=True)

    # All video candidates table
    with st.expander(f"🎞️ All YouTube Candidates Checked ({len(video_meta)} videos)"):
        for i, v in enumerate(video_meta):
            status = v.get("transcript_status", "not tried")
            link = v.get("link", "")
            st.markdown(
                f"**{i+1}.** [{v['title']}]({link})  \n"
                f"📺 {v.get('channel','?')} · 📅 {v.get('date','?')} · "
                f"Transcript: `{status}`"
            )
            st.markdown("---")

    # Transcript preview
    with st.expander("📜 Raw Transcript Preview (first 3000 chars sent to Gemini)"):
        st.text_area(
            "Transcript",
            transcript,
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )
        st.caption(f"Truncated to 3,000 chars for Gemini context. Full length: {char_count:,} chars / {word_count:,} words.")

    # ════════════════════════════════════════════════════════════════════════════
    # STEP 3 — GEMINI
    # ════════════════════════════════════════════════════════════════════════════

    with st.spinner("🤖 Asking Gemini for recommendation..."):
        recommendation, raw_prompt, usage, gem_ms, model_used = get_recommendation(
            user_query=user_query.strip(),
            budget=budget,
            products=products,
            youtube_transcript=transcript,
            selected_video=selected_video,
        )

    set_step("done", "done", "done", "done")

    st.markdown('<div class="section-label" style="margin-top:1.5rem">🤖 STEP 3 — GEMINI METADATA</div>', unsafe_allow_html=True)

    # Token usage
    input_tokens  = getattr(usage, "prompt_token_count",      0) or 0
    output_tokens = getattr(usage, "candidates_token_count",  0) or 0
    total_tokens  = getattr(usage, "total_token_count",       0) or 0
    # Gemini 2.5 Flash free tier limit reference
    token_limit   = 1_000_000
    pct = min(total_tokens / token_limit * 100, 100)

    st.markdown(f"""
    <div class="section-card">
      <div class="section-label">Token Usage</div>
      <div class="metric-row">
        <div class="metric-pill">📥 Input tokens <span class="val">{input_tokens:,}</span></div>
        <div class="metric-pill">📤 Output tokens <span class="val">{output_tokens:,}</span></div>
        <div class="metric-pill">🔢 Total tokens <span class="val">{total_tokens:,}</span></div>
        <div class="metric-pill">⚡ Model <span class="val">{model_used}</span></div>
        <div class="metric-pill">⏱️ Latency <span class="val">{gem_ms:,} ms</span></div>
        <div class="metric-pill">📏 Prompt length <span class="val">{len(raw_prompt):,} chars</span></div>
      </div>
      <div style="margin-top:1rem;">
        <div style="font-size:0.75rem; color:#64748b; margin-bottom:4px;">
          Context window usage: <strong style="color:#a5b4fc;">{total_tokens:,}</strong> / {token_limit:,} tokens ({pct:.2f}%)
        </div>
        <div class="token-bar-wrap">
          <div class="token-bar-fill" style="width:{pct:.2f}%;"></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Prompt sent to Gemini
    with st.expander("📋 Raw Prompt Sent to Gemini"):
        st.code(raw_prompt, language="markdown")

    # Full Gemini raw response
    with st.expander("📄 Raw Gemini Response (unformatted)"):
        st.text_area(
            "Raw response",
            recommendation,
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )

    # ════════════════════════════════════════════════════════════════════════════
    # FINAL RECOMMENDATION
    # ════════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-label" style="margin-top:1.5rem">📋 FINAL RECOMMENDATION</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="verdict-box">
        <h2>📋 Gemini's Pick for "{user_query}"</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(recommendation)

    # Summary footer
    st.markdown(f"""
    <div class="section-card" style="margin-top:1.5rem;">
      <div class="section-label">📊 Run Summary</div>
      <div class="metric-row">
        <div class="metric-pill">🛒 Products found <span class="val">{within}</span></div>
        <div class="metric-pill">🎬 Videos checked <span class="val">{len(video_meta)}</span></div>
        <div class="metric-pill">📝 Transcript words <span class="val">{word_count:,}</span></div>
        <div class="metric-pill">🔢 Total tokens used <span class="val">{total_tokens:,}</span></div>
        <div class="metric-pill">⏱️ Total latency <span class="val">{shop_ms + yt_ms + gem_ms:,} ms</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
