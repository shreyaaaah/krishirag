const BASE_URL = 'http://localhost:8000/api';

/**
 * Sends a farmer query to the RAG backend endpoint.
 * @param {string} query
 * @returns {Promise<{answer: string, sources: Array<{file: string, page: number}>, response_time_ms: number}>}
 */
export async function sendQuery(query) {
  try {
    const response = await fetch(`${BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error (${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to send query:', error);
    throw error;
  }
}

/**
 * Streams a farmer query response word-by-word from the RAG backend endpoint using Server-Sent Events (SSE).
 * @param {string} query
 * @param {(chunk: string) => void} onChunk
 * @param {(data: {sources: Array<{file: string, page: number}>, response_time_ms?: number}) => void} onDone
 * @param {(err: Error) => void} onError
 */
export async function streamQuery(query, onChunk, onDone, onError) {
  try {
    const response = await fetch(`${BASE_URL}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(trimmed.slice(6));
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            }
            if (parsed.done) {
              onDone({
                sources: parsed.sources || [],
                response_time_ms: parsed.response_time_ms
              });
            }
          } catch (err) {
            console.error('Failed to parse SSE JSON:', err);
          }
        }
      }
    }
  } catch (error) {
    console.error('Streaming failed:', error);
    if (onError) onError(error);
  }
}

/**
 * Fetches structured mandi prices from the backend database endpoint.
 * @param {{state?: string, district?: string, commodity?: string}} filters
 * @returns {Promise<{total: number, data: Array}>}
 */
export async function fetchMandiPrices(filters = {}) {
  try {
    const params = new URLSearchParams();
    if (filters.state) params.append('state', filters.state);
    if (filters.district) params.append('district', filters.district);
    if (filters.commodity) params.append('commodity', filters.commodity);

    const url = `${BASE_URL}/mandi-prices?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Database lookup error (${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to fetch mandi prices:', error);
    throw error;
  }
}

/**
 * Checks server health status.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}
