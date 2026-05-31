# 🛍️ Product Recommender — Phase 1

Tell it what you need + your budget.
It searches Google Shopping, reads Reddit opinions, pulls YouTube review transcripts,
and asks Gemini to pick the best product for you.

---

## Folder structure

```
recommender/
├── recommender.py       ← main script
├── requirements.txt     ← all dependencies
├── .env.example         ← copy this to .env and fill in keys
└── .env                 ← YOUR keys go here (never commit this!)
```

---

## Step 1 — Get the API keys (do this first)

You need accounts on 3 services. All have free tiers.

### A) Google Gemini
1. Go to https://aistudio.google.com
2. Sign up → click "Get API key"
3. Create an API key and copy it

### B) Serper (Google Shopping)
1. Go to https://serper.dev
2. Sign up (no credit card needed)
3. Dashboard → copy your API key
4. Free tier = 2500 searches/month — more than enough

### C) Reddit API
1. Go to https://www.reddit.com/prefs/apps
2. Scroll down → click "create another app"
3. Fill in:
   - Name: anything (e.g. "my_recommender")
   - Type: ✅ script
   - Redirect URI: http://localhost:8080
4. Click "create app"
5. You'll see:
   - Under your app name = CLIENT ID (short string)
   - "secret" field = CLIENT SECRET (longer string)

---

## Step 2 — Set up the project

```bash
# 1. Clone / download the project folder, then cd into it
cd recommender

# 2. (Recommended) create a virtual environment
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
```

Now open `.env` in any text editor and fill in your keys:

```
GEMINI_API_KEY=xxxxxxxx
SERPER_API_KEY=xxxxxxxx
REDDIT_CLIENT_ID=xxxxxxxx
REDDIT_CLIENT_SECRET=xxxxxxxx
REDDIT_USER_AGENT=recommender_app/1.0 by YourRedditUsername
```

Replace `YourRedditUsername` with your actual Reddit username.

---

## Step 3 — Run it

Open `recommender.py` and edit the last two lines:

```python
recommend(
    user_query="laptop for video editing and coding",
    budget=70000,
)
```

Change the query and budget to whatever you want, then:

```bash
python recommender.py
```

---

## What you'll see

```
============================================================
  🛍️   PRODUCT RECOMMENDER
  Query  : laptop for video editing and coding
  Budget : ₹70,000
============================================================

🔍  Searching Google Shopping...
✅  Found 8 products within budget

💬  Fetching Reddit opinions...
✅  Got 4 Reddit threads

▶️   Fetching YouTube transcript...
✅  Got transcript: ASUS VivoBook 15 Full Review...

🤖  Asking Gemini for recommendation...

============================================================
  📋  RECOMMENDATION
============================================================

**BEST PICK**
ASUS VivoBook 15 (Ryzen 5) | ₹62,990
Best balance of CPU performance and display quality for
video editing in this budget...

**PROS**
- ...

**CONS**
- ...

**STRETCH OPTION**
At ₹84,000 you could get...

**VERDICT**
Best value creative laptop under ₹70K.
============================================================
```

---

## Common errors

| Error | Fix |
|-------|-----|
| `Missing keys in .env` | Open `.env` and make sure all 5 keys are filled in |
| `401 Unauthorized` (Serper) | Wrong Serper key — double check on serper.dev dashboard |
| `prawcore.exceptions.ResponseException` | Wrong Reddit credentials — re-check client ID and secret |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again (make sure venv is active) |
| No products found | Try a more generic query e.g. "gaming laptop" instead of a specific model |

---

## What's next (Phase 2+)

- [ ] Wrap in FastAPI so it becomes an API endpoint
- [ ] Add LangGraph for proper multi-agent orchestration
- [ ] Add a simple chat frontend
