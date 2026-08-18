export default function ChatMessage({ message, onShowCitations }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message ${message.role} ${message.error ? 'error' : ''}`}>
      <div className="avatar">{isUser ? 'You' : 'AI'}</div>
      <div className="bubble">
        <p>{message.content}</p>
        {!isUser && message.citations?.length > 0 && (
          <button
            type="button"
            className="citation-link"
            onClick={() => onShowCitations(message.citations)}
          >
            View {message.citations.length} source
            {message.citations.length > 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  )
}
