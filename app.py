import streamlit as st

st.set_page_config(
    page_title="AI-Manager | Controllo di Gestione",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ─── STILE GLOBALE ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #F8F9FB;
}
.main-header {
    background: linear-gradient(135deg, #0F2044 0%, #1A3A7A 100%);
    color: white;
    padding: 1.1rem 2rem;
    border-radius: 0 0 16px 16px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.main-header h1 { font-family: 'DM Serif Display', serif; font-size: 1.5rem; margin: 0; color: white !important; }
.main-header .subtitle { font-size: 0.76rem; color: #90AEE8; margin: 2px 0 0 0; }
.badge-tenant {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 5px 16px;
    font-size: 0.75rem;
    color: white;
}
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    border-left: 4px solid #1A3A7A;
    margin-bottom: 12px;
}
.metric-card .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #8896AB; font-weight: 600; }
.metric-card .value { font-size: 1.55rem; font-weight: 600; color: #0F2044; margin-top: 3px; }
.delta-pos { color: #059669; font-size: 0.78rem; }
.delta-neg { color: #DC2626; font-size: 0.78rem; }
.section-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.5px; color: #8896AB; font-weight: 700; margin: 1.5rem 0 0.8rem 0; }
[data-testid="stSidebar"] { background: #0F2044 !important; }
[data-testid="stSidebar"] label { color: #CBD5E8 !important; }
[data-testid="stSidebar"] .stSelectbox label { color: #CBD5E8 !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #CBD5E8 !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08);
    color: white !important;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    font-weight: 400;
    font-size: 0.85rem;
    text-align: left;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.16) !important;
    transform: none;
    box-shadow: none;
}
.stButton > button {
    background: #1A3A7A;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: #0F2044;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15,32,68,0.2);
}
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 2px solid #E2E8F0; }
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 8px 8px 0 0;
    font-weight: 500; font-size: 0.84rem; color: #64748B; padding: 10px 18px;
}
.stTabs [aria-selected="true"] {
    background: #EEF2FF !important; color: #1A3A7A !important;
    border-bottom: 3px solid #1A3A7A !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; }
div[data-testid="stExpander"] { background: white; border-radius: 10px; border: 1px solid #E2E8F0; }
</style>
""", unsafe_allow_html=True)

from auth.login import render_login
from modules.workspace import render_workspace
from modules.dashboard import render_dashboard
from modules.rettifiche import render_rettifiche
from modules.configurazione import render_configurazione

# ─── INIT SESSION STATE ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        'authenticated': False,
        'user': None,
        'tenant': None,
        'role': None,
        'clienti': {},
        'cliente_attivo': None,
        'page': 'Dashboard',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

if not st.session_state['authenticated']:
    render_login()
    st.stop()

# ─── HEADER ───────────────────────────────────────────────────────────────────
user = st.session_state['user']
tenant = st.session_state['tenant']
role = st.session_state['role']
role_label = '🏢 Studio Professionale' if role == 'professionista' else '👔 Azienda'

st.markdown(f"""
<div class="main-header">
    <div>
        <h1>📊 AI-Manager</h1>
        <p class="subtitle">Piattaforma Professionale di Controllo di Gestione</p>
    </div>
    <div class="badge-tenant">👤 {user} &nbsp;·&nbsp; {tenant} &nbsp;·&nbsp; {role_label}</div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📁 Clienti")

    clienti = list(st.session_state['clienti'].keys())

    if clienti:
        idx_default = 0
        if st.session_state['cliente_attivo'] in clienti:
            idx_default = clienti.index(st.session_state['cliente_attivo'])
        cliente_sel = st.selectbox("Cliente attivo:", clienti, index=idx_default)
        st.session_state['cliente_attivo'] = cliente_sel
    else:
        st.caption("Nessun cliente caricato")
        st.session_state['cliente_attivo'] = None

    if role == 'professionista':
        with st.expander("➕ Aggiungi cliente"):
            nuovo = st.text_input("Nome cliente:", key="nuovo_cliente_input")
            if st.button("Crea", key="btn_crea_cliente"):
                nome = nuovo.strip()
                if nome and nome not in st.session_state['clienti']:
                    st.session_state['clienti'][nome] = {
                        'df_piano': None, 'df_db': None, 'df_ricl': None,
                        'rettifiche': [], 'mapping': {}, 'schemi': {},
                        'schema_attivo': None
                    }
                    st.session_state['cliente_attivo'] = nome
                    st.rerun()
    else:
        # Azienda: crea automaticamente un cliente col proprio nome se non esiste
        if tenant not in st.session_state['clienti']:
            st.session_state['clienti'][tenant] = {
                'df_piano': None, 'df_db': None, 'df_ricl': None,
                'rettifiche': [], 'mapping': {}, 'schemi': {},
                'schema_attivo': None
            }
            st.session_state['cliente_attivo'] = tenant

    st.markdown("---")
    st.markdown("## 🧭 Menu")

    nav_items = [
        ("📊", "Dashboard", "Dashboard"),
        ("🗂️", "Workspace Dati", "Workspace"),
        ("✏️", "Rettifiche", "Rettifiche"),
        ("⚙️", "Configurazione", "Configurazione"),
    ]
    for icon, label, key in nav_items:
        is_active = st.session_state['page'] == key
        btn_label = f"{'▶ ' if is_active else ''}{icon} {label}"
        if st.button(btn_label, key=f"nav_{key}", use_container_width=True):
            st.session_state['page'] = key
            st.rerun()

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ─── ROUTER ───────────────────────────────────────────────────────────────────
page = st.session_state.get('page', 'Dashboard')

if page == 'Dashboard':
    render_dashboard()
elif page == 'Workspace':
    render_workspace()
elif page == 'Rettifiche':
    render_rettifiche()
elif page == 'Configurazione':
    render_configurazione()
