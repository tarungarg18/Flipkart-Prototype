import streamlit as st

_CSS = """
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"]  { display: none !important; }
footer                    { display: none !important; }
#MainMenu                 { display: none !important; }

/* Prevent the "fading" overlay during reruns — only show it on explicit spinner */
[data-stale="true"] { opacity: 1 !important; transition: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

[data-testid="stAppViewContainer"] { background: #f0f4f8 !important; }

.block-container {
    max-width: 900px !important;
    padding: 106px 2rem 4rem !important;
    margin: 0 auto !important;
    background: transparent !important;
}

.app-header {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    width: min(900px, 95vw);
    z-index: 1000;
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 16px;
    box-shadow: 0 2px 20px rgba(0,0,0,0.08);
    height: 72px;
}
.app-header-inner {
    height: 100%;
    padding: 0 20px 0 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
}
.header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
}
.header-title {
    color: #0f172a;
    font-size: 1rem;
    font-weight: 800;
    letter-spacing: -0.3px;
    line-height: 1.2;
    white-space: nowrap;
}
.header-sub {
    color: #94a3b8;
    font-size: 0.68rem;
    margin-top: 3px;
    white-space: nowrap;
}
.header-nav {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
}
.nav-link {
    display: flex;
    align-items: center;
    text-decoration: none !important;
    padding: 7px 16px;
    border-radius: 8px;
    color: #4f46e5;
    font-size: 0.84rem;
    font-weight: 500;
    white-space: nowrap;
    transition: background 0.13s;
    line-height: 1;
}
.nav-link:hover {
    background: #eef2ff !important;
    color: #4f46e5 !important;
    text-decoration: none !important;
}
.nav-active {
    background: #4f46e5 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}
.nav-active:hover {
    background: #4338ca !important;
    color: #ffffff !important;
}

/* Content area sits on white to contrast the gray page background */
[data-testid="stMain"] .block-container {
    background: #ffffff !important;
    border-radius: 16px !important;
    padding-bottom: 4rem !important;
}

.section-label {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
}
.section-label-hint {
    font-size: 0.68rem !important;
    font-weight: 400 !important;
    color: #cbd5e1 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}

iframe {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
}

div[data-testid="stButton"] button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #374151 !important;
    font-size: 0.82rem !important;
    cursor: pointer !important;
    text-align: center !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
    background: #f5f3ff !important;
}

.confirmed-addr {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    padding: 9px 14px;
    margin: 6px 0 10px;
    font-size: 0.83rem;
    color: #166534;
    font-weight: 600;
}

.result-card {
    border: 1.5px solid;
    border-radius: 14px;
    padding: 28px 24px 22px;
    margin-top: 20px;
    text-align: center;
    animation: fadeIn 0.3s ease;
}
.rc-header  { font-size: 0.67rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; margin-bottom: 14px; }
.rc-score   { font-size: 4rem; font-weight: 900; line-height: 1; letter-spacing: -2px; }
.rc-max     { font-size: 0.9rem; color: #94a3b8; margin-top: 2px; margin-bottom: 14px; }
.rc-bar-bg  { height: 7px; background: #e2e8f0; border-radius: 99px; overflow: hidden; margin: 0 auto 16px; max-width: 260px; }
.rc-bar     { height: 100%; border-radius: 99px; animation: barGrow 0.6s cubic-bezier(.4,0,.2,1) both; }
.rc-badges  { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 18px; }
.rc-badge   { display: inline-block; font-size: 0.73rem; font-weight: 700; letter-spacing: 0.5px; border: 1.5px solid; border-radius: 99px; padding: 4px 16px; }
.rc-closure-badge {
    display: inline-block;
    font-size: 0.73rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: 1.5px solid;
    border-radius: 99px;
    padding: 4px 16px;
}
.rc-details { border-top: 1px solid #e2e8f0; padding-top: 16px; margin-top: 4px; text-align: left; display: flex; flex-direction: column; gap: 11px; }
.rc-detail  { display: flex; justify-content: space-between; gap: 18px; font-size: 1rem; align-items: baseline; }
.rc-detail span { color: #94a3b8; font-weight: 600; white-space: nowrap; }
.rc-detail b { color: #1e293b; font-weight: 700; text-align: right; }

.skeleton {
    border-radius: 10px;
    background: linear-gradient(90deg, #eef2f7 25%, #e2e8f0 37%, #eef2f7 63%);
    background-size: 400% 100%;
    animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }

.assume-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; }
.assume-title { font-size: 1.08rem; font-weight: 700; color: #1e293b; margin-bottom: 8px; }
.assume-body { font-size: 0.97rem; color: #475569; line-height: 1.65; }
.assume-list { display: flex; flex-direction: column; gap: 7px; margin-top: 12px; }
.assume-row { display: flex; align-items: center; gap: 10px; font-size: 0.97rem; color: #334155; }
.assume-row b { font-weight: 600; }
.assume-row .rng { margin-left: auto; color: #64748b; font-variant-numeric: tabular-nums; }
.assume-row .dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }

label[data-testid="stWidgetLabel"] > div > p {
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
}

div[data-testid="stSelectbox"] [data-baseweb="select"],
div[data-testid="stSelectbox"] [data-baseweb="select"] * {
    cursor: pointer !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {
    border-color: #4f46e5 !important;
    background: #f5f3ff !important;
    box-shadow: 0 1px 4px rgba(79,70,229,0.10) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] > div[aria-expanded="true"],
div[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 2px rgba(79,70,229,0.12) !important;
}

div[data-baseweb="popover"] ul[role="listbox"] {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.12) !important;
    padding: 4px !important;
    background: #ffffff !important;
}
div[data-baseweb="popover"] li[role="option"] {
    cursor: pointer !important;
    border-radius: 6px !important;
    font-size: 0.86rem !important;
    color: #374151 !important;
    margin: 1px 0 !important;
    transition: background 0.12s ease, color 0.12s ease, padding-left 0.12s ease !important;
}
div[data-baseweb="popover"] li[role="option"]:hover {
    background: #f5f3ff !important;
    color: #4f46e5 !important;
    padding-left: 16px !important;
}
div[data-baseweb="popover"] li[role="option"][aria-selected="true"] {
    background: #eef2ff !important;
    color: #4f46e5 !important;
    font-weight: 600 !important;
}

div[data-testid="stNumberInput"] input {
    border-color: #e2e8f0 !important;
    border-radius: 8px !important;
}
div[data-testid="stNumberInput"] input:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 2px rgba(79,70,229,0.12) !important;
}

div[data-testid="stTextInput"] input {
    border-color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 2px rgba(79,70,229,0.12) !important;
}

div[data-testid="stDateInput"] input {
    border-color: #e2e8f0 !important;
    border-radius: 8px !important;
    cursor: pointer !important;
}
div[data-testid="stDateInput"] input:hover {
    border-color: #4f46e5 !important;
}

div[data-testid="stButton"] button[kind="primary"] {
    background: #4f46e5 !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    color: #ffffff !important;
    cursor: pointer !important;
    transition: opacity 0.15s ease !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover { opacity: 0.88 !important; }

@keyframes fadeIn  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes barGrow { from { width: 0 !important; } }
"""


def inject_css():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
