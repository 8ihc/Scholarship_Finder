import json
import streamlit as st

def load_scholarships():
    """
    載入獎學金資料，使用 Streamlit cache。
    """
    @st.cache_data
    def _load():
        with open('data/merged/scholarships_merged_300.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return _load()
