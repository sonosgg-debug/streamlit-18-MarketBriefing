"""
summary_engine.py
금융 데이터 분석 및 인텔리전트 마감/장중 요약 브리핑 생성 엔진
- 장 진행 중(Live) 및 마감 완료(Closed) 상태를 구분하여 맞춤형 텍스트 제공
"""

def generate_krx_briefing(krx_data, is_live=False, time_str=""):
    """
    한국 시장(KRX) 요약 생성 (is_live에 따라 장중/마감 문구 자동 분기)
    """
    kospi = krx_data.get('kospi', {})
    kosdaq = krx_data.get('kosdaq', {})
    inv_kp = krx_data.get('investors_kospi', {})
    inv_kd = krx_data.get('investors_kosdaq', {})
    fx = krx_data.get('exchange_rate', {})
    top_stocks = krx_data.get('top_stocks', [])

    kp_price = kospi.get('price', 0.0)
    kp_change = kospi.get('change', 0.0)
    kp_ratio = kospi.get('ratio', 0.0)

    kd_price = kosdaq.get('price', 0.0)
    kd_change = kosdaq.get('change', 0.0)
    kd_ratio = kosdaq.get('ratio', 0.0)

    fx_price = fx.get('price', 1345.0)
    fx_change = fx.get('change', 0.0)

    kp_foreign = inv_kp.get('foreign', 0.0)
    kp_inst = inv_kp.get('institutional', 0.0)
    kp_indiv = inv_kp.get('personal', 0.0)

    program = krx_data.get('program', {})
    prog_non_arb = program.get('non_arbitrage', 0.0)

    breadth = krx_data.get('breadth', {})
    kp_breadth = breadth.get('kospi', {})
    kd_breadth = breadth.get('kosdaq', {})

    # 1. 시장 분위기 판정 (Market Tone)
    action_verb = "흐름을 보이고 있습니다" if is_live else "마감했습니다"
    state_suffix = "전개 중" if is_live else "마감"

    if kp_ratio >= 1.0:
        kp_tone = f"강한 상승 탄력으로 안도 랠리 {state_suffix}"
    elif kp_ratio > 0:
        kp_tone = f"상승세를 유지하며 완만한 오름세 {state_suffix}"
    elif kp_ratio > -0.5:
        kp_tone = f"숨고르기 장세 속 약보합 혼조 {state_suffix}"
    elif kp_ratio > -1.5:
        kp_tone = f"하방 압력 속 경계 매물 출회 {state_suffix}"
    else:
        kp_tone = f"급격한 차익실현 및 투자심리 위축으로 급락 {state_suffix}"

    # 수급 코멘트 판정
    verb_flow = "나타내고 있습니다" if is_live else "나타냈습니다"
    prog_word = f"프로그램 비차익 매매는 {prog_non_arb:+,.0f}억원 규모의 {'순매수 유입' if prog_non_arb >= 0 else '순매도 출회'}"
    if kp_foreign < 0 and kp_inst < 0:
        flow_comment = f"외국인(-{abs(kp_foreign):,.0f}억)과 기관(-{abs(kp_inst):,.0f}억)의 동반 순매도 속에 개인이 홀로 물량을 받아내는 양상이며, {prog_word}"
    elif kp_foreign > 0 and kp_inst > 0:
        flow_comment = f"외국인(+{kp_foreign:,.0f}억)과 기관(+{kp_inst:,.0f}억)의 '쌍끌이' 순매수세가 지수 반등을 견인하고 있으며, {prog_word}"
    elif kp_foreign > 0 and kp_inst <= 0:
        flow_comment = f"외국인의 순매수(+{kp_foreign:,.0f}억) 유입에도 기관 매도세로 지수 상단이 제한되는 흐름 속에 {prog_word}"
    else:
        flow_comment = f"기관의 방어적 매수에도 외국인 순매도(-{abs(kp_foreign):,.0f}억)가 이어지며 수급 공방 속에 {prog_word}"

    # 시총 상위주 동향
    up_stocks = [s['name'] for s in top_stocks if s.get('ratio', 0) > 0]
    down_stocks = [s['name'] for s in top_stocks if s.get('ratio', 0) < 0]
    stock_trend = ""
    st_action = "강세를 나타내는 반면" if is_live else "강세를 보인 반면"
    st_down_action = "하락세를 보이며" if is_live else "하락 마감하며"
    if up_stocks and down_stocks:
        stock_trend = f"대형주 중에서는 {', '.join(up_stocks[:2])} 등이 {st_action}, {', '.join(down_stocks[:2])} 등은 {st_down_action} 종목별 차별화"
    elif up_stocks:
        stock_trend = f"대형주 전반에서 {', '.join(up_stocks[:3])} 등을 필두로 고른 상승세"
    elif down_stocks:
        stock_trend = f"{', '.join(down_stocks[:3])} 등 주요 대형주들이 동반 약세를 기록"

    # 체감 등락 코멘트
    breadth_comment = ""
    kp_up_cnt = kp_breadth.get('up', 0)
    kp_down_cnt = kp_breadth.get('down', 0)
    if kp_breadth.get('total', 0) > 0 and (kp_up_cnt > 0 or kp_down_cnt > 0):
        feel_tone = '우세' if kp_up_cnt > kp_down_cnt else ('팽팽' if kp_up_cnt == kp_down_cnt else '둔화')
        breadth_comment = f" (코스피 상승 {kp_up_cnt}종목 vs 하락 {kp_down_cnt}종목으로 체감 장세 {feel_tone})"

    # 1분 핵심 총평 (3 Bullets)
    bullets = [
        f"**지수 동향**: 코스피는 {kp_tone} ({kp_price:,.2f}pt, {kp_ratio:+.2f}%), 코스닥은 {kd_price:,.2f}pt({kd_ratio:+.2f}%)를 기록{breadth_comment}.",
        f"**수급 핵심**: 유가증권시장에서 {flow_comment}.",
        f"**거시/환율**: 원/달러 환율은 {fx_price:,.2f}원({fx_change:+.2f}원)선에서 등락하며 글로벌 금리 및 대외 변수를 반영."
    ]

    # 상세 마켓 브리핑
    title_brief_sec = "장중 지수 흐름 & 분위기" if is_live else "장세 총평 & 지수 흐름"
    detailed_brief = f"""
**[{title_brief_sec}]**
오늘 국내 증시는 코스피가 {kp_price:,.2f}pt({kp_ratio:+.2f}%), 코스닥이 {kd_price:,.2f}pt({kd_ratio:+.2f}%) 수준에서 {action_verb}. 
장 초반 글로벌 매크로 지표 관망 심리와 주요 이벤트를 앞두고 관망세가 짙었으나, {('코스닥 성장주 중심의 저가 매수세가 유입되며 시장 전반에 방어력이 형성' if kd_ratio > 0 else '대형주 전반에 매물이 출회되며 숨고르기 양상')}되고 있습니다.
코스피 시장의 등락 분포는 상승 {kp_breadth.get('up', 0)}개, 하락 {kp_breadth.get('down', 0)}개(상승 비율 {kp_breadth.get('up_ratio', 0.0)}%), 코스닥은 상승 {kd_breadth.get('up', 0)}개, 하락 {kd_breadth.get('down', 0)}개(상승 비율 {kd_breadth.get('up_ratio', 0.0)}%)를 나타내고 있습니다.

**[투자 주체별 수급 & 자금 동향]**
코스피 시장에서는 {flow_comment}을 {verb_flow}. 기관과 외국인의 알고리즘 패시브 매매 척도인 비차익 순매매는 {prog_non_arb:+,.0f}억 원으로 집계되었습니다. 코스닥 시장에서는 개인 {inv_kd.get('personal', 0):+,.0f}억, 외국인 {inv_kd.get('foreign', 0):+,.0f}억, 기관 {inv_kd.get('institutional', 0):+,.0f}억 원의 포지션을 취하고 있습니다. 
특히 외국인의 현·선물 포지션 변화와 환율 변동성({fx_price:,.1f}원)이 지수 방향성에 결정적인 변수로 작용하고 있습니다.

**[주요 섹터 및 대형주 동향]**
{stock_trend if stock_trend else '시총 상위 종목군에서 실적 모멘텀 보유주와 밸류업 수혜주 중심으로 순환매'}가 활발히 전개되고 있습니다. 특히 반도체, 2차전지, 바이오 등 주요 수출 주도 업종 간 엇갈린 수급이 관찰됩니다.
""".strip()

    # 체크포인트 3선
    chk_title = "오후 장 및 마감 관전 포인트" if is_live else "내일의 핵심 투자 체크포인트"
    checkpoints = [
        f"원/달러 환율 {fx_price:,.1f}원선 안착 여부 및 외국인의 현·선물 및 프로그램 비차익 순매수 복귀 시점 확인",
        "미국 야간 증시에서의 필라델피아 반도체 지수 및 빅테크(M7) 주가 변동성 체크",
        "다가오는 주요 경제 이벤트(금통위 및 글로벌 중앙은행 통화정책)를 앞둔 차익실현 매물 소화 과정 주시"
    ]

    report_type_kr = "실시간 장중 브리핑" if is_live else "마감 데일리 브리핑"
    full_report_text = f"""[한국 증시(KRX) {report_type_kr}]
📅 기준: {time_str if time_str else krx_data.get('date')}

■ 주요 지수 및 등락 현황
- 코스피(KOSPI): {kp_price:,.2f}pt ({kp_ratio:+.2f}%) [상승: {kp_breadth.get('up', 0)}, 하락: {kp_breadth.get('down', 0)}, 보합: {kp_breadth.get('flat', 0)}]
- 코스닥(KOSDAQ): {kd_price:,.2f}pt ({kd_ratio:+.2f}%) [상승: {kd_breadth.get('up', 0)}, 하락: {kd_breadth.get('down', 0)}, 보합: {kd_breadth.get('flat', 0)}]
- 원/달러 환율: {fx_price:,.2f}원 ({fx_change:+.2f}원)

■ 투자자별 및 프로그램 수급 (코스피)
- 개인: {kp_indiv:+,.0f}억원
- 외국인: {kp_foreign:+,.0f}억원
- 기관: {kp_inst:+,.0f}억원
- 프로그램 비차익: {prog_non_arb:+,.0f}억원

■ 핵심 3줄 요약
1. {bullets[0].replace('**', '')}
2. {bullets[1].replace('**', '')}
3. {bullets[2].replace('**', '')}

■ 마켓 브리핑
{detailed_brief}

■ 주요 관전 포인트
- {checkpoints[0]}
- {checkpoints[1]}
- {checkpoints[2]}
"""

    return {
        'bullets': bullets,
        'detailed_brief': detailed_brief,
        'checkpoints': checkpoints,
        'full_text': full_report_text,
        'chk_title': chk_title
    }


def generate_us_briefing(us_data, is_live=False, time_str=""):
    """
    미국 시장(US) 요약 생성
    """
    indices = us_data.get('indices', {})
    macro = us_data.get('macro', {})
    m7 = us_data.get('m7_stocks', [])

    sp500 = indices.get('^GSPC', {'price': 0.0, 'change': 0.0, 'ratio': 0.0})
    nasdaq = indices.get('^IXIC', {'price': 0.0, 'change': 0.0, 'ratio': 0.0})
    sox = indices.get('^SOX', {'price': 0.0, 'change': 0.0, 'ratio': 0.0})
    dow = indices.get('^DJI', {'price': 0.0, 'change': 0.0, 'ratio': 0.0})
    rut = indices.get('^RUT', {'price': 0.0, 'change': 0.0, 'ratio': 0.0})

    vix = macro.get('^VIX', {'price': 15.0, 'change': 0.0, 'ratio': 0.0})
    tnx = macro.get('^TNX', {'price': 4.0, 'change': 0.0, 'ratio': 0.0})
    oil = macro.get('CL=F', {'price': 70.0, 'change': 0.0, 'ratio': 0.0})
    dxy = macro.get('DX-Y.NYB', {'price': 101.0, 'change': 0.0, 'ratio': 0.0})

    sp_ratio = sp500.get('ratio', 0.0)
    nasdaq_ratio = nasdaq.get('ratio', 0.0)
    sox_ratio = sox.get('ratio', 0.0)
    
    state_suffix = "전개 중" if is_live else "마감"
    action_verb = "등락을 보이고 있습니다" if is_live else "마감했습니다"

    if nasdaq_ratio >= 1.0:
        us_tone = f"빅테크 중심의 강력한 매수세 유입으로 기술주 랠리 {state_suffix}"
    elif nasdaq_ratio > 0:
        us_tone = f"완만한 상승 탄력을 유지하며 안도 장세 {state_suffix}"
    elif nasdaq_ratio > -0.7:
        us_tone = f"주요 경제지표 발표를 앞두고 관망세 속 혼조 {state_suffix}"
    elif nasdaq_ratio > -1.5:
        us_tone = f"국채 금리 부담 및 고점 부담 속 차익 매물 출회 {state_suffix}"
    else:
        us_tone = f"경기 침체 및 밸류에이션 부담이 부각되며 급락 {state_suffix}"

    m7_up = [s['name'].split(' ')[0] for s in m7 if s.get('ratio', 0) > 0]
    m7_down = [s['name'].split(' ')[0] for s in m7 if s.get('ratio', 0) < 0]
    m7_summary = ""
    if m7_up and m7_down:
        m7_summary = f"M7 메가캡 종목군에서는 {', '.join(m7_up[:2])}가 선방한 반면, {', '.join(m7_down[:2])}는 조정을 받으며 혼조세"
    elif m7_up:
        m7_summary = f"M7 종목군 전반에서 {', '.join(m7_up[:3])} 등을 중심으로 매수세가 확산"
    elif m7_down:
        m7_summary = f"{', '.join(m7_down[:3])} 등 주요 빅테크 종목들이 일제히 약세를 보이며 지수에 부담"

    sox_comment = f" / 필라델피아 반도체 {sox.get('price', 0):,.2f}pt({sox_ratio:+.2f}%)" if sox.get('price', 0) > 0 else ""

    bullets = [
        f"**지수 동향**: 뉴욕 증시는 {us_tone} (S&P500 {sp500.get('price'):,.2f}, {sp_ratio:+.2f}% / 나스닥 {nasdaq.get('price'):,.2f}, {nasdaq_ratio:+.2f}%{sox_comment}).",
        f"**빅테크(M7) 흐름**: {m7_summary if m7_summary else 'AI 반도체 및 빅테크 종목 간 실적 기대감과 차익 실현 욕구가 교차'}.",
        f"**매크로 & 채권**: 미 국채 10년물 금리는 {tnx.get('price', 0):.2f}%({tnx.get('change', 0):+.2f}%p), VIX 변동성 지수는 {vix.get('price', 0):.2f}pt 수준 기록."
    ]

    title_sec = "뉴욕 장중 지수 흐름" if is_live else "뉴욕 주요 지수 흐름 & 총평"
    detailed_brief = f"""
**[{title_sec}]**
미국 증시는 S&P 500({sp500.get('price'):,.2f}, {sp_ratio:+.2f}%), 나스닥({nasdaq.get('price'):,.2f}, {nasdaq_ratio:+.2f}%), 다우존스({dow.get('price'):,.2f}, {dow.get('ratio', 0):+.2f}%)로 {action_verb}. 
글로벌 기술주 바로미터인 필라델피아 반도체 지수(SOX)는 {sox.get('price', 0):,.2f}pt({sox_ratio:+.2f}%)를 기록하며 반도체 하드웨어 업황에 대한 투자 심리를 반영했습니다. 중소형주 중심의 러셀 2000 지수는 {rut.get('ratio', 0):+.2f}%로 마감했습니다.

**[매크로 지표 & 금리 환경]**
미 국채 10년물 금리가 {tnx.get('price', 0):.2f}%선에서 등락하며 연준의 통화정책 경로를 가늠하고 있습니다. 
달러 인덱스(DXY)는 {dxy.get('price', 0):.2f}pt, WTI 원유는 배럴당 ${oil.get('price', 0):.2f}에 거래되며, 시장 공포지표인 VIX는 {vix.get('price', 0):.2f}pt를 기록해 시장 위험은 제한적인 범위에 머물렀습니다.

**[빅테크(M7) 및 주도 섹터 인사이트]**
{m7_summary if m7_summary else '엔비디아를 비롯한 반도체 및 AI 하드웨어 밸류체인과 소프트웨어 기업 간의 차별화'}가 이어졌습니다. 
투자자들은 단순한 테마성 기대감을 넘어 실질적인 어닝 서프라이즈와 잉여현금흐름을 창출하는 우량주 중심의 압축 포트폴리오 전략을 선호하고 있습니다.
""".strip()

    chk_title = "오후 장 및 마감 관전 포인트" if is_live else "다음 거래일 핵심 체크포인트"
    checkpoints = [
        f"미 연준 주요 인사들의 발언 및 다가오는 인플레이션/고용 지표 발표 영향 점검",
        f"10년물 국채 금리({tnx.get('price', 0):.2f}%)의 추가 하향 안정 여부와 성장주 밸류에이션 탄력성",
        f"필라델피아 반도체 지수({sox.get('price', 0):,.2f}pt) 및 엔비디아/애플 등 핵심 대형주 지지선 테스트"
    ]

    report_type_us = "실시간 장중 브리핑" if is_live else "마감 데일리 브리핑"
    full_report_text = f"""[미국 증시(US) {report_type_us}]
📅 기준: {time_str if time_str else us_data.get('date')}

■ 주요 지수 현황
- S&P 500: {sp500.get('price'):,.2f}pt ({sp_ratio:+.2f}%)
- 나스닥(Nasdaq): {nasdaq.get('price'):,.2f}pt ({nasdaq_ratio:+.2f}%)
- 필라델피아 반도체(SOX): {sox.get('price', 0):,.2f}pt ({sox_ratio:+.2f}%)
- 다우존스(Dow): {dow.get('price'):,.2f}pt ({dow.get('ratio', 0):+.2f}%)
- 러셀 2000: {rut.get('price'):,.2f}pt ({rut.get('ratio', 0):+.2f}%)


■ 주요 거시 매크로 지표
- 미 국채 10년물 금리: {tnx.get('price', 0):.2f}%
- VIX 변동성 지수: {vix.get('price', 0):.2f}pt
- WTI 원유 선물: ${oil.get('price', 0):.2f}
- 달러 인덱스(DXY): {dxy.get('price', 0):.2f}pt

■ 핵심 3줄 요약
1. {bullets[0].replace('**', '')}
2. {bullets[1].replace('**', '')}
3. {bullets[2].replace('**', '')}

■ 마켓 브리핑
{detailed_brief}

■ 주요 체크포인트
- {checkpoints[0]}
- {checkpoints[1]}
- {checkpoints[2]}
"""

    return {
        'bullets': bullets,
        'detailed_brief': detailed_brief,
        'checkpoints': checkpoints,
        'full_text': full_report_text,
        'chk_title': chk_title
    }
