import streamlit as st

st.title("台股AI趨勢研究室")
st.write("我的第一個台股分析APP！")

stock = st.text_input("請輸入股票代號", "3491")

st.write("目前查詢的股票：", stock)
