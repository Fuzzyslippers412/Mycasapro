# ClawdBot Integration Guide

## Using Finance Page with ClawdBot Tab Viewer

The Finance page (Polymarket BTC 15m predictor) is fully compatible with ClawdBot's tab viewer for easier analysis.

### Setup

1. **Install MyCasa Pro Extension** (if not already installed)
   - See main README.md for installation steps

2. **Open Finance Page in ClawdBot**
   - In ClawdBot, open tab viewer
   - Navigate to: `http://localhost:3000/finance`
   - The Finance page will load in the ClawdBot interface

### Usage Workflow

#### Method 1: Auto-Receive (Recommended)

1. **Open Finance page in ClawdBot tab viewer**
   - URL: `http://localhost:3000/finance`
   
2. **Visit Polymarket BTC market in another tab**
   - Go to any BTC 15-minute market on Polymarket
   - Extension automatically extracts data
   
3. **Data appears in Finance page automatically**
   - Green notification shows "Data received from extension"
   - Market data populates in the textarea
   
4. **Click "Analyze Direction"**
   - EDGE_SCORE v1.0 runs analysis
   - Results show in "Results" tab

#### Method 2: Extension Popup

1. **On Polymarket page, click extension icon**
2. **Click "Extract Market Data"**
3. **Click "Send to Finance Page"**
4. **Finance page opens/updates with data**

#### Method 3: Manual Entry

1. **Click "Load Example"** to test with sample data
2. **Or paste your own JSON** market data

### How It Works

**Automatic Data Flow:**

```
Polymarket Page
  ↓
Extension Content Script (auto-extracts on BTC markets)
  ↓
Background Script (broadcasts to all Finance tabs)
  ↓
Finance Page in ClawdBot Tab
  ↓
postMessage API receives data
  ↓
Auto-populates analysis form
```

**Message Types:**

The Finance page listens for:
- `MYCASA_MARKET_DATA` - Market data from extension
- `MYCASA_MARKET_DATA_RESPONSE` - Response from content script
- `MYCASA_REQUEST_ANALYSIS_RESULT` - Request for latest analysis

The Finance page sends:
- `MYCASA_FINANCE_PAGE_READY` - Announces page is loaded
- `MYCASA_ANALYSIS_RESULT` - Sends analysis result

### ClawdBot-Specific Features

1. **iframe-safe** - Finance page works inside ClawdBot's iframe
2. **Cross-origin messaging** - Accepts messages from chrome-extension:// origins
3. **Auto-announce** - Broadcasts "page ready" on load
4. **Result sharing** - Can send analysis results back to ClawdBot

### Benefits of Using ClawdBot Tab Viewer

✅ **Keep Finance page visible** - Don't need separate browser tab  
✅ **Integrated workflow** - Analyze markets without leaving ClawdBot  
✅ **Auto-refresh** - Data updates automatically when you visit new markets  
✅ **Side-by-side** - View Polymarket and analysis simultaneously  
✅ **Chat integration** - Can discuss results with ClawdBot AI  

### Troubleshooting

**"Data not appearing"**
- Check that extension is installed and enabled
- Verify you're on a BTC market on Polymarket
- Check browser console for messages (F12)
- Ensure backend is running (http://localhost:8000)

**"Analysis not working"**
- Check that MyCasa Pro backend is running
- Verify Finance agent has Polymarket skill installed
- Check Network tab for failed API calls

**"ClawdBot tab not loading page"**
- Ensure frontend is running (http://localhost:3000)
- Check that ClawdBot can access localhost
- Try refreshing the tab viewer

### Security

- Extension only runs on polymarket.com
- Finance page only accepts messages from:
  - Same origin (localhost:3000)
  - localhost domains
  - chrome-extension:// origins
- No data sent to external servers
- All analysis happens locally

---

**For more details, see:**
- Main extension README.md
- Finance page documentation
- ClawdBot extension docs
