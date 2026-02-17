/**
 * Background Service Worker
 * Handles extension lifecycle and message routing
 */

console.log("[MyCasa Pro] Background service worker started");

/**
 * Listen for extension installation
 */
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[MyCasa Pro] Extension installed:", details.reason);

  if (details.reason === "install") {
    // Set default configuration
    chrome.storage.local.set({
      apiUrl: "http://localhost:8000",
      frontendUrl: "http://localhost:3000",
      autoAnalyze: false
    });
  }
});

/**
 * Listen for messages from popup or content script
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("[MyCasa Pro] Background received message:", request);

  if (request.action === "analyzeMarket") {
    handleAnalyzeMarket(request.marketData)
      .then(result => sendResponse({ success: true, result: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));

    return true; // Keep channel open for async response
  }

  if (request.action === "openFinancePage") {
    chrome.tabs.create({ url: request.url || "http://localhost:3000/finance" });
    sendResponse({ success: true });
  }

  // Broadcast market data to all Finance page tabs
  if (request.action === "broadcastMarketData") {
    chrome.tabs.query({ url: "*://localhost:3000/finance*" }, (tabs) => {
      tabs.forEach(tab => {
        if (tab.id) {
          chrome.tabs.sendMessage(tab.id, {
            type: 'MYCASA_MARKET_DATA',
            marketData: request.data
          }).catch(() => {
            // Tab might not have content script, that's ok
          });
        }
      });
    });
    sendResponse({ success: true });
  }

  return true;
});

/**
 * Send market data to MyCasa Pro backend for analysis
 */
async function handleAnalyzeMarket(marketData) {
  const config = await chrome.storage.local.get(["apiUrl"]);
  const apiUrl = config.apiUrl || "http://localhost:8000";

  console.log("[MyCasa Pro] Sending market data to API:", apiUrl);

  const response = await fetch(`${apiUrl}/finance/polymarket/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      market_data: marketData,
      bankroll_usd: 5000
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Analysis failed");
  }

  const result = await response.json();
  console.log("[MyCasa Pro] Analysis complete:", result);

  // Store result
  await chrome.storage.local.set({
    lastAnalysis: result,
    lastAnalysisTime: new Date().toISOString()
  });

  return result;
}

/**
 * Context menu for quick analysis (optional enhancement)
 */
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "analyzeBTC",
    title: "Analyze BTC Direction with MyCasa Pro",
    contexts: ["page"],
    documentUrlPatterns: ["https://polymarket.com/*"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "analyzeBTC") {
    // Trigger analysis from context menu
    chrome.tabs.sendMessage(tab.id, { action: "extractMarketData" }, (response) => {
      if (response?.data) {
        handleAnalyzeMarket(response.data)
          .then(result => {
            chrome.notifications.create({
              type: "basic",
              iconUrl: "icons/icon128.png",
              title: "MyCasa Pro - BTC Direction",
              message: `Call: ${result.call} | Confidence: ${result.confidence}`,
              priority: 2
            });
          });
      }
    });
  }
});
