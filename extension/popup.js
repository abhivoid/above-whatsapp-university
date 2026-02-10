'use strict';

const API_BASE = 'http://localhost:8000';

const claimEl = document.getElementById('claim');
const verifyBtn = document.getElementById('verify');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const verdictEl = document.getElementById('verdict');
const reasoningEl = document.getElementById('reasoning');
const citationsEl = document.getElementById('citations');

function showStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className = 'status ' + (type || '');
  statusEl.classList.remove('hidden');
}

function hideStatus() {
  statusEl.classList.add('hidden');
}

function showResult(verdict, reasoning, citations) {
  resultEl.classList.remove('hidden');
  verdictEl.textContent = verdict;
  verdictEl.className = 'verdict ' + verdict.toLowerCase().replace(/\s+/g, '-');
  reasoningEl.textContent = reasoning || '';

  citationsEl.innerHTML = '';
  if (citations && citations.length) {
    citations.forEach((c) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = c.url || '#';
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = c.title || 'Source';
      li.appendChild(a);
      if (c.snippet) {
        const span = document.createElement('span');
        span.textContent = ' — ' + (c.snippet.length > 80 ? c.snippet.slice(0, 80) + '…' : c.snippet);
        span.style.display = 'block';
        span.style.marginTop = '2px';
        span.style.color = '#9ca3af';
        li.appendChild(span);
      }
      citationsEl.appendChild(li);
    });
  } else {
    const li = document.createElement('li');
    li.textContent = 'No citations.';
    li.style.color = '#9ca3af';
    citationsEl.appendChild(li);
  }
}

async function verify() {
  const claim = (claimEl.value || '').trim();
  if (!claim) {
    showStatus('Enter or paste a claim to verify.', 'error');
    return;
  }

  verifyBtn.disabled = true;
  resultEl.classList.add('hidden');
  showStatus('Verifying…', 'loading');

  try {
    const res = await fetch(API_BASE + '/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim }),
    });
    const data = await res.json().catch(() => ({}));
    hideStatus();
    if (!res.ok) {
      showStatus('Request failed: ' + (data.detail || res.statusText), 'error');
      return;
    }
    showResult(
      data.verdict || 'Not Enough Evidence',
      data.reasoning || '',
      data.citations || []
    );
  } catch (e) {
    hideStatus();
    showStatus('Network error. Is the backend running at ' + API_BASE + '?', 'error');
  } finally {
    verifyBtn.disabled = false;
  }
}

verifyBtn.addEventListener('click', verify);

// Pre-fill claim from context menu (stored by background)
chrome.storage.local.get(['pendingClaim'], (o) => {
  if (o.pendingClaim) {
    claimEl.value = o.pendingClaim;
    chrome.storage.local.remove('pendingClaim');
    chrome.runtime.sendMessage({ type: 'POPUP_READY' }).catch(() => {});
  }
});
