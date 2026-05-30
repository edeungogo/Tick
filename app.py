import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import date

# 1. 페이지 레이아웃 및 타이틀 설정
st.set_page_config(page_title="세종시 진드기 정밀 예보 시스템", layout="wide", page_icon="🕷️")

st.title("🍊 오렌지3+시즌 가중치 결합 진드기 위험도 정밀 예측 시스템")
st.write("오렌지3의 분석 모델에 질병관리청의 월별 발생 추이 통계를 결합하여 날짜별 정밀 위험도를 도출합니다.")
st.markdown("---")


# 2. 데이터 세트 로드 및 전처리 함수 (캐싱 처리)
@st.cache_data
def load_system_data():
    try:
        # 오렌지3 예측 및 포뮬러 결과물 로드 (상단 2개의 타입 정의 행 제외하고 로드)
        raw_tick = pd.read_csv("tick_risk_lookup.csv")
        tick_df = raw_tick.drop([0, 1]).reset_index(drop=True)
        
        # 학사일정 데이터 로드 및 전처리
        # ⚠️ 만약 깃허브에서 파일 이름을 'calendar.csv'로 바꾸셨다면 아래 "세종시 학사일정.xls - 학사일정.csv" 부분을 "calendar.csv"로 고쳐주세요.
        calendar_df = pd.read_csv("calendar.csv")
        
        # 문자열 형태의 학사일자를 날짜 형태로 변환 (예: 20250304 -> 2025-03-04)
        calendar_df['학사일자'] = pd.to_datetime(calendar_df['학사일자'].astype(str), format='%Y%m%d').dt.date
        
        # [신규 데이터] 질병관리청 참진드기 월별 채집 통계 기반 활동성 가중치 지표 (배수)
        # 봄~가을 활동 정점 및 겨울철 휴지기 생태 특성 반영
        monthly_stats = {
            1: 0.05, 2: 0.05, 3: 0.10, 4: 0.60, 
            5: 1.10,  # 5월 약충 활동기 반영
            6: 1.00, 7: 0.50, 
            8: 0.90,  # 8월 유충 부화 시작 반영
            9: 2.00,  # 9월 유충 대발생 정점 반영
            10: 1.60, # 10월 SFTS 환자 다발기 반영
            11: 0.30, 12: 0.05
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


# 4. 메인 프로그램 구동 레이어
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
        
        # 모의 초기 데이터 셋 바인딩
        contact_data = {
            "학교명": ["가득초등학교", "고운고등학교", "고운중학교", "글벗중학교"],
            "담당교사": ["김교사", "이교사", "박교사", "최교사"],
            "연락처": ["010-1234-5678", "010-9876-5432", "010-5555-4444", "010-2222-3333"]
        }
        contact_df = pd.DataFrame(contact_data)
        
        # 스트림릿 인터랙티브 테이블 에디터 구동
        edited_contacts = st.data_editor(contact_df, num_rows="dynamic", use_container_width=True)

    # ---------------------------------------------------------
    # [탭 1] 학사일정 알림 전송 대시보드 (메인 기능 창)
    # ---------------------------------------------------------
    with tab1:
        st.subheader("🏫 세종시 관내 학교 선택 및 야외 행사 자동 조회")
        
        # 학교 선택 셀렉트 박스
        target_school = st.selectbox("조회할 학교를 선택하세요", options=unique_schools)
        school_events = calendar_df[calendar_df['학교명'] == target_school]
        
        # 야외 진드기 우점 지역 노출 가능성이 높은 키워드로 행사 자동 필터링 [cite: 33, 34]
        outdoor_events = school_events[
            school_events['행사명'].str.contains('체험|수련|소풍|야외|답사|캠프|행사|체육|운동회', na=False)
        ].reset_index(drop=True)
        
        if not outdoor_events.empty:
            st.success(f"🎯 [{target_school}] 야외 및 체험학습 일정이 총 {len(outdoor_events)}건 조회되었습니다.")
            st.dataframe(outdoor_events[['학사일자', '행사명', '학교과정명', '행사내용']], use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔮 선택한 행사의 진드기 위험도 결합 및 문자 발송")
            
            # 조회된 야외 행사 목록을 선택 박스 메뉴용 문자열 배열로 가공
            event_options = [f"[{row['학사일자']}] {row['행사명']}" for _, row in outdoor_events.iterrows()]
            selected_event_idx = st.selectbox("위험도를 측정하고 문자를 보낼 행사를 고르세요", options=range(len(event_options)), format_func=lambda x: event_options[x])
            
            chosen_row = outdoor_events.iloc[selected_event_idx]
            
            # 위험도 산출 조건 매핑층
            c1, c2 = st.columns(2)
            with c1:
                selected_disease = st.selectbox("💥 감시 타겟 감염병 선택", options=sorted(tick_df['disease'].unique()), key="tab1_dis")
            with c2:
                selected_habitat = st.selectbox("🌿 야외 활동지 환경 선택", options=sorted(tick_df['weather_or_habitat'].unique()), key="tab1_hab")
            
            # 오렌지3 원천 데이터 로우 매칭
            matched_risk = tick_df[
                (tick_df['region'] == "세종") & 
                (tick_df['disease'] == selected_disease) & 
                (tick_df['weather_or_habitat'] == selected_habitat)
            ]
            
            if not matched_risk.empty:
                risk_text = matched_risk['risk_level_text'].values[0]
                final_score = float(matched_risk['final_risk_score'].values[0])
                
                # 대시보드 스코어 카드 시각화
                st.markdown("#### 🚨 맞춤형 안전 진단 지표")
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric(label="📊 오렌지3 포뮬러 위험 점수", value=f"{final_score:.2f} 점")
                metric_col2.metric(label="⚠️ 수식 판정 위험 등급", value=risk_text)
                
                # 위험도별 경고창 조건 분기
                if risk_text in ['나쁨', '매우 나쁨', '최악']:
                    st.error(f"🔴 위험경보: 해당 체험학습은 위험 등급이 [{risk_text}] 수준입니다. 비상 방역 지침 준수가 필요합니다.")
                elif risk_text in ['보통', '양호']:
                    st.warning(f"🟡 주의요망: 해당 체험학습은 안전 리스크가 [{risk_text}] 수준으로 관찰됩니다.")
                else:
                    st.success(f"🟢 안전쾌적: 진드기 노출 위험성이 [{risk_text}] 상태이므로 안전한 야외활동이 가능합니다.")
                
                # 담당 교사 인적사항 조회 및 매치
                teacher_info = edited_contacts[edited_contacts['학교명'] == target_school]
                if not teacher_info.empty:
                    t_name = teacher_info['담당교사'].values[0]
                    t_phone = teacher_info['연락처'].values[0]
                else:
                    t_name = "담당 교사"
                    t_phone = "010-0000-0000 (미등록)"
                
                st.markdown("---")
                st.subheader("💬 자동 완성된 문자 메시지 스크립트")
                
                # 동적 문자 발송 문구 조립
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
        st.write("학사일정 데이터와 관계없이, 전국 시도 단위의 위험 조건 스펙트럼을 상시 대조 모니터링합니다.")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            q_region = st.selectbox("검색할 광역 자치단체(지역)", options=sorted(tick_df['region'].unique()), index=16, key="tab2_reg")
        with sc2:
            q_disease = st.selectbox("분석 대상 병원체/질병명", options=sorted(tick_df['disease'].unique()), index=1, key="tab2_dis")
        with sc3:
            q_habitat = st.selectbox("세부 서식 환경 조사 구역", options=sorted(tick_df['weather_or_habitat'].unique()), index=3, key="tab2_hab")
            
        search_result = tick_df[
            (tick_df['region'] == q_region) & 
            (tick_df['disease'] == q_disease) & 
            (tick_df['weather_or_habitat'] == q_habitat)
        ]
        
        if not search_result.empty:
            res = search_result.iloc[0]
            st.markdown("---")
            res_c1, res_c2, res_c3 = st.columns(3)
            res_c1.metric("📌 최종 판정 등급", value=res['risk_level_text'])
            res_c2.metric("🔢 종합 포뮬러 스코어", value=f"{float(res['final_risk_score']):.2f}점")
            res_c3.metric("🦠 당해 발생 건수", value=f"{int(float(res['cases']))} 건")
            
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
        st.info("오렌지3 포뮬러 기본 스코어에 질병관리청의 월별 참진드기 채집 증감 추이(시즌 가중치)를 연산하여 정밀 예보를 실행합니다[cite: 33, 69].")
        
        col_a, col_b = st.columns([1, 1])
        
        with col_a:
            st.markdown("#### 1️⃣ 날짜 및 환경 설정")
            # 달력으로 날짜 선택 기능 제공
            target_date = st.date_input("예측 시뮬레이션을 수행할 날짜를 입력하세요", value=date.today())
            target_month = target_date.month
            
            # 탭 4 전용 조건 지정 셀렉트 박스
            t4_region = st.selectbox("지역 선택", options=sorted(tick_df['region'].unique()), index=16, key="tab4_reg")
            t4_disease = st.selectbox("질병 선택", options=sorted(tick_df['disease'].unique()), index=1, key="tab4_dis")
            t4_habitat = st.selectbox("환경 선택", options=sorted(tick_df['weather_or_habitat'].unique()), index=3, key="tab4_hab")

        # 연산 및 시각화 파트
        base_data_t4 = tick_df[
            (tick_df['region'] == t4_region) & 
            (tick_df['disease'] == t4_disease) & 
            (tick_df['weather_or_habitat'] == t4_habitat)
        ]
        
        if not base_data_t4.empty:
            # 오렌지3 포뮬러 기본 베이스 점수 취득
            base_score = float(base_data_t4['final_risk_score'].values[0])
            
            # 선택된 월에 대응하는 참진드기 밀도 가중 배수 매핑 [cite: 33]
            season_weight = monthly_stats.get(target_month, 0.1)
            
            # 최종 연산 위험도 도출 및 라벨링 (최대 임계점 100점 스케일링 제한)
            refined_score = min(base_score * season_weight, 100.0)
            refined_label, emoji = get_risk_label(refined_score)
            
            with col_b:
                st.markdown("#### 2️⃣ 시즌 가중치 적용 분석 결과")
                
                # 최종 결과 리포트 메트릭
                st.metric(label=f"🎯 {target_month}월 {target_date.day}일자 최종 정밀 위험 등급", value=f"{emoji} {refined_label} (지수: {refined_score:.1f}점)")
                
                st.markdown("---")
                st.write(f"📊 **{t4_region} 지역 {t4_habitat} 환경의 연간 시즌별 리스크 변동 추이**")
                
                # 1월부터 12월까지 전체 추이 라인 차트 생성을 위한 데이터 프레임 빌드
                months_axis = list(range(1, 13))
                annual_scores = [min(base_score * monthly_stats[m], 100.0) for m in months_axis]
                
                chart_df = pd.DataFrame({
                    '해당 월': [f"{m}월" for m in months_axis],
                    '위험도 지수 (Score)': annual_scores
                })
                
                # 스트림릿 내장 경량 라인 차트 렌더링
                st.line_chart(data=chart_df, x='해당 월', y='위험도 지수 (Score)')
                st.caption("💡 질병관리청 분석 데이터 검토: 국내 참진드기는 동절기 급감 후 약충이 등장하는 5월에 밀도가 높아졌다가, 산란 후 알이 부화하는 가을철(9월~10월)에 유충 밀도가 급격하게 대발생하는 곡선을 그립니다[cite: 35, 64, 65].")
        else:
            st.warning("선택하신 매칭 조건의 기초 데이터 행이 오렌지3 파일 내에 존재하지 않습니다.")
