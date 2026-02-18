# MyCasa Pro - Polymarket Analyzer Chrome Extension

Browser extension for extracting Polymarket BTC 15-minute market data and analyzing direction with EDGE_SCORE v1.0.

## Features

- 🎯 **Auto-Extract Market Data** - Scrapes prices, spreads, order book, trades, and time remaining directly from Polymarket pages
- 📊 **One-Click Analysis** - Run EDGE_SCORE v1.0 analysis directly from the extension popup
- 🔄 **Seamless Integration** - Send data to MyCasa Pro Finance page for detailed analysis
- 🚀 **Real-Time Updates** - Extract fresh data every time you need it
- ✅ **No Manual JSON** - No more copying/pasting JSON data manually

## Installation

### 1. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **"Load unpacked"**
4. Navigate to and select:
   ```
   /path/to/mycasa-pro/browser-extension/polymarket-analyzer
   ```
5. Extension should appear in your Chrome toolbar

### 2. Pin Extension (Optional)

1. Click the puzzle piece icon in Chrome toolbar
2. Find "MyCasa Pro - Polymarket Analyzer"
3. Click the pin icon to keep it visible

### 3. Create Icons (Required)

The extension needs icon files. Create these simple PNG files in the `icons/` directory:

**Option A: Quick Placeholders**
- Create 4 solid purple/violet squares: 16x16, 32x32, 48x48, 128x128
- Name them: `icon16.png`, `icon32.png`, `icon48.png`, `icon128.png`

**Option B: Use MyCasa Pro Logo**
- Export MyCasa Pro logo in 4 sizes
- Place in `icons/` directory with correct names

## Usage

### Method 1: Extension Popup (Recommended)

1. **Navigate to Polymarket**
   - Go to any BTC 15-minute market on Polymarket.com
   - Example: `https://polymarket.com/event/btc-above-105k`

2. **Open Extension**
   - Click the MyCasa Pro extension icon in toolbar
   - You'll see the market title and extraction options

3. **Extract Data**
   - Click **"Extract Market Data"**
   - Extension will scrape all market information automatically
   - Preview shows UP/DOWN probabilities and time remaining

4. **Analyze (Option A)**
   - Click **"Analyze Direction"** in the popup
   - Extension sends data to MyCasa Pro backend
   - Result shows call (UP/DOWN/NO_TRADE), confidence, and probability

5. **Send to Finance Page (Option B)**
   - Click **"Send to Finance Page"**
   - Opens Finance page with data pre-loaded
   - Click "Analyze Direction" on the page for detailed analysis

### Method 2: Right-Click Context Menu

1. Navigate to any Polymarket page
2. Right-click anywhere on the page
3. Select **"Analyze BTC Direction with MyCasa Pro"**
4. Extension extracts data and runs analysis automatically
5. Shows desktop notification with result

### Method 3: Programmatic (Advanced)

From the Finance page console:

```javascript
// Request market data from extension
window.postMessage({
  type: "MYCASA_REQUEST_MARKET_DATA"
}, "*");

// Extension will respond with:
// { type: "MYCASA_MARKET_DATA_RESPONSE", data: {...} }
```

## Data Extracted

The extension captures:

### Market Information
- Market URL, title, and ID
- Outcome labels (UP/DOWN, Yes/No)
- Current probabilities

### Pricing & Spreads
- Best bid and ask prices for UP and DOWN
- Spread calculations
- Mid-market prices

### Order Book
- Top 10 bid levels (price, size)
- Top 10 ask levels (price, size)
- Separate books for UP and DOWN outcomes

### Trade History
- Recent trades (side, price, size, time)
- Up to 10 most recent trades

### Market Stats
- 24h volume (USD)
- Total volume (USD)
- Open interest (USD)
- Time remaining (seconds)

## Configuration

Extension settings are stored in Chrome local storage:

```javascript
// Access in extension popup
chrome.storage.local.get(['apiUrl', 'frontendUrl', 'autoAnalyze'], (config) => {
  console.log(config);
});

// Update settings
chrome.storage.local.set({
  apiUrl: "http://localhost:8000",
  frontendUrl: "http://localhost:3000",
  autoAnalyze: false
});
```

## Troubleshooting

### Extension not showing popup
- Make sure you're on a `polymarket.com` page
- Check that extension is enabled in `chrome://extensions/`
- Reload the extension if you made code changes

### "Failed to extract data"
- Check browser console for errors (F12)
- Polymarket page structure may have changed
- Try refreshing the page and extracting again

### "Analysis failed"
- Ensure MyCasa Pro backend is running (`http://localhost:8000`)
- Check that Finance agent has Polymarket skill installed
- Verify extracted data has required fields (prices, time remaining)

### No icons showing
- Create icon files in `icons/` directory (see Installation step 3)
- Reload extension after adding icons

## Development

### File Structure

```
polymarket-analyzer/
├── manifest.json          # Extension configuration
├── content-script.js      # Runs on Polymarket pages, extracts data
├── background.js          # Service worker, message routing
├── popup.html            # Extension popup UI
├── popup.js              # Popup logic and event handlers
├── popup.css             # Popup styles
├── icons/                # Extension icons (16, 32, 48, 128px)
└── README.md             # This file
```

### Modifying Data Extraction

Edit `content-script.js` and update the `extractMarketData()` function:

```javascript
function extractMarketData() {
  // Add new selectors or extraction logic here
  // Return marketData object with new fields
}
```

### Adding Features

1. **New Button in Popup**: Edit `popup.html` and `popup.js`
2. **New Message Type**: Add handler in `background.js`
3. **New Permissions**: Update `manifest.json` permissions array

## API Integration

The extension communicates with MyCasa Pro backend:

### Endpoint: POST /finance/polymarket/analyze

```typescript
Request:
{
  market_data: {
    captured_at_iso: string,
    market_url: string,
    up_prob: number,
    down_prob: number,
    // ... full market data
  },
  bankroll_usd: number
}

Response:
{
  call: "UP" | "DOWN" | "NO_TRADE",
  confidence: "HIGH" | "MEDIUM" | "LOW",
  prob_up: number,
  reasons: string[],
  key_signals: {...},
  action_intents: [...]
}
```

## Security

- Extension only runs on `polymarket.com` domains
- API calls are limited to `localhost:8000` and `localhost:3000`
- No data is stored externally or transmitted to third parties
- All analysis happens locally via MyCasa Pro backend

## Support

For issues, questions, or feature requests:
- Check console logs (F12) for error details
- Review MyCasa Pro backend logs
- Verify all services are running (backend on :8000, frontend on :3000)

## Version History

**v1.0.0** (2026-01-31)
- Initial release
- Market data extraction from Polymarket
- One-click EDGE_SCORE v1.0 analysis
- Integration with MyCasa Pro Finance page
- Context menu support
- Desktop notifications

---

Built with ❤️ for MyCasa Pro Home Operating System
