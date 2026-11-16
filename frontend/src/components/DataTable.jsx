import { useState } from 'react'

const PREVIEW_ROWS = 10

// rows 는 배열의 배열이다. cellClass(값, 열 이름, 행) 로 칸마다 강조를 줄 수 있다.
export default function DataTable({ table, cellClass, renderCell }) {
  const [isExpanded, setIsExpanded] = useState(false)
  if (!table || table.rows.length === 0) return <p className="empty">표시할 행이 없습니다.</p>

  const rows = isExpanded ? table.rows : table.rows.slice(0, PREVIEW_ROWS)
  const hiddenCount = table.rows.length - PREVIEW_ROWS

  return (
    <div className="table-block">
      <div className="table-scroll" tabIndex={0} role="region" aria-label="데이터 표">
        <table>
          <thead>
            <tr>
              {table.columns.map((column) => (
                <th key={column} scope="col">{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((value, columnIndex) => {
                  const column = table.columns[columnIndex]
                  return (
                    <td key={column} className={cellClass?.(value, column, row) || undefined}>
                      {renderCell?.(value, column, row) ?? value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-foot">
        <span>{table.rows.length}행</span>
        {hiddenCount > 0 && (
          <button type="button" className="link-button" onClick={() => setIsExpanded(!isExpanded)}>
            {isExpanded ? '접기' : `나머지 ${hiddenCount}행 보기`}
          </button>
        )}
      </div>
    </div>
  )
}
