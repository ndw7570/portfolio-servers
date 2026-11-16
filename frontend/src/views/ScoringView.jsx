import Radar from '../components/Radar'
import { SCORE_AXES, SERIES_COLORS } from '../content'

const FULL_SCORE = 100

export default function ScoringView({ run }) {
  const { items, totals, overall } = run.scores
  const failing = items.filter((item) => item.score < FULL_SCORE)

  return (
    <>
      <section className="score-top">
        <div>
          <h3>방금 만든 사전을 채점한 결과</h3>
          <p className="lead">
            진단 항목 {items.length}개를 실제로 계산했습니다. 사전별 점수는 항목 평균이고, 총점은 네 사전의 평균입니다.
          </p>
          <dl className="totals">
            <div className="total-overall"><dt>총점</dt><dd>{overall}</dd></div>
            {SCORE_AXES.map((axis) => (
              <div key={axis}><dt>{axis}사전</dt><dd>{totals[axis]}</dd></div>
            ))}
          </dl>
        </div>
        <Radar
          axes={SCORE_AXES}
          series={[{ name: '샘플 사전', color: SERIES_COLORS[0], scores: SCORE_AXES.map((axis) => totals[axis]) }]}
        />
      </section>

      {failing.length > 0 && (
        <section>
          <h3>감점된 항목 {failing.length}개</h3>
          <p className="aside">
            샘플이 일부러 고친 데이터가 아니라서 원본의 결함이 그대로 잡힙니다. 예를 들어 분류어가 영문뿐인 ID는
            규칙상 "기타"로 바뀌는데, 단어사전에는 "기타"라는 분류어가 없습니다.
          </p>
        </section>
      )}

      <section>
        <h3>진단 항목 전체</h3>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="진단 항목 표">
          <table className="score-table">
            <thead>
              <tr><th scope="col">진단 코드</th><th scope="col">사전</th><th scope="col">항목</th><th scope="col">조건</th><th scope="col">통과 / 전체</th><th scope="col">점수</th></tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.code} className={item.score < FULL_SCORE ? 'row-fail' : undefined}>
                  <td className="mono">{item.code}</td>
                  <td>{item.group}</td>
                  <td>{item.title}</td>
                  <td>{item.rule}</td>
                  <td className="num">{item.passed} / {item.total}</td>
                  <td className="num">
                    <span className="bar" aria-hidden="true"><span style={{ width: `${item.score}%` }} /></span>
                    {item.score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}
