"""Optional V4.2-02 valuation panel; does not change existing trade signals."""
import pandas as pd
import streamlit as st
from valuation import ValuationInput, evaluate_scenario, safety_margin, validate_scenarios


def render_valuation_panel(stock: str, latest_price: float):
    with st.expander('🧮 V4.2-02 三情境 EPS 與合理估值（研究試算）', expanded=False):
        st.warning('此模組是使用者輸入假設的情境試算，**不是已驗證的 EPS 預測或買進訊號**。目前尚未自動串接可信的完整財報、公告時間與流通股數。')
        st.caption('金額單位：年度營收「百萬元」、股數「百萬股」、EPS／合理價值「元／股」。預測期：下一個完整年度（假設）。')
        source = st.text_input('財務數據來源／報告名稱（必填）', key='v4202_source', placeholder='例：公司公告 2025 年度合併財報')
        source_date = st.date_input('來源公開日期', key='v4202_source_date')
        annual_revenue = st.number_input('基準年度營收（百萬元）', min_value=0.0, value=0.0, step=100.0, key='v4202_revenue')
        shares = st.number_input('估值使用流通股數（百萬股）', min_value=0.0, value=0.0, step=1.0, key='v4202_shares')
        price = st.number_input('比較股價（元／股）', min_value=0.01, value=max(0.01, float(latest_price)), step=1.0, key=f'v4202_price_{stock}')
        st.caption('請自行核對營收期間、合併／個體口徑、股本變動與來源日期；不允許以股價資料推算股數。')
        st.write('**各情境假設（預設值僅為教學示例，不代表該股票）**')
        specs = {
            '保守': (-10.0, 5.0, 65.0, 15.0),
            '基準': (10.0, 12.0, 75.0, 25.0),
            '樂觀': (30.0, 18.0, 80.0, 35.0),
        }
        scenarios = {}
        for name, defaults in specs.items():
            with st.container():
                st.markdown(f'**{name}情境**')
                a,b,c,d = st.columns(4)
                with a:
                    growth = st.number_input('營收成長 %', min_value=-100.0, max_value=500.0, value=defaults[0], step=5.0, key=f'v4202_g_{name}')
                with b:
                    margin = st.number_input('營業利益率 %', min_value=-100.0, max_value=100.0, value=defaults[1], step=1.0, key=f'v4202_m_{name}')
                with c:
                    conversion = st.number_input('淨利／營業利益 %', min_value=0.0, max_value=200.0, value=defaults[2], step=5.0, key=f'v4202_n_{name}')
                with d:
                    pe = st.number_input('假設 P/E 倍數', min_value=0.1, max_value=100.0, value=defaults[3], step=1.0, key=f'v4202_pe_{name}')
                scenarios[name] = ValuationInput(annual_revenue, growth, margin, conversion, shares, pe)
        st.caption('P/E 僅為輸入假設；尚未建立產業估值上限引擎。對虧損、景氣循環或 P/E 不適用公司，不應使用本模型作買賣判斷。')
        if st.button('計算三情境估值', key='v4202_calculate'):
            if not source.strip() or annual_revenue <= 0 or shares <= 0:
                st.error('請先填寫真實資料來源、正數年度營收及正數流通股數。')
                return
            if source_date > pd.Timestamp.now(tz='Asia/Taipei').date():
                st.error('來源公開日期不可晚於今天。')
                return
            for warning in validate_scenarios(scenarios):
                st.warning(warning)
            rows = []
            for name, params in scenarios.items():
                try:
                    result = evaluate_scenario(params)
                    rows.append({'情境': name, '預估年度營收（百萬元）': round(result['revenue_millions'],2),
                                 '假設 EPS（元）': round(result['eps'],2), '假設 P/E': params.pe,
                                 '情境合理價（元）': round(result['fair_value'],2) if result['fair_value'] is not None else '不適用',
                                 '基於情境價的安全邊際 %': round(safety_margin(price, result['fair_value']),2) if result['fair_value'] is not None else '不適用'})
                except ValueError as exc:
                    st.error(f'{name}情境輸入錯誤：{exc}')
                    return
            st.dataframe(pd.DataFrame(rows).set_index('情境'), use_container_width=True)
            st.info(f'股票 {stock}｜資料來源：{source}｜公開日期：{source_date}｜比較股價：{price:.2f} 元。此結果只反映假設，尚未經資料可信度分級與估值陷阱審核，因此**不產生買進／賣出訊號**。')
