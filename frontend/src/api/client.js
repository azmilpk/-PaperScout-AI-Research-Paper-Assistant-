const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)

  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }

  return response.json()
}

export function getStatus() {
  return request('/status')
}

export function getPapers() {
  return request('/papers')
}

export function deletePaper(paperId) {
  return request(`/papers/${paperId}`, { method: 'DELETE' })
}

export function loadSamplePaper() {
  return request('/papers/sample', { method: 'POST' })
}

export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/upload', { method: 'POST', body: formData })
}

export function sendChat(query, paperId = null, topK = 4) {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, paper_id: paperId, top_k: topK }),
  })
}

export function getApiKeyConfig() {
  return request('/settings/api-key')
}

export function saveApiKey(provider, apiKey, model = null) {
  return request('/settings/api-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, api_key: apiKey, model }),
  })
}
