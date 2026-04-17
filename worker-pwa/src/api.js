const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return payload;
}

export async function getWorkerProfileByToken(token) {
  return request(`/api/v1/share-tokens/profile/${token}`);
}

export async function sessionLoginByToken(token, payload) {
  return request(`/api/v1/share-tokens/session-login/${token}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateWorkerProfileByToken(token, updates) {
  return request(`/api/v1/share-tokens/profile/${token}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}
