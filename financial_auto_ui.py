"""Read-only automatic financial data verification panel."""
import pandas as pd
import streamlit as st
from financial_auto import fetch_dataset, complete_annual_revenues, audit_income_statements, review_financial_periods, audit_eps_profit_consistency
from financial_evidence import validate_evidence, period_matches_income, KINDS


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
                    st.session_state[f'v4203_periods_{stock}'] = review_financial_periods(income)
                    st.session_state[f'v4203_stage3_{stock}'] = audit_eps_profit_consistency(income)
                except Exception as exc:
                    st.session_state[f'v4203_income_{stock}'] = (pd.DataFrame(), [f'損益表查詢失敗：{exc}'])
                    st.session_state.pop(f'v4203_periods_{stock}', None)
                    st.session_state.pop(f'v4203_stage3_{stock}', None)
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
        periods = st.session_state.get(f'v4203_periods_{stock}')
        if periods is not None:
            period_table, period_issues = periods
            st.markdown('**V4.2-03 第二階段｜財報期間與 EPS 口徑稽核**')
            st.caption('EPS 與淨利為 FinMind 原始科目；目前不判定其為單季、累計或全年，也不推算股數。')
            if not period_table.empty:
                st.dataframe(period_table.head(16), use_container_width=True)
            for issue in period_issues:
                st.warning(issue)
        stage3 = st.session_state.get(f'v4203_stage3_{stock}')
        if stage3 is not None:
            checks, notices = stage3
            st.markdown('**V4.2-03 第三階段｜EPS 與母公司淨利一致性檢查（僅供診斷）**')
            st.caption('隱含股數 ≠ 官方加權平均股數；未核實公告日與 EPS 口徑前，仍禁止自動估值。')
            if not checks.empty:
                st.dataframe(checks.head(16), use_container_width=True)
            for notice in notices:
                st.warning(notice)
        if revenue is not None or income is not None:
            st.error('資料可信度：尚未達自動估值門檻。缺少已核實公告日期、獲利口徑與適用股數；暫不判定買進。')

    render_stage4_evidence_panel(stock)

def render_stage4_evidence_panel(stock: str):
    """Manual source-evidence intake, strictly separated from automated validation."""
    with st.expander('📑 V4.2-03 第四階段｜財報公告佐證與時點檢查', expanded=False):
        st.info('這裡是人工提供的公告佐證紀錄，不會自行驗證連結內容或認定官方股數。即使檢查通過，也不會解鎖自動估值。')
        income_state = st.session_state.get(f'v4203_income_{stock}')
        income = income_state[0] if income_state else pd.DataFrame()
        periods = st.session_state.get(f'v4203_periods_{stock}')
        available = periods[0]['財報截止日'].tolist() if periods is not None and not periods[0].empty else []
        if not available:
            st.warning('請先在上方按「讀取並檢查財務資料」，取得財報期間後再輸入佐證。')
            return
        with st.form(key=f'v4203_evidence_form_{stock}'):
            period_end = st.selectbox('選擇財報截止日', available, key=f'v4203_evidence_period_{stock}')
            release_date = st.date_input('正式公告日期（需依公告查證）', value=pd.Timestamp.now(tz='Asia/Taipei').date(), key=f'v4203_evidence_release_{stock}')
            eps_kind = st.selectbox('EPS 口徑（依公告填寫）', KINDS, key=f'v4203_evidence_kind_{stock}')
            shares = st.number_input('公告加權平均股數（百萬股）', min_value=0.0, value=0.0, step=1.0, key=f'v4203_evidence_shares_{stock}')
            source_url = st.text_input('官方公告 HTTPS 連結', placeholder='https://...', key=f'v4203_evidence_url_{stock}')
            as_of = st.date_input('分析日期（歷史時點檢查）', value=pd.Timestamp.now(tz='Asia/Taipei').date(), key=f'v4203_evidence_asof_{stock}')
            submitted = st.form_submit_button('檢查佐證資料（不解鎖估值）')
        if submitted:
            result = validate_evidence(period_end, release_date.isoformat(), eps_kind, shares, source_url, as_of.isoformat())
            if not period_matches_income(income, period_end):
                result['問題'].append('所選財報期間與已讀取損益表不符')
                result['格式與時點檢查'] = '未通過'
            st.session_state[f'v4203_evidence_result_{stock}'] = result
        result = st.session_state.get(f'v4203_evidence_result_{stock}')
        if result:
            st.write('**格式與時點檢查：**', result['格式與時點檢查'])
            for problem in result['問題']:
                st.warning(problem)
            st.warning('來源真偽：尚未獨立核實。不得將手動輸入視為已驗證官方資料。')
            st.error('自動估值資格：禁止自動估值（尚未完成官方來源查證及 EPS／股數口徑交叉核對）。')
