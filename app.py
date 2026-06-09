import streamlit as st
import pandas as pd
import numpy as np

# [Pro 설정] 페이지 레이아웃 확장 및 테마 고정
st.set_page_config(page_title="HEDS - 수문 설계 우수유출량 산정 시스템", page_icon="🏗️", layout="wide")

# Custom CSS로 프로페셔널한 UI 스타일링
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #0F4C81; margin-bottom: 5px; }
    .sub-title { font-size: 16px; color: #555555; margin-bottom: 25px; }
    .report-box { padding: 20px; background-color: #F8F9FA; border-left: 5px solid #0F4C81; border-radius: 4px; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True) # 👈 에러의 원인이었던 unsafe_scale을 unsafe_allow_html로 고쳤습니다!

st.markdown('<div class="main-title">🏗️ 수문 설계 및 우수 유출량 산정 시스템 (Pro Ver.)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Hydrological Engineering Design System for Stormwater Runoff Estimation</div>', unsafe_allow_html=True)
st.markdown("---")

# 탭 구조를 활용한 전공 프로세스 분리
tab1, tab2, tab3 = st.tabs(["📊 수문 매개변수 입력 및 산정", "📈 IDF 곡선 및 수문 분석", "📋 설계 검토 보고서 출력"])

# 초기 데이터 구조 정의 (KDS 설계 기준 유출계수)
c_factors = {
    "아스팔트/콘크리트 포장면": 0.85,
    "상업 및 업무 중심지구": 0.75,
    "시가지 고밀도 주거지역": 0.65,
    "일반 단독주택지": 0.55,
    "공원, 녹지 및 잔디밭": 0.25,
    "자연 임야 및 산림지대": 0.15
}

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📍 1. 유역 토지이용 계획 및 복합 유출계수($C$) 산정")
        st.caption("유역 내 구역별 면적(ha)을 입력하면 가중평균 복합 유출계수가 자동 계산됩니다.")
        
        areas = {}
        for land_use, c_val in c_factors.items():
            val = st.number_input(f"▪️ {land_use} (C = {c_val}) [ha]", min_value=0.0, max_value=1000.0, value=0.0, step=0.5, key=f"area_{land_use}")
            if val > 0:
                areas[land_use] = {"area": val, "c": c_val}
                
        total_area = sum([item["area"] for item in areas.values()])
        
        if total_area > 0:
            weighted_c = sum([item["area"] * item["c"] for item in areas.values()]) / total_area
        else:
            weighted_c = 0.0
            
        st.metric("계산된 복합 유출계수 (C_avg)", f"{weighted_c:.3f}")

    with col2:
        st.subheader("⏱️ 2. 도달시간($T_c$) 정밀 산정 (Kerby & Kraven 공식 적용)")
        
        st.markdown("**[유입 시간 ($t_1$) : Kerby 공식 적용]**")
        st.latex(r"t_1 = 1.44 \cdot \left(\frac{L \cdot n}{\sqrt{S}}\right)^{0.467}")
        
        k_l = st.number_input("지표면 흐름 길이 L (m)", min_value=10.0, max_value=1000.0, value=100.0)
        k_s = st.number_input("지표면 평균 경사 S (m/m)", min_value=0.001, max_value=0.5, value=0.02, format="%.4f")
        k_n = st.slider("지표면 조도계수 (n)", min_value=0.02, max_value=0.8, value=0.1, step=0.01)
        
        t1 = 1.44 * ((k_l * k_n) / np.sqrt(k_s))**0.467
        st.caption(f"➔ 산정된 유입 시간 (t1) = {t1:.2f} 분")
        
        st.markdown("<br>**[유하 시간 ($t_2$) : Kraven 공식 적용]**", unsafe_allow_html=True)
        st.latex(r"t_2 = \frac{L_{channel}}{60 \cdot V}")
        
        channel_l = st.number_input("배수 관로/하천 총 유하 거리 (m)", min_value=0.0, max_value=5000.0, value=500.0)
        v_option = st.selectbox("관로 경사 및 유속(V) 조건 선택", [
            "급경사 수로 (경사 > 4/100, V = 4.5 m/s)",
            "완경사 수로 (경사 2/100 ~ 4/100, V = 3.0 m/s)",
            "평지 수로 (경사 < 2/100, V = 2.1 m/s)"
        ])
        
        v = 4.5 if "4.5" in v_option else (3.0 if "3.0" in v_option else 2.1)
        t2 = channel_l / (60 * v)
        st.caption(f"➔ 산정된 유하 시간 (t2) = {t2:.2f} 분")
        
        Tc = t1 + t2
        st.info(f"🎯 최종 계획 유역 도달시간 (Tc) = **{Tc:.2f} 분**")

with tab2:
    st.subheader("🌦️ 3. 설계 강우강도($I$) 산정 및 IDF 연동 분석")
    
    talbot_coefficients = {
        "5년 빈도 (소규모 하수관거)": {"a": 2450, "b": 19},
        "10년 빈도 (일반 방재성능)": {"a": 3120, "b": 21},
        "30년 빈도 (간선 배수시설)": {"a": 4180, "b": 24}
    }
    
    selected_frequency = st.selectbox("📊 적용 설계 재현기간 선택", list(talbot_coefficients.keys()))
    current_coeff = talbot_coefficients[selected_frequency]

    I_design = current_coeff["a"] / (Tc + current_coeff["b"])

    Q_design = (weighted_c * I_design * total_area) / 360
    
    time_axis = np.linspace(5, 120, 100)
    idf_data = pd.DataFrame({"지속시간 (분)": time_axis})
    
    for name, coeff in talbot_coefficients.items():
        idf_data[name] = coeff["a"] / (time_axis + coeff["b"])
        
    idf_data = idf_data.set_index("지속시간 (분)")
    
    col_graph, col_metric = st.columns([2, 1])
    
    with col_graph:
        st.line_chart(idf_data)
        st.caption("📈 빈도별 강우강도-지속시간 곡선(IDF Curve) 상 현재 설계 지속시간 조건 매핑 완료.")
        
    with col_metric:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.metric(label="설계 강우강도 (I)", value=f"{I_design:.2f} mm/hr", delta=f"지속시간 {Tc:.1f}분 기준")
        st.write(f"현재 선택된 빈도 공식:  \n$$I = \\frac{{{current_coeff['a']}}}{{T_c + {current_coeff['b']}}}$$")

with tab3:
        st.markdown(f"""
<div style="background-color: #f8f9fa; padding: 25px; border-radius: 10px; border: 1px solid #e2e8f0;">
<h4>📋 수리·수문 설계 검토 의견서</h4>

<p><strong>1. 유역 현황 개요</strong><br>
- 총 배수 면적: <strong>{total_area:.2f} ha</strong><br>
- 토지이용계획 가중치를 적용한 복합 유출계수(C): <strong>{weighted_c:.3f}</strong></p>

<p><strong>2. 수리학적 도달시간(Tc) 산정 결과</strong><br>
- 지표면 유입시간 (t1, Kerby식 적용): <strong>{t1:.2f} 분</strong><br>
- 설계 집중 시간 (Tc): <strong>{Tc:.2f} 분</strong></p>

<p><strong>3. 기상 수문 분석 및 강우강도</strong><br>
- 산정된 계획 설계 강우강도(I): <strong>{I_design:.2f} mm/hr</strong></p>

<hr style="border: 0.5px solid #cccccc;">
<h4 style="color:#0F4C81;">🎯 4. 계획 최대 우수 유출량 (최종 설계 유량)</h4>
<span style="font-size: 24px; font-weight: bold; color: #D9534F;">Q_design = {Q_design:.3f} m³/sec</span>
<p style="margin-top:10px;">본 유역의 수문학적 특성 및 국토교통부 하천설계기준을 준용하여 수리계산을 실시한 결과,
해당 배수구역의 말단 설계 유량은 <strong>{Q_design:.3f} m³/sec</strong>로 산정되었습니다.
향후 하수 암거 및 측구 등 배수 구조물 단면 설계 시 본 유량을 허용 통수능의 원수량 기준으로 채택할 것을 심사 보고합니다.</p>
</div>
""", unsafe_allow_html=True)
        summary_df = pd.DataFrame({
            "설계 인자": ["C (복합)", "Tc (분)", "I (mm/hr)", "A (총 면적)", "Q (설계 유량)"],
            "적용 수치": [round(weighted_c, 3), round(Tc, 2), round(I_design, 2), round(total_area, 2), round(Q_design, 3)],
            "단위": ["무차원", "min", "mm/hr", "ha", "m³/s"]
        })
        st.dataframe(summary_df, use_container_width=True)