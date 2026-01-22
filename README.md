🧪 AI 서술형 채점 및 데이터 저장 시스템

이 프로젝트는 Streamlit을 기반으로 학생들의 서술형 답안을 수집하고, OpenAI GPT API를 사용하여 실시간 피드백을 제공하며, 그 결과를 Supabase 데이터베이스에 자동으로 저장하는 교육용 웹 애플리케이션입니다.

🚀 주요 기능

서술형 문항 인터페이스: 3가지 과학 문항에 대해 학번과 답안을 입력받는 사용자 친화적 폼(Form).

AI 실시간 채점: OpenAI의 최신 모델을 활용하여 교사가 설정한 채점 기준에 따라 O/X 판정 및 맞춤형 피드백 생성.

데이터베이스 연동: 제출된 답안, AI 피드백, 채점 기준, 시간 정보를 Supabase 클라우드 DB에 실시간 저장.

세션 관리: 페이지 리런(Rerun) 시에도 채점 결과가 초기화되지 않도록 세션 상태 유지.

🛠 기술 스택

분류

기술

비고

Frontend



파이썬 기반 웹 프레임워크

AI Engine



GPT 모델을 통한 서술형 채점

Backend



PostgreSQL 기반 실시간 DB 저장

⚙️ 설정 방법 (Secrets.toml)

Streamlit 앱 배포 또는 로컬 실행 시 .streamlit/secrets.toml 파일에 아래 정보를 설정해야 합니다.

# OpenAI API 설정
OPENAI_API_KEY = "your_openai_api_key_here"

# Supabase 설정
SUPABASE_URL = "[https://your-project-id.supabase.co](https://your-project-id.supabase.co)"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key_here"


📝 시스템 아키텍처 및 흐름

학생: 학번 및 3문항 답안 작성 → [제출] 버튼 클릭.

시스템: 필수 입력값 검증 후 submitted_ok 상태 활성화.

교사/학생: [GPT 피드백 확인] 버튼 클릭.

AI: 설정된 GRADING_GUIDELINES를 참고하여 문항별 피드백 생성.

DB: 생성된 모든 데이터(답안+피드백)를 student_submissions 테이블에 insert.

화면: 시각적으로 구분된(Success/Info) 피드백 박스 노출.

💡 채점 기준 예시 (코드 내 수정 가능)

GRADING_GUIDELINES = {
    1: "기체 입자의 운동은 온도와 비례 관계임을 언급하고, 입자 충돌·속도 증가 예를 기술한다.",
    2: "일정한 온도에서, 기체의 압력과 부피가 서로 반비례한다.",
    3: "전도는 입자 간 직접 충돌, 대류는 유체의 순환, 복사는 전자기파를 통한 열 이동 방식이다.",
}


⚠️ 주의 사항

API 키 보안: SUPABASE_SERVICE_ROLE_KEY는 서버 전용 키이므로 절대 클라이언트 코드에 노출되지 않도록 주의하세요.

라이브러리 설치: 실행 전 pip install streamlit supabase openai 명령어로 필수 라이브러리를 설치해야 합니다.

GPT 모델: 현재 코드는 gpt-5-mini(가칭)로 설정되어 있으니, 실제 사용 가능한 모델명(예: gpt-4o-mini)으로 수정하여 사용하세요.

이 시스템을 통해 서술형 채점의 부담을 줄이고 학생들에게 즉각적인 학습 교정을 지원할 수 있습니다! 🎓
