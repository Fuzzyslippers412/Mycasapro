# MyCasa Pro - Required API Keys & Setup

## ✅ Build Status: PASSING

Both backend and frontend compile without errors. All connectors and features are ready.

---

## 🔑 API Keys Required

### 1. **Anthropic API Key** (REQUIRED)
**Purpose:** Powers all AI agents (Manager, Finance, Maintenance, Contractors, Projects, Janitor)

**Get it from:** https://console.anthropic.com/settings/keys

**Add to `.env`:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

**Cost:** ~$15/million input tokens, ~$75/million output tokens (Claude 3.5 Sonnet)

---

### 2. **Google OAuth** (REQUIRED for Gmail & Calendar)
**Purpose:** Gmail sync, Calendar events, contact management

**Setup:**
1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable **Gmail API** and **Google Calendar API**
4. Create OAuth 2.0 credentials
5. Download credentials JSON

**Easiest method - Use `gog` CLI:**
```bash
# Install gog
brew install doitintl/tap/gog

# Login (opens browser)
gog auth login
```

No `.env` needed if using gog - it handles OAuth automatically.

---

### 3. **WhatsApp** (ALREADY CONFIGURED)
**Purpose:** Messaging via Clawdbot gateway

**Status:** ✅ Uses existing Clawdbot WhatsApp connection - no additional setup needed.

---

## 📋 Optional API Keys

### 4. **ElevenLabs** (Optional - Voice)
**Purpose:** Text-to-speech for voice notifications

**Get it from:** https://elevenlabs.io/api

**Add to `.env`:**
```bash
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxx
```

---

### 5. **Apify** (Optional - Web Scraping)
**Purpose:** Contractor discovery, market research, lead generation

**Get it from:** https://console.apify.com/account/integrations

**Add to `.env`:**
```bash
APIFY_TOKEN=apify_api_xxxxx
```

**Cost:** Pay-per-result (~$0.0025/result for Google Maps)

---

## 🚀 Quick Start

### Step 1: Create .env file
```bash
cd /path/to/mycasa-pro
cp .env.example .env
```

### Step 2: Add your API keys
```bash
# Edit .env and add at minimum:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### Step 3: Setup Google Auth (Gmail/Calendar)
```bash
# Install gog CLI
brew install doitintl/tap/gog

# Authenticate
gog auth login
```

### Step 4: Start the app
```bash
./start_all.sh
```

### Step 5: Open in browser
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

---

## 📊 Cost Estimate (Monthly)

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| Anthropic | ~1M tokens | $15-50 |
| Google APIs | Free tier | $0 |
| Apify (optional) | ~500 results | $1-2 |
| **Total** | | **$15-52/month** |

---

## 🔧 Verification Commands

After setup, verify everything works:

```bash
# Check Anthropic
cd /path/to/mycasa-pro
source .venv/bin/activate
python -c "import anthropic; print('Anthropic OK')"

# Check Gmail
gog gmail profile

# Check Calendar
gog calendar list

# Check WhatsApp (via Clawdbot)
wacli auth status --json
```

---

## 📝 Notes

1. **Anthropic is the only hard requirement** - everything else is optional

2. **Google OAuth via gog** - The `gog` CLI is the easiest way to authenticate. It handles token refresh automatically.

3. **No database setup needed** - MyCasa Pro uses SQLite by default (data stored in `data/mycasa.db`)

4. **SecondBrain vault** - Automatically created in your configured data directory

---

## 🆘 Troubleshooting

**"Anthropic key invalid"**
- Check the key starts with `sk-ant-api03-`
- Ensure no trailing whitespace

**"gog auth failed"**
- Run `gog auth logout` then `gog auth login` again
- Check Google Cloud Console for correct OAuth scopes

**"WhatsApp not connected"**
- Run `wacli auth status --json` to check status
- Re-auth with `wacli auth` if needed
