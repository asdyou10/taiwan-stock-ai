"""Read-only automatic financial data verification panel."""
import pandas as pd
import streamlit as st
from financial_auto import fetch_dataset, complete_annual_revenues, audit_income_statements


def render_auto_financial_panel(stock: str):
    with st.expander('🔎 V4.2-03 真實財務資料自動讀取與驗證（測試版）', expanded=False):
        st.info('本功能讀取真實資料，但尚未完成公告時間、EPS、股數及估值模型驗證。**目前不產生自動合理價或買進訊號。**')
        token = ''
        try:
            token = st.secrets.get('FINMIND_TOKEN', '')
        except Exception:
            pass
        if st.button('讀取並檢查財務資料', key=f'v4203_load_{stock}'):
            with st.spinner('正在查詢 FinMind 財務資料...'):
                try:
                    monthly = fetch_dataset(stock, 'TaiwanStockMonthRevenue', '2020-01-01', token)
                    annual, warnings = complete_annual_revenues(monthly, as_of=pd.Timestamp.now(tz='Asia/Taipei').date().isoformat())
                    st.session_state[f'v4203_revenue_{stock}'] = (annual, warnings)
                except Exception as exc:
                    st.session_state[f'v4203_revenue_{stock}'] = (pd.DataFrame(), [f'月營收查詢失敗：{exc}'])
                try:
                    income = fetch_dataset(stock, 'TaiwanStockFinancialStatements', '2023-01-01', token)
                    audited, warnings = audit_income_statements(income)
                    st.session_state[f'v4203_income_{stock}'] = (audited, warnings)
                except Exception as exc:
                    st.session_state[f'v4203_income_{stock}'] = (pd.DataFrame(), [f'損益表查詢失敗：{exc}'])
        revenue = st.session_state.get(f'v4203_revenue_{stock}')
        income = st.session_state.get(f'v4203_income_{stock}')
        if revenue is not None:
            annual, warnings = revenue
            st.markdown('**完整年度營收（FinMind，百萬元）**')
            if not annual.empty:
                st.dataframe(annual, use_container_width=True)
                st.caption(f"最新完整年度：{int(annual.iloc[-1]['年度'])}；年度營收：{annual.iloc[-1]['年度營收（百萬元）']:,.2f} 百萬元")
            for warning in warnings:
                st.warning(warning)
        if income is not None:
            audited, warnings = income
            st.markdown('**損益表原始科目查核（僅供核對，不自動推估 EPS）**')
            if not audited.empty:
                available = [c for c in ('date', 'type', 'value', 'origin_name') if c in audited.columns]
                st.dataframe(audited[available].head(80), use_container_width=True)
            for warning in warnings:
                st.warning(warning)
        if revenue is not None or income is not None:
            st.error('資料可信度：尚未達自動估值門檻。缺少已核實公告日期、獲利口徑與適用股數；暫不判定買進。')
