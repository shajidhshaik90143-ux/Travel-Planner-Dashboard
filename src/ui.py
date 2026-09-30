import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; max-width: 1450px;}
    .hero {
        padding: 1.3rem 1.5rem; border-radius: 18px; margin-bottom: 1rem;
        background: linear-gradient(135deg,#172033,#273b66);
        color: white; box-shadow: 0 10px 30px rgba(0,0,0,.14);
    }
    .hero h1 {margin:0; font-size:2rem;}
    .hero p {margin:.35rem 0 0; opacity:.82;}
    .metric-card {
        border: 1px solid rgba(128,128,128,.22); border-radius: 15px;
        padding: 1rem; min-height: 110px; background: rgba(128,128,128,.05);
    }
    .metric-label {font-size:.82rem; opacity:.7;}
    .metric-value {font-size:1.65rem; font-weight:700; margin-top:.25rem;}
    .small-muted {font-size:.8rem; opacity:.65;}
    .section-title {font-size:1.25rem; font-weight:700; margin:1rem 0 .5rem;}
    div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.18); padding:.7rem; border-radius:12px;}
    </style>
    """, unsafe_allow_html=True)

def metric_cards(items):
    cols = st.columns(len(items))
    for col, (label, value, note) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
              <div class="small-muted">{note}</div>
            </div>""", unsafe_allow_html=True)
