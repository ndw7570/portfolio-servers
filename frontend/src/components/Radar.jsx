const SIZE = 320
const CENTER = SIZE / 2
const RADIUS = 112
const RINGS = [25, 50, 75, 100]

// 12시 방향에서 시작해 시계 방향으로 돈다 (원본 matplotlib 차트와 같은 방향)
function point(axisIndex, axisCount, value) {
  const angle = (Math.PI * 2 * axisIndex) / axisCount - Math.PI / 2
  const distance = (RADIUS * value) / 100
  return [CENTER + distance * Math.cos(angle), CENTER + distance * Math.sin(angle)]
}

const polygon = (values) => values.map((value, i) => point(i, values.length, value).join(',')).join(' ')

export default function Radar({ axes, series }) {
  const summary = series.map((s) => `${s.name}: ${axes.map((a, i) => `${a} ${s.scores[i]}`).join(', ')}`).join(' / ')
  return (
    <svg className="radar" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={`점수 레이더 차트. ${summary}`}>
      {RINGS.map((ring) => (
        <polygon key={ring} className="radar-ring" points={polygon(axes.map(() => ring))} />
      ))}
      {axes.map((axis, i) => {
        const [x, y] = point(i, axes.length, 100)
        const [labelX, labelY] = point(i, axes.length, 122)
        return (
          <g key={axis}>
            <line className="radar-axis" x1={CENTER} y1={CENTER} x2={x} y2={y} />
            <text className="radar-label" x={labelX} y={labelY} textAnchor="middle" dominantBaseline="middle">
              {axis}
            </text>
          </g>
        )
      })}
      {series.map((s) => (
        <polygon key={s.name} points={polygon(s.scores)} fill={s.color} fillOpacity="0.14" stroke={s.color} strokeWidth="2" />
      ))}
    </svg>
  )
}
