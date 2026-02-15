'use strict';

// Create context menu item when extension is installed/updated
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'verify-claim',
    title: 'Check with Above WhatsApp University',
    contexts: ['selection']
  });
});

// When user clicks "Check with Above WhatsApp University" in context menu, get selection and open popup with claim
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'verify-claim' || !info.selectionText) return;
  const claim = info.selectionText.trim();
  if (!claim) return;
  // Store claim and autoVerify flag for popup to read and auto-trigger verification
  chrome.storage.local.set({ pendingClaim: claim, autoVerify: true }, () => {
    chrome.action.openPopup?.().catch(() => {});
    // Fallback: open popup by focusing the extension (user clicks icon to see claim)
    chrome.windows.getCurrent((win) => {
      chrome.action.setBadgeText({ text: '1', tabId: tab.id });
      chrome.action.setBadgeBackgroundColor({ color: '#E6501B', tabId: tab.id });
    });
  });
});

// Clear badge when popup reads the claim
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'POPUP_READY') {
    chrome.storage.local.remove('pendingClaim');
    if (sender.tab?.id) chrome.action.setBadgeText({ text: '', tabId: sender.tab.id });
    sendResponse({ ok: true });
  }
  return true;
});
