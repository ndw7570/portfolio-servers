import { useEffect, useState } from 'react'
import { tryTerm } from '../api'

const DATA_TYPES = ['CHAR', 'VARCHAR2', 'NUMBER', 'DATE']
const EXAMPLES = ['HSP_CAR_APV_CHG_DT', 'TRN_NO', 'rgtr_id', 'STN_RUN_ORDR']
const TYPING_PAUSE_MS = 350

// 컬럼 이름을 '_' 에서 뜯어 단어로 나누는 과정을 그대로 보여 준다. 계산은 서버의 파이썬이 한다.
export default function TicketSplitter() {
  const [name, setName] = useState(EXAMPLES[0])
  const [dataType, setDataType] = useState('CHAR')
  const [length, setLength] = useState(8)
  const [trace, setTrace] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (name.trim() === '') {
      setTrace(null)
      setError('')
      return undefined
    }
    let isCurrent = true
    const timer = setTimeout(async () => {
      try {
        const result = await tryTerm({ name, data_type: dataType, data_length: Number(length) || 1, data_scale: 0 })
        if (isCurrent) {
          setTrace(result)
          setError('')
        }
      } catch (caught) {
        if (isCurrent) setError(caught.message)
      }
    }, TYPING_PAUSE_MS)
    return () => {
      isCurrent = false
      clearTimeout(timer)
    }
  }, [name, dataType, length])

  return (
    <section className="splitter" aria-labelledby="splitter-title">
      <h3 id="splitter-title">컬럼 이름 하나를 넣어 보세요</h3>
      <div className="splitter-form">
        <label className="field field-wide">
          <span>컬럼 물리명</span>
          <input value={name} maxLength={60} spellCheck={false} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="field">
          <span>데이터타입</span>
          <select value={dataType} onChange={(event) => setDataType(event.target.value)}>
            {DATA_TYPES.map((type) => <option key={type}>{type}</option>)}
          </select>
        </label>
        <label className="field field-narrow">
          <span>길이</span>
          <input type="number" min={1} max={4000} value={length} onChange={(event) => setLength(event.target.value)} />
        </label>
      </div>
      <div className="examples">
        {EXAMPLES.map((example) => (
          <button key={example} type="button" className="chip-button" onClick={() => setName(example)}>{example}</button>
        ))}
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      {trace && (
        <div className="ticket-area" aria-live="polite">
          {trace.removed && (
            <p className="ticket-note">
              규칙에 맞지 않는 글자를 정리했습니다: <code>{trace.input}</code> → <code>{trace.cleaned || '(남은 글자 없음)'}</code>
            </p>
          )}
          <ol className="ticket">
            {trace.words.map((word, index) => (
              <li key={`${word.abbr}-${index}`} className={word.name ? 'stub' : 'stub is-unknown'}>
                <span className="stub-abbr">{word.abbr}</span>
                <span className="stub-name">{word.name || '사전에 없음'}</span>
              </li>
            ))}
          </ol>
          {trace.is_complete ? (
            <dl className="ticket-result">
              <div><dt>표준 용어명</dt><dd>{trace.term_kor}</dd></div>
              <div><dt>도메인명</dt><dd className="mono">{trace.domain}</dd></div>
            </dl>
          ) : (
            <p className="ticket-note">
              {trace.words.length === 0
                ? '쪼갤 단어가 없습니다. 영문 대문자와 숫자, 밑줄로 이름을 적어 주세요.'
                : '사전에 없는 단어가 있어 용어명을 만들지 않았습니다. 원본 도구는 여기서 멈추고 사람이 단어를 정의합니다.'}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
