/**
 * API client for InvestIQ backend.
 * All fetch errors bubble up as thrown Error instances.
 */

/**
 * fetchBriefing — GET /api/briefing to retrieve the latest cached briefing.
 * @returns {Promise<{portfolio, indices, fx, generated_at, briefing_date, fetched_at}>}
 */
export async function fetchBriefing() {
  const response = await fetch('/api/briefing');
  if (!response.ok) {
    throw new Error(`Briefing fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

/**
 * triggerRefresh — POST /api/refresh to trigger on-demand briefing regeneration.
 * @returns {Promise<{status: string, generated_at: string}>}
 */
export async function triggerRefresh() {
  const response = await fetch('/api/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Refresh failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function fetchIndices() {
  const response = await fetch('/api/indices');
  if (!response.ok) {
    throw new Error(`Indices fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function fetchFX() {
  const response = await fetch('/api/fx');
  if (!response.ok) {
    throw new Error(`FX fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

/**
 * setFXAlert — POST /api/fx/alert to persist EUR/INR alert threshold.
 * @param {number} threshold - Alert threshold value (must be > 0)
 * @returns {Promise<{alert_threshold: number, message: string}>}
 */
export async function setFXAlert(threshold) {
  const response = await fetch('/api/fx/alert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ threshold }),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = errorBody.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export async function fetchPortfolio() {
  const response = await fetch('/api/portfolio');
  if (!response.ok) {
    throw new Error(`Portfolio fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function fetchHealth() {
  const response = await fetch('/health');
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

/**
 * importCSV — upload a broker CSV file to POST /api/import.
 * @param {string} broker - "zerodha" or "trade_republic"
 * @param {File} file - File object from <input type="file">
 * @returns {Promise<{broker, imported_count, message}>}
 */
/**
 * sendChat — POST /api/chat to ask a question about today's briefing.
 * @param {string} message - User question
 * @param {object} briefing - Full briefing object from GET /api/briefing
 * @returns {Promise<string>} Chat response text
 */
export async function sendChat(message, briefing) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, briefing }),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = errorBody.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  const data = await response.json();
  return data.response;
}

/**
 * saveAlertSettings — POST /api/alerts to persist alert configuration.
 * @param {object} settings - Alert settings payload
 * @returns {Promise<{ok: boolean}>}
 */
export async function saveAlertSettings(settings) {
  const response = await fetch('/api/alerts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = errorBody.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

/**
 * fetchAlertSettings — GET /api/alerts to read current alert configuration.
 * @returns {Promise<object>} Alert settings in the same shape as the POST body
 */
export async function fetchAlertSettings() {
  const response = await fetch('/api/alerts');
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = errorBody.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export async function importCSV(broker, file) {
  const formData = new FormData();
  formData.append('broker', broker);
  formData.append('file', file);

  const response = await fetch('/api/import', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = errorBody.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }

  return response.json();
}
