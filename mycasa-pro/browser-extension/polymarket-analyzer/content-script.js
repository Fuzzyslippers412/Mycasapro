/**
 * Content Script - Runs on Polymarket pages
 * Extracts market data for BTC 15m direction analysis
 */

console.log("[MyCasa Pro] Polymarket Analyzer extension loaded");

/**
 * Extract market data from Polymarket page
 */
function extractMarketData() {
  console.log("[MyCasa Pro] Extracting market data from page...");

  try {
    // Get market title
    const titleElement = document.querySelector('h1, [class*="title"], [class*="Title"]');
    const marketTitle = titleElement?.textContent?.trim() || "Unknown Market";

    // Get current URL
    const marketUrl = window.location.href;

    // Extract market ID from URL
    const marketId = marketUrl.split('/').pop() || 'unknown';

    // Try to find price elements (Polymarket displays prices as probabilities)
    const priceElements = document.querySelectorAll('[class*="price"], [class*="probability"], [class*="Probability"]');

    let upProb = null;
    let downProb = null;

    // Look for "Yes" and "No" prices
    const yesElement = Array.from(document.querySelectorAll('*')).find(el =>
      el.textContent.includes('Yes') && el.textContent.includes('¢')
    );
    const noElement = Array.from(document.querySelectorAll('*')).find(el =>
      el.textContent.includes('No') && el.textContent.includes('¢')
    );

    if (yesElement) {
      const match = yesElement.textContent.match(/(\d+\.?\d*)¢/);
      if (match) upProb = parseFloat(match[1]) / 100;
    }

    if (noElement) {
      const match = noElement.textContent.match(/(\d+\.?\d*)¢/);
      if (match) downProb = parseFloat(match[1]) / 100;
    }

    // Calculate complement if one is missing
    if (upProb && !downProb) downProb = 1 - upProb;
    if (downProb && !upProb) upProb = 1 - downProb;

    // Extract order book data (if visible)
    const orderBookBids = [];
    const orderBookAsks = [];

    // Look for order book elements
    const orderBookRows = document.querySelectorAll('[class*="orderbook"], [class*="OrderBook"], tbody tr');

    orderBookRows.forEach(row => {
      const cells = row.querySelectorAll('td, [class*="cell"]');
      if (cells.length >= 2) {
        const price = parseFloat(cells[0]?.textContent?.replace(/[^\d.]/g, ''));
        const size = parseFloat(cells[1]?.textContent?.replace(/[^\d.]/g, ''));

        if (!isNaN(price) && !isNaN(size)) {
          // Determine if bid or ask based on position or color
          const isBid = row.classList.contains('bid') || cells[0]?.classList.contains('bid');

          if (isBid) {
            orderBookBids.push({ price_prob: price, size: size });
          } else {
            orderBookAsks.push({ price_prob: price, size: size });
          }
        }
      }
    });

    // Extract recent trades
    const recentTrades = [];
    const tradeRows = document.querySelectorAll('[class*="trade"], [class*="Trade"], [class*="history"] tr');

    tradeRows.forEach((row, idx) => {
      if (idx > 10) return; // Limit to 10 trades

      const cells = row.querySelectorAll('td, [class*="cell"]');
      if (cells.length >= 3) {
        const side = cells[0]?.textContent?.toLowerCase().includes('buy') ? 'buy' : 'sell';
        const price = parseFloat(cells[1]?.textContent?.replace(/[^\d.]/g, ''));
        const size = parseFloat(cells[2]?.textContent?.replace(/[^\d.]/g, ''));

        if (!isNaN(price) && !isNaN(size)) {
          recentTrades.push({
            side: side,
            price_prob: price,
            size: size,
            time_iso: new Date().toISOString()
          });
        }
      }
    });

    // Extract volume data
    const volumeElements = document.querySelectorAll('[class*="volume"], [class*="Volume"]');
    let volume24h = null;
    let totalVolume = null;
    let openInterest = null;

    volumeElements.forEach(el => {
      const text = el.textContent;
      const match = text.match(/\$?([\d,]+\.?\d*)/);
      if (match) {
        const value = parseFloat(match[1].replace(/,/g, ''));
        if (text.toLowerCase().includes('24h')) {
          volume24h = value;
        } else if (text.toLowerCase().includes('total')) {
          totalVolume = value;
        } else if (text.toLowerCase().includes('open')) {
          openInterest = value;
        }
      }
    });

    // Extract time remaining
    const timeElements = document.querySelectorAll('[class*="time"], [class*="Time"], [class*="countdown"], [class*="Countdown"]');
    let timeRemainingSeconds = null;

    for (const el of timeElements) {
      const text = el.textContent;

      // Try to parse time formats like "15m", "1h 30m", "2d 5h"
      const minutesMatch = text.match(/(\d+)m/i);
      const hoursMatch = text.match(/(\d+)h/i);
      const daysMatch = text.match(/(\d+)d/i);

      if (minutesMatch || hoursMatch || daysMatch) {
        let seconds = 0;
        if (daysMatch) seconds += parseInt(daysMatch[1]) * 86400;
        if (hoursMatch) seconds += parseInt(hoursMatch[1]) * 3600;
        if (minutesMatch) seconds += parseInt(minutesMatch[1]) * 60;

        if (seconds > 0) {
          timeRemainingSeconds = seconds;
          break;
        }
      }
    }

    // Calculate spreads
    let upSpread = null;
    let downSpread = null;

    if (orderBookBids.length > 0 && orderBookAsks.length > 0) {
      const upBestBid = Math.max(...orderBookBids.map(b => b.price_prob));
      const upBestAsk = Math.min(...orderBookAsks.map(a => a.price_prob));
      upSpread = upBestAsk - upBestBid;

      // Assume symmetric for now
      downSpread = upSpread;
    } else {
      // Estimate from bid-ask if visible
      upSpread = 0.02; // 2% default
      downSpread = 0.025; // 2.5% default
    }

    // Build market data object
    const marketData = {
      captured_at_iso: new Date().toISOString(),
      market_url: marketUrl,
      market_title: marketTitle,
      market_id: marketId,

      // Outcomes
      up_label: "Yes",
      down_label: "No",
      yes_means_up: true,

      // Prices
      up_prob: upProb,
      down_prob: downProb,

      // Spreads
      up_spread: upSpread,
      down_spread: downSpread,
      up_best_bid: upProb ? upProb - upSpread / 2 : null,
      up_best_ask: upProb ? upProb + upSpread / 2 : null,
      down_best_bid: downProb ? downProb - downSpread / 2 : null,
      down_best_ask: downProb ? downProb + downSpread / 2 : null,

      // Liquidity
      volume_24h_usd: volume24h,
      total_volume_usd: totalVolume,
      open_interest_usd: openInterest,

      // Time
      time_remaining_seconds: timeRemainingSeconds,

      // Order book
      up_bids: orderBookBids.slice(0, 10),
      up_asks: orderBookAsks.slice(0, 10),
      down_bids: [], // Would need separate extraction for DOWN outcome
      down_asks: [],

      // Recent trades
      recent_trades: recentTrades
    };

    console.log("[MyCasa Pro] Market data extracted:", marketData);
    return marketData;

  } catch (error) {
    console.error("[MyCasa Pro] Error extracting market data:", error);
    return null;
  }
}

/**
 * Listen for messages from popup or background script
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("[MyCasa Pro] Received message:", request);

  if (request.action === "extractMarketData") {
    const data = extractMarketData();
    sendResponse({ success: true, data: data });
  }

  return true; // Keep channel open for async response
});

/**
 * Listen for messages from the MyCasa Pro web app
 */
window.addEventListener("message", (event) => {
  // Only accept messages from localhost (MyCasa Pro app)
  if (!event.origin.includes("localhost")) return;

  if (event.data.type === "MYCASA_REQUEST_MARKET_DATA") {
    console.log("[MyCasa Pro] Web app requested market data");

    const data = extractMarketData();

    // Send back to web app
    window.postMessage({
      type: "MYCASA_MARKET_DATA_RESPONSE",
      data: data
    }, event.origin);
  }
});

// Auto-extract on page load if this is a BTC market
if (window.location.href.includes('polymarket.com')) {
  const pageTitle = document.title.toLowerCase();

  if (pageTitle.includes('btc') || pageTitle.includes('bitcoin')) {
    console.log("[MyCasa Pro] Detected BTC market, data ready to extract");

    // Store indicator in page
    chrome.storage.local.set({
      lastPolymarketPage: window.location.href,
      isBTCMarket: true
    });

    // Auto-extract and send to Finance page if ClawdBot is detected
    // (ClawdBot tab viewer will have the Finance page loaded)
    setTimeout(() => {
      const data = extractMarketData();
      if (data) {
        // Try to send to all open Finance pages (including ClawdBot tabs)
        chrome.runtime.sendMessage({
          action: 'broadcastMarketData',
          data: data
        });

        // Also broadcast via postMessage for iframe scenarios
        window.postMessage({
          type: 'MYCASA_MARKET_DATA_RESPONSE',
          data: data
        }, '*');
      }
    }, 2000); // Wait 2 seconds for page to fully load
  }
}
