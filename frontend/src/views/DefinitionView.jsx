import { useMemo, useState } from 'react'
import DataTable from '../components/DataTable'
import Tabs from '../components/Tabs'

const TABLES = [
  { id: 'column_definition', label: '테이블컬럼정의서' },
  { id: 'code_definition', label: '코드정의서' },
  { id: 'term_mapping', label: '용어 매핑' },
  { id: 'code_mapping', label: '코드 매핑' },
]
const CHANGED = '변경'
const CHANGE_COLUMN = '변경'
const WORD_ABBR_COLUMN = '단어영문약어명'
const WORD_NAME_COLUMN = '표준단어명'

export default function DefinitionView({ run }) {
  const [tab, setTab] = useState('column_definition')
  const table = run.outputs[tab]
  const isMapping = tab.endsWith('_mapping')

  const words = useMemo(() => {
    const dictionary = run.outputs.word_dict
    const abbr = dictionary.columns.indexOf(WORD_ABBR_COLUMN)
    const name = dictionary.columns.indexOf(WORD_NAME_COLUMN)
    return dictionary.rows.map((row) => `${row[abbr]} ${row[name]}`)
  }, [run])

  const changedCount = (id) => {
    const target = run.outputs[id]
    const index = target.columns.indexOf(CHANGE_COLUMN)
    return target.rows.filter((row) => row[index] === CHANGED).length
  }

  const changeIndex = table.columns.indexOf(CHANGE_COLUMN)
  const cellClass = (value, column, row) => {
    if (changeIndex < 0 || row[changeIndex] !== CHANGED) return ''
    if (column.includes('TO-BE')) return 'cell-changed'
    if (column.includes('AS-IS')) return 'cell-before'
    return ''
  }
  // 매핑 표의 숫자는 단어사전의 행 번호다. 번호만으로는 읽을 수 없어 단어를 옆에 붙인다
  const renderCell = (value, column) =>
    isMapping && column.startsWith('단어') && value !== ''
      ? <span className="map-cell"><b>{value}</b> {words[Number(value)]}</span>
      : undefined

  return (
    <>
      <section>
        <h3>이름이 어떻게 바뀌었나</h3>
        <p className="lead">
          컬럼 한글명 {run.outputs.column_definition.rows.length}개 가운데 {changedCount('column_definition')}개,
          코드 한글명 {run.outputs.code_definition.rows.length}행 가운데 {changedCount('code_definition')}행이
          표준 단어 조합으로 바뀌었습니다. 영문 물리명은 그대로 두고 한글명만 사전에 맞춥니다.
        </p>
        <Tabs label="정의서와 매핑" active={tab} onChange={setTab} tabs={TABLES} />
        {isMapping && (
          <p className="aside">
            굵은 숫자는 단어사전의 행 번호입니다. 단어 이름을 고치면 이 번호를 따라 용어 전체에 반영됩니다.
          </p>
        )}
        <DataTable key={tab} table={table} cellClass={cellClass} renderCell={renderCell} />
      </section>
    </>
  )
}
