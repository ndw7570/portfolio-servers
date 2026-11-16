// 화면에 나오는 고정 내용. 프로젝트가 늘면 PROJECTS 에 항목을 더한다.

export const OWNER = '남덕우'

export const PROJECTS = [
  {
    id: 'standardization',
    title: '데이터 표준화',
    period: '2023',
    summary:
      '공공기관 DB의 컬럼 이름을 단어 단위로 쪼개 표준사전을 만들고, 그 사전이 얼마나 정돈됐는지 점수로 재는 도구입니다. 기획부터 파이썬 구현까지 혼자 했습니다.',
    notice: '화면의 데이터는 공개용으로 줄이고 가린 샘플입니다. 부서, 시스템, 테이블 이름은 실제 값이 아닙니다.',
    items: [
      {
        id: 'process',
        plan: '표준화 프로세스 정리',
        planNote: '입력에서 사전 4종까지 가는 처리 순서를 정의한 문서',
        result: '사전 4종 자동 구축',
        doc: { key: 'process', shown: 5, total: 21 },
      },
      {
        id: 'design',
        plan: '표준화 설계',
        planNote: '용어, 단어, 도메인, 코드 사이의 관계와 매핑 구조 설계',
        result: '정의서와 매핑 정보',
        doc: { key: 'design', shown: 4, total: 21 },
      },
      {
        id: 'criteria',
        plan: '표준화 점검 기준',
        planNote: '사전 품질을 재는 진단 항목과 계산식',
        result: '정규성 채점',
        doc: { key: 'criteria', shown: 3, total: 7 },
      },
      {
        id: 'pmss',
        plan: '점검 기준 개발 과정',
        planNote: '행안부 지침을 진단 코드로 옮긴 과정 (PMSS)',
        result: '사전별 점수 비교',
        doc: { key: 'pmss', shown: 3, total: 17 },
      },
    ],
  },
]

export const SCORE_AXES = ['용어', '단어', '도메인', '코드']

// 2023년에 원본 노트북으로 실제 사전을 채점한 기록이다. 이 사이트에서 다시 계산한 값이 아니다.
// 기관 내부 사전은 이름을 가렸다.
export const RECORDED_SCORES = [
  { name: '행안부 공통표준사전', note: '코드사전은 제공되지 않아 100점으로 둠', scores: [99.91, 100.0, 98.74, 100.0] },
  { name: '기관 내부 사전 A', note: '', scores: [98.51, 97.53, 83.7, 100.0] },
  { name: '민간 SI 표준사전 (2010)', note: '', scores: [99.59, 81.7, 78.97, 64.29] },
  { name: '기관 내부 사전 B', note: '단어 점수 0점으로 기록됨', scores: [99.83, 0.0, 56.71, 55.3] },
  { name: '기관 내부 사전 C', note: '단어 점수 0점으로 기록됨', scores: [90.58, 0.0, 70.78, 63.14] },
]

export const SERIES_COLORS = ['#0C6B6B', '#D99A00', '#B8402F', '#4A5FA8', '#7A4E8C', '#13262B']
