import streamlit as st

SETTORI_ATECO = [
    "A - Agricoltura, silvicoltura e pesca",
    "B - Estrazione di minerali",
    "C - Attività manifatturiere",
    "D - Fornitura di energia elettrica, gas",
    "E - Fornitura di acqua, reti fognarie",
    "F - Costruzioni",
    "G - Commercio all'ingrosso e al dettaglio",
    "H - Trasporto e magazzinaggio",
    "I - Attività dei servizi di alloggio e ristorazione",
    "J - Servizi di informazione e comunicazione",
    "K - Attività finanziarie e assicurative",
    "L - Attività immobiliari",
    "M - Attività professionali, scientifiche e tecniche",
    "N - Noleggio, agenzie di viaggio, servizi alle imprese",
    "O - Amministrazione pubblica",
    "P - Istruzione",
    "Q - Sanità e assistenza sociale",
    "R - Attività artistiche, sportive",
    "S - Altre attività di servizi",
]

FASCE_FATTURATO = [
    "< 500K €",
    "500K - 2M €",
    "2M - 10M €",
    "10M - 50M €",
    "> 50M €",
]


def is_onboarding_complete() -> bool:
    return st.session_state.get('onboarding_done', False)


def render_onboarding(edit_mode: bool = False):
    """
    Wizard di onboarding (2 step) o form di editing del profilo.
    I dati vengono salvati in st.session_state['company_profile'].
    """
    profile = st.session_state.get('company_profile', {})

    if edit_mode:
        _render_profile_editor(profile)
        return

    step = st.session_state.get('onboarding_step', 1)

    # Layout centrato
    _, col, _ = st.columns([1, 2, 1])
    with col:
        # Progress dots
        dots = ''.join([
            f'<div class="step-dot {"step-dot-active" if i + 1 <= step else ""}"></div>'
            for i in range(2)
        ])
        st.markdown(f"""
        <div class="onboarding-step">
            <div class="onboarding-header">
                <h2>{'🏢 Profilo Aziendale' if step == 1 else '⚙️ Configurazione Iniziale'}</h2>
                <p style="color:#6B7280; font-size:0.85rem; margin-top:8px;">
                    {'Inserisci le informazioni della tua azienda. Saranno utilizzate dall\'AI per analisi contestualizzate.' if step == 1 else 'Configura le preferenze operative della piattaforma.'}
                </p>
            </div>
            <div class="step-indicator">{dots}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if step == 1:
            _render_step1(profile)
        elif step == 2:
            _render_step2(profile)


def _render_step1(profile):
    with st.form("onboarding_step1"):
        st.markdown("##### Dati Aziendali")

        nome = st.text_input("Ragione Sociale *",
                              value=profile.get('nome_azienda', st.session_state.get('tenant', '')))
        sito_web = st.text_input("Sito Web",
                                  value=profile.get('sito_web', ''),
                                  placeholder="https://www.azienda.it")

        c1, c2 = st.columns(2)
        settore = c1.selectbox("Settore ATECO *",
                                SETTORI_ATECO,
                                index=SETTORI_ATECO.index(profile['settore'])
                                if profile.get('settore') in SETTORI_ATECO else 0)
        fatturato = c2.selectbox("Fascia di fatturato",
                                  FASCE_FATTURATO,
                                  index=FASCE_FATTURATO.index(profile['fascia_fatturato'])
                                  if profile.get('fascia_fatturato') in FASCE_FATTURATO else 0)

        c3, c4 = st.columns(2)
        dipendenti = c3.number_input("N. Dipendenti",
                                      min_value=0, step=1,
                                      value=int(profile.get('dipendenti', 0)))
        anni_attivita = c4.number_input("Anni di attività",
                                         min_value=0, step=1,
                                         value=int(profile.get('anni_attivita', 0)))

        descrizione = st.text_area("Descrizione business (facoltativo)",
                                    value=profile.get('descrizione', ''),
                                    placeholder="Breve descrizione delle attività principali...",
                                    height=80)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Avanti →", use_container_width=True):
            if not nome.strip():
                st.error("Inserisci la Ragione Sociale.")
            else:
                st.session_state['company_profile'].update({
                    'nome_azienda': nome.strip(),
                    'sito_web': sito_web.strip(),
                    'settore': settore,
                    'fascia_fatturato': fatturato,
                    'dipendenti': dipendenti,
                    'anni_attivita': anni_attivita,
                    'descrizione': descrizione.strip(),
                })
                st.session_state['onboarding_step'] = 2
                st.rerun()


def _render_step2(profile):
    with st.form("onboarding_step2"):
        st.markdown("##### Preferenze Operative")

        ruolo_utente = st.selectbox("Il mio ruolo principale:", [
            "Imprenditore / Proprietario",
            "CFO / Direttore Amministrativo",
            "Controller di Gestione",
            "Commercialista / Consulente",
            "Responsabile Operativo",
        ], index=0)

        st.markdown("##### Configurazione Alert Sentinel")
        c1, c2 = st.columns(2)
        soglia_warn = c1.slider("Soglia Warning scostamento %", 5, 50, 15,
                                 help="Sotto questa soglia: alert giallo")
        soglia_crit = c2.slider("Soglia Critical scostamento %", 10, 100, 30,
                                  help="Sopra questa soglia: alert rosso")

        st.markdown("##### Valuta di riferimento")
        valuta = st.selectbox("Valuta:", ["EUR (€)", "USD ($)", "GBP (£)", "CHF"], index=0)

        st.markdown("##### API Key Anthropic")
        st.markdown("""
        <div class="info-box info-box-blue">
        💡 La API Key è necessaria per le funzionalità AI (mappatura automatica, AI CFO, Sentinel).
        Puoi inserirla ora o aggiungerla in seguito nel Workspace. Ottienila su <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>
        </div>
        """, unsafe_allow_html=True)

        api_key = st.text_input("API Key (opzionale ora)", type="password",
                                 placeholder="sk-ant-api03-...",
                                 value=st.session_state.get('anthropic_api_key', ''))

        st.markdown("<br>", unsafe_allow_html=True)
        col_back, col_next = st.columns(2)

        back = col_back.form_submit_button("← Indietro", use_container_width=True)
        next_ = col_next.form_submit_button("Inizia →", type="primary", use_container_width=True)

        if back:
            st.session_state['onboarding_step'] = 1
            st.rerun()

        if next_:
            st.session_state['company_profile'].update({
                'ruolo': ruolo_utente,
                'soglia_warn': soglia_warn,
                'soglia_crit': soglia_crit,
                'valuta': valuta,
            })
            if api_key.strip():
                st.session_state['anthropic_api_key'] = api_key.strip()

            st.session_state['onboarding_done'] = True

            # Crea cliente automatico per aziende
            if st.session_state.get('role') != 'professionista':
                nome_a = st.session_state['company_profile'].get('nome_azienda', st.session_state['tenant'])
                if nome_a not in st.session_state.get('clienti', {}):
                    if 'clienti' not in st.session_state:
                        st.session_state['clienti'] = {}
                    st.session_state['clienti'][nome_a] = {
                        'df_piano': None, 'df_db': None, 'df_ricl': None,
                        'rettifiche': [], 'mapping': {}, 'mapping_staging': None,
                        'schemi': {}, 'schema_attivo': None, 'budget': None
                    }
                    st.session_state['cliente_attivo'] = nome_a

            st.session_state['page'] = 'Workspace'
            st.rerun()


def _render_profile_editor(profile):
    """Form di editing del profilo in modalità pagina normale."""
    st.markdown("## 🏢 Profilo Aziendale")

    with st.form("edit_profile"):
        st.markdown("### Dati Aziendali")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Ragione Sociale", value=profile.get('nome_azienda', ''))
        sito = c2.text_input("Sito Web", value=profile.get('sito_web', ''))

        c3, c4 = st.columns(2)
        settore = c3.selectbox("Settore ATECO", SETTORI_ATECO,
                                index=SETTORI_ATECO.index(profile['settore'])
                                if profile.get('settore') in SETTORI_ATECO else 0)
        fatturato = c4.selectbox("Fascia fatturato", FASCE_FATTURATO,
                                  index=FASCE_FATTURATO.index(profile['fascia_fatturato'])
                                  if profile.get('fascia_fatturato') in FASCE_FATTURATO else 0)

        c5, c6 = st.columns(2)
        dip = c5.number_input("Dipendenti", min_value=0, value=int(profile.get('dipendenti', 0)))
        anni = c6.number_input("Anni attività", min_value=0, value=int(profile.get('anni_attivita', 0)))

        desc = st.text_area("Descrizione business", value=profile.get('descrizione', ''), height=80)

        st.markdown("### Alert Sentinel")
        ca1, ca2 = st.columns(2)
        sw = ca1.slider("Soglia Warning %", 5, 50, int(profile.get('soglia_warn', 15)))
        sc = ca2.slider("Soglia Critical %", 10, 100, int(profile.get('soglia_crit', 30)))

        st.markdown("### API Key")
        ak = st.text_input("Anthropic API Key", type="password",
                            value=st.session_state.get('anthropic_api_key', ''),
                            placeholder="sk-ant-api03-...")

        if st.form_submit_button("💾 Salva Modifiche", type="primary"):
            st.session_state['company_profile'].update({
                'nome_azienda': nome, 'sito_web': sito,
                'settore': settore, 'fascia_fatturato': fatturato,
                'dipendenti': dip, 'anni_attivita': anni,
                'descrizione': desc, 'soglia_warn': sw, 'soglia_crit': sc,
            })
            if ak.strip():
                st.session_state['anthropic_api_key'] = ak.strip()
            st.success("✅ Profilo aggiornato")

    # Mostra riepilogo
    st.markdown("---")
    st.markdown("### Riepilogo Profilo Attivo")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-label">Azienda</div>
            <div style="font-size:1.1rem; font-weight:600; color:#0F2044;">{profile.get('nome_azienda','—')}</div>
            <div style="font-size:0.8rem; color:#6B7280; margin-top:4px;">{profile.get('settore','—')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="card">
            <div class="kpi-label">Dati operativi</div>
            <div style="font-size:0.85rem; color:#374151;">
                👥 {profile.get('dipendenti','—')} dipendenti &nbsp;·&nbsp;
                💰 {profile.get('fascia_fatturato','—')}<br>
                🌐 {profile.get('sito_web','Non inserito')}
            </div>
        </div>
        """, unsafe_allow_html=True)
