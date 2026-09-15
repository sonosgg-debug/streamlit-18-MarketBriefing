"""
app.py
한국 & 미국 증시 마감/장중 요약 및 주요 예정 사항 대시보드
(실시간 장중 vs 정규장 마감 상태 자동 감지 및 고대비 다크 테마)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import importlib

import data_loader
import summary_engine
import calendar_data
from styles import CUSTOM_CSS

# 서브모듈 캐시 무효화 및 강제 리로드 (Streamlit 핫 리로드 보장)
importlib.reload(data_loader)
importlib.reload(summary_engine)
importlib.reload(calendar_data)


# 1. 페이지 설정
st.set_page_config(
    page_title="글로벌 증시 브리핑 | 한국 & 미국",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 적용 (다크 테마 고대비 폰트/배경)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 2. 캐시 데이터 로더
@st.cache_data(ttl=60) # 실시간 장중 갱신을 위해 캐시 TTL을 60초로 최적화
def load_krx():
    return data_loader.get_krx_summary()

@st.cache_data(ttl=60)
def load_us():
    return data_loader.get_us_summary()

# 3. 사이드바 구성
with st.sidebar:
    st.markdown("## 📊 **글로벌 마켓 브리핑**")
    st.markdown("<div style='color: #94a3b8; font-size: 0.9rem;'>정규장 실시간 상황 및 마감 결과를 한눈에 요약해 드립니다.</div>", unsafe_allow_html=True)
    st.markdown("---")

    # [핵심 요구사항] 증시 구분 선택
    market_choice = st.radio(
        "**증시 구분 (Market Select)**",
        ["한국 (KRX)", "미국 (US)"],
        index=0,
        help="조회하고자 하는 주식 시장을 선택하세요."
    )

    st.markdown("---")
    
    # 동적 시장 상태 계산
    target_market_key = 'KRX' if "KRX" in market_choice else 'US'
    m_status = data_loader.get_market_status(target_market_key)

    # 시장 운영 안내 및 상태 뱃지 (실시간 감지)
    if "KRX" in market_choice:
        st.markdown("### 🕒 **한국 증시(KRX) 운영 안내**")
        st.caption("• 정규 거래시간: 09:00 ~ 15:30 (KST)")
        st.caption("• 현재 시각: " + datetime.now().strftime('%H:%M:%S'))
        
        if m_status['is_live']:
            st.markdown(f"<div style='background: #064e3b; color: #a7f3d0; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 0.88rem; border: 1px solid #10b981;'>{m_status['label']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background: #1e293b; color: #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600; font-size: 0.88rem; border: 1px solid #475569;'>{m_status['label']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("### 🕒 **미국 증시(US) 운영 안내**")
        st.caption("• 정규 거래시간: 09:30 ~ 16:00 (ET)")
        st.caption("• 한국시간 환산: 22:30 ~ 05:00 (서머타임 기준)")
        
        if m_status['is_live']:
            st.markdown(f"<div style='background: #064e3b; color: #a7f3d0; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 0.88rem; border: 1px solid #10b981;'>{m_status['label']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='background: #1e293b; color: #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600; font-size: 0.88rem; border: 1px solid #475569;'>{m_status['label']}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 새로고침 버튼
    if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='color: #64748b; font-size: 0.8rem; line-height: 1.5;'>💡 <b>데이터 안내</b>: 네이버 금융 및 Yahoo Finance를 통해 최신 시황을 실시간 수집하며, 장중 실시간 지수와 마감 종가를 자동으로 구분하여 제공합니다.</div>", unsafe_allow_html=True)

# 4. 메인 대시보드 로직
if "KRX" in market_choice:
    # 한국 증시 (KRX) 화면
    data = load_krx()
    briefing = summary_engine.generate_krx_briefing(data, is_live=m_status['is_live'], time_str=m_status['time_str'])
    events = calendar_data.get_upcoming_events('KRX')

    # 타이틀 헤더 (장중 vs 마감 동적 텍스트 적용)
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"<div class='main-title'>🇰🇷 한국 증시 (KRX) {m_status['title_suffix']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.92rem;'>📅 <b>기준 일시:</b> {m_status['time_str']} | 실시간 지수, 수급, 주요 일정 큐레이션</div>", unsafe_allow_html=True)
    with col_t2:
        kp_ratio = data.get('kospi', {}).get('ratio', 0.0)
        action_word = "상승 중" if m_status['is_live'] else "상승 마감"
        down_word = "하락 중" if m_status['is_live'] else "하락 마감"
        flat_word = "보합 거래" if m_status['is_live'] else "보합 마감"

        if kp_ratio > 0:
            badge_html = f"<span style='background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>🔴 코스피 {action_word} ({kp_ratio:+.2f}%)</span>"
        elif kp_ratio < 0:
            badge_html = f"<span style='background: #172554; color: #93c5fd; border: 1px solid #1e40af; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>🔵 코스피 {down_word} ({kp_ratio:+.2f}%)</span>"
        else:
            badge_html = f"<span style='background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>⚪ 코스피 {flat_word}</span>"
        st.markdown(f"<div style='text-align: right; padding-top: 10px;'>{badge_html}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 1. 상단 주요 지표 카드 (KPI)
    k1, k2, k3, k4 = st.columns(4)
    
    kospi = data.get('kospi', {})
    kosdaq = data.get('kosdaq', {})
    fx = data.get('exchange_rate', {})
    inv_kp = data.get('investors_kospi', {})

    with k1:
        ratio = kospi.get('ratio', 0.0)
        st.metric(
            label="코스피 (KOSPI) " + ("(실시간)" if m_status['is_live'] else "(종가)"),
            value=f"{kospi.get('price', 0.0):,.2f}",
            delta=f"{kospi.get('change', 0.0):+,.2f} ({ratio:+.2f}%)"
        )
    with k2:
        kd_ratio = kosdaq.get('ratio', 0.0)
        st.metric(
            label="코스닥 (KOSDAQ) " + ("(실시간)" if m_status['is_live'] else "(종가)"),
            value=f"{kosdaq.get('price', 0.0):,.2f}",
            delta=f"{kosdaq.get('change', 0.0):+,.2f} ({kd_ratio:+.2f}%)"
        )
    with k3:
        fx_ratio = fx.get('ratio', 0.0)
        st.metric(
            label="원/달러 환율 (USD/KRW)",
            value=f"{fx.get('price', 1345.0):,.2f}원",
            delta=f"{fx.get('change', 0.0):+,.2f}원 ({fx_ratio:+.2f}%)",
            delta_color="inverse"
        )
    with k4:
        for_val = inv_kp.get('foreign', 0.0)
        st.metric(
            label="코스피 외국인 순매매",
            value=f"{for_val:+,.0f} 억원",
            delta="순매수 유입" if for_val > 0 else "순매도 출회",
            delta_color="normal" if for_val > 0 else "inverse"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 오늘의 시장 요약 (핵심 3선 + 심층 브리핑)
    section_summary_title = "📌 현재 장중 시장 상황 요약" if m_status['is_live'] else "📌 오늘의 시장 마감 요약"
    st.markdown(f"<div class='section-header'>{section_summary_title}</div>", unsafe_allow_html=True)
    
    # 3줄 핵심 총평 (다크 배경 + 고선명 텍스트)
    st.markdown("#### ⚡ **1분 핵심 총평**")
    for b in briefing['bullets']:
        b_formatted = b.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        st.markdown(f"<div class='summary-bullet'>• {b_formatted}</div>", unsafe_allow_html=True)

    # 상세 마켓 브리핑
    expander_title = "📖 **상세 마켓 브리핑 보기 (지수·수급·주도섹터 심층 분석)**"
    with st.expander(expander_title, expanded=True):
        st.markdown(briefing['detailed_brief'])

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. 차트 및 수급/대형주 2열 배치
    col_chart, col_stocks = st.columns([1, 1])

    with col_chart:
        st.markdown("<div class='section-header'>💰 투자 주체별 수급 동향 (KOSPI)</div>", unsafe_allow_html=True)
        # 수급 바 차트 (개인: 옐로우/골드, 외국인: 퍼플/바이올렛, 기관: 에메랄드 그린으로 3색 명확 분리)
        p_val = inv_kp.get('personal', 0.0)
        f_val = inv_kp.get('foreign', 0.0)
        i_val = inv_kp.get('institutional', 0.0)

        color_p = '#f59e0b' if p_val >= 0 else '#d97706'  # 개인: 골드/앰버
        color_f = '#8b5cf6' if f_val >= 0 else '#6366f1'  # 외국인: 바이올렛/퍼플
        color_i = '#10b981' if i_val >= 0 else '#059669'  # 기관: 에메랄드 그린

        fig_inv = go.Figure(go.Bar(
            x=['개인', '외국인', '기관'],
            y=[p_val, f_val, i_val],
            marker_color=[color_p, color_f, color_i],
            marker_line=dict(width=1.5, color=['#fbbf24', '#a78bfa', '#34d399']),
            text=[f"{p_val:+,.0f}억", f"{f_val:+,.0f}억", f"{i_val:+,.0f}억"],
            textposition='auto',
            textfont=dict(color='#ffffff', size=13, family='Pretendard')
        ))
        fig_inv.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=260,
            yaxis_title="순매수액 (억원)",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30,41,59,0.5)',
            font=dict(color='#e2e8f0')
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with col_stocks:
        st.markdown("<div class='section-header'>🏆 코스피 시가총액 상위 대형주</div>", unsafe_allow_html=True)
        top_stocks = data.get('top_stocks', [])
        if top_stocks:
            stock_data = []
            for s in top_stocks:
                stock_data.append({
                    "종목명": s.get('name'),
                    "현재가(원)": f"{s.get('price', 0):,.0f}",
                    "전일대비": f"{s.get('change', 0):+,.0f}",
                    "등락률": f"{s.get('ratio', 0):+.2f}%"
                })
            df_st = pd.DataFrame(stock_data)
            st.dataframe(df_st, use_container_width=True, hide_index=True)
        else:
            st.info("시가총액 상위 종목 데이터를 집계 중입니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. 주요 예정 사항 (Upcoming Catalysts) & 체크포인트
    col_cal, col_chk = st.columns([1, 1])

    with col_cal:
        st.markdown("<div class='section-header'>📅 주요 예정 사항 (Upcoming Events)</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #94a3b8; font-size: 0.88rem; margin-bottom: 12px;'>향후 증시 방향성을 결정지을 핵심 이벤트 캘린더입니다.</div>", unsafe_allow_html=True)
        
        for ev in events:
            st.markdown(f"""
            <div class='event-card'>
                <div>
                    <div class='event-title'>
                        {ev['title']}
                        <span class='{"badge-high" if ev["impact"] == "High" else "badge-med"}'>{ev['impact']}</span>
                    </div>
                    <div class='event-desc'>🗓️ {ev['date']} &nbsp;|&nbsp; {ev['desc']}</div>
                </div>
                <div class='event-dday {ev["color_cls"]}'>{ev['dday']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_chk:
        st.markdown(f"<div class='section-header'>💡 {briefing['chk_title']}</div>", unsafe_allow_html=True)
        chk_sub = "오늘 오후 장과 장 마감까지 확인해야 할 주요 팩터입니다." if m_status['is_live'] else "다음 거래일 시작 전 반드시 확인해야 할 3대 관전 포인트입니다."
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.88rem; margin-bottom: 12px;'>{chk_sub}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='checklist-box'>", unsafe_allow_html=True)
        for i, chk in enumerate(briefing['checkpoints'], 1):
            st.markdown(f"""
            <div class='checklist-item'>
                <div class='checklist-num'>{i}</div>
                <div style='color: #f1f5f9;'>{chk}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 리포트 다운로드 버튼
        btn_label = f"📥 {m_status['title_suffix']} 텍스트 다운로드 (.txt)"
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label=btn_label,
            data=briefing['full_text'],
            file_name=f"KRX_Market_Report_{data.get('date')}_{m_status['status']}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # 미국 증시 (US) 화면
    data = load_us()
    briefing = summary_engine.generate_us_briefing(data, is_live=m_status['is_live'], time_str=m_status['time_str'])
    events = calendar_data.get_upcoming_events('US')

    # 타이틀 헤더
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"<div class='main-title'>🇺🇸 미국 증시 (US) {m_status['title_suffix']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.92rem;'>📅 <b>기준 일시:</b> {m_status['time_str']} | 지수, 빅테크, 글로벌 매크로 브리핑</div>", unsafe_allow_html=True)
    with col_t2:
        indices = data.get('indices', {})
        sp_ratio = indices.get('^GSPC', {}).get('ratio', 0.0)
        action_word = "상승 중" if m_status['is_live'] else "상승 마감"
        down_word = "하락 중" if m_status['is_live'] else "하락 마감"
        flat_word = "혼조 거래" if m_status['is_live'] else "혼조 마감"

        if sp_ratio > 0:
            badge_html = f"<span style='background: #064e3b; color: #a7f3d0; border: 1px solid #059669; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>🟢 뉴욕 증시 {action_word}</span>"
        elif sp_ratio < 0:
            badge_html = f"<span style='background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>🔴 뉴욕 증시 {down_word}</span>"
        else:
            badge_html = f"<span style='background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 0.9rem;'>⚪ 뉴욕 증시 {flat_word}</span>"
        st.markdown(f"<div style='text-align: right; padding-top: 10px;'>{badge_html}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # 1. 상단 주요 지표 카드 (KPI)
    u1, u2, u3, u4 = st.columns(4)
    sp500 = indices.get('^GSPC', {})
    nasdaq = indices.get('^IXIC', {})
    macro = data.get('macro', {})
    tnx = macro.get('^TNX', {})
    vix = macro.get('^VIX', {})

    with u1:
        st.metric(
            label="S&P 500 " + ("(실시간)" if m_status['is_live'] else "(종가)"),
            value=f"{sp500.get('price', 0.0):,.2f}",
            delta=f"{sp500.get('change', 0.0):+,.2f} ({sp500.get('ratio', 0.0):+.2f}%)"
        )
    with u2:
        st.metric(
            label="나스닥 종합 (Nasdaq) " + ("(실시간)" if m_status['is_live'] else "(종가)"),
            value=f"{nasdaq.get('price', 0.0):,.2f}",
            delta=f"{nasdaq.get('change', 0.0):+,.2f} ({nasdaq.get('ratio', 0.0):+.2f}%)"
        )
    with u3:
        st.metric(
            label="미 국채 10년물 금리",
            value=f"{tnx.get('price', 0.0):.2f}%",
            delta=f"{tnx.get('change', 0.0):+,.2f}%p",
            delta_color="inverse"
        )
    with u4:
        st.metric(
            label="변동성 지수 (VIX)",
            value=f"{vix.get('price', 0.0):.2f} pt",
            delta=f"{vix.get('change', 0.0):+,.2f} pt",
            delta_color="inverse"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 오늘의 시장 요약 (핵심 3선 + 심층 브리핑)
    section_summary_title = "📌 현재 장중 시장 상황 요약" if m_status['is_live'] else "📌 오늘의 시장 마감 요약"
    st.markdown(f"<div class='section-header'>{section_summary_title}</div>", unsafe_allow_html=True)
    
    # 3줄 핵심 총평 (다크 테마 고선명 텍스트)
    st.markdown("#### ⚡ **1분 핵심 총평**")
    for b in briefing['bullets']:
        b_formatted = b.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        st.markdown(f"<div class='summary-bullet'>• {b_formatted}</div>", unsafe_allow_html=True)

    # 상세 마켓 브리핑
    with st.expander("📖 **상세 마켓 브리핑 보기 (3대 지수·매크로·M7 동향 심층 분석)**", expanded=True):
        st.markdown(briefing['detailed_brief'])

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. M7 종목 & 매크로 지표 2열 배치
    col_m7, col_macro = st.columns([1, 1])

    with col_m7:
        st.markdown("<div class='section-header'>🚀 M7 (빅테크 메가캡) 등락 현황</div>", unsafe_allow_html=True)
        m7_list = data.get('m7_stocks', [])
        if m7_list:
            m7_data = []
            for st_item in m7_list:
                m7_data.append({
                    "종목명": st_item.get('name'),
                    "티커": st_item.get('ticker'),
                    "현재가($)": f"${st_item.get('price', 0):,.2f}",
                    "등락률": f"{st_item.get('ratio', 0):+.2f}%"
                })
            df_m7 = pd.DataFrame(m7_data)
            st.dataframe(df_m7, use_container_width=True, hide_index=True)
        else:
            st.info("M7 종목 데이터를 집계 중입니다.")

    with col_macro:
        st.markdown("<div class='section-header'>🌐 글로벌 거시 매크로 지표</div>", unsafe_allow_html=True)
        macro_items = []
        for sym, m in macro.items():
            macro_items.append({
                "지표명": m.get('name'),
                "현재 수치": f"{m.get('price', 0):,.2f} {m.get('unit', '')}",
                "변동 폭": f"{m.get('change', 0):+,.2f}",
                "등락률": f"{m.get('ratio', 0):+.2f}%"
            })
        df_macro = pd.DataFrame(macro_items)
        st.dataframe(df_macro, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. 주요 예정 사항 (Upcoming Catalysts) & 체크포인트
    col_cal, col_chk = st.columns([1, 1])

    with col_cal:
        st.markdown("<div class='section-header'>📅 주요 예정 사항 (Upcoming Events)</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #94a3b8; font-size: 0.88rem; margin-bottom: 12px;'>FOMC, 핵심 물가/고용 지표, 어닝 시즌 등 글로벌 주요 촉매 캘린더입니다.</div>", unsafe_allow_html=True)
        
        for ev in events:
            st.markdown(f"""
            <div class='event-card'>
                <div>
                    <div class='event-title'>
                        {ev['title']}
                        <span class='{"badge-high" if ev["impact"] == "High" else "badge-med"}'>{ev['impact']}</span>
                    </div>
                    <div class='event-desc'>🗓️ {ev['date']} &nbsp;|&nbsp; {ev['desc']}</div>
                </div>
                <div class='event-dday {ev["color_cls"]}'>{ev['dday']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_chk:
        st.markdown(f"<div class='section-header'>💡 {briefing['chk_title']}</div>", unsafe_allow_html=True)
        chk_sub = "오늘 오후 장과 장 마감까지 확인해야 할 주요 팩터입니다." if m_status['is_live'] else "다음 거래일 시작 전 반드시 확인해야 할 3대 관전 포인트입니다."
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.88rem; margin-bottom: 12px;'>{chk_sub}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='checklist-box'>", unsafe_allow_html=True)
        for i, chk in enumerate(briefing['checkpoints'], 1):
            st.markdown(f"""
            <div class='checklist-item'>
                <div class='checklist-num'>{i}</div>
                <div style='color: #f1f5f9;'>{chk}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 리포트 다운로드 버튼
        btn_label = f"📥 {m_status['title_suffix']} 텍스트 다운로드 (.txt)"
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label=btn_label,
            data=briefing['full_text'],
            file_name=f"US_Market_Report_{data.get('date')}_{m_status['status']}.txt",
            mime="text/plain",
            use_container_width=True
        )

# 푸터
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>© 2026 글로벌 증시 브리핑 대시보드 | Real-time & Closing Intelligence</div>", unsafe_allow_html=True)
