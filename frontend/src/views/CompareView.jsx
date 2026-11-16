import { useState } from 'react'
import Radar from '../components/Radar'
import { RECORDED_SCORES, SCORE_AXES, SERIES_COLORS } from '../content'

const average = (values) => (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2)

export default function CompareView({ run }) {
  const live = { name: '이 사이트의 샘플 사전', note: '지금 실행한 값', scores: SCORE_AXES.map((axis) => run.scores.totals[axis]) }
  const all = [...RECORDED_SCORES, live].map((entry, index) => ({ ...entry, color: SERIES_COLORS[index % SERIES_COLORS.length] }))
  const [hidden, setHidden] = useState([])
  const visible = all.filter((entry) => !hidden.includes(entry.name))

  const toggle = (name) =>
    setHidden(hidden.includes(name) ? hidden.filter((other) => other !== name) : [...hidden, name])

  return (
    <section>
      <h3>같은 기준으로 여러 사전을 재면</h3>
      <p className="lead">
        위 다섯 줄은 2023년에 원본 노트북으로 실제 사전을 채점한 기록입니다. 이 사이트에서 다시 계산한 값이 아니고,
        기관 내부 사전은 이름을 가렸습니다. 마지막 줄만 지금 서버가 계산한 값입니다.
      </p>
      <div className="compare">
        <Radar axes={SCORE_AXES} series={visible} />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="사전별 점수 표">
          <table className="score-table">
            <thead>
              <tr>
                <th scope="col">사전</th>
                {SCORE_AXES.map((axis) => <th key={axis} scope="col">{axis}</th>)}
                <th scope="col">평균</th>
              </tr>
            </thead>
            <tbody>
              {all.map((entry) => (
                <tr key={entry.name}>
                  <td>
                    <label className="series-toggle">
                      <input type="checkbox" checked={!hidden.includes(entry.name)} onChange={() => toggle(entry.name)} />
                      <span className="swatch" style={{ background: entry.color }} />
                      {entry.name}
                    </label>
                    {entry.note && <small>{entry.note}</small>}
                  </td>
                  {entry.scores.map((score, index) => <td key={SCORE_AXES[index]} className="num">{score}</td>)}
                  <td className="num"><b>{average(entry.scores)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
