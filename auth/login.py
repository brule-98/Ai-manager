"""login.py — Autenticazione con design premium dark."""
import streamlit as st

UTENTI_DEMO = {
    "studio_rossi": {"password": "demo123", "nome": "Studio Rossi & Associati", "tenant": "Studio Rossi", "role": "professionista"},
    "mario.bianchi": {"password": "demo123", "nome": "Mario Bianchi", "tenant": "Bianchi Srl",           "role": "azienda"},
    "admin":         {"password": "admin",   "nome": "Admin Demo",              "tenant": "Demo Corp",    "role": "professionista"},
}


def render_login():
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        background: #060D1A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    section[data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    .stTextInput input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #F1F5F9 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus {
        border-color: #C9A84C !important;
        box-shadow: 0 0 0 3px rgba(201,168,76,0.15) !important;
    }
    .stTextInput input::placeholder { color: #475569 !important; }
    .stTextInput label { color: #94A3B8 !important; font-size: 0.8rem !important; font-weight: 500 !important; letter-spacing: 0.5px !important; }
    .stButton > button {
        background: linear-gradient(135deg, #C9A84C 0%, #A8833A 100%) !important;
        color: #0A0F1A !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 0 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
    div[data-testid="stForm"] { background: transparent !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Full-page layout
    st.markdown("""
    <div style="min-height:100vh;background:radial-gradient(ellipse at 30% 40%,rgba(26,58,110,0.35) 0%,transparent 60%),
                radial-gradient(ellipse at 80% 10%,rgba(201,168,76,0.08) 0%,transparent 50%),#060D1A;
                display:flex;align-items:center;justify-content:center;padding:40px 20px">
        <div style="width:100%;max-width:420px">
            <!-- Brand -->
            <div style="text-align:center;margin-bottom:40px">
                <div style="display:inline-flex;align-items:center;justify-content:center;
                            width:56px;height:56px;background:linear-gradient(135deg,#C9A84C,#A8833A);
                            border-radius:16px;margin-bottom:16px;font-size:1.5rem;
                            box-shadow:0 8px 32px rgba(201,168,76,0.3)">📊</div>
                <div style="font-size:9px;text-transform:uppercase;letter-spacing:5px;color:#C9A84C;font-weight:700;margin-bottom:8px">AI-Manager Platform</div>
                <div style="font-size:1.75rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.5px;margin-bottom:6px">Controllo di Gestione</div>
                <div style="font-size:0.82rem;color:#475569">Virtual CFO per PMI italiane</div>
            </div>
            <!-- Card -->
            <div style="background:rgba(15,22,40,0.8);border:1px solid rgba(255,255,255,0.07);
                        border-radius:20px;padding:36px 40px;backdrop-filter:blur(20px);
                        box-shadow:0 24px 80px rgba(0,0,0,0.6)">
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 10, 1])
    with col:
        with st.form("form_login", clear_on_submit=False):
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            username = st.text_input("USERNAME", placeholder="es. studio_rossi", key="login_user")
            password = st.text_input("PASSWORD", type="password", placeholder="••••••••", key="login_pass")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Accedi →", use_container_width=True)

            if submitted:
                if username in UTENTI_DEMO and UTENTI_DEMO[username]["password"] == password:
                    u = UTENTI_DEMO[username]
                    st.session_state.update({
                        'authenticated': True, 'user': u['nome'],
                        'tenant': u['tenant'], 'role': u['role'],
                        'clienti': {}, 'cliente_attivo': None, 'page': 'Dashboard',
                    })
                    st.rerun()
                else:
                    st.error("Credenziali non valide.")

        st.markdown("""
        <div style="margin-top:20px;padding:12px 16px;background:rgba(255,255,255,0.03);
                    border:1px solid rgba(255,255,255,0.06);border-radius:10px;
                    font-size:0.76rem;color:#475569;text-align:center;line-height:1.8">
            <span style="color:#64748B;font-weight:600">Account demo</span><br>
            studio_rossi / demo123 &nbsp;·&nbsp; mario.bianchi / demo123
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div></div></div>", unsafe_allow_html=True)
