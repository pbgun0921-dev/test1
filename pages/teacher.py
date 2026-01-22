import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime
import pytz

# --------------------------------------------------
# 1. 설정 및 Supabase 연결
# --------------------------------------------------
st.set_page_config(page_title="교사용 대시보드", layout="wide", page_icon="📊")

# 로그인 보안 (간단한 비밀번호 설정)
# secrets.toml에 [TEACHER_PASSWORD]를 설정해야 합니다.
# 예: TEACHER_PASSWORD = "school_admin"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def check_password():
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if password == st.secrets["TEACHER_PASSWORD"]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")

if not st.session_state.logged_in:
    st.title("🔒 교사용 대시보드 로그인")
    check_password()
    st.stop()

# Supabase 클라이언트 연결
@st.cache_resource
def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Secrets 설정 오류: SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인하세요.")
        st.stop()

supabase = get_supabase_client()

# --------------------------------------------------
# 2. 데이터 로드 및 전처리 함수
# --------------------------------------------------
def load_data():
    """Supabase에서 전체 제출 데이터를 가져와 DataFrame으로 변환"""
    try:
        response = supabase.table("student_submissions").select("*").execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # 날짜 포맷 변환 (UTC -> KST)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            kst = pytz.timezone('Asia/Seoul')
            df['제출시간'] = df['created_at'].dt.tz_convert(kst).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

def process_scores(df):
    """피드백(O/X) 텍스트를 분석하여 점수 컬럼 생성"""
    if df.empty:
        return df

    # 점수 계산 로직 (O로 시작하면 1점, 아니면 0점)
    # 학생 코드의 normalize_feedback 함수 덕분에 포맷이 일정함
    for i in range(1, 4):
        col_name = f'feedback_{i}'
        score_col = f'Q{i}_점수'
        
        if col_name in df.columns:
            # "O:" 로 시작하는지 확인하여 점수 부여
            df[score_col] = df[col_name].apply(lambda x: 1 if str(x).strip().startswith("O") else 0)
    
    # 총점 계산 (3점 만점)
    score_cols = [c for c in df.columns if c.endswith('_점수')]
    if score_cols:
        df['총점'] = df[score_cols].sum(axis=1)
        
    return df

# --------------------------------------------------
# 3. 메인 UI 구성
# --------------------------------------------------
st.title("📊 과학 서술형 평가 결과 대시보드")

# 데이터 새로고침 버튼
if st.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로딩
raw_df = load_data()
df = process_scores(raw_df)

if df.empty:
    st.warning("아직 제출된 데이터가 없습니다.")
    st.stop()

# 사이드바 필터
st.sidebar.header("검색 필터")
search_id = st.sidebar.text_input("학번 검색", "")
if search_id:
    df = df[df['student_id'].str.contains(search_id)]

# --------------------------------------------------
# 4. 통계 요약 (Metrics)
# --------------------------------------------------
st.header("1. 전체 현황")
col1, col2, col3, col4 = st.columns(4)

total_students = len(df)
avg_score = df['총점'].mean()
perfect_score_count = len(df[df['총점'] == 3])

col1.metric("총 제출 수", f"{total_students}명")
col2.metric("평균 점수 (3점 만점)", f"{avg_score:.1f}점")
col3.metric("만점자 수", f"{perfect_score_count}명")
col4.metric("최근 제출", df['제출시간'].max())

st.divider()

# --------------------------------------------------
# 5. 차트 시각화
# --------------------------------------------------
st.header("2. 성취도 분석")

c1, c2 = st.columns(2)

with c1:
    st.subheader("문항별 정답률")
    # 문항별 평균 점수 계산 (0~1 사이 값이므로 *100 해서 퍼센트로)
    q_stats = df[['Q1_점수', 'Q2_점수', 'Q3_점수']].mean() * 100
    q_stats_df = q_stats.reset_index()
    q_stats_df.columns = ['문항', '정답률']
    
    fig_bar = px.bar(q_stats_df, x='문항', y='정답률', text_auto='.1f', 
                     color='정답률', range_y=[0, 100], title="문항별 정답률 (%)")
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.subheader("총점 분포")
    score_counts = df['총점'].value_counts().sort_index().reset_index()
    score_counts.columns = ['점수', '학생수']
    
    fig_pie = px.pie(score_counts, values='학생수', names='점수', 
                     title="점수대별 학생 분포", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --------------------------------------------------
# 6. 상세 데이터 테이블
# --------------------------------------------------
st.header("3. 학생별 상세 결과")

# 테이블에 표시할 주요 컬럼 선택
display_cols = ['student_id', '총점', 'Q1_점수', 'Q2_점수', 'Q3_점수', '제출시간']
st.dataframe(
    df[display_cols].sort_values(by='제출시간', ascending=False),
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# 7. 개별 학생 답안 상세 조회 (Drill-down)
# --------------------------------------------------
st.subheader("🔍 개별 학생 답안 및 피드백 상세 조회")

selected_student = st.selectbox("학생 선택 (학번)", df['student_id'].unique())

if selected_student:
    student_data = df[df['student_id'] == selected_student].iloc[-1] # 가장 최근 제출 기준
    
    with st.container(border=True):
        st.markdown(f"### 👤 학번: {student_data['student_id']} (총점: {student_data['총점']}점)")
        st.caption(f"제출 시간: {student_data['제출시간']}")
        
        tab1, tab2, tab3 = st.tabs(["문항 1", "문항 2", "문항 3"])
        
        # 문항 1
        with tab1:
            c_q, c_a = st.columns([1, 1])
            with c_q:
                st.info("**학생 답안**")
                st.write(student_data['answer_1'])
            with c_a:
                status = "✅ 정답" if student_data['Q1_점수'] == 1 else "❌ 오답"
                color = "green" if student_data['Q1_점수'] == 1 else "red"
                st.markdown(f":{color}[**AI 피드백 ({status})**]")
                st.write(student_data['feedback_1'])

        # 문항 2
        with tab2:
            c_q, c_a = st.columns([1, 1])
            with c_q:
                st.info("**학생 답안**")
                st.write(student_data['answer_2'])
            with c_a:
                status = "✅ 정답" if student_data['Q2_점수'] == 1 else "❌ 오답"
                color = "green" if student_data['Q2_점수'] == 1 else "red"
                st.markdown(f":{color}[**AI 피드백 ({status})**]")
                st.write(student_data['feedback_2'])

        # 문항 3
        with tab3:
            c_q, c_a = st.columns([1, 1])
            with c_q:
                st.info("**학생 답안**")
                st.write(student_data['answer_3'])
            with c_a:
                status = "✅ 정답" if student_data['Q3_점수'] == 1 else "❌ 오답"
                color = "green" if student_data['Q3_점수'] == 1 else "red"
                st.markdown(f":{color}[**AI 피드백 ({status})**]")
                st.write(student_data['feedback_3'])
```

### ✅ 구현된 기능 설명

1.  **관리자 로그인**:
    * 학생들이 결과를 보지 못하도록 간단한 비밀번호 잠금 기능을 추가했습니다.
    * `.streamlit/secrets.toml` 파일에 `TEACHER_PASSWORD = "원하는비번"`을 추가해야 합니다.
2.  **데이터 시각화**:
    * **전체 현황**: 총 제출 수, 평균 점수 등을 Metric으로 한눈에 봅니다.
    * **문항별 정답률**: 막대 그래프로 어떤 문제가 가장 어려웠는지 파악할 수 있습니다.
    * **총점 분포**: 파이 차트로 점수대별 분포를 확인합니다.
3.  **자동 채점 점수 변환**:
    * AI가 남긴 피드백(`O: ...`, `X: ...`)을 자동으로 파싱하여 1점(정답)과 0점(오답)으로 변환합니다.
4.  **개별 상세 조회 (Drill-down)**:
    * 특정 학번을 선택하면 그 학생이 쓴 답안과 AI의 피드백을 나란히 비교해서 볼 수 있습니다.

### ⚙️ 실행 전 필수 설정 (`.streamlit/secrets.toml`)

`teacher.py`를 실행하기 위해 기존 `secrets.toml` 파일에 **비밀번호** 설정을 한 줄 추가해야 합니다.

```toml
# 기존 설정 유지
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
OPENAI_API_KEY = "sk-..."

# [추가] 교사용 대시보드 비밀번호
TEACHER_PASSWORD = "4321"
