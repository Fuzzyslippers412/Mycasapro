# EdgeLab Integration for Finance Agent

## Overview

EdgeLab provides data acquisition capabilities for the MyCasa Pro Finance Agent (Mamadou):

1. **Browser Adapter** - Live scraping via `agent-browser` CLI or Clawd Chrome extension
2. **Polymarket Adapter** - Prediction market prices, sentiment, and search

## New Files

```
backend/
├── edgelab/
│   └── adapters/
│       ├── browser.py      # Browser scraping adapter (NEW)
│       └── polymarket.py   # Polymarket API adapter (NEW)
├── api/
│   └── routes/
│       └── edgelab.py      # API endpoints (NEW)
└── agents/
    └── finance.py          # Updated with EdgeLab integration
```

## API Endpoints

### Browser Scraping
- `POST /edgelab/browser/quote` - Scrape live quote for a symbol
- `GET /edgelab/browser/news?symbol=AAPL` - Scrape news headlines
- `GET /edgelab/browser/overview` - Scrape market overview

### Polymarket
- `GET /edgelab/polymarket/markets?category=Politics&limit=10` - Top markets
- `POST /edgelab/polymarket/search` - Search markets by query
- `GET /edgelab/polymarket/price/{market_slug}` - Get live price
- `POST /edgelab/polymarket/sentiment` - Aggregate sentiment from keywords

### Status
- `GET /edgelab/status` - Check adapter availability
- `GET /edgelab/adapters` - List adapters with capabilities

## Finance Agent Chat Commands

When talking to Mamadou (Finance Agent):

```
# Live quotes via browser scraping
"live quote AAPL"
"scrape price NVDA"
"current price GOOGL"

# Polymarket prediction markets
"prediction market crypto"
"polymarket market politics"
"betting odds sports"

# Sentiment analysis
"polymarket sentiment Fed rate cut"
"prediction sentiment BTC halving"
"polymarket sentiment AAPL earnings"
```

## Browser Adapter Features

### agent-browser CLI Integration
Uses the `agent-browser` CLI tool for headless browser automation:
- Navigate to finance sites (Yahoo Finance, FinViz)
- Extract prices, news, market data
- Execute JavaScript for dynamic content

### Clawd Chrome Extension Support
Set `use_chrome_relay=True` to use the Clawd Browser Relay for:
- Sites requiring authentication
- Bypassing rate limits
- Accessing logged-in sessions

Example:
```python
adapter = BrowserAdapter(config={
    "session": "finance_agent",
    "use_chrome_relay": True,  # Use Chrome extension
    "timeout": 30000,
})
```

## Polymarket Adapter Features

### Direct API Integration
Uses Polymarket's public APIs:
- **Gamma API** (`https://gamma-api.polymarket.com`) - Market discovery
- **CLOB API** (`https://clob.polymarket.com`) - Live prices

### Sentiment Analysis
Aggregates probabilities from multiple markets:
```python
sentiment = adapter.get_market_sentiment(["Fed", "rate", "cut"])
# Returns weighted probability based on market volume
```

### Categories
- Politics
- Crypto
- Sports
- Pop Culture
- Business
- Science

## Configuration

The adapters are auto-registered with `AdapterRegistry`:

```python
from backend.edgelab.adapters import AdapterRegistry

# List available adapters
print(AdapterRegistry.list_adapters())
# ['mock', 'yfinance', 'browser', 'polymarket']

# Get adapter instance
browser = AdapterRegistry.get("browser", config={"headed": False})
polymarket = AdapterRegistry.get("polymarket")
```

## Testing

```bash
# Test adapter imports
cd ~/clawd/apps/mycasa-pro
source .venv/bin/activate
python -c "from backend.edgelab.adapters import BrowserAdapter, PolymarketAdapter; print('OK')"

# Test API routes
python -c "from backend.api.routes.edgelab import router; print('Routes:', len(router.routes))"
```

## Dependencies

- `httpx` - HTTP client for Polymarket API
- `agent-browser` - CLI tool for browser automation (npm install -g agent-browser)

## Future Enhancements

1. **Real-time WebSocket** - Subscribe to Polymarket price updates
2. **News Sentiment** - Combine news scraping with sentiment analysis
3. **Alert System** - Notify on prediction market moves
4. **Historical Data** - Track Polymarket probability changes over time
