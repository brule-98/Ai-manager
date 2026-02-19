"""login.py — Login funzionante garantito."""
import streamlit as st

UTENTI_DEMO = {
    "studio_rossi": {"password": "demo123", "nome": "Studio Rossi & Associati", "tenant": "Studio Rossi", "role": "professionista"},
    "mario.bianchi": {"password": "demo123", "nome": "Mario Bianchi", "tenant": "Bianchi Srl", "role": "azienda"},
    "admin":         {"password": "admin",   "nome": "Admin Demo",    "tenant": "Demo Corp",   "role": "professionista"},
}


def render_login():
    st.markdown("""
<style>
/* ── Nascondi sidebar e header ── */
[data-testid="stSidebar"]        { display: none !important; }
[data-testid="stHeader"]         { display: none !important; }
[data-testid="stToolbar"]        { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
[data-testid="stStatusWidget"]   { display: none !important; }
#MainMenu                        { display: none !important; }
footer                           { display: none !important; }

/* ── Sfondo pagina ── */
html, body, [class*="css"],
.main, .main > div,
[data-testid="stAppViewContainer"] {
    background: #060D1A !important;
}
.block-container {
    padding: 3rem 1rem 1rem !important;
    max-width: 100% !important;
}

/* ── Form card ── */
[data-testid="stForm"] {
    background: #0D1625 !important;
    border: 1px solid rgba(201,168,76,0.2) !important;
    border-radius: 16px !important;
    padding: 32px 28px !important;
    box-shadow: 0 24px 80px rgba(0,0,0,0.6) !important;
}

/* ── Inputs ── */
[data-testid="stForm"] .stTextInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #F1F5F9 !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
    padding: 10px 14px !important;
}
[data-testid="stForm"] .stTextInput input:focus {
    border-color: #C9A84C !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.15) !important;
    background: rgba(255,255,255,0.07) !important;
}
[data-testid="stForm"] .stTextInput input::placeholder {
    color: #334155 !important;
}
[data-testid="stForm"] .stTextInput label {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}

/* ── Submit button ── */
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #C9A84C 0%, #A8833A 100%) !important;
    color: #060D1A !important;
    font-weight: 800 !important;
    font-size: 0.9rem !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px !important;
    letter-spacing: 0.4px !important;
    transition: opacity 0.2s !important;
    width: 100% !important;
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
    opacity: 0.82 !important;
}

/* ── Error ── */
.stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

    # Centering: 3 colonne, quella centrale contiene tutto
    c1, c2, c3 = st.columns([2, 3, 2])
    with c2:
        # Logo + titolo — HTML STATICO sopra il form, non dentro
        st.markdown("""
<div style="text-align:center; padding: 0 0 28px 0;">
    <div style="
        display:inline-flex; align-items:center; justify-content:center;
        width:54px; height:54px;
        background:linear-gradient(135deg,#C9A84C,#8B6914);
        border-radius:14px; font-size:1.5rem;
        box-shadow:0 8px 28px rgba(201,168,76,0.35);
        margin-bottom:18px;">📊</div>
    <div style="font-size:8px; text-transform:uppercase; letter-spacing:5px;
                color:#C9A84C; font-weight:700; margin-bottom:12px;">
        AI-Manager Platform
    </div>
    <div style="font-size:1.65rem; font-weight:800; color:#F1F5F9;
                letter-spacing:-0.5px; margin-bottom:6px;">
        Controllo di Gestione
    </div>
    <div style="font-size:0.8rem; color:#334155;">
        Virtual CFO &nbsp;·&nbsp; PMI Italiane
    </div>
</div>
""", unsafe_allow_html=True)

        # Form Streamlit puro — nessun HTML intorno ai widget
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="es. studio_rossi")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Accedi →", use_container_width=True)

            if submitted:
                u = UTENTI_DEMO.get(username.strip())
                if u and u["password"] == password:
                    st.session_state.update({
                        "authenticated": True,
                        "user":          u["nome"],
                        "tenant":        u["tenant"],
                        "role":          u["role"],
                        "clienti":       {},
                        "cliente_attivo": None,
                        "page":          "Dashboard",
                    })
                    st.rerun()
                else:
                    st.error("Credenziali non valide. Riprova.")

        # Note demo — HTML STATICO dopo il form
        st.markdown("""
<div style="margin-top:16px; padding:12px 16px;
            background:rgba(255,255,255,0.02);
            border:1px solid rgba(255,255,255,0.05);
            border-radius:8px; text-align:center;
            font-size:0.73rem; color:#334155; line-height:2;">
    <span style="color:#475569; font-weight:700;">Account demo</span><br>
    studio_rossi&nbsp;/&nbsp;demo123
    &nbsp;&nbsp;·&nbsp;&nbsp;
    mario.bianchi&nbsp;/&nbsp;demo123
</div>
""", unsafe_allow_html=True)
