/**
 * API client for InvestIQ backend.
 * All fetch errors bubble up as thrown Error instances.
 */

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
