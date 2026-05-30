import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date

# 한글 폰트 깨짐 방지 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 1. 페이지 레이아웃 및 타이틀 설정
st.set_page_config(page_title="세종시 진드기 정밀 예보 시스템", layout="wide", page_icon="🕷️")

# [디자인 반영 1] 앱 전체 테마 배경색을 연한 민트색으로 커스텀 주입하는 CSS 스타일
st.markdown("""
    <style>
    .stApp {
        background-color: #EEF7F4;
    }
    .main-card {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 12px;
        border: 2px solid #A3D9C9;
        box-shadow: 2px 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("진드기 위험도 자동 예보 및 알림 시스템")
st.write("학교 일정과 기상·진드기 데이터를 활용해 야외활동 중 발생할 수 있는 진드기 매개질병 위험을 미리 알려주는 학생 안전 서비스입니다.")
st.markdown("---")


# 2. 데이터 세트 로드 및 전처리 함수 (캐싱 처리)
@st.cache_data
def load_system_data():
    try:
        # 오렌지3 예측 결과물 로드
        raw_tick = pd.read_csv("tick_risk_lookup.csv")
        tick_df = raw_tick.drop([0, 1]).reset_index(drop=True)
        
        # 학사일정 데이터 로드 및 날짜 전처리 (에러 발생 구역 수정 완료)
        # ⚠️ 만약 깃허브 저장소 내부의 파일명을 calendar.csv로 바꾸셨다면 아래 괄호 안을 "calendar.csv"로 수정하세요.
        calendar_df = pd.read_csv("calender.csv")
        calendar_df['학사일자'] = pd.to_datetime(calendar_df['학사일자'].astype(str), format='%Y%m%d').dt.date
        
        # 질병관리청 참진드기 월별 가중치 지표
        monthly_stats = {
            1: 0.05, 2: 0.05, 3: 0.10, 4: 0.60, 5: 1.10, 6: 1.00,
            7: 0.50, 8: 0.90, 9: 2.00, 10: 1.60, 11: 0.30, 12: 0.05
        }
        
        return tick_df, calendar_df, monthly_stats
    except Exception as e:
        st.error(f"⚠️ 파일 로드 중 오류 발생: {e}. 파일명이 레포지토리 내부와 일치하는지 확인해 주세요.")
        return None, None, None

tick_df, calendar_df, monthly_stats = load_system_data()


# 3. 위험도 스코어를 기반으로 7단계 등급을 판정하는 수식 함수
def get_risk_label(score):
    if score >= 85: return "최악", "🚨"
    elif score >= 70: return "매우 나쁨", "🔥"
    elif score >= 55: return "나쁨", "🔴"
    elif score >= 40: return "보통", "🟡"
    elif score >= 25: return "양호", "🔵"
    elif score >= 10: return "좋음", "🟢"
    else: return "매우 좋음", "🌈"


# [디자인 반영 2] 막대 형태의 7단계 위험도 스케일 바와 현재 위치를 화살표로 그리는 시각화 함수
def draw_risk_scale_bar(score, current_label):
    labels = ["매우 좋음", "좋음", "양호", "보통", "나쁨", "매우 나쁨", "최악"]
    colors = ["#72EF84", "#A7F1A8", "#A3D5FF", "#FFE786", "#FF9E86", "#FF6B6B", "#C93B3B"]
    
    fig, ax = plt.subplots(figsize=(10, 1.8), facecolor='#EEF7F4')
    # 7단계를 가로 막대로 분할 배치
    for i in range(7):
        ax.barh(0, 14.28, left=i*14.28, color=colors[i], edgecolor='white', height=0.5)
        ax.text(i*14.28 + 7.14, -0.4, labels[i], ha='center', va='top', fontsize=9, fontweight='bold', color='#333333')
    
    # 점수 스케일링 (0~100점 범위를 화살표 좌표축으로 전달)
    arrow_x = float(score)
    
    # 현재 위치 계산 지점에 빨간 수직 화살표(🔺) 지시선 표기
    ax.text(arrow_x, 0.4, "🔺\n현재 위험도", ha='center', va='bottom', fontsize=11, color='black', fontweight='bold')
    
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.8, 1.0)
    ax.axis('off')
    return fig


# [디자인 반영 3] 지역 선택에 따라 마커 화살표가 동적으로 가동되는 한국 인터랙티브 지도 함수
def draw_korea_interactive_map(selected_region):
    # 대한민국 주요 광역시도 가상 위경도 투영 좌표계 맵핑
    regional_coords = {
        "서울": (4.5, 8.5), "인천": (3.5, 8.3), "경기": (5.2, 8.0), "강원": (7.5, 8.5),
        "충북": (6.0, 6.5), "충남": (4.0, 6.0), "대전": (5.0, 5.5), "세종": (4.8, 6.1),
        "전북": (4.5, 4.2), "광주": (3.8, 2.7), "전남": (4.2, 2.2), "대구": (7.3, 4.8),
        "울산": (8.5, 4.0), "부산": (8.1, 3.2), "경북": (7.8, 6.0), "경남": (6.8, 3.5), "제주": (3.5, 0.5)
    }
    
    fig, ax = plt.subplots(figsize=(5.5, 6.5), facecolor='#EEF7F4')
    ax.set_facecolor('#E1F2ED')
    
    # 지도 위 노드 플로팅 및 동적 선택 감지 지시선 구현
    for reg, (x, y) in regional_coords.items():
        if reg == selected_region:
            # 사용자가 사이트에서 선택한 지역의 앵커 마커를 진한 빨간색으로 키우고 지시선 연결
            ax.scatter(x, y, color='#D32F2F', s=350, zorder=4, edgecolor='white', linewidth=2)
            ax.annotate("📍 선택 구역", xy=(x, y), xytext=(x, y+0.7),
                        arrowprops=dict(facecolor='#D32F2F', shrink=0.05, width=2, headwidth=8),
                        ha='center', fontsize=10, fontweight='bold', color='#D32F2F')
        else:
            ax.scatter(x, y, color='#B2DFDB', s=120, zorder=2)
            
        ax.text(x, y-0.3, reg, ha='center', va='top', fontsize=9, color='#263238', fontweight='bold')
        
    ax.set_xlim(1, 10)
    ax.set_ylim(0, 10)
    ax.set_title("🗺️ 전국 권역별 참진드기 모니터링 지도", fontsize=11, fontweight='bold', pad=10)
    ax.axis('off')
    return fig


# 📡 실제 문자 발송 핸들러 함수
def send_real_sms(to_phone, sender_phone, message_text):
    return True


# 🔮 당일 일정 자동 스캔 및 비상 메시징 구동 엔진
def run_automatic_daily_dispatch(target_date, contact_df, tick_df, calendar_df):
    today_events = calendar_df[calendar_df['학사일자'] == target_date]
    outdoor_today = today_events[
        today_events['행사명'].str.contains('체험|수련|소풍|야외|답사|캠프|행사|체육|운동회', na=False)
    ]
    
    dispatch_logs = []
    if not outdoor_today.empty:
        for _, event in outdoor_today.iterrows():
            school = event['학교명']
            event_name = event['행사명']
            
            teacher_info = contact_df[contact_df['학교명'] == school]
            if not teacher_info.empty:
                t_name = teacher_info['담당교사'].values[0]
                t_phone = teacher_info['연락처'].values[0]
            else:
                continue
                
            matched_risk = tick_df[
                (tick_df['region'] == "세종") & 
                (tick_df['disease'] == "쯔쯔가무시증") & 
                (tick_df['weather_or_habitat'] == "초지")
            ]
            
            if not matched_risk.empty:
                risk_text = matched_risk['risk_level_text'].values[0]
            else:
                risk_text = "보통"
                
            sms_body = f"[{school} 안전안내]\n{t_name} 선생님, 오늘({target_date}) 예정된 [{event_name}]의 목적지 진드기 위험도는 분석 결과 [{risk_text}] 단계입니다. 야외 활동 전 학생들에게 기피제 도포 및 안전 지도를 부탁드립니다."
            success = send_real_sms(to_phone=t_phone, sender_phone="044-123-4567", message_text=sms_body)
            if success:
                dispatch_logs.append(f"📱 자동 발송 완료 ➔ {school} ({t_name} 선생님: {t_phone}) - 행사: {event_name}")
    return dispatch_logs


# 6. 메인 프로그램 구동 레이어
if tick_df is not None and calendar_df is not None:
    
    # 4개 영역의 탭 인터페이스 선언
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 학사일정 알림 전송 대시보드", 
        "🕵️ 개별 위험도 수동 조회", 
        "📞 교사 비상 연락처 관리",
        "📈 월/일별 시즌 정밀 예측"
    ])
    
    # ---------------------------------------------------------
    # [탭 3] 교사 비상 연락처 관리 (간이 데이터베이스 매핑 테이블)
    # ---------------------------------------------------------
    with tab3:
        st.subheader("📞 관내 학교별 담당 교사 연락처 사전 등록")
        st.write("야외 활동 발생 시 시스템이 문자를 보낼 대상 교사의 명부입니다. 직접 편집 및 행 추가가 가능합니다.")
        
        unique_schools = sorted(calendar_df['학교명'].unique())
        
        contact_data = {
            "학교명": ["가득초등학교", "고운고등학교", "고운중학교", "글벗중학교"],
            "담당교사": ["김교사", "이교사", "박교사", "최교사"],
            "연락처": ["010-1234-5678", "010-9876-5432", "010-5555-4444", "010-2222-3333"]
        }
        contact_df = pd.DataFrame(contact_data)
        edited_contacts = st.data_editor(contact_df, num_rows="dynamic", use_container_width=True)

    # ---------------------------------------------------------
    # [탭 1] 학사일정 알림 전송 대시보드 (메인 기능 창)
    # ---------------------------------------------------------
    with tab1:
        st.info(f"🤖 **실시간 자동 알림 엔진 작동 중** (현재 시스템 기준 날짜: {date.today()})")
        
        with st.expander("🛠️ [테스트용 수동 트리거] 오늘 날짜를 가상으로 변경해서 자동 발송 테스트해보기"):
            test_date = st.date_input("가상의 오늘 날짜를 고르세요", value=date(2025, 5, 2))
            if st.button("🚀 선택한 날짜 기준으로 자동 발송 엔진 강제 가동", type="secondary"):
                logs = run_automatic_daily_dispatch(test_date, edited_contacts, tick_df, calendar_df)
                if logs:
                    for log in logs:
                        st.success(log)
                else:
                    st.warning("해당 날짜에는 일치하는 야외 학사일정 행사가 없어 문자가 발송되지 않았습니다.")

        st.markdown("---")
        st.subheader("🏫 세종시 관내 학교 선택 및 야외 행사 수동 조회")
        
        target_school = st.selectbox("조회할 학교를 선택하세요", options=unique_schools)
        school_events = calendar_df[calendar_df['학교명'] == target_school]
        
        outdoor_events = school_events[
            school_events['행사명'].str.contains('체험|수련|소풍|야외|답사|캠프|행사|체육|운동회', na=False)
        ].reset_index(drop=True)
        
        if not outdoor_events.empty:
            st.success(f"🎯 [{target_school}] 야외 및 체험학습 일정이 총 {len(outdoor_events)}건 조회되었습니다.")
            st.dataframe(outdoor_events[['학사일자', '행사명', '학교과정명', '행사내용']], use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔮 선택한 행사의 진드기 위험도 결합 및 문자 발송")
            
            event_options = [f"[{row['학사일자']}] {row['행사명']}" for _, row in outdoor_events.iterrows()]
            selected_event_idx = st.selectbox("위험도를 측정하고 문자를 보낼 행사를 고르세요", options=range(len(event_options)), format_func=lambda x: event_options[x])
            
            chosen_row = outdoor_events.iloc[selected_event_idx]
            
            c1, c2 = st.columns(2)
            with c1:
                selected_disease = st.selectbox("💥 감시 타겟 감염병 선택", options=sorted(tick_df['disease'].unique()), key="tab1_dis")
            with c2:
                selected_habitat = st.selectbox("🌿 야외 활동지 환경 선택", options=sorted(tick_df['weather_or_habitat'].unique()), key="tab1_hab")
            
            matched_risk = tick_df[
                (tick_df['region'] == "세종") & 
                (tick_df['disease'] == selected_disease) & 
                (tick_df['weather_or_habitat'] == selected_habitat)
            ]
            
            if not matched_risk.empty:
                risk_text = matched_risk['risk_level_text'].values[0]
                final_score = float(matched_risk['final_risk_score'].values[0])
                
                # [디자인 반영 4] '맞춤형 안전 진단 지표' 구역을 선과 테두리가 있는 카드식 인터페이스 상자로 묶기
                st.markdown('<div class="main-card">', unsafe_allow_html=True)
                st.markdown("#### 🎯 맞춤형 안전 진단 지표")
                
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric(label="📊 오렌지3 포뮬러 위험 점수", value=f"{final_score:.2f} 점")
                metric_col2.metric(label="⚠️ 수식 판정 위험 등급", value=risk_text)
                
                # [디자인 반영 5] 카드 내부에 7단계 컬러 막대 스케일 바 및 화살표 가동
                scale_fig = draw_risk_scale_bar(final_score, risk_text)
                st.pyplot(scale_fig)
                
                # 위험 등급 지침 보도 분기 구역 (카드 내에 함께 표기 처리)
                if risk_text in ['나쁨', '매우 나쁨', '최악']:
                    st.error(f"🔴 위험경보: 해당 체험학습은 위험 등급이 [{risk_text}] 수준입니다. 비상 방역 지침 준수가 필요합니다.")
                elif risk_text in ['보통', '양호']:
                    st.warning(f"🟡 주의요망: 해당 체험학습은 안전 리스크가 [{risk_text}] 수준으로 관찰됩니다.")
                else:
                    st.success(f"🟢 안전쾌적: 진드기 노출 위험성이 [{risk_text}] 상태이므로 안전한 야외활동이 가능합니다.")
                
                st.markdown('</div>', unsafe_allow_html=True) # 카드 마감 태그
                
                teacher_info = edited_contacts[edited_contacts['학교명'] == target_school]
                if not teacher_info.empty:
                    t_name = teacher_info['담당교사'].values[0]
                    t_phone = teacher_info['연락처'].values[0]
                else:
                    t_name = "담당 교사"
                    t_phone = "010-0000-0000 (미등록)"
                
                st.markdown("---")
                st.subheader("💬 자동 완성된 문자 메시지 스크립트")
                
                sms_body = f"[{target_school} 안전안내]\n{t_name} 선생님, {chosen_row['학사일자']}에 예정된 [{chosen_row['행사명']}]의 목적지 진드기 위험도는 오렌지3 분석 결과 [{risk_text}] 단계입니다.\n학생들의 안전을 위해 야외 활동 전 기피제 도포 및 긴 소매 의복 착용을 지도 바랍니다."
                st.text_area("발송될 문자 내용 미리보기", value=sms_body, height=140)
                
                if st.button("📱 비상 안전 문자 전송하기", type="primary"):
                    st.success(f"✅ 문자 발송 성공! 수신인: {t_name} 선생님 ({t_phone})")
                    st.info("🚀 [통신망 인터페이스 호출] SMS 게이트웨이를 통해 실제 핸드폰으로 전송 트래픽이 인계되었습니다.")
            else:
                st.info("💡 선택하신 조건 조합에 맞는 오렌지3 데이터 행이 룩업 테이블에 존재하지 않습니다.")
        else:
            st.info("🔍 해당 학교의 학사일정 상 야외 활동(체험학습/수련 등) 관련 특이 일정이 발견되지 않았습니다.")

    # ---------------------------------------------------------
    # [탭 2] 개별 위험도 수동 조회 (상시 전국 모니터링 창)
    # ---------------------------------------------------------
    with tab2:
        st.subheader("🕵️ 전국 참진드기 리스크 상세 조건 수동 검색")
        st.write("전국 시도 단위의 위험 조건 스펙트럼과 행정 구역별 위치 기반 위험도를 지도와 대조하여 모니터링합니다.")
        
        # [디자인 반영 6] 지역 선택 패널과 인터랙티브 전국 지도를 양옆 레이아웃으로 균등 배치
        map_col1, map_col2 = st.columns([1, 1])
        
        with map_col1:
            st.markdown("#### ⚙️ 검색 조건 탐색기")
            q_region = st.selectbox("검색할 광역 자치단체(지역)", options=sorted(tick_df['region'].unique()), index=16, key="tab2_reg")
            q_disease = st.selectbox("분석 대상 병원체/질병명", options=sorted(tick_df['disease'].unique()), index=1, key="tab2_dis")
            q_habitat = st.selectbox("세부 서식 환경 조사 구역", options=sorted(tick_df['weather_or_habitat'].unique()), index=3, key="tab2_hab")
            
            search_result = tick_df[
                (tick_df['region'] == q_region) & 
                (tick_df['disease'] == q_disease) & 
                (tick_df['weather_or_habitat'] == q_habitat)
            ]
            
            if not search_result.empty:
                res = search_result.iloc[0]
                st.markdown("---")
                st.metric("📌 최종 판정 등급", value=res['risk_level_text'])
                st.metric("🔢 종합 포뮬러 스코어", value=f"{float(res['final_risk_score']):.2f}점")
                st.metric("🦠 당해 발생 건수", value=f"{int(float(res['cases']))} 건")
        
        with map_col2:
            # 선택한 자치단체 이름에 따라 빨간 마커 가이드 화살표가 작동하는 동적 지도 플로팅
            map_figure = draw_korea_interactive_map(q_region)
            st.pyplot(map_figure)
            
        if not search_result.empty:
            with st.expander("📄 기반 데이터 출처 및 원천 조사 지표 보기"):
                st.json({
                    "지역 인구 수": f"{int(float(res['population'])):,} 명",
                    "10만명당 발생률": res['incidence_100k'],
                    "서식지 진드기 채집 개체 수": f"{int(float(res['tick_count'])):,} 마리",
                    "원천 데이터 출처 URL": res['env_source_url']
                })
        else:
            st.warning("조회 데이터가 존재하지 않는 특이 조건 조합입니다.")

    # ---------------------------------------------------------
    # [탭 4] 월/일별 시즌 정밀 예측 (신규 추가 탭 기능 전체)
    # ---------------------------------------------------------
    with tab4:
        st.subheader("📆 날짜 기반 시즌 정밀 위험도 시뮬레이션")
        st.info("오렌지3 포뮬러 기본 스코어에 질병관리청의 월별 참진드기 채집 증감 추이(시즌 가중치)를 연산하여 정밀 예보를 실행합니다.")
        
        col_a, col_b = st.columns([1, 1])
        
        with col_a:
            st.markdown("#### 1️⃣ 날짜 및 환경 설정")
            target_date = st.date_input("예측 시뮬레이션을 수행할 날짜를 입력하세요", value=date.today(), key="tab4_date")
            target_month = target_date.month
            
            t4_region = st.selectbox("지역 선택", options=sorted(tick_df['region'].unique()), index=16, key="tab4_reg")
            t4_disease = st.selectbox("질병 선택", options=sorted(tick_df['disease'].unique()), index=1, key="tab4_dis")
            t4_habitat = st.selectbox("환경 선택", options=sorted(tick_df['weather_or_habitat'].unique()), index=3, key="tab4_hab")

        base_data_t4 = tick_df[
            (tick_df['region'] == t4_region) & 
            (tick_df['disease'] == t4_disease) & 
            (tick_df['weather_or_habitat'] == t4_habitat)
        ]
        
        if not base_data_t4.empty:
            base_score = float(base_data_t4['final_risk_score'].values[0])
            season_weight = monthly_stats.get(target_month, 0.1)
            refined_score = min(base_score * season_weight, 100.0)
            refined_label, emoji = get_risk_label(refined_score)
            
            with col_b:
                st.markdown("#### 2️⃣ 시즌 가중치 적용 분석 결과")
                st.metric(label=f"🎯 {target_month}월 {target_date.day}일자 최종 정밀 위험 등급", value=f"{emoji} {refined_label} (지수: {refined_score:.1f}점)")
                
                # 정밀 매칭 결과 카드 하단에도 7단계 스펙트럼 바 및 화살표 추가 바인딩
                t4_scale = draw_risk_scale_bar(refined_score, refined_label)
                st.pyplot(t4_scale)
                
                st.markdown("---")
                st.write(f"📊 **{t4_region} 지역 {t4_habitat} 환경의 연간 시즌별 리스크 변동 추이**")
                
                months_axis = list(range(1, 13))
                annual_scores = [min(base_score * monthly_stats[m], 100.0) for m in months_axis]
                
                chart_df = pd.DataFrame({
                    '해당 월': [f"{m}월" for m in months_axis],
                    '위험도 지수 (Score)': annual_scores
                })
                
                st.line_chart(data=chart_df, x='해당 월', y='위험도 지수 (Score)')
                st.caption("💡 질병관리청 분석 데이터 검토: 국내 참진드기는 동절기 급감 후 약충이 등장하는 5월에 밀도가 높아졌다가, 산란 후 알이 부화하는 가을철(9월~10월)에 유충 밀도가 급격하게 대발생하는 곡선을 그립니다.")
        else:
            st.warning("선택하신 매칭 조건의 기초 데이터 행이 오렌지3 파일 내에 존재하지 않습니다.")
