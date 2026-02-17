/**
 * Popup Script
 * Handles user interactions in the extension popup
 */

let extractedData = null;
let analysisResult = null;

// DOM elements
const notPolymarketDiv = document.getElementById('notPolymarket');
const onPolymarketDiv = document.getElementById('onPolymarket');
const statusDiv = document.getElementById('status');
const statusText = document.getElementById('statusText');
const marketTitle = document.getElementById('marketTitle');

const extractBtn = document.getElementById('extractBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const sendToAppBtn = document.getElementById('sendToAppBtn');

const dataPreview = document.getElementById('dataPreview');
const analysisResultDiv = document.getElementById('analysisResult');

// Initialize popup
async function init() {
  console.log("[MyCasa Pro] Popup initialized");

  // Check if we're on Polymarket
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (tab.url && tab.url.includes('polymarket.com')) {
    showPolymarketUI();
    updateMarketTitle(tab.title);
  } else {
    showNotPolymarketUI();
  }
}

function showNotPolymarketUI() {
  notPolymarketDiv.classList.remove('hidden');
  onPolymarketDiv.classList.add('hidden');
}

function showPolymarketUI() {
  notPolymarketDiv.classList.add('hidden');
  onPolymarketDiv.classList.remove('hidden');
}

function updateMarketTitle(title) {
  marketTitle.textContent = title || "Unknown Market";
}

function showStatus(message, type = 'info') {
  statusDiv.classList.remove('hidden');
  statusText.textContent = message;
  statusDiv.className = `status status-${type}`;

  // Auto-hide after 3 seconds
  setTimeout(() => {
    statusDiv.classList.add('hidden');
  }, 3000);
}

// Extract market data
extractBtn.addEventListener('click', async () => {
  console.log("[MyCasa Pro] Extract button clicked");

  extractBtn.disabled = true;
  extractBtn.textContent = "Extracting...";
  showStatus("Extracting market data...", "info");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.tabs.sendMessage(tab.id, { action: "extractMarketData" }, (response) => {
      extractBtn.disabled = false;
      extractBtn.textContent = "Extract Market Data";

      if (response && response.success && response.data) {
        extractedData = response.data;
        console.log("[MyCasa Pro] Data extracted:", extractedData);

        showStatus("Data extracted successfully!", "success");
        displayDataPreview(extractedData);

        // Show analysis button
        analyzeBtn.classList.remove('hidden');
        sendToAppBtn.classList.remove('hidden');
      } else {
        showStatus("Failed to extract data", "error");
        console.error("[MyCasa Pro] Extraction failed:", response);
      }
    });
  } catch (error) {
    extractBtn.disabled = false;
    extractBtn.textContent = "Extract Market Data";
    showStatus("Error: " + error.message, "error");
    console.error("[MyCasa Pro] Error:", error);
  }
});

// Analyze market
analyzeBtn.addEventListener('click', async () => {
  if (!extractedData) {
    showStatus("No data to analyze", "error");
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";
  showStatus("Running EDGE_SCORE v1.0...", "info");

  try {
    const response = await chrome.runtime.sendMessage({
      action: "analyzeMarket",
      marketData: extractedData
    });

    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Direction";

    if (response.success) {
      analysisResult = response.result;
      console.log("[MyCasa Pro] Analysis complete:", analysisResult);

      showStatus("Analysis complete!", "success");
      displayAnalysisResult(analysisResult);
    } else {
      showStatus("Analysis failed: " + response.error, "error");
    }
  } catch (error) {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Direction";
    showStatus("Error: " + error.message, "error");
    console.error("[MyCasa Pro] Error:", error);
  }
});

// Send to Finance page
sendToAppBtn.addEventListener('click', async () => {
  if (!extractedData) {
    showStatus("No data to send", "error");
    return;
  }

  console.log("[MyCasa Pro] Sending data to Finance page");

  // Open Finance page with data
  const dataJson = encodeURIComponent(JSON.stringify(extractedData));
  const url = `http://localhost:3000/finance?polymarket_data=${dataJson}`;

  chrome.runtime.sendMessage({
    action: "openFinancePage",
    url: url
  });

  showStatus("Opening Finance page...", "success");
});

// Display extracted data preview
function displayDataPreview(data) {
  document.getElementById('upProb').textContent = data.up_prob
    ? (data.up_prob * 100).toFixed(1) + '%'
    : 'N/A';

  document.getElementById('downProb').textContent = data.down_prob
    ? (data.down_prob * 100).toFixed(1) + '%'
    : 'N/A';

  document.getElementById('timeRemaining').textContent = data.time_remaining_seconds
    ? `${Math.floor(data.time_remaining_seconds / 60)}m ${data.time_remaining_seconds % 60}s`
    : 'N/A';

  dataPreview.classList.remove('hidden');
}

// Display analysis result
function displayAnalysisResult(result) {
  const callBadge = document.getElementById('resultCall');
  callBadge.textContent = result.call;
  callBadge.className = 'badge badge-' + result.call.toLowerCase();

  const confidenceBadge = document.getElementById('resultConfidence');
  confidenceBadge.textContent = result.confidence;
  confidenceBadge.className = 'badge badge-' + result.confidence.toLowerCase();

  document.getElementById('resultProb').textContent = (result.prob_up * 100).toFixed(1) + '%';

  analysisResultDiv.classList.remove('hidden');
}

// Initialize on load
init();
