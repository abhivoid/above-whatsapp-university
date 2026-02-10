'use strict';

// Listen for selection and optionally notify background (for context menu availability)
document.addEventListener('selectionchange', () => {
  const sel = window.getSelection();
  const text = (sel && sel.toString() || '').trim();
  if (text) {
    chrome.runtime.sendMessage({ type: 'selection', text }).catch(() => {});
  }
});
