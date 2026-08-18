export default function CitationCard({ citation }) {
  const relevance = Math.max(0, (1 - citation.distance) * 100).toFixed(1)

  return (
    <article className="citation-card">
      <header>
        <h3>{citation.section}</h3>
        <span className="score">{relevance}% match</span>
      </header>
      <p className="source">Source: {citation.source}</p>
      <p className="passage">{citation.text}</p>
    </article>
  )
}
