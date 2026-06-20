import streamlit as st

PRIMARY = "#4f46e5"
TEAL    = "#0d9488"
ORANGE  = "#d97706"
RED     = "#dc2626"
MUTED   = "#64748b"

_CSS = """
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"]  { display: none !important; }
footer                    { display: none !important; }
#MainMenu                 { display: none !important; }

.block-container {
    max-width: 820px !important;
    padding: 2.5rem 2rem 4rem !important;
    margin: 0 auto !important;
}

/* ── Page header ── */
.page-header {
    padding: 0 0 20px;
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 28px;
}
.ph-title { font-size: 1.35rem; font-weight: 700; color: #1e1e2e; }
.ph-sub   { font-size: 0.8rem; color: #64748b; margin-top: 3px; }

/* ── Section label ── */
.section-label {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
}

/* ── Suggestion buttons ── */
div[data-testid="stButton"] button[kind="secondary"].suggestion-btn {
    text-align: left !important;
}

/* ── Confirmed address ── */
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

/* ── Road closure banner ── */
.road-closure-banner {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 11px 16px;
    margin-top: 10px;
}
.rcb-title { font-size: 0.85rem; font-weight: 700; color: #92400e; }
.rcb-sub   { font-size: 0.72rem; color: #a16207; margin-top: 1px; }
.rcb-badge {
    margin-left: auto;
    font-size: 0.64rem;
    font-weight: 800;
    letter-spacing: 0.7px;
    color: #92400e;
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-radius: 6px;
    padding: 3px 8px;
    white-space: nowrap;
}

/* ── Result card ── */
.result-card {
    border: 1.5px solid;
    border-radius: 14px;
    padding: 28px 24px 22px;
    margin-top: 20px;
    text-align: center;
    animation: fadeIn 0.3s ease;
}
.rc-header { font-size: 0.67rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #94a3b8; margin-bottom: 14px; }
.rc-score  { font-size: 4rem; font-weight: 900; line-height: 1; letter-spacing: -2px; }
.rc-max    { font-size: 0.9rem; color: #94a3b8; margin-top: 2px; margin-bottom: 14px; }
.rc-bar-bg { height: 7px; background: #e2e8f0; border-radius: 99px; overflow: hidden; margin: 0 auto 14px; max-width: 260px; }
.rc-bar    { height: 100%; border-radius: 99px; animation: barGrow 0.6s cubic-bezier(.4,0,.2,1) both; }
.rc-badge  { display: inline-block; font-size: 0.73rem; font-weight: 700; letter-spacing: 0.5px; border: 1.5px solid; border-radius: 99px; padding: 4px 16px; margin-bottom: 18px; }
.rc-details { border-top: 1px solid #e2e8f0; padding-top: 12px; text-align: left; display: flex; flex-direction: column; gap: 4px; }
.rc-detail  { font-size: 0.8rem; color: #64748b; }

/* ── Widget labels ── */
label[data-testid="stWidgetLabel"] > div > p {
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
}

/* ── Primary button ── */
div[data-testid="stButton"] button[kind="primary"] {
    background: #4f46e5 !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    color: #ffffff !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover { opacity: 0.88 !important; }

/* ── Secondary button ── */
div[data-testid="stButton"] button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #374151 !important;
    font-size: 0.82rem !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
}

@keyframes fadeIn  { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes barGrow { from { width: 0 !important; } }
"""


def inject_css():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
