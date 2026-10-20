export default function CitationCard({ citation }) {
  const relevance = Math.max(0, (1 - (citation.distance || 0)) * 100).toFixed(1)

  return (
    <article className="citation-card">
      <header>
        <div>
          <span className="cite-badge">[{citation.citation_id || 1}]</span>
          <h3>{citation.paper_title || citation.section}</h3>
        </div>
        <span className="score">{relevance}% match</span>
      </header>
      <div className="citation-meta">
        <span className="meta-tag">📄 Page {citation.page || 1}</span>
        {citation.section && <span className="meta-tag">§ {citation.section}</span>}
      </div>
      <p className="passage">{citation.text}</p>
    </article>
  )
}
