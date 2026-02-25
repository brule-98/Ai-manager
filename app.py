"""
app.py — AI-Manager: Piattaforma Controllo di Gestione.
Design system: Tailwind-style utility CSS, dark theme, DM Sans.
"""
import streamlit as st

st.set_page_config(
    page_title="AI-Manager | CFO Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ── TAILWIND-STYLE DESIGN SYSTEM ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── 1. FONTS ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

/* ── 2. CSS VARIABLES ── */
:root {
  --bg-base:      #060D1A;
  --bg-surface:   #0D1625;
  --bg-surface2:  #121E30;
  --bg-elevated:  #162540;
  --gold:         #C9A84C;
  --gold-light:   #E8C96A;
  --blue:         #1E3A6E;
  --blue-bright:  #2563EB;
  --green:        #10B981;
  --red:          #EF4444;
  --amber:        #F59E0B;
  --text-primary: #F1F5F9;
  --text-second:  #94A3B8;
  --text-muted:   #475569;
  --text-faint:   #334155;
  --border:       rgba(255,255,255,0.07);
  --border-gold:  rgba(201,168,76,0.25);
}

/* ── 3. BASE RESET ── */
html, body, [class*="css"], .main, [data-testid="stAppViewContainer"] {
  font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
}
.main .block-container {
  background: var(--bg-base) !important;
  padding: 0 2rem 3rem !important;
  max-width: 1440px;
}

/* ── 4. SIDEBAR ── */
[data-testid="stSidebar"] {
  background: var(--bg-surface) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-second) !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] b { color: var(--text-primary) !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 8px !important;
}

/* ── 5. SIDEBAR NAV BUTTONS ── */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: 1px solid transparent !important;
  border-radius: 8px !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  text-align: left !important;
  padding: 9px 14px !important;
  width: 100% !important;
  margin-bottom: 2px !important;
  transition: all 0.15s !important;
  justify-content: flex-start !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,0.05) !important;
  color: var(--text-primary) !important;
  border-color: var(--border) !important;
}
[data-testid="stSidebar"] .stButton > button p {
  text-align: left !important;
  font-size: 0.83rem !important;
  color: inherit !important;
}

/* ── 6. MAIN BUTTONS ── */
.stButton > button {
  background: linear-gradient(135deg, #1A3A7A, #0F2044) !important;
  color: var(--text-primary) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  font-family: 'DM Sans', sans-serif !important;
  transition: all 0.18s !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, #1E4A9A, #132855) !important;
  border-color: rgba(255,255,255,0.15) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 16px rgba(26,58,122,0.4) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #C9A84C, #A8833A) !important;
  color: #060D1A !important;
  font-weight: 800 !important;
  border: none !important;
  box-shadow: 0 2px 12px rgba(201,168,76,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
  opacity: 0.88 !important;
  transform: translateY(-1px) !important;
}

/* ── 7. TABS ── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,0.02) !important;
  border-radius: 10px 10px 0 0;
  gap: 2px;
  padding: 4px 4px 0;
  border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-muted) !important;
  border-radius: 8px 8px 0 0 !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  padding: 8px 18px !important;
  border: none !important;
  transition: color 0.15s !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(255,255,255,0.05) !important;
  color: var(--text-primary) !important;
  border-bottom: 2px solid var(--gold) !important;
  font-weight: 700 !important;
}

/* ── 8. EXPANDERS ── */
div[data-testid="stExpander"] {
  background: rgba(255,255,255,0.02) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  margin-bottom: 8px !important;
}
div[data-testid="stExpander"] summary {
  color: var(--text-second) !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
}
div[data-testid="stExpander"] p { color: var(--text-second) !important; }

/* ── 9. INPUTS — target baseweb WRAPPER (dove Streamlit mette sfondo bianco) ── */
/* Il problema è div[data-baseweb="base-input"] che ha bg bianco di default */
div[data-baseweb="base-input"],
div[data-baseweb="textarea"] {
  background: #0B1422 !important;
  background-color: #0B1422 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 8px !important;
}
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
  background: #0B1422 !important;
  border-color: #C9A84C !important;
  box-shadow: 0 0 0 3px rgba(201,168,76,0.14) !important;
}
/* Input DENTRO il wrapper: background transparent così eredita il dark del wrapper */
div[data-baseweb="base-input"] input,
div[data-baseweb="textarea"] textarea {
  background: transparent !important;
  background-color: transparent !important;
  color: #F1F5F9 !important;
  -webkit-text-fill-color: #F1F5F9 !important;
  caret-color: #C9A84C !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.87rem !important;
}
div[data-baseweb="base-input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
  color: #3D5068 !important;
  -webkit-text-fill-color: #3D5068 !important;
}
/* Autofill browser override */
div[data-baseweb="base-input"] input:-webkit-autofill,
div[data-baseweb="base-input"] input:-webkit-autofill:focus {
  -webkit-box-shadow: 0 0 0 60px #0B1422 inset !important;
  -webkit-text-fill-color: #F1F5F9 !important;
}
/* Label */
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stMultiSelect label, .stSlider label,
.stRadio label, .stCheckbox label, .stFileUploader label {
  color: var(--text-muted) !important;
  font-size: 0.74rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.6px !important;
  text-transform: uppercase !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stRadio label, .stCheckbox label,
.stFileUploader label, .stSlider label, .stMultiSelect label {
  color: var(--text-muted) !important;
  font-size: 0.76rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.5px !important;
  text-transform: uppercase !important;
}

/* ── 10. SELECTBOX ── */
.stSelectbox > div > div {
  background: rgba(255,255,255,0.04) !important;
  color: var(--text-primary) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
}
/* dropdown option text */
[data-baseweb="select"] [data-testid="stMarkdown"] p { color: var(--text-primary) !important; }
li[role="option"] { background: var(--bg-surface) !important; color: var(--text-primary) !important; }
li[role="option"]:hover { background: var(--bg-elevated) !important; }

/* ── 11. MULTISELECT ── */
.stMultiSelect > div > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
}
.stMultiSelect span[data-baseweb="tag"] {
  background: rgba(201,168,76,0.15) !important;
  color: var(--gold) !important;
  border: 1px solid var(--border-gold) !important;
}

/* ── 12. RADIO / CHECKBOX ── */
.stRadio > div { color: var(--text-second) !important; }
.stCheckbox > label > div { color: var(--text-second) !important; }
.stRadio [data-testid="stMarkdown"] p { color: var(--text-second) !important; }

/* ── 13. SLIDER ── */
.stSlider .rc-slider-track { background: var(--gold) !important; }
.stSlider .rc-slider-handle { border-color: var(--gold) !important; background: var(--gold) !important; }
[data-testid="stSlider"] p { color: var(--text-second) !important; }
[data-testid="stSliderThumb"] { color: var(--text-primary) !important; }

/* ── 14. ALERTS ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
[data-testid="stAlert"] p { color: var(--text-primary) !important; }
.stSuccess { background: rgba(16,185,129,0.08) !important; border-left: 3px solid var(--green) !important; }
.stWarning { background: rgba(245,158,11,0.08) !important; border-left: 3px solid var(--amber) !important; }
.stError   { background: rgba(239,68,68,0.08)  !important; border-left: 3px solid var(--red)   !important; }
.stInfo    { background: rgba(37,99,235,0.08)   !important; border-left: 3px solid var(--blue-bright) !important; }

/* ── 15. DATAFRAME ── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
[data-testid="stDataFrame"] th {
  background: var(--bg-surface2) !important;
  color: var(--text-muted) !important;
  font-size: 0.72rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.8px !important;
}
[data-testid="stDataFrame"] td { color: var(--text-second) !important; }

/* ── 16. METRICS ── */
[data-testid="stMetric"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 16px 20px !important;
}
[data-testid="stMetric"] label { color: var(--text-muted) !important; font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { color: var(--text-primary) !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── 17. FILE UPLOADER ── */
[data-testid="stFileUploader"] {
  background: rgba(255,255,255,0.02) !important;
  border: 1px dashed rgba(255,255,255,0.12) !important;
  border-radius: 10px !important;
}
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p { color: var(--text-muted) !important; }

/* ── 18. PROGRESS ── */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--blue), var(--gold)) !important;
}

/* ── 19. CODE / CAPTION ── */
code { background: rgba(255,255,255,0.06) !important; color: var(--gold) !important; border-radius: 4px !important; }
.stCaption { color: var(--text-faint) !important; }

/* ── 20. DETAILS / SUMMARY (CE Matrix expandable rows) ── */
details { border: none !important; background: transparent !important; }
details > summary {
  cursor: pointer;
  list-style: none;
  outline: none;
}
details > summary::-webkit-details-marker { display: none; }

/* ── 21. SCROLLBARS ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.16); }

/* ── 22. HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; }

/* ── 23. MARKDOWN HEADINGS ── */
h1, h2, h3, h4, h5 { color: var(--text-primary) !important; }
p { color: var(--text-second) !important; }

/* ── 24. SPINNER ── */
[data-testid="stSpinner"] p { color: var(--text-muted) !important; }
</style>
""", unsafe_allow_html=True)


# ── IMPORTS E ROUTING ─────────────────────────────────────────────────────────
from auth.login import render_login

if not st.session_state.get('authenticated'):
    render_login()
    st.stop()

from modules.clienti      import render_clienti
from modules.workspace    import render_workspace
from modules.dashboard    import render_dashboard
from modules.configurazione import render_configurazione
from modules.cfo_agent    import render_cfo_agent
from modules.budget       import render_budget
from modules.rettifiche   import render_rettifiche


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown("""
<div style="padding:20px 12px 16px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:34px;height:34px;background:linear-gradient(135deg,#C9A84C,#8B6914);
                border-radius:9px;display:flex;align-items:center;justify-content:center;
                font-size:1rem;flex-shrink:0">📊</div>
    <div>
      <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;color:#C9A84C;font-weight:700">AI-Manager</div>
      <div style="font-size:0.82rem;font-weight:700;color:#F1F5F9;margin-top:1px">CFO Dashboard</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Cliente attivo
    clienti_dict = st.session_state.get('clienti', {})
    nomi_clienti = list(clienti_dict.keys())
    if nomi_clienti:
        ca_idx = 0
        ca_cur = st.session_state.get('cliente_attivo')
        if ca_cur in nomi_clienti:
            ca_idx = nomi_clienti.index(ca_cur)
        sel = st.selectbox("Cliente attivo", nomi_clienti, index=ca_idx, label_visibility="collapsed")
        if sel != ca_cur:
            st.session_state['cliente_attivo'] = sel
            st.rerun()
    else:
        st.markdown("<div style='padding:8px 12px;font-size:0.78rem;color:#334155'>Nessun cliente — aggiungi in Clienti</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Navigazione
    NAV = [
        ("📊", "Dashboard",     "Dashboard"),
        ("🤖", "CFO Agent",     "CFO Agent"),
        ("🏢", "Clienti",       "Clienti"),
        ("📁", "Workspace",     "Workspace"),
        ("⚙️", "Configurazione","Configurazione"),
        ("🎯", "Budget",        "Budget"),
        ("✏️", "Rettifiche",    "Rettifiche"),
    ]
    page = st.session_state.get('page', 'Dashboard')
    for icon, label, key in NAV:
        active = page == key
        label_md = f"**{icon} {label}**" if active else f"{icon} {label}"
        if st.button(label_md, key=f"nav_{key}", use_container_width=True):
            st.session_state['page'] = key
            st.rerun()

    st.markdown("<div style='position:absolute;bottom:16px;left:0;right:0;padding:0 12px'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.7rem;color:#334155;text-align:center'>{st.session_state.get('user','')}</div>", unsafe_allow_html=True)
    if st.button("Esci", key="logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ── ROUTING ───────────────────────────────────────────────────────────────────
page = st.session_state.get('page', 'Dashboard')

if   page == 'Dashboard':      render_dashboard()
elif page == 'CFO Agent':      render_cfo_agent()
elif page == 'Clienti':        render_clienti()
elif page == 'Workspace':      render_workspace()
elif page == 'Configurazione': render_configurazione()
elif page == 'Budget':         render_budget()
elif page == 'Rettifiche':     render_rettifiche()
else:                          render_dashboard()
