/**
 * API client for InvestIQ backend.
 * All fetch errors bubble up as thrown Error instances.
 */

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
