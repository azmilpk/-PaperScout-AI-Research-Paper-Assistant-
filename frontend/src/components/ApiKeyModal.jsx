import { useState, useEffect } from 'react'
import { saveApiKey, getApiKeyConfig } from '../api/client'

export default function ApiKeyModal({ isOpen, onClose, onKeySaved }) {
  const [provider, setProvider] = useState('huggingface')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [currentConfig, setCurrentConfig] = useState(null)
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setError('')
      setSuccess('')
      getApiKeyConfig()
        .then((data) => {
          setCurrentConfig(data)
          if (data.llm_provider && data.llm_provider !== 'none') {
            setProvider(data.llm_provider)
          }
          if (data.llm_model && data.llm_model !== 'none') {
            setModel(data.llm_model)
          }
        })
        .catch(() => {})
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleSave = async (e) => {
    e.preventDefault()
    if (!apiKey.trim()) {
      setError('Please enter a valid API key or token.')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const res = await saveApiKey(provider, apiKey.trim(), model.trim() || undefined)
      setSuccess(res.message || 'Key saved successfully!')
      setApiKey('')
      if (onKeySaved) {
        await onKeySaved()
      }
      setTimeout(() => {
        onClose()
      }, 1200)
    } catch (err) {
      setError(err.message || 'Failed to save API key')
    } finally {
      setLoading(false)
    }
  }

  const getHelpLink = () => {
    if (provider === 'huggingface') {
      return { url: 'https://huggingface.co/settings/tokens', label: 'Get Hugging Face Token (Free)' }
    }
    if (provider === 'google') {
      return { url: 'https://aistudio.google.com/app/apikey', label: 'Get Gemini Key' }
    }
    return { url: 'https://platform.openai.com/api-keys', label: 'Get OpenAI Key' }
  }

  const help = getHelpLink()

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>Configure Real LLM Keys</h2>
            <p className="modal-subtitle">
              Power your LangChain RAG pipeline with real models
            </p>
          </div>
          <button type="button" className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        {currentConfig?.key_configured && (
          <div className="current-key-badge">
            <span className="dot online" />
            <span>
              Active: <strong>{currentConfig.llm_provider.toUpperCase()}</strong> ({currentConfig.llm_model})
              {currentConfig.masked_key && ` • Token: ${currentConfig.masked_key}`}
            </span>
          </div>
        )}

        {error && <div className="banner error">{error}</div>}
        {success && <div className="banner success">{success}</div>}

        <form onSubmit={handleSave} className="modal-form">
          <div className="form-group">
            <label>LLM Provider</label>
            <div className="provider-tabs">
              <button
                type="button"
                className={`provider-tab ${provider === 'huggingface' ? 'active' : ''}`}
                onClick={() => {
                  setProvider('huggingface')
                  setModel('mistralai/Mistral-7B-Instruct-v0.3')
                }}
              >
                Hugging Face
                <span className="badge-free">100% Free</span>
              </button>
              <button
                type="button"
                className={`provider-tab ${provider === 'google' ? 'active' : ''}`}
                onClick={() => {
                  setProvider('google')
                  setModel('gemini-2.5-flash')
                }}
              >
                Google Gemini
              </button>
              <button
                type="button"
                className={`provider-tab ${provider === 'openai' ? 'active' : ''}`}
                onClick={() => {
                  setProvider('openai')
                  setModel('gpt-4o-mini')
                }}
              >
                OpenAI
              </button>
            </div>
          </div>

          <div className="form-group">
            <div className="label-row">
              <label htmlFor="api-key-input">
                {provider === 'huggingface'
                  ? 'Hugging Face Access Token'
                  : provider === 'google'
                  ? 'Google AI Studio Key'
                  : 'OpenAI API Key'}
              </label>
              <a
                href={help.url}
                target="_blank"
                rel="noreferrer"
                className="helper-link"
              >
                {help.label} &rarr;
              </a>
            </div>
            <div className="input-password-wrapper">
              <input
                id="api-key-input"
                type={showKey ? 'text' : 'password'}
                placeholder={
                  provider === 'huggingface'
                    ? 'hf_...'
                    : provider === 'google'
                    ? 'AIzaSy...'
                    : 'sk-proj-...'
                }
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                autoFocus
                required
              />
              <button
                type="button"
                className="show-key-btn"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="model-select">Model</label>
            {provider === 'huggingface' ? (
              <select
                id="model-select"
                value={model || 'mistralai/Mistral-7B-Instruct-v0.3'}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="mistralai/Mistral-7B-Instruct-v0.3">
                  mistralai/Mistral-7B-Instruct-v0.3 (Recommended)
                </option>
                <option value="meta-llama/Llama-3.2-3B-Instruct">
                  meta-llama/Llama-3.2-3B-Instruct (Fast)
                </option>
                <option value="Qwen/Qwen2.5-7B-Instruct">
                  Qwen/Qwen2.5-7B-Instruct (High Accuracy)
                </option>
                <option value="microsoft/Phi-3.5-mini-instruct">
                  microsoft/Phi-3.5-mini-instruct (Compact)
                </option>
                <option value="HuggingFaceH4/zephyr-7b-beta">
                  HuggingFaceH4/zephyr-7b-beta
                </option>
              </select>
            ) : provider === 'google' ? (
              <select
                id="model-select"
                value={model || 'gemini-2.5-flash'}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash (Fast & Recommended)</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro (High Reasoning)</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
              </select>
            ) : (
              <select
                id="model-select"
                value={model || 'gpt-4o-mini'}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="gpt-4o-mini">gpt-4o-mini (Fast & Recommended)</option>
                <option value="gpt-4o">gpt-4o</option>
              </select>
            )}
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn primary"
              disabled={loading || !apiKey.trim()}
            >
              {loading ? 'Saving...' : 'Save & Activate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
