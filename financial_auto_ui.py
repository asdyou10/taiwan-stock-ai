"""Read-only automatic financial data verification panel."""
import pandas as pd
import streamlit as st
from financial_auto import fetch_dataset, complete_annual_revenues, audit_income_statements, review_financial_periods, audit_eps_profit_consistency
from financial_evidence import validate_evidence, period_matches_income, KINDS
from financial_gate import audit_valuation_readiness
from financial_crosscheck import inspect_periods
from financial_official_source import check_official_url, source_precheck_table, OFFICIAL_PORTALS
from financial_twse_api_probe import ENDPOINTS, probe_twse_api
from financial_market_probe import inspect_market_sources
from financial_eps_period_probe import inspect_official_eps_period
from financial_history import build_quarterly_history, inspect_history_quality


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
    render_stage5_readiness_panel(stock)
    render_stage6_crosscheck_panel(stock)
    render_stage7_official_source_panel(stock)
    render_stage8_twse_probe_panel(stock)
    render_stage9_market_probe_panel(stock)
    render_stage10_eps_period_probe_panel(stock)
    render_stage11_history_panel(stock)

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


def render_stage5_readiness_panel(stock: str):
    """V4.2-04 readiness diagnostics; never unlocks automatic valuation."""
    with st.expander('🛡️ V4.2-04｜自動估值前置資格審查（第一版）', expanded=False):
        st.info('本階段自動彙整資料缺口，不會自行查證公告內容，也不會解鎖自動估值。原有 V4.2-02 手動情境試算維持獨立。')
        income_state = st.session_state.get(f'v4203_income_{stock}')
        periods_state = st.session_state.get(f'v4203_periods_{stock}')
        evidence = st.session_state.get(f'v4203_evidence_result_{stock}')
        income = income_state[0] if income_state else None
        periods = periods_state[0] if periods_state else None
        checks, reasons = audit_valuation_readiness(income, periods, evidence)
        st.dataframe(checks, use_container_width=True, hide_index=True)
        st.error('自動估值資格：禁止自動估值。尚未取得可獨立核實的官方公告時點、EPS 口徑及加權平均股數。')
        st.caption(f'尚待補齊／核實項目：{len(reasons)} 項；這是資料準備度診斷，不是財報真實性認證。')
        if income is None:
            st.warning('請先展開上方 V4.2-03，按「讀取並檢查財務資料」，再查看更新後的審查表。')


def render_stage6_crosscheck_panel(stock: str):
    """Diagnostic only: does not verify disclosures or enable valuation."""
    with st.expander('🔍 V4.2-04 第二版｜財報期間與 EPS 交叉核對（診斷版）', expanded=False):
        st.info('自動整理季度候選、EPS 與母公司淨利是否同時存在；目前尚未串接官方公告查證，因此不會判定 EPS 口徑、股數或解鎖估值。')
        state = st.session_state.get(f'v4203_income_{stock}')
        income = state[0] if state else None
        as_of = pd.Timestamp.now(tz='Asia/Taipei').date().isoformat()
        table, warnings = inspect_periods(income, as_of)
        if table.empty:
            st.warning('尚無可分析的損益表，請先在 V4.2-03 讀取財務資料。')
        else:
            st.dataframe(table.head(20), use_container_width=True, hide_index=True)
        for msg in warnings:
            st.warning(msg)
        st.error('自動估值資格：禁止自動估值；仍缺官方公告時間、EPS 口徑與正式加權平均股數的獨立驗證。')


def render_stage7_official_source_panel(stock: str):
    """Official-domain source precheck. Does not authenticate disclosures."""
    with st.expander('🏛️ V4.2-04 第三版｜官方公告來源預檢（第一階段）', expanded=False):
        st.info('本階段僅提供官方查詢入口、官方網域格式檢查及逐期缺口清單；**尚未自動取得或核實公告內容**，不會解鎖估值。')
        st.markdown('**官方資料查詢入口**')
        for name, url in OFFICIAL_PORTALS:
            st.markdown(f'- [{name}]({url})')
        st.caption('官方入口連結不代表特定股票、季度、公告日、EPS 或股數已核實。')
        periods_state = st.session_state.get(f'v4203_periods_{stock}')
        periods = periods_state[0] if periods_state else None
        table = source_precheck_table(periods)
        if table.empty:
            st.warning('請先在 V4.2-03 按「讀取並檢查財務資料」，建立財報期間清單。')
        else:
            st.markdown('**待逐期查證的財報清單**')
            st.dataframe(table, use_container_width=True, hide_index=True)
        with st.form(key=f'v4204_official_url_form_{stock}'):
            url = st.text_input('貼上要核對的官方財報公告網址（僅檢查網址，不會連線讀取）', key=f'v4204_official_url_{stock}', placeholder='https://mops.twse.com.tw/...')
            submitted = st.form_submit_button('檢查官方來源網域')
        if submitted:
            st.session_state[f'v4204_official_url_result_{stock}'] = check_official_url(url)
        result = st.session_state.get(f'v4204_official_url_result_{stock}')
        if result:
            status, explanation = result
            st.write(f'**網址預檢：{status}**')
            st.caption(explanation)
        st.warning('官方網域格式符合 ≠ 官方公告內容已核實。公告日期、EPS 口徑、加權平均股數仍需逐期核對。')
        st.error('自動估值資格：禁止自動估值（尚未建立官方公告資料自動比對）。')


def render_stage8_twse_probe_panel(stock: str):
    """User-triggered read-only official API diagnostics; no valuation unlock."""
    with st.expander('🏛️ V4.2-04 第三版第二階段｜證交所官方 API 實測（診斷版）', expanded=False):
        st.info('按下按鈕才會連線官方 API。只檢查可用性、欄位與股票代號候選紀錄；不會自動核實歷史公告或解鎖估值。')
        choice = st.selectbox('官方 API 資料集', list(ENDPOINTS), key=f'v4204_twse_api_select_{stock}')
        st.caption(f'固定官方來源：{ENDPOINTS[choice]}')
        if st.button('測試官方 API 連線與資料欄位', key=f'v4204_twse_api_run_{stock}'):
            with st.spinner('正在讀取官方 API（最多約 12 秒）...'):
                st.session_state[f'v4204_twse_api_result_{stock}'] = (choice, probe_twse_api(stock, choice))
        stored = st.session_state.get(f'v4204_twse_api_result_{stock}')
        if stored:
            queried_name, result = stored
            st.write('**已測試資料集：**', queried_name)
            st.write('**連線狀態：**', result['狀態'])
            st.caption(result['說明'])
            if result['狀態'] == '連線成功':
                st.write('**API 回傳紀錄數：**', result['總紀錄數'])
                st.write('**可見欄位名稱（最多 100 個）：**', '、'.join(result['欄位']) or '無')
                st.write('**股票代號欄位候選：**', '、'.join(result['代號欄位候選']) or '無法自動辨識')
                st.write('**符合代號的候選筆數：**', result['候選紀錄數'])
                if result['候選紀錄']:
                    st.json(result['候選紀錄'])
                else:
                    st.warning('未找到可辨識的股票代號候選資料；可能為欄位名稱不同、非一般業或資料期間不符。')
            else:
                st.warning('官方 API 連線或解析失敗；可稍後重試，不影響其他模組。')
            st.warning(result['限制'])
        st.error('自動估值資格：禁止自動估值。API 連線成功不等於公告日期、EPS 口徑及加權平均股數已核實。')


def render_stage9_market_probe_panel(stock: str):
    """Read-only official TWSE / OTC dataset comparison."""
    with st.expander('🏛️ V4.2-04 第三版第三階段｜上市／上櫃官方財報來源辨識（診斷版）', expanded=False):
        st.info('點擊後分別查詢上市及上櫃一般業官方損益表，依公司代號尋找候選紀錄。這不是正式市場別認證，也不會驗證歷史公告或解鎖估值。')
        if st.button('測試上市／上櫃官方財報來源', key=f'v4204_market_run_{stock}'):
            with st.spinner('正在查詢兩個官方資料集，請稍候...'):
                st.session_state[f'v4204_market_result_{stock}'] = inspect_market_sources(stock)
        result = st.session_state.get(f'v4204_market_result_{stock}')
        if result:
            st.write('**市場候選判定：**', result['市場判定'])
            st.caption(result['說明'])
            for item in result['結果']:
                st.markdown(f"**{item['資料集']}**")
                st.caption(f"來源：{item['來源']}")
                st.write(f"連線：{item['連線']}｜總筆數：{item['總筆數'] if item['總筆數'] is not None else '未知'}｜符合代號筆數：{item['符合筆數']}")
                if item['錯誤']:
                    st.warning('官方來源查詢失敗：' + item['錯誤'])
                if item['候選資料']:
                    st.json(item['候選資料'])
            if '無法判定' in result['市場判定'] or '衝突' in result['市場判定']:
                st.warning('目前資料不足以可靠辨識市場別；可能是連線、產業類別或資料集涵蓋範圍問題。')
        st.error('自動估值資格：禁止自動估值。仍需正式公告日期、EPS 口徑及加權平均股數的逐期核實。')


def render_stage10_eps_period_probe_panel(stock: str):
    """Official EPS raw-period inspection; explicitly not a period-conversion engine."""
    with st.expander('🔎 V4.2-04 第四階段｜官方 EPS 季度與口徑核對（診斷版）', expanded=False):
        st.info('按下按鈕查詢上市／上櫃官方一般業損益表的年度、季別及 EPS 原始值。若來源只提供最新季度，會標示歷史季度缺口；不會猜測單季 EPS。')
        if st.button('檢查官方 EPS 季度資料', key=f'v4204_eps_period_run_{stock}'):
            with st.spinner('正在查詢官方季度資料...'):
                st.session_state[f'v4204_eps_period_result_{stock}'] = inspect_official_eps_period(stock)
        result = st.session_state.get(f'v4204_eps_period_result_{stock}')
        if result:
            st.write('**查詢狀態：**', result['狀態'])
            if result['紀錄']:
                st.dataframe(pd.DataFrame(result['紀錄']), use_container_width=True, hide_index=True)
            for error in result.get('錯誤', []):
                st.warning('查詢失敗：' + error)
            for notice in result['警示']:
                st.warning(notice)
        st.error('自動估值資格：禁止自動估值。尚未核實官方公告日期、EPS 口徑及加權平均股數。')


def render_stage11_history_panel(stock: str):
    with st.expander('📚 V4.2-04 第四階段第二版｜歷史季度財報完整性檢查', expanded=False):
        st.caption('FinMind 歷史原始科目；不代表官方公告日期或 EPS 口徑已核實。')
        if st.button('讀取近五年季度財報', key=f'v4204_history_{stock}'):
            token = ''
            try:
                token = st.secrets.get('FINMIND_TOKEN', '')
            except Exception:
                pass
            now = pd.Timestamp.now(tz='Asia/Taipei')
            start = f'{now.year - 4}-01-01'
            try:
                with st.spinner('正在讀取 FinMind 歷史財報...'):
                    records = fetch_dataset(stock, 'TaiwanStockFinancialStatements', start, token)
                    table, issues = build_quarterly_history(records, years=5, as_of=now.date().isoformat())
                    st.session_state[f'v4204_history_result_{stock}'] = (table, issues)
            except Exception as exc:
                st.session_state[f'v4204_history_result_{stock}'] = (pd.DataFrame(), [f'查詢失敗：{exc}'])
        result = st.session_state.get(f'v4204_history_result_{stock}')
        if result is None:
            st.info('按下按鈕後才會查詢；不影響其他財報模組。')
            return
        table, issues = result
        if not table.empty:
            st.metric('取得季度紀錄', len(table))
            st.dataframe(table, use_container_width=True, hide_index=True)
        # Diagnostic completeness is distinct from disclosure verification.
        summary, gaps = inspect_history_quality(table, years=5, as_of=pd.Timestamp.now(tz='Asia/Taipei').date().isoformat())
        st.markdown('**歷史資料品質摘要（僅來源完整性，不代表官方查證）**')
        st.dataframe(pd.DataFrame([summary]), use_container_width=True, hide_index=True)
        st.markdown('**未取得季度與申報期限參考分類**')
        if not gaps.empty:
            st.dataframe(gaps, use_container_width=True, hide_index=True)
        else:
            st.success('分析期間內沒有未取得的已結束季度；不代表公告日期或 EPS 口徑已核實。')
        st.caption('一般申報期限為非金融業曆年制公司的概略參考，並非實際公告日；提前公告、延期、例外與公司適用規定均須另查。')
        for issue in issues:
            st.warning(issue)
        st.error('尚未驗證正式公告日期、EPS 口徑及加權平均股數：禁止自動估值。')
