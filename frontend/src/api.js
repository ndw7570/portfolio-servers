async function request(path, options) {
  let response
  try {
    response = await fetch(`/api${path}`, options)
  } catch {
    throw new Error('서버에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(typeof body.detail === 'string' ? body.detail : '요청을 처리하지 못했습니다.')
    error.status = response.status
    throw error
  }
  return response.json()
}

const postJson = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) })

export const fetchInput = () => request('/input')
export const runPipeline = () => postJson('/runs')
export const tryTerm = (payload) => postJson('/try', payload)

// 첫 방문이면 실행 기록이 없다. 그때는 한 번 돌려서 보여 준다.
export async function fetchLatestRun() {
  try {
    return await request('/runs/latest')
  } catch (error) {
    if (error.status === 404) return runPipeline()
    throw error
  }
}
