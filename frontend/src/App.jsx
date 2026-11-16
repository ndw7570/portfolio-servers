import { useEffect, useState } from 'react'
import { fetchInput, fetchLatestRun, runPipeline } from './api'
import DocViewer from './components/DocViewer'
import Tabs from './components/Tabs'
import { OWNER, PROJECTS } from './content'
import CompareView from './views/CompareView'
import DefinitionView from './views/DefinitionView'
import PipelineView from './views/PipelineView'
import ScoringView from './views/ScoringView'

const RESULT_VIEWS = { process: PipelineView, design: DefinitionView, criteria: ScoringView, pmss: CompareView }
const PANE_TABS = [
  { id: 'result', label: '결과물' },
  { id: 'plan', label: '기획 문서' },
]

export default function App() {
  const project = PROJECTS[0]
  // 주소의 # 뒤에 항목을 남겨서, 특정 결과물 화면을 링크로 바로 보낼 수 있게 한다
  const [itemId, setItemId] = useState(() => {
    const fromHash = window.location.hash.slice(1)
    return project.items.some((entry) => entry.id === fromHash) ? fromHash : project.items[0].id
  })
  const [pane, setPane] = useState('result')
  const [run, setRun] = useState(null)
  const [input, setInput] = useState(null)
  const [error, setError] = useState('')
  const [isRunning, setIsRunning] = useState(false)

  useEffect(() => {
    Promise.all([fetchLatestRun(), fetchInput()])
      .then(([latestRun, sampleInput]) => {
        setRun(latestRun)
        setInput(sampleInput)
      })
      .catch((caught) => setError(caught.message))
  }, [])

  const rerun = async () => {
    setIsRunning(true)
    setError('')
    try {
      setRun(await runPipeline())
    } catch (caught) {
      setError(caught.message)
    } finally {
      setIsRunning(false)
    }
  }

  const selectItem = (id) => {
    setItemId(id)
    window.history.replaceState(null, '', `#${id}`)
    setPane('result')
  }

  const item = project.items.find((candidate) => candidate.id === itemId)
  const ResultView = RESULT_VIEWS[item.id]
  const isReady = run !== null && input !== null

  return (
    <div className="shell">
      <aside className="rail">
        <p className="rail-owner">{OWNER} 포트폴리오</p>
        <h1 className="rail-title">{project.title}</h1>
        <p className="rail-summary">{project.summary}</p>
        <nav aria-label="기획 문서 목록">
          <p className="rail-label">기획 문서를 고르면 오른쪽에 그 결과물이 나옵니다</p>
          <ul className="plan-list">
            {project.items.map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  className={entry.id === itemId ? 'plan is-active' : 'plan'}
                  aria-current={entry.id === itemId ? 'true' : undefined}
                  onClick={() => selectItem(entry.id)}
                >
                  <span className="plan-name">{entry.plan}</span>
                  <span className="plan-result">결과물: {entry.result}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <p className="rail-notice">{project.notice}</p>
      </aside>

      <main className="stage">
        <header className="stage-head">
          <div>
            <p className="stage-plan">기획: {item.plan}</p>
            <h2>{pane === 'result' ? item.result : item.plan}</h2>
          </div>
          <Tabs label="보기 전환" tabs={PANE_TABS} active={pane} onChange={setPane} />
        </header>

        {error && <p className="error" role="alert">{error}</p>}

        {pane === 'plan' && <DocViewer key={item.id} item={item} />}
        {pane === 'result' && isReady && (
          <ResultView key={item.id} run={run} input={input} onRerun={rerun} isRunning={isRunning} />
        )}
        {pane === 'result' && !isReady && !error && <p className="empty">서버에서 파이프라인을 실행하고 있습니다.</p>}
      </main>
    </div>
  )
}
