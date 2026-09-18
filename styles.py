"""
styles.py
Streamlit 대시보드를 위한 맞춤형 다크 테마(Dark Theme) CSS 스타일 정의
"""

CUSTOM_CSS = """
<style>
/* 전체 폰트 및 Pretendard 로드 */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

* {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
}

/* 상단 패딩 축소 및 너비 확보 (상단 툴바와 타이틀 간 쾌적한 여백 확보) */
.main .block-container,
[data-testid="stMainBlockContainer"],
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 2.5rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
    max-width: 100% !important;
}

/* 메트릭 카드 */
.metric-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    margin-bottom: 12px;
    color: #f8fafc;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.3);
    border-color: #475569;
}

.metric-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 4px;
}

/* 상단 메인 타이틀 (00 Bookmarks 스타일 일치: #8AB4F8, 여백 및 줄간격 확보) */
.main-title {
    color: #8AB4F8 !important;
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    text-align: center;
    letter-spacing: -0.5px;
    line-height: 1.4 !important;
    padding-top: 6px !important;
    padding-bottom: 2px !important;
    margin-top: 0 !important;
    margin-bottom: 6px !important;
    display: block;
    overflow: visible;
}

/* 섹션 타이틀 */
.section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.25rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-top: 26px;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 2px solid #334155;
}

/* 1분 핵심 총평 박스 & 불릿 */
.summary-bullet {
    background: #1e293b;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border: 1px solid #334155;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    font-size: 0.96rem;
    line-height: 1.65;
    color: #f1f5f9; /* 어두운 배경에 선명하고 편안한 오프화이트 글자 */
}

.summary-bullet strong {
    color: #60a5fa; /* 타이틀 강조 블루 */
}

/* 주요 예정 사항 (Upcoming Events) 카드 */
.event-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #f8fafc;
}

.event-title {
    font-weight: 700;
    font-size: 0.98rem;
    color: #ffffff;
}

.event-desc {
    color: #94a3b8;
    font-size: 0.84rem;
    margin-top: 4px;
    line-height: 1.4;
}

/* D-Day 뱃지 (다크 모드 고대비 디자인) */
.event-dday {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 800;
    white-space: nowrap;
    letter-spacing: 0.3px;
}
.dday-red {
    background: #450a0a;
    color: #fca5a5;
    border: 1px solid #7f1d1d;
}
.dday-orange {
    background: #451a03;
    color: #fde047;
    border: 1px solid #78350f;
}
.dday-blue {
    background: #172554;
    color: #93c5fd;
    border: 1px solid #1e40af;
}
.dday-gray {
    background: #1e293b;
    color: #cbd5e1;
    border: 1px solid #475569;
}

/* 중요도 뱃지 */
.badge-high {
    background: #7f1d1d;
    color: #fecaca;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    border: 1px solid #b91c1c;
}
.badge-med {
    background: #1e3a8a;
    color: #bfdbfe;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    border: 1px solid #2563eb;
}

/* 다음 거래일 핵심 체크포인트 박스 */
.checklist-box {
    background: #132e27;
    border: 1px solid #1c5244;
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 6px;
}

.checklist-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 0.95rem;
    line-height: 1.55;
    color: #e2e8f0;
}

.checklist-item:last-child {
    margin-bottom: 0;
}

.checklist-num {
    background: #10b981;
    color: #064e3b;
    font-weight: 800;
    border-radius: 50%;
    min-width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    margin-top: 2px;
}

/* Streamlit Expander 다크 스타일 보정 */
div[data-testid="stExpander"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}
div[data-testid="stExpander"] summary {
    color: #f1f5f9 !important;
}

/* 사이드바 다크 스타일 */
section[data-testid="stSidebar"] {
    background-color: #0b0f19;
    border-right: 1px solid #1e293b;
}

/* 사이드바 시장 운영 상태 뱃지 (가운데 정렬 강제 보장) */
.market-status-badge {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding: 8px 14px !important;
    border-radius: 6px !important;
    font-size: 0.88rem !important;
    margin-bottom: 4px !important;
}
.market-status-live {
    background: #064e3b !important;
    color: #a7f3d0 !important;
    font-weight: 700 !important;
    border: 1px solid #10b981 !important;
}
.market-status-closed {
    background: #1e293b !important;
    color: #cbd5e1 !important;
    font-weight: 600 !important;
    border: 1px solid #475569 !important;
}

/* 버튼 스타일 */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    background-color: #2563eb;
    color: #ffffff;
    border: none;
}
.stButton > button:hover {
    background-color: #1d4ed8;
    color: #ffffff;
}

/* 다운로드 버튼 */
.stDownloadButton > button {
    border-radius: 8px;
    font-weight: 600;
    background-color: #334155;
    color: #f1f5f9;
    border: 1px solid #475569;
}
.stDownloadButton > button:hover {
    background-color: #475569;
    color: #ffffff;
}

    /* =========================================================
       사이드바 접기(<<) 및 펼치기(>>) 버튼 항상 표시 및 시인성/대비 강화
       ========================================================= */
    /* 1. 사이드바가 열려 있을 때 접기 버튼 (<<) 상시 표시 */
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
        display: inline-flex !important;
    }
    
    [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        opacity: 1 !important;
        background-color: #1e293b !important;       /* 진한 네이비 배경 */
        border: 1.5px solid #38bdf8 !important;     /* 선명한 스카이블루 테두리로 상자 명확화 */
        border-radius: 8px !important;
        width: 38px !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    
    /* 상자 내부의 << 아이콘(Material Icon span/svg/문자)을 순백색으로 강제하여 상자와 극명한 대비 구현 */
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }

    /* =========================================================
       5열 메트릭 카드 및 슬림 인포 리본 바 스타일
       ========================================================= */
    /* Streamlit 메트릭 컴포넌트 폰트 및 여백 최적화 */
    [data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #475569;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        line-height: 1.25 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.80rem !important;
        font-weight: 600 !important;
    }

    /* 슬림 인포 리본 바 */
    .info-ribbon-container {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 10px 18px;
        margin-top: 4px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
    }
    .info-ribbon-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.88rem;
        font-weight: 700;
        color: #cbd5e1;
        white-space: nowrap;
    }
    .info-ribbon-content {
        display: flex;
        align-items: center;
        gap: 14px;
        flex-wrap: wrap;
    }
    .info-ribbon-group {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.84rem;
    }
    .info-group-label {
        color: #94a3b8;
        font-weight: 600;
    }
    .breadth-chip {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.2px;
    }
    .chip-up {
        background: rgba(239, 68, 68, 0.15);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .chip-flat {
        background: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    .chip-down {
        background: rgba(59, 130, 246, 0.15);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.35);
    }
    .chip-neutral {
        background: rgba(51, 65, 85, 0.4);
        color: #e2e8f0;
        border: 1px solid #475569;
    }
    .ribbon-divider {
        color: #334155;
        font-weight: 300;
        margin: 0 2px;
    }

    /* 코스피/코스닥 등락분포 슬림 인포 리본 바 */
    .metric-ribbon {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 10px 18px;
        margin-top: 4px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 16px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
    }
    .metric-ribbon-item {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .metric-ribbon-label {
        font-size: 0.88rem;
        font-weight: 700;
        color: #cbd5e1;
        white-space: nowrap;
    }
    .metric-ribbon-value {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .metric-ribbon-divider {
        width: 1px;
        height: 24px;
        background-color: #334155;
    }
    .up-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(239, 68, 68, 0.15);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .down-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(59, 130, 246, 0.15);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.35);
    }
    .flat-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    .ratio-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        background: rgba(51, 65, 85, 0.4);
        color: #e2e8f0;
        border: 1px solid #475569;
    }

    
    /* 호버(PC) 및 터치 시 반전 효과 */
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }

    /* 2. 사이드바 헤더 영역 패딩 및 정렬 보정 */
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 3. 사이드바가 닫혔을 때 다시 여는 버튼 (>>) 시인성 강화 */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button *,
    [data-testid="stSidebarCollapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapsedControl"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
    }
</style>
"""
