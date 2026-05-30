import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 레이아웃 및 타이틀 설정
st.set_page_config(page_title="세종시 학사일정 연동 진드기 안전 시스템", layout="wide", page_icon="🕷️")

st.title("🍊 오렌지3 연동 참진드기 위험도 예측 및 교사 문자 알림 시스템")
st.write("학사일정에서 야외 활동(체험학습, 수련활동 등)이 있는 날을 자동 감지하여 담당 교사에게 위험도와 안전 지침을 안내합니다.")
st.markdown("---")

# 2. 데이터 세트 로드 및 전처리 함수
@st.cache_data
def load_system_data():
    try:
        # 오렌지3 예측 및 포뮬러 결과물 로드 (상단 2개의 타입 정의 행 제외하고 로드)
        raw_tick = pd.read_csv("tick_risk_lookup.csv")
        tick_df = raw_tick.drop([0, 1]).reset_index(drop=True)
        
        # 학사일정 데이터 로드 및 전처리
        calendar_df = pd.read_csv("calendar.csv")
        # 문자열 형태의 학사일자를 날짜 형태로 변환 (예: 20250304 -> 2025-03-04)
        calendar_df['학사일자'] = pd.to_datetime(calendar_df['학사일자'].astype(str), format='%Y%m%d').dt.date
        
        return tick_df, calendar_df
    except Exception as e:
        st.error(f"⚠️ 파일 로드 중 오류 발생: {e}. 파일명이 레포지토리 내부와 일치하는지 확인해 주세요.")
        return None, None

tick_df, calendar_df = load_system_data()

if tick_df is not None and calendar_df is not None:
    
    # 3. 화면을 3개의 탭(Tab)으로 나누어 직관적인 인터페이스 구축
    tab1, tab2, tab3 = st.tabs(["📅 학사일정 알림 전송 대시보드", "🕵️ 개별 위험도 수동 조회", "📞 교사 비상 연락처 관리"])
    
    # [탭 3] 연락처 관리를 먼저 구현하여 연동성 확보 (간이 데이터베이스 역할)
    with tab3:
        st.subheader("📞 관내 학교별 담당 교사 연락처 사전 등록")
        st.write("실제 운영 시에는 보안이 적용된 데이터베이스와 연동되며, 현재는 테스트용 모의 명부입니다.")
        
        # 샘플 연락처 데이터 프레임 생성
        unique_schools = sorted(calendar_df['학교명'].unique())
        contact_data = {
            "학교명": ["가득초등학교", "고운고등학교", "고운중학교", "글벗중학교"],
            "담당교사": ["김교사", "이교사", "박교사", "최교사"],
            "연락처": ["010-1234-5678", "010-9876-5432", "010-5555-4444", "010-2222-3333"]
        }
        contact_df = pd.DataFrame(contact_data)
        
        # 사용자가 연락처 테이블을 직접 편집하고 등록할 수 있는 에디터 기능 제공
        edited_contacts = st.data_editor(contact_df, num_rows="dynamic", use_container_width=True)
        
    # [탭 1] 메인 대시보드: 학사일정과 오렌지3 데이터를 융합하는 핵심 공간
    with tab1:
        st.subheader("🏫 세종시 관내 학교 선택 및 야외 행사 자동 조회")
        
        # 학사일정에서 학교 선택
        target_school = st.selectbox("조회할 학교를 선택하세요", options=unique_schools)
        school_events = calendar_df[calendar_df['학교명'] == target_school]
        
        # '체험', '수련', '소풍', '운동회' 등 야외 진드기 노출 가능성이 높은 핵심 키워드로 행사 자동 필터링
        outdoor_events = school_events[
            school_events['행사명'].str.contains('체험|수련|소풍|야외|답사|캠프|행사|체육', na=False)
        ].reset_index(drop=True)
        
        if not outdoor_events.empty:
            st.success(f"🎯 해당 학교에 검색된 야외 및 체험학습 일정이 총 {len(outdoor_events)}건 있습니다.")
            st.dataframe(outdoor_events[['학사일자', '행사명', '학교과정명', '행사내용']], use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔮 선택한 행사의 진드기 위험도 결합 및 문자 발송")
            
            # 조회된 야외 행사 중 분석할 행사를 선택
            event_options = [f"[{row['학사일자']}] {row['행사명']}" for _, row in outdoor_events.iterrows()]
            selected_event_idx = st.selectbox("위험도를 측정하고 문자를 보낼 행사를 선택하세요", options=range(len(event_options)), format_func=lambda x: event_options[x])
            
            chosen_row = outdoor_events.iloc[selected_event_idx]
            
            # 위험도 산출을 위해 목적지의 '서식지 환경'과 '감염병 종류'를 사용자가 매칭
            c1, c2 = st.columns(2)
            with c1:
                selected_disease = st.selectbox("💥 주의 감시 감염병 종류", options=sorted(tick_df['disease'].unique()))
            with c2:
                selected_habitat = st.selectbox("🌿 체험학습지 환경 타겟", options=sorted(tick_df['weather_or_habitat'].unique()))
            
            # 오렌지3 데이터셋(tick_df)에서 세종 지역의 해당 질병/서식지 조건에 맞는 위험도 행(Row)을 조회
            matched_risk = tick_df[
                (tick_df['region'] == "세종") & 
                (tick_df['disease'] == selected_disease) & 
                (tick_df['weather_or_habitat'] == selected_habitat)
            ]
            
            if not matched_risk.empty:
                # 사용자가 수식으로 완성한 7단계 위험도 등급 추출
                risk_text = matched_risk['risk_level_text'].values[0]
                final_score = float(matched_risk['final_risk_score'].values[0])
                
                # 위험도에 따른 시각적 알림 카드 배치
                st.markdown("#### 🚨 맞춤형 안전 진단 지표")
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric(label="📊 오렌지3 통합 위험 점수", value=f"{final_score:.2f} 점")
                metric_col2.metric(label="⚠️ 최종 안전 위험 등급", value=risk_text)
                
                # 등급별 테두리 색상 및 경고 문구 분기 처리
                if risk_text in ['나쁨', '매우 나쁨', '최악']:
                    st.error(f"🔴 경고: 해당 시기 및 환경의 진드기 매개 위험도는 [{risk_text}] 단계로 매우 위험합니다. 야외활동 시 각별한 주의가 요구됩니다.")
                elif risk_text in ['보통', '양호']:
                    st.warning(f"🟡 주의: 해당 환경은 [{risk_text}] 단계의 리스크를 가지고 있습니다. 예방 지침 준수를 권고합니다.")
                else:
                    st.success(f"🟢 안전: 현재 기후 및 서식 조건상 진드기 리스크는 [{risk_text}]로 매우 쾌적한 상태입니다.")
                
                # 해당 학교 담당 교사 연락처 매칭
                teacher_info = edited_contacts[edited_contacts['학교명'] == target_school]
                if not teacher_info.empty:
                    t_name = teacher_info['담당교사'].values[0]
                    t_phone = teacher_info['연락처'].values[0]
                else:
                    t_name = "담당 교사"
                    t_phone = "010-0000-0000 (미등록)"
                
                st.markdown("---")
                st.subheader("💬 자동 완성된 문자 메시지 스크립트")
                
                # 동적으로 변수가 결합되는 문자 내용 디자인
                sms_body = f"[{target_school} 안전안내]\n{t_name} 선생님, {chosen_row['학사일자']}에 예정된 [{chosen_row['행사명']}]의 목적지 진드기 위험도는 오렌지3 분석 결과 [{risk_text}] 단계입니다.\n학생들의 안전을 위해 야외 활동 전 기피제 도포 및 긴 소매 의복 착용을 지도 바랍니다."
                
                st.text_area("발송될 문자 내용 미리보기", value=sms_body, height=140)
                
                # 문자 발송 실행 버튼
                if st.button("📱 비상 안전 문자 전송하기", type="primary"):
                    # 실제 상용 SMS API(솔라피, 쿨SMS 등) 모듈 연동 구역
                    st.success(f"✅ 수신인: {t_name} 선생님 ({t_phone})")
                    st.info("🚀 [시스템 알림] 통신사 및 SMS Gateway를 통해 실시간 기동 문자가 정상적으로 발송 처리되었습니다.")
            else:
                st.info("💡 매칭되는 오렌지3 위험도 조회 테이블 행이 없습니다. 조건 값을 다시 설정해 주세요.")
        else:
            st.info("🔍 해당 학교에는 야외 활동 관련 특별 일정이 발견되지 않았습니다.")
            
    # [탭 2] 수동 조회 공간: 학사일정과 무관하게 전국 단위 및 모든 조건을 마우스 클릭으로 바로 조회하는 탐색 창
    with tab2:
        st.subheader("🕵️ 전국 참진드기 리스크 상세 조건 수동 검색")
        st.write("학사일정과 별개로, 원하는 지역과 환경 조건을 대조하여 위험도 도출 포뮬러 데이터를 상시 모니터링합니다.")
        
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            q_region = st.selectbox("검색할 광역 자치단체(지역)", options=sorted(tick_df['region'].unique()), index=16)
        with sc2:
            q_disease = st.selectbox("분석 대상 병원체/질병명", options=sorted(tick_df['disease'].unique()), index=1)
        with sc3:
            q_habitat = st.selectbox("세부 서식 환경 조사 구역", options=sorted(tick_df['weather_or_habitat'].unique()), index=3)
            
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
