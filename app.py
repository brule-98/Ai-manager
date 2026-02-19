"""
app.py — AI-Manager: Piattaforma Professionale di Controllo di Gestione.
Entry point Streamlit con routing multi-pagina e design corporate premium.
"""
import streamlit as st

st.set_page_config(
    page_title="AI-Manager | Controllo di Gestione",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #060D1A !important;
    color: #E2E8F0 !important;
}

/* ── Main area ── */
.main .block-container {
    background: #060D1A !important;
    padding: 0 2rem 3rem !important;
    max-width: 1400px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #080F1E !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stSidebar"] * { color: #94A3B8 !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong, [data-testid="stSidebar"] b { color: #E2E8F0 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
}

/* ── Sidebar nav buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #64748B !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 9px 12px !important;
    width: 100% !important;
    margin-bottom: 2px !important;
    transition: all 0.15s !important;
    justify-content: flex-start !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.05) !important;
    color: #CBD5E1 !important;
    border-color: rgba(255,255,255,0.08) !important;
}
[data-testid="stSidebar"] .stButton > button p {
    text-align: left !important;
    font-size: 0.83rem !important;
}

/* ── Main buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1A3A7A, #0F2044) !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.84rem !important;
    transition: all 0.2s !important;
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
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 2px 12px rgba(201,168,76,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(201,168,76,0.35) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.02) !important;
    border-radius: 10px 10px 0 0;
    gap: 2px;
    padding: 4px 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #475569 !important;
    border-radius: 8px 8px 0 0 !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    border: none !important;
    transition: color 0.15s !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.05) !important;
    color: #E2E8F0 !important;
    border-bottom: 2px solid #C9A84C !important;
    font-weight: 600 !important;
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
}
div[data-testid="stExpander"] summary {
    color: #94A3B8 !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
div[data-testid="stExpander"] p { color: #94A3B8 !important; }

/* ── Input fields ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: rgba(255,255,255,0.04) !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #C9A84C !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.12) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #334155 !important; }
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stRadio label, .stCheckbox label,
.stFileUploader label, .stSlider label {
    color: #64748B !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.3px !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
}

/* ── Radio / Checkbox ── */
.stRadio > div { color: #94A3B8 !important; }
.stCheckbox > label > div { color: #94A3B8 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
[data-testid="stAlert"] p { color: #E2E8F0 !important; }
.stSuccess { background: rgba(16,185,129,0.1) !important; border-color: rgba(16,185,129,0.3) !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border-color: rgba(245,158,11,0.3) !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border-color: rgba(239,68,68,0.3)  !important; }
.stInfo    { background: rgba(59,130,246,0.1)  !important; border-color: rgba(59,130,246,0.3)  !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
}
[data-testid="stMetric"] label { color: #475569 !important; }
[data-testid="stMetricValue"] { color: #F1F5F9 !important; }

/* ── Progress ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #1A3A7A, #C9A84C) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px dashed rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploader"] span, [data-testid="stFileUploader"] p { color: #475569 !important; }

/* ── Caption ── */
.stCaption, [data-testid="stCaptionContainer"] { color: #334155 !important; }

/* ── Code ── */
code { background: rgba(255,255,255,0.06) !important; color: #C9A84C !important; border-radius: 4px !important; }

/* ── Hide Streamlit branding ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; }

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
""", unsafe_allow_html=True)

# ── IMPORTS ───────────────────────────────────────────────────────────────────
from auth.login import render_login
from modules.workspace import render_workspace
from modules.dashboard import render_dashboard
from modules.cfo_agent import render_cfo_agent
from modules.rettifiche import render_rettifiche
from modules.configurazione import render_configurazione
from modules.budget import render_budget
from services.data_utils import cliente_vuoto


def init_state():
    defaults = {
        'authenticated': False, 'user': None, 'tenant': None, 'role': None,
        'clienti': {}, 'cliente_attivo': None, 'page': 'Dashboard',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ── AUTH ─────────────────────────────────────────────────────────────────────
if not st.session_state['authenticated']:
    render_login()
    st.stop()

user   = st.session_state['user']
tenant = st.session_state['tenant']
role   = st.session_state['role']

# ── HEADER ───────────────────────────────────────────────────────────────────
role_badge = '🏢 Studio' if role == 'professionista' else '👔 Azienda'
st.markdown(f"""
<div style='background:#080F1E;border-bottom:1px solid rgba(201,168,76,0.15);
            padding:12px 32px;margin-bottom:24px;
            display:flex;align-items:center;justify-content:space-between'>
    <div style='display:flex;align-items:center;gap:16px'>
        <div style='width:32px;height:32px;background:linear-gradient(135deg,#C9A84C,#A8833A);
                    border-radius:8px;display:flex;align-items:center;justify-content:center;
                    font-size:0.9rem;flex-shrink:0'>📊</div>
        <div>
            <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;color:#C9A84C;font-weight:700'>AI-Manager</div>
            <div style='font-size:0.88rem;font-weight:700;color:#F1F5F9;letter-spacing:-0.2px'>Controllo di Gestione</div>
        </div>
    </div>
    <div style='display:flex;align-items:center;gap:8px'>
        <div style='font-size:0.72rem;color:#475569;background:rgba(255,255,255,0.04);
                    padding:4px 12px;border-radius:6px;border:1px solid rgba(255,255,255,0.06)'>
            👤 {user} &nbsp;·&nbsp; <span style='color:#64748B'>{tenant}</span>
        </div>
        <div style='font-size:0.72rem;color:#C9A84C;background:rgba(201,168,76,0.08);
                    padding:4px 10px;border-radius:6px;border:1px solid rgba(201,168,76,0.15)'>
            {role_badge}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown(f"""
    <div style='text-align:center;padding:16px 0 20px'>
        <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;
                    color:#C9A84C;font-weight:700;margin-bottom:4px'>
            AI-Manager
        </div>
        <div style='font-size:0.7rem;color:#475569'>Virtual CFO Platform</div>
        <div style='width:40px;height:1px;background:rgba(201,168,76,0.3);margin:10px auto 0'></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Gestione clienti ─────────────────────────────────────────────────────
    st.markdown("**📁 Cliente**")
    clienti = list(st.session_state['clienti'].keys())

    if not clienti and role != 'professionista':
        # Auto-crea cliente per utente azienda
        if tenant not in st.session_state['clienti']:
            st.session_state['clienti'][tenant] = cliente_vuoto()
            st.session_state['cliente_attivo'] = tenant
            clienti = [tenant]

    if clienti:
        idx_def = 0
        ca_cur  = st.session_state.get('cliente_attivo')
        if ca_cur in clienti:
            idx_def = clienti.index(ca_cur)
        sel = st.selectbox("Attivo:", clienti, index=idx_def, label_visibility="collapsed")
        st.session_state['cliente_attivo'] = sel
    else:
        st.markdown("<div style='font-size:0.78rem;color:#475569;font-style:italic;padding:4px 0'>Nessun cliente</div>", unsafe_allow_html=True)
        st.session_state['cliente_attivo'] = None

    if role == 'professionista':
        with st.expander("➕ Nuovo cliente"):
            nome_n = st.text_input("Nome cliente:", key="new_cli_name", label_visibility="collapsed",
                                    placeholder="Es. Rossi Srl")
            if st.button("✚ Crea", key="btn_new_cli"):
                nome_n = nome_n.strip()
                if nome_n and nome_n not in st.session_state['clienti']:
                    st.session_state['clienti'][nome_n] = cliente_vuoto()
                    st.session_state['cliente_attivo'] = nome_n
                    st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:16px 0 12px'>", unsafe_allow_html=True)

    # ── Navigazione ──────────────────────────────────────────────────────────
    page_cur = st.session_state.get('page', 'Dashboard')

    NAV = [
        ("📊  Dashboard",      "Dashboard"),
        ("🗂️  Workspace",      "Workspace"),
        ("🏦  CFO Agent",      "CFO Agent"),
        ("🎯  Budget",         "Budget"),
        ("✏️  Rettifiche",    "Rettifiche"),
        ("⚙️  Configurazione","Configurazione"),
    ]

    # Inject active-state CSS for the current page button
    active_styles = ""
    for i, (_, pg) in enumerate(NAV):
        if pg == page_cur:
            # nth-child won't work reliably; use a wrapper div trick
            # Instead we inject per-button style via a unique key marker
            active_styles += (
                "/* active nav item */"
            )

    # Build nav section with label above + styled button
    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
    for btn_label, page_key in NAV:
        active = (page_cur == page_key)
        if active:
            st.markdown(
                "<div style='background:rgba(201,168,76,0.08);"
                "border:1px solid rgba(201,168,76,0.22);"
                "border-radius:8px;margin-bottom:2px;"
                "overflow:hidden'>",
                unsafe_allow_html=True
            )
        if st.button(btn_label, key="nav_" + page_key, use_container_width=True):
            st.session_state['page'] = page_key
            st.rerun()
        if active:
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:12px 0'>", unsafe_allow_html=True)

    # ── Info cliente attivo ────────────────────────────────────────────────
    ca = st.session_state.get('cliente_attivo')
    if ca:
        from services.data_utils import get_cliente
        cl = get_cliente()
        if cl:
            has_data   = cl.get('df_db') is not None
            has_map    = bool(cl.get('mapping'))
            has_budget = bool(cl.get('budget'))
            has_ai     = bool(st.session_state.get('anthropic_api_key') or
                              (hasattr(st, 'secrets') and st.secrets.get('ANTHROPIC_API_KEY','')))

            stati = [
                ("Dati caricati",  has_data),
                ("Mapping OK",     has_map),
                ("Budget attivo",  has_budget),
                ("CFO AI pronto",  has_ai),
            ]
            def _stato_row(nome, ok):
                clr = '#10B981' if ok else '#EF4444'
                sym = '✓' if ok else '○'
                return (f"<div style='display:flex;justify-content:space-between;font-size:0.72rem;"
                        f"padding:3px 0;color:#475569'>"
                        f"<span>{nome}</span>"
                        f"<span style='color:{clr}'>{sym}</span></div>")
            righe = "".join(_stato_row(n, o) for n, o in stati)
            st.markdown(f"""
            <div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                        border-radius:8px;padding:10px 12px;margin-bottom:12px'>
                <div style='font-size:9px;text-transform:uppercase;letter-spacing:1.5px;
                            color:#C9A84C;font-weight:700;margin-bottom:8px'>{ca}</div>
                {righe}
            </div>""", unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    # ── API Key auto-load ──────────────────────────────────────────────────
    if not st.session_state.get('anthropic_api_key'):
        try:
            k = st.secrets.get('ANTHROPIC_API_KEY', '')
            if k:
                st.session_state['anthropic_api_key'] = k
        except Exception:
            pass


# ── ROUTER ───────────────────────────────────────────────────────────────────
page = st.session_state.get('page', 'Dashboard')

if   page == 'Dashboard':     render_dashboard()
elif page == 'Workspace':     render_workspace()
elif page == 'CFO Agent':     render_cfo_agent()
elif page == 'Budget':        render_budget()
elif page == 'Rettifiche':    render_rettifiche()
elif page == 'Configurazione':render_configurazione()
