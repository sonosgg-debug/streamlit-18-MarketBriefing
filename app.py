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



# 1. 페이지 설정
st.set_page_config(
    page_title="글로벌 증시 브리핑 | 한국 & 미국",
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
        st.caption(f"• 현재 시각: {m_status.get('current_time_str', '')}")
        
        if m_status['is_live']:
            st.markdown(f"<div class='market-status-badge market-status-live' style='display: flex !important; align-items: center !important; justify-content: center !important; text-align: center !important; width: 100% !important; background: #064e3b; color: #a7f3d0; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 0.88rem; border: 1px solid #10b981;'>{m_status['label']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='market-status-badge market-status-closed' style='display: flex !important; align-items: center !important; justify-content: center !important; text-align: center !important; width: 100% !important; background: #1e293b; color: #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600; font-size: 0.88rem; border: 1px solid #475569;'>{m_status['label']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("### 🕒 **미국 증시(US) 운영 안내**")
        st.caption("• 정규 거래시간: 09:30 ~ 16:00 (ET)")
        st.caption(f"• 뉴욕 시각: {m_status.get('current_time_str', '')}")
        
        if m_status['is_live']:
            st.markdown(f"<div class='market-status-badge market-status-live' style='display: flex !important; align-items: center !important; justify-content: center !important; text-align: center !important; width: 100% !important; background: #064e3b; color: #a7f3d0; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 0.88rem; border: 1px solid #10b981;'>{m_status['label']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='market-status-badge market-status-closed' style='display: flex !important; align-items: center !important; justify-content: center !important; text-align: center !important; width: 100% !important; background: #1e293b; color: #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600; font-size: 0.88rem; border: 1px solid #475569;'>{m_status['label']}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 새로고침 버튼
    if st.button("🔄 Update", use_container_width=True):
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
    kp_ratio = data.get('kospi', {}).get('ratio', 0.0)
    action_word = "상승 중" if m_status['is_live'] else "상승 마감"
    down_word = "하락 중" if m_status['is_live'] else "하락 마감"
    flat_word = "보합 거래" if m_status['is_live'] else "보합 마감"

    if kp_ratio > 0:
        badge_html = f"<span style='background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>🔴 코스피 {action_word} ({kp_ratio:+.2f}%)</span>"
    elif kp_ratio < 0:
        badge_html = f"<span style='background: #172554; color: #93c5fd; border: 1px solid #1e40af; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>🔵 코스피 {down_word} ({kp_ratio:+.2f}%)</span>"
    else:
        badge_html = f"<span style='background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>⚪ 코스피 {flat_word}</span>"

    st.markdown(
        f"<div class='main-title'>🇰🇷 한국 증시 (KRX) {m_status['title_suffix']}</div>\n"
        f"<div style='text-align: center; color: #94a3b8; font-size: 0.92rem; margin-bottom: 8px;'>📅 <b>기준 일시:</b> {m_status['time_str']} | 실시간 지수, 수급, 주요 일정 큐레이션</div>\n"
        f"<div style='text-align: right; margin-bottom: 14px;'>{badge_html}</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # 1. 상단 주요 지표 카드 (KPI - 5개 패널 확장)
    k1, k2, k3, k4, k5 = st.columns(5)
    
    kospi = data.get('kospi', {})
    kosdaq = data.get('kosdaq', {})
    fx = data.get('exchange_rate', {})
    inv_kp = data.get('investors_kospi', {})
    prog = data.get('program', {})

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
        if m_status['is_live']:
            for_val = inv_kp.get('foreign', 0.0)
            kp_for_label = "코스피 외국인 순매매 (실시간)"
        else:
            inv_prev = data.get('investors_kospi_prev', {})
            prev_fmt = inv_prev.get('bizdate_fmt') or (inv_prev.get('date')[3:] if len(inv_prev.get('date', '')) >= 5 else '')
            badge = f"(마감: {prev_fmt})" if prev_fmt else "(마감)"
            kp_for_label = f"코스피 외국인 순매매 {badge}"
            for_val = inv_prev.get('foreign', inv_kp.get('foreign', 0.0))

        st.metric(
            label=kp_for_label,
            value=f"{for_val:+,.0f} 억원",
            delta="순매수 유입" if for_val > 0 else ("순매도 출회" if for_val < 0 else "보합"),
            delta_color="normal" if for_val > 0 else ("inverse" if for_val < 0 else "off")
        )
    with k5:
        non_arb = prog.get('non_arbitrage', 0.0)
        prog_time = prog.get('time_str', '')
        prog_badge = f"(실시간 {prog_time})" if (prog.get('is_live') and prog_time) else ("(실시간)" if prog.get('is_live') else f"(마감: {prog.get('bizdate_fmt', '')})")
        prog_label = f"프로그램 비차익 순매매 {prog_badge}"
        st.metric(
            label=prog_label,
            value=f"{non_arb:+,.0f} 억원",
            delta="순매수 유입" if non_arb > 0 else ("순매도 출회" if non_arb < 0 else "보합"),
            delta_color="normal" if non_arb > 0 else ("inverse" if non_arb < 0 else "off")
        )

    # 1-1. 시장 등락 종목 수 슬림 인포 리본 바 (Option 1)
    breadth = data.get('breadth', {})
    kp_b = breadth.get('kospi', {})
    kd_b = breadth.get('kosdaq', {})

    kp_up = kp_b.get('up', 0)
    kp_down = kp_b.get('down', 0)
    kp_flat = kp_b.get('flat', 0)
    kp_ratio = kp_b.get('up_ratio', 0.0)

    kd_up = kd_b.get('up', 0)
    kd_down = kd_b.get('down', 0)
    kd_flat = kd_b.get('flat', 0)
    kd_ratio = kd_b.get('up_ratio', 0.0)

    st.markdown(f"""
    <div class='metric-ribbon'>
        <div class='metric-ribbon-item'>
            <span class='metric-ribbon-label'>KS 코스피 등락분포</span>
            <span class='metric-ribbon-value'>
                <span class='up-badge'>▲ 상승 {kp_up}</span>
                <span class='down-badge'>▼ 하락 {kp_down}</span>
                <span class='flat-badge'>- 보합 {kp_flat}</span>
                <span class='ratio-badge'>({kp_ratio:.1f}%)</span>
            </span>
        </div>
        <div class='metric-ribbon-divider'></div>
        <div class='metric-ribbon-item'>
            <span class='metric-ribbon-label'>KQ 코스닥 등락분포</span>
            <span class='metric-ribbon-value'>
                <span class='up-badge'>▲ 상승 {kd_up}</span>
                <span class='down-badge'>▼ 하락 {kd_down}</span>
                <span class='flat-badge'>- 보합 {kd_flat}</span>
                <span class='ratio-badge'>({kd_ratio:.1f}%)</span>
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 1분 핵심 요약 총평 (Executive Bullets)
    st.markdown("<div class='section-header'>⚡ 당일 시장 핵심 1분 총평</div>", unsafe_allow_html=True)
    bullets_html = "".join([f"<li class='bullet-item' style='margin-bottom: 8px;'>{b}</li>" for b in briefing['bullets']])
    st.markdown(f"""
    <div class='bullet-box'>
        <ul style='list-style-type: none; padding-left: 0; margin-bottom: 0;'>
            {bullets_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 2-1. 상세 마켓 브리핑 (아코디언 형태)
    expander_title = "📖 **상세 마켓 브리핑 보기 (지수·수급·주도섹터 심층 분석)**"
    with st.expander(expander_title, expanded=False):
        st.markdown(briefing['detailed_brief'])

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. 차트 및 수급/대형주 2열 배치
    col_chart, col_stocks = st.columns([1, 1])

    with col_chart:
        st.markdown("<div class='section-header'>💰 투자 주체별 수급 동향 (KOSPI)</div>", unsafe_allow_html=True)
        
        tab_live, tab_prev = st.tabs(["🔴 당일 장중 실시간 잠정", "🏁 전일 마감 확정 수급"])

        with tab_live:
            # 1. 당일 실시간 바 차트
            is_pre_market = m_status.get('status') == 'PRE_MARKET'
            is_today = inv_kp.get('is_today', True)
            if is_pre_market or not is_today:
                p_val, f_val, i_val = 0.0, 0.0, 0.0
            else:
                p_val = inv_kp.get('personal', 0.0)
                f_val = inv_kp.get('foreign', 0.0)
                i_val = inv_kp.get('institutional', 0.0)

            live_time = prog.get('time_str', '')
            live_time_str = f" ({live_time} 기준)" if live_time else ""

            if m_status.get('status') == 'PRE_MARKET':
                st.caption(f"📅 **현재 시각**: {m_status.get('current_time_str', '')} | ⏳ **개장 전 대기**: 현재 정규장 개장 전으로 실시간 잠정치는 0으로 표시됩니다. (직전 거래일 마감 확정치는 오른쪽 탭 참조)")
            else:
                st.caption(f"📅 **집계 기준**: {m_status.get('current_time_str', '')}{live_time_str} | 💡 주요 거래원 상위 5개사 기반 실시간 잠정치")

            color_p = '#f59e0b' if p_val > 0 else ('#d97706' if p_val < 0 else '#64748b')  # 개인: 골드/앰버 (0: 슬레이트)
            color_f = '#8b5cf6' if f_val > 0 else ('#6366f1' if f_val < 0 else '#64748b')  # 외국인: 바이올렛/퍼플 (0: 슬레이트)
            color_i = '#10b981' if i_val > 0 else ('#059669' if i_val < 0 else '#64748b')  # 기관: 에메랄드 그린 (0: 슬레이트)

            # 상단 텍스트 잘림 방지 헤드룸 계산
            vals_live = [p_val, f_val, i_val]
            max_lv = max(vals_live)
            min_lv = min(vals_live)
            span_lv = max(abs(max_lv), abs(min_lv), 100.0)
            pad_lv = max(span_lv * 0.25, 200.0)
            yl_upper = (max_lv + pad_lv) if max_lv > 0 else pad_lv
            yl_lower = (min_lv - pad_lv) if min_lv < 0 else -pad_lv

            fig_inv = go.Figure(go.Bar(
                x=['개인', '외국인', '기관'],
                y=[p_val, f_val, i_val],
                marker_color=[color_p, color_f, color_i],
                marker_line=dict(width=1.5, color=['#fbbf24' if p_val != 0 else '#94a3b8', '#a78bfa' if f_val != 0 else '#94a3b8', '#34d399' if i_val != 0 else '#94a3b8']),
                text=[f"{p_val:+,.0f}억" if p_val != 0 else "0억", f"{f_val:+,.0f}억" if f_val != 0 else "0억", f"{i_val:+,.0f}억" if i_val != 0 else "0억"],
                textposition='auto',
                cliponaxis=False,
                textfont=dict(color='#ffffff', size=13, family='Pretendard')
            ))
            fig_inv.update_layout(
                margin=dict(l=20, r=20, t=32, b=15),
                height=230,
                yaxis_title="순매수액 (억원)",
                yaxis=dict(range=[yl_lower, yl_upper]),
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.5)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig_inv, use_container_width=True)

        with tab_prev:
            inv_prev = data.get('investors_kospi_prev', {})
            prev_date = inv_prev.get('date', '직전 거래일')
            st.caption(f"🏁 **집계 기준**: 20{prev_date} 정규장 마감 확정치 (한국거래소 공식 정산 집계)")

            pp_val = inv_prev.get('personal', 0.0)
            pf_val = inv_prev.get('foreign', 0.0)
            pi_val = inv_prev.get('institutional', 0.0)

            color_pp = '#f59e0b' if pp_val >= 0 else '#d97706'
            color_pf = '#8b5cf6' if pf_val >= 0 else '#6366f1'
            color_pi = '#10b981' if pi_val >= 0 else '#059669'

            # 상단 텍스트 잘림 방지 헤드룸 계산
            vals_prev = [pp_val, pf_val, pi_val]
            max_pv = max(vals_prev) if vals_prev else 0.0
            min_pv = min(vals_prev) if vals_prev else 0.0
            span_pv = max(abs(max_pv), abs(min_pv), 100.0)
            pad_pv = max(span_pv * 0.25, 200.0)
            yp_upper = (max_pv + pad_pv) if max_pv > 0 else pad_pv
            yp_lower = (min_pv - pad_pv) if min_pv < 0 else -pad_pv

            fig_prev = go.Figure(go.Bar(
                x=['개인', '외국인', '기관'],
                y=[pp_val, pf_val, pi_val],
                marker_color=[color_pp, color_pf, color_pi],
                marker_line=dict(width=1.5, color=['#fbbf24', '#a78bfa', '#34d399']),
                text=[f"{pp_val:+,.0f}억", f"{pf_val:+,.0f}억", f"{pi_val:+,.0f}억"],
                textposition='auto',
                cliponaxis=False,
                textfont=dict(color='#ffffff', size=13, family='Pretendard')
            ))
            fig_prev.update_layout(
                margin=dict(l=20, r=20, t=32, b=15),
                height=230,
                yaxis_title="순매수액 (억원)",
                yaxis=dict(range=[yp_lower, yp_upper]),
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,41,59,0.5)',
                font=dict(color='#e2e8f0')
            )
            st.plotly_chart(fig_prev, use_container_width=True)

            # 최근 5거래일 일자별 수급 표
            df_hist = data.get('investors_history_kospi', pd.DataFrame())
            if not df_hist.empty:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 600; margin-top: 10px; margin-bottom: 4px; color: #cbd5e1;'>📋 최근 5거래일 일자별 수급 추이 (단위: 억원)</div>", unsafe_allow_html=True)
                show_cols = [c for c in ['날짜', '개인', '외국인', '기관계', '금융투자', '연기금', '기타법인'] if c in df_hist.columns]
                df_disp = df_hist[show_cols].copy()
                for c in show_cols[1:]:
                    df_disp[c] = df_disp[c].apply(lambda x: f"{x:+,.0f}")
                st.dataframe(df_disp, use_container_width=True, hide_index=True)

    with col_stocks:
        st.markdown("<div class='section-header'>🏆 코스피 시가총액 상위 대형주</div>", unsafe_allow_html=True)
        
        tab_st_live, tab_st_prev = st.tabs(["🔴 당일 장중 실시간 시세", "🏁 전일 마감 확정 시세"])

        with tab_st_live:
            top_stocks = data.get('top_stocks', [])
            if m_status.get('status') == 'PRE_MARKET':
                st.caption(f"📅 **현재 시각**: {m_status.get('current_time_str', '')} | ⏳ **개장 전 대기**: 09:00 정규장 개장 후 실시간 체결 시세가 반영됩니다.")
            else:
                st.caption(f"📅 **집계 기준**: {m_status.get('current_time_str', '')} | 💡 실시간 정규장 체결 기준")

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

        with tab_st_prev:
            top_stocks_prev = data.get('top_stocks_prev', [])
            prev_date_st = data.get('top_stocks_prev_date', '')
            prev_badge_st = prev_date_st if prev_date_st else "직전 거래일"
            st.caption(f"🏁 **집계 기준**: {prev_badge_st} 정규장 마감 확정치 (한국거래소 공식 종가)")

            if top_stocks_prev:
                stock_prev_data = []
                for s in top_stocks_prev:
                    stock_prev_data.append({
                        "종목명": s.get('name'),
                        "종가(원)": f"{s.get('price', 0):,.0f}",
                        "전일대비": f"{s.get('change', 0):+,.0f}",
                        "등락률": f"{s.get('ratio', 0):+.2f}%"
                    })
                df_st_prev = pd.DataFrame(stock_prev_data)
                st.dataframe(df_st_prev, use_container_width=True, hide_index=True)
            else:
                st.info("전일 마감 종목 데이터를 집계 중입니다.")

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
            file_name=f"KRX_Market_Briefing_{data.get('date')}_{m_status['status']}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # 미국 증시 (US) 화면
    data = load_us()
    briefing = summary_engine.generate_us_briefing(data, is_live=m_status['is_live'], time_str=m_status['time_str'])
    events = calendar_data.get_upcoming_events('US')

    # 타이틀 헤더
    indices = data.get('indices', {})
    sp_ratio = indices.get('^GSPC', {}).get('ratio', 0.0)
    action_word = "상승 중" if m_status['is_live'] else "상승 마감"
    down_word = "하락 중" if m_status['is_live'] else "하락 마감"
    flat_word = "혼조 거래" if m_status['is_live'] else "혼조 마감"

    if sp_ratio > 0:
        badge_html = f"<span style='background: #064e3b; color: #a7f3d0; border: 1px solid #059669; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>🟢 뉴욕 증시 {action_word}</span>"
    elif sp_ratio < 0:
        badge_html = f"<span style='background: #450a0a; color: #fca5a5; border: 1px solid #7f1d1d; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>🔴 뉴욕 증시 {down_word}</span>"
    else:
        badge_html = f"<span style='background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.88rem; display: inline-block;'>⚪ 뉴욕 증시 {flat_word}</span>"

    st.markdown(
        f"<div class='main-title'>🇺🇸 미국 증시 (US) {m_status['title_suffix']}</div>\n"
        f"<div style='text-align: center; color: #94a3b8; font-size: 0.92rem; margin-bottom: 8px;'>📅 <b>기준 일시:</b> {m_status['time_str']} | 지수, 빅테크, 글로벌 매크로 브리핑</div>\n"
        f"<div style='text-align: right; margin-bottom: 14px;'>{badge_html}</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # 1. 상단 주요 지표 카드 (KPI - 5개 패널 확장)
    u1, u2, u3, u4, u5 = st.columns(5)
    sp500 = indices.get('^GSPC', {})
    nasdaq = indices.get('^IXIC', {})
    sox = indices.get('^SOX', {})
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
            label="필라델피아 반도체 (SOX) " + ("(실시간)" if m_status['is_live'] else "(종가)"),
            value=f"{sox.get('price', 0.0):,.2f}",
            delta=f"{sox.get('change', 0.0):+,.2f} ({sox.get('ratio', 0.0):+.2f}%)"
        )
    with u4:
        st.metric(
            label="미 국채 10년물 금리",
            value=f"{tnx.get('price', 0.0):.2f}%",
            delta=f"{tnx.get('change', 0.0):+,.2f}%p",
            delta_color="inverse"
        )
    with u5:
        st.metric(
            label="변동성 지수 (VIX)",
            value=f"{vix.get('price', 0.0):.2f} pt",
            delta=f"{vix.get('change', 0.0):+,.2f} pt",
            delta_color="inverse"
        )

    # 1-1. 글로벌 거시 & 주요 지수 슬림 인포 리본 바 (대칭 컴포넌트)
    dow = indices.get('^DJI', {})
    rut = indices.get('^RUT', {})
    oil = macro.get('CL=F', {})
    dxy = macro.get('DX-Y.NYB', {})

    dow_ratio = dow.get('ratio', 0.0)
    rut_ratio = rut.get('ratio', 0.0)
    oil_price = oil.get('price', 0.0)
    oil_ratio = oil.get('ratio', 0.0)
    dxy_price = dxy.get('price', 0.0)
    dxy_ratio = dxy.get('ratio', 0.0)

    dow_chip_cls = 'chip-up' if dow_ratio > 0 else ('chip-down' if dow_ratio < 0 else 'chip-flat')
    rut_chip_cls = 'chip-up' if rut_ratio > 0 else ('chip-down' if rut_ratio < 0 else 'chip-flat')
    oil_chip_cls = 'chip-up' if oil_ratio > 0 else ('chip-down' if oil_ratio < 0 else 'chip-flat')
    dxy_chip_cls = 'chip-up' if dxy_ratio > 0 else ('chip-down' if dxy_ratio < 0 else 'chip-flat')

    us_ribbon_html = f"""
    <div class='info-ribbon-container'>
        <div class='info-ribbon-title'>
            <span>🌐 <b>뉴욕 보조 지표 및 거시 지표 요약</b></span>
        </div>
        <div class='info-ribbon-content'>
            <div class='info-ribbon-group'>
                <span class='info-group-label'>다우존스:</span>
                <span class='breadth-chip {dow_chip_cls}'>{dow.get('price', 0.0):,.2f} ({dow_ratio:+.2f}%)</span>
            </div>
            <div class='info-ribbon-group'>
                <span class='info-group-label'>러셀 2000(소형주):</span>
                <span class='breadth-chip {rut_chip_cls}'>{rut.get('price', 0.0):,.2f} ({rut_ratio:+.2f}%)</span>
            </div>
            <span class='ribbon-divider'>|</span>
            <div class='info-ribbon-group'>
                <span class='info-group-label'>WTI 유가:</span>
                <span class='breadth-chip {oil_chip_cls}'>${oil_price:.2f} ({oil_ratio:+.2f}%)</span>
            </div>
            <div class='info-ribbon-group'>
                <span class='info-group-label'>달러 인덱스:</span>
                <span class='breadth-chip {dxy_chip_cls}'>{dxy_price:.2f}pt ({dxy_ratio:+.2f}%)</span>
            </div>
        </div>
    </div>
    """
    st.markdown(us_ribbon_html, unsafe_allow_html=True)


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
            unit = m.get('unit', '')
            price = m.get('price', 0)
            if unit == '$':
                cur_val = f"${price:,.2f}"
            elif unit == '%':
                cur_val = f"{price:,.2f}%"
            elif unit:
                cur_val = f"{price:,.2f} {unit}"
            else:
                cur_val = f"{price:,.2f}"

            macro_items.append({
                "지표명": m.get('name'),
                "현재 수치": cur_val,
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
            file_name=f"US_Market_Briefing_{data.get('date')}_{m_status['status']}.txt",
            mime="text/plain",
            use_container_width=True
        )

# 푸터
st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>© 2026 글로벌 증시 브리핑 대시보드 | Real-time & Closing Intelligence</div>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 8px; margin-bottom: 24px; line-height: 1.6;'>⚠️ 본 서비스에서 제공하는 모든 정보는 투자 참고용이며, 투자의 최종 결정과 책임은 투자자 본인에게 있습니다.</div>", unsafe_allow_html=True)
