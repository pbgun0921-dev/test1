import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime
import pytz

# --------------------------------------------------
# 1. 페이지 설정 및 로그인
# --------------------------------------------------
st.set_page_config(page_title="교사용 대시보드", layout="wide", page_icon="📊")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def check_password():
    # secrets에 비밀번호가 설정되어 있는지 확인
    if "TEACHER_PASSWORD" not in st.secrets:
        st.error("secrets.toml 파일에 [TEACHER_PASSWORD] 설정이 필요합니다.")
        st.stop()
        
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

# --------------------------------------------------
# 2. Supabase 연결 및 데이터 로드
# --------------------------------------------------
@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("secrets.toml 파일에 Supabase 설정이 누락되었습니다.")
        st.stop()

supabase = get_supabase_client()

def load_data():
    """Supabase에서 전체 데이터를 가져와 DataFrame으로 변환"""
    try:
        # 모든 데이터를 최신순으로 가져오기
        response = supabase.table("student_submissions").select("*").execute()
        data = response.data
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # 날짜 포맷 변환 (UTC -> KST)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            kst = pytz.timezone('Asia/Seoul')
            # tz_convert 전 timezone 정보가 없는 경우 처리
            if df['created_at'].dt.tz is None:
                df['created_at'] = df['created_at'].dt.tz_localize('UTC')
            
            df['제출시간'] = df['created_at'].dt.tz_convert(kst).dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            df['제출시간'] = "시간 정보 없음"
            
        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

def process_scores(df):
    """피드백(O/X) 텍스트를 분석하여 점수 컬럼 생성"""
    if df.empty:
        return df

    # 문항별 점수 계산 (O: 1점, X: 0점)
    for i in range(1, 4):
        col_name = f'feedback_{i}'
        score_col = f'Q{i}_점수'
        
        if col_name in df.columns:
            # 안전한 처리를 위해 문자열 변환 후 체크
            df[score_col] = df[col_name].apply(
                lambda x: 1 if str(x).strip().upper().startswith("O") else 0
            )
        else:
            df[score_col] = 0
    
    # 총점 계산
    score_cols = ['Q1_점수', 'Q2_점수', 'Q3_점수']
    df['총점'] = df[score_cols].sum(axis=1)
    
    return df

# --------------------------------------------------
# 3. 메인 UI 구성
# --------------------------------------------------
st.title("📊 과학 서술형 평가 결과")

if st.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로딩 및 처리
raw_df = load_data()
df = process_scores(raw_df)

if df.empty:
    st.warning("아직 제출된 데이터가 없습니다.")
    st.stop()

# --------------------------------------------------
# 4. 통계 및 시각화
# --------------------------------------------------
# 상단 지표 (Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 제출 수", f"{len(df)}명")
col2.metric("평균 점수", f"{df['총점'].mean():.1f}점 / 3.0점")
col3.metric("만점자 수", f"{len(df[df['총점'] == 3])}명")
col4.metric("최근 제출", df['제출시간'].max())

st.markdown("---")

# 차트 영역
c1, c2 = st.columns(2)

with c1:
    st.subheader("문항별 정답률")
    q_means = df[['Q1_점수', 'Q2_점수', 'Q3_점수']].mean() * 100
    q_stats = pd.DataFrame({
        '문항': ['문항 1', '문항 2', '문항 3'],
        '정답률': q_means.values
    })
    
    fig_bar = px.bar(
        q_stats, x='문항', y='정답률',
        text_auto='.1f',
        color='정답률',
        range_y=[0, 100],
        title="문항별 정답률 (%)"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.subheader("총점 분포")
    score_counts = df['총점'].value_counts().sort_index().reset_index()
    score_counts.columns = ['점수', '학생수']
    
    fig_pie = px.pie(
        score_counts, values='학생수', names='점수',
        title="점수대별 학생 분포",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# --------------------------------------------------
# 5. 상세 데이터 및 개별 조회
# --------------------------------------------------
st.markdown("---")
st.header("학생별 상세 결과")

# 전체 데이터 테이블
display_cols = ['student_id', '총점', 'Q1_점수', 'Q2_점수', 'Q3_점수', '제출시간']
# 존재하는 컬럼만 선택
final_cols = [c for c in display_cols if c in df.columns]

st.dataframe(
    df[final_cols].sort_values(by='제출시간', ascending=False),
    use_container_width=True,
    hide_index=True
)

# 개별 조회 (Drill-down)
st.subheader("🔍 개별 학생 답안 조회")

# 학번 리스트 생성 (중복 제거 및 정렬)
student_list = sorted(df['student_id'].unique())
selected_student = st.selectbox("학생 선택", student_list)

if selected_student:
    # 해당 학생의 가장 최근 제출 데이터 가져오기
    student_data = df[df['student_id'] == selected_student].sort_values('제출시간').iloc[-1]
    
    with st.container(border=True):
        st.markdown(f"### 👤 {student_data['student_id']} (총점: {student_data['총점']}점)")
        st.caption(f"제출 시간: {student_data['제출시간']}")
        
        tab1, tab2, tab3 = st.tabs(["문항 1", "문항 2", "문항 3"])
        
        # 반복되는 표시 로직을 함수화하여 실수 방지
        def show_qna(num):
            ans_key = f'answer_{num}'
            fb_key = f'feedback_{num}'
            score_key = f'Q{num}_점수'
            
            c_q, c_a = st.columns(2)
            with c_q:
                st.info(f"**학생 답안 {num}**")
                st.write(student_data.get(ans_key, "-"))
            with c_a:
                is_correct = student_data.get(score_key, 0) == 1
                status = "✅ 정답" if is_correct else "❌ 오답"
                color = "green" if is_correct else "red"
                
                # f-string 포맷 단순화
                st.markdown(f":{color}[**AI 피드백 ({status})**]")
                st.write(student_data.get(fb_key, "-"))

        with tab1: show_qna(1)
        with tab2: show_qna(2)
        with tab3: show_qna(3)
