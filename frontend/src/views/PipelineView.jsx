import { useState } from 'react'
import DataTable from '../components/DataTable'
import Tabs from '../components/Tabs'
import TicketSplitter from '../components/TicketSplitter'

const DICTIONARIES = [
  { id: 'term_dict', label: '용어사전' },
  { id: 'word_dict', label: '단어사전' },
  { id: 'domain_dict', label: '도메인사전' },
  { id: 'code_dict', label: '코드사전' },
]

export default function PipelineView({ run, input, onRerun, isRunning }) {
  const [inputTab, setInputTab] = useState('columns')
  const [outputTab, setOutputTab] = useState('term_dict')

  return (
    <>
      <TicketSplitter />

      <section>
        <div className="section-head">
          <h3>샘플 전체를 돌린 결과</h3>
          <button type="button" className="primary-button" onClick={onRerun} disabled={isRunning}>
            {isRunning ? '실행 중' : '다시 실행'}
          </button>
        </div>
        <p className="run-meta">
          실행 #{run.id} · {new Date(run.created_at).toLocaleString('ko-KR')} · {run.elapsed_ms}ms · 결과는 PostgreSQL에 저장됨
        </p>
        <ol className="steps">
          {run.steps.map((step) => (
            <li key={step.title} className="step">
              <div>
                <strong>{step.title}</strong>
                <p>{step.detail}</p>
              </div>
              <dl className="metrics">
                {Object.entries(step.metrics).map(([label, value]) => (
                  <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
                ))}
              </dl>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h3>입력</h3>
        <Tabs
          label="입력 데이터"
          active={inputTab}
          onChange={setInputTab}
          tabs={[
            { id: 'columns', label: '테이블컬럼정의서', count: input.columns.rows.length },
            { id: 'codes', label: '코드사전', count: input.codes.rows.length },
          ]}
        />
        <DataTable key={inputTab} table={input[inputTab]} />
        <p className="aside">한글명을 찾는 누적사전에는 단어 {input.word_count}개가 들어 있습니다.</p>
      </section>

      <section>
        <h3>출력: 표준사전 4종</h3>
        <Tabs
          label="표준사전"
          active={outputTab}
          onChange={setOutputTab}
          tabs={DICTIONARIES.map((d) => ({ ...d, count: run.outputs[d.id].rows.length }))}
        />
        <DataTable key={outputTab} table={run.outputs[outputTab]} />
      </section>
    </>
  )
}
