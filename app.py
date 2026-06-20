import streamlit as st

st.set_page_config(
    page_title="Event Traffic Severity Predictor",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from utils.styles import inject_css
from pages_src.home import render

inject_css()
render()
