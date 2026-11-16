export default function DocViewer({ item }) {
  const { key, shown, total } = item.doc
  const pages = Array.from({ length: shown }, (_, index) => index + 1)
  return (
    <div className="doc">
      <p className="doc-meta">
        {item.planNote}. 전체 {total}쪽 가운데 {shown}쪽만 공개합니다.
      </p>
      {pages.map((page) => (
        <figure key={page} className="doc-page">
          <img src={`/docs/${key}-${page}.png`} alt={`${item.plan} 발췌 ${page}번째 쪽`} loading="lazy" />
        </figure>
      ))}
    </div>
  )
}
