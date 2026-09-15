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

/* 상단 패딩 축소 및 너비 확보 */
.block-container {
    padding-top: 1.8rem;
    padding-bottom: 2.5rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
    max-width: 1300px;
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

/* 상단 메인 타이틀 (00 Bookmarks 스타일 일치: #8AB4F8) */
.main-title {
    color: #8AB4F8 !important;
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
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
</style>
"""
