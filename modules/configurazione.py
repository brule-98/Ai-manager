import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column


def render_configurazione():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    df_ricl  = cliente.get('df_ricl')
    schemi   = cliente.get('schemi', {})
    schema_attivo = cliente.get('schema_attivo', '')

    st.markdown(f"## ⚙️ Configurazione Schema — {ca}")

    tab1, tab2, tab3 = st.tabs(["🗂️ Gestione Schemi", "🌳 Visualizer Schema", "⚙️ Configurazione Voci"])

    # ══════════════════════════════════════════════════════════════
    # TAB 1: GESTIONE SCHEMI
    # ══════════════════════════════════════════════════════════════
    with tab1:
        _render_gestione_schemi(ca, cliente, df_ricl, schemi, schema_attivo)

    # ══════════════════════════════════════════════════════════════
    # TAB 2: VISUALIZER
    # ══════════════════════════════════════════════════════════════
    with tab2:
        _render_schema_visualizer(schemi, schema_attivo)

    # ══════════════════════════════════════════════════════════════
    # TAB 3: CONFIGURAZIONE VOCI
    # ══════════════════════════════════════════════════════════════
    with tab3:
        _render_configurazione_voci(ca, cliente, schemi, schema_attivo)


def _render_gestione_schemi(ca, cliente, df_ricl, schemi, schema_attivo):
    st.markdown("### Schemi di Riclassificazione")
    st.markdown("""
    <div class="info-box info-box-blue">
    Puoi avere più schemi per lo stesso cliente (CE Gestionale, CE Civilistico, CE per Area) e
    attivarli con un click. Lo schema attivo viene usato dalla Dashboard e dal CFO Digitale.
    </div>
    """, unsafe_allow_html=True)

    if schemi:
        for nome_schema, config in schemi.items():
            n_voci = len(config)
            is_active = nome_schema == schema_attivo

            col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
            with col_a:
                badge = '<span class="sentinel-badge badge-ok">● ATTIVO</span>' if is_active else ""
                st.markdown(
                    f"**{nome_schema}** &nbsp; {badge} &nbsp; "
                    f"<span style='font-size:0.75rem; color:#6B7280;'>{n_voci} voci</span>",
                    unsafe_allow_html=True
                )
            with col_b:
                if not is_active:
                    if st.button("Attiva", key=f"att_{nome_schema}", use_container_width=True):
                        save_cliente({'schema_attivo': nome_schema})
                        st.success(f"Schema '{nome_schema}' attivato")
                        st.rerun()
            with col_c:
                if st.button("Duplica", key=f"dup_{nome_schema}", use_container_width=True):
                    nuovo_nome = f"{nome_schema} (copia)"
                    schemi[nuovo_nome] = dict(config)
                    save_cliente({'schemi': schemi})
                    st.rerun()
            with col_d:
                if st.button("🗑️", key=f"del_{nome_schema}", help="Elimina schema"):
                    del schemi[nome_schema]
                    if schema_attivo == nome_schema:
                        save_cliente({'schemi': schemi, 'schema_attivo': ''})
                    else:
                        save_cliente({'schemi': schemi})
                    st.rerun()
    else:
        st.info("Nessuno schema configurato.")

    st.markdown("---")
    st.markdown("#### Crea Nuovo Schema")

    with st.form("form_nuovo_schema"):
        c1, c2 = st.columns(2)
        nome_nuovo = c1.text_input("Nome schema *", placeholder="es. CE Gestionale 2024")
        template = c2.selectbox("Template base:", [
            "Vuoto",
            "Da Schema Riclassifica caricato",
            "CE Civilistico (template standard)",
        ])

        if st.form_submit_button("Crea Schema"):
            n = nome_nuovo.strip()
            if not n:
                st.error("Inserisci un nome.")
            elif n in schemi:
                st.error("Schema già esistente.")
            else:
                config_init = {}

                if template == "Da Schema Riclassifica caricato" and df_ricl is not None:
                    col_cod  = find_column(df_ricl, ['Codice','codice','Voce','voce','ID'])
                    col_desc = find_column(df_ricl, ['Descrizione','descrizione','voce','Voce','Nome'])
                    for i, (_, row) in enumerate(df_ricl.iterrows()):
                        voce = str(row[col_cod]) if col_cod else f"voce_{i}"
                        config_init[voce] = {
                            'ordine': i * 10,
                            'segno': 1,
                            'subtotale': False,
                            'descrizione_override': str(row[col_desc]) if col_desc else voce,
                            'formula': '',
                            'style_class': 'normal',
                        }
                elif template == "CE Civilistico (template standard)":
                    config_init = _template_ce_civilistico()

                schemi[n] = config_init
                save_cliente({'schemi': schemi, 'schema_attivo': n})
                st.success(f"✅ Schema '{n}' creato con {len(config_init)} voci")
                st.rerun()


def _render_schema_visualizer(schemi, schema_attivo):
    st.markdown("### 🌳 Visualizzazione Schema")

    if not schemi:
        st.info("Crea prima uno schema nel tab 'Gestione Schemi'.")
        return

    schema_sel = st.selectbox("Schema da visualizzare:", list(schemi.keys()),
                               index=list(schemi.keys()).index(schema_attivo)
                               if schema_attivo in schemi else 0,
                               key="viz_schema_sel")

    config = schemi.get(schema_sel, {})
    if not config:
        st.info("Schema vuoto.")
        return

    voci_ordinate = sorted(config.items(), key=lambda x: x[1].get('ordine', 999))

    st.markdown(f"""
    <div class="card">
        <div style="font-weight:700; font-size:0.95rem; color:#0F2044; margin-bottom:1rem;">
            📊 {schema_sel}
        </div>
    """, unsafe_allow_html=True)

    for voce, cfg in voci_ordinate:
        label = cfg.get('descrizione_override', voce)
        segno = cfg.get('segno', 1)
        subtot = cfg.get('subtotale', False)
        formula = cfg.get('formula', '')
        style_class = cfg.get('style_class', 'normal')
        ordine = cfg.get('ordine', 0)

        # Indicatori
        segno_html = '🔵 <span style="color:#059669">+</span>' if segno == 1 else '🔴 <span style="color:#DC2626">-</span>'
        formula_html = f'<span style="font-family:monospace; font-size:0.7rem; color:#7C3AED; background:#F5F3FF; padding:1px 6px; border-radius:4px;">ƒ {formula[:30]}</span>' if formula else ''
        highlight_html = '<span class="sentinel-badge badge-info">highlight</span>' if style_class == 'highlight' else ''

        if subtot:
            css = 'tree-root tree-subtotal'
            depth = ''
        else:
            css = 'tree-node'
            depth = ''

        st.markdown(f"""
        <div class="{css}" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                {depth}<span style="margin-right:6px; font-size:0.72rem; color:#9CA3AF;">#{ordine}</span>
                <b>{label}</b>
                <span style="font-size:0.72rem; color:#9CA3AF; margin-left:8px;">({voce})</span>
                {formula_html}
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
                {highlight_html}
                {segno_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Stats schema
    n_subtot = sum(1 for _, c in voci_ordinate if c.get('subtotale'))
    n_form   = sum(1 for _, c in voci_ordinate if c.get('formula'))
    n_hl     = sum(1 for _, c in voci_ordinate if c.get('style_class') == 'highlight')
    n_inv    = sum(1 for _, c in voci_ordinate if c.get('segno') == -1)

    cols = st.columns(4)
    cols[0].metric("Voci totali", len(config))
    cols[1].metric("Subtotali", n_subtot)
    cols[2].metric("Con formula", n_form)
    cols[3].metric("Con segno invertito", n_inv)


def _render_configurazione_voci(ca, cliente, schemi, schema_attivo):
    st.markdown("### Configurazione Dettagliata Voci")

    if not schemi:
        st.info("Crea prima uno schema nel tab 'Gestione Schemi'.")
        return

    schema_sel = st.selectbox("Schema:", list(schemi.keys()),
                               index=list(schemi.keys()).index(schema_attivo)
                               if schema_attivo in schemi else 0,
                               key="cfg_schema_sel")

    config = schemi.get(schema_sel, {})

    st.markdown("""
    <div class="info-box info-box-amber">
    <b>Legenda:</b> &nbsp;
    <b>Segno</b>: +1 mantieni il segno contabile (ricavi positivi), -1 inverti (costi mostrati come positivi) &nbsp;·&nbsp;
    <b>Subtotale</b>: evidenzia in grassetto/navy nel report &nbsp;·&nbsp;
    <b>Highlight</b>: colore blu chiaro nel report &nbsp;·&nbsp;
    <b>Formula</b>: es. <code>VOCE_A + VOCE_B - VOCE_C</code>
    </div>
    """, unsafe_allow_html=True)

    if not config:
        st.info("Schema vuoto.")
        _form_aggiungi_voce(schema_sel, config, schemi)
        return

    voci_ordinate = sorted(config.keys(), key=lambda v: config[v].get('ordine', 999))
    config_updated = {k: dict(v) for k, v in config.items()}

    # Header colonne
    col_h = st.columns([1, 3, 1, 1, 1, 2, 2, 1])
    for h, c in zip(["Ord.", "Voce", "Segno", "Sub.", "Style", "Etichetta", "Formula", ""], col_h):
        c.markdown(f"<div style='font-size:0.7rem; font-weight:700; color:#6B7280; text-transform:uppercase;'>{h}</div>",
                   unsafe_allow_html=True)

    for voce in voci_ordinate:
        cfg = config[voce]
        cols = st.columns([1, 3, 1, 1, 1, 2, 2, 1])

        with cols[0]:
            new_ord = st.number_input("", value=int(cfg.get('ordine', 0)), step=10,
                                       label_visibility="collapsed", key=f"ord_{schema_sel}_{voce}")
            config_updated[voce]['ordine'] = new_ord

        with cols[1]:
            label_curr = cfg.get('descrizione_override', voce)
            st.markdown(
                f"<div style='padding:8px 2px; font-size:0.82rem;'><b>{voce}</b><br>"
                f"<span style='color:#6B7280; font-size:0.75rem;'>{label_curr}</span></div>",
                unsafe_allow_html=True
            )

        with cols[2]:
            segno = st.selectbox("", [1, -1], index=0 if cfg.get('segno', 1) == 1 else 1,
                                  format_func=lambda x: "+1" if x == 1 else "-1",
                                  label_visibility="collapsed", key=f"sgn_{schema_sel}_{voce}")
            config_updated[voce]['segno'] = segno

        with cols[3]:
            sub = st.checkbox("", value=cfg.get('subtotale', False),
                               label_visibility="collapsed", key=f"sub_{schema_sel}_{voce}")
            config_updated[voce]['subtotale'] = sub

        with cols[4]:
            style = st.selectbox("", ['normal', 'highlight', 'muted'],
                                   index=['normal','highlight','muted'].index(cfg.get('style_class','normal'))
                                   if cfg.get('style_class','normal') in ['normal','highlight','muted'] else 0,
                                   label_visibility="collapsed", key=f"stl_{schema_sel}_{voce}")
            config_updated[voce]['style_class'] = style

        with cols[5]:
            label_ov = st.text_input("", value=cfg.get('descrizione_override', voce),
                                      label_visibility="collapsed", key=f"lbl_{schema_sel}_{voce}")
            config_updated[voce]['descrizione_override'] = label_ov

        with cols[6]:
            formula = st.text_input("", value=cfg.get('formula', ''),
                                     label_visibility="collapsed",
                                     placeholder="A+B-C",
                                     key=f"frm_{schema_sel}_{voce}")
            config_updated[voce]['formula'] = formula

        with cols[7]:
            if st.button("🗑", key=f"del_{schema_sel}_{voce}", help="Elimina"):
                del config_updated[voce]
                schemi[schema_sel] = config_updated
                save_cliente({'schemi': schemi})
                st.rerun()

    st.markdown("---")
    col_s1, col_s2 = st.columns([1, 5])
    with col_s1:
        if st.button("💾 Salva", type="primary", key="btn_salva_cfg"):
            schemi[schema_sel] = config_updated
            save_cliente({'schemi': schemi, 'schema_attivo': schema_sel})
            st.success(f"✅ Schema '{schema_sel}' salvato")

    st.markdown("---")
    _form_aggiungi_voce(schema_sel, config_updated, schemi)


def _form_aggiungi_voce(schema_sel, config, schemi):
    with st.expander("➕ Aggiungi voce"):
        with st.form(f"form_add_v_{schema_sel}"):
            c1, c2, c3, c4, c5 = st.columns(5)
            cod_v  = c1.text_input("Codice *")
            lab_v  = c2.text_input("Etichetta")
            sgn_v  = c3.selectbox("Segno", [1,-1], format_func=lambda x:"+1" if x==1 else "-1")
            sub_v  = c4.checkbox("Subtotale")
            stl_v  = c5.selectbox("Style", ['normal','highlight','muted'])
            frm_v  = st.text_input("Formula (opzionale)", placeholder="VOCE_A + VOCE_B")

            if st.form_submit_button("Aggiungi"):
                cod = cod_v.strip()
                if not cod:
                    st.error("Inserisci il codice.")
                else:
                    max_ord = max([v.get('ordine',0) for v in config.values()], default=0) + 10
                    config[cod] = {
                        'ordine': max_ord, 'segno': sgn_v,
                        'subtotale': sub_v, 'style_class': stl_v,
                        'descrizione_override': lab_v.strip() or cod,
                        'formula': frm_v.strip()
                    }
                    schemi[schema_sel] = config
                    save_cliente({'schemi': schemi})
                    st.success(f"Voce '{cod}' aggiunta.")
                    st.rerun()


def _template_ce_civilistico() -> dict:
    """Restituisce un template CE civilistico standard."""
    voci = [
        ("A_RICAVI",        "Ricavi delle vendite e prestazioni",     10,  1, True,  'highlight'),
        ("A_RICAVI_OTHER",  "Altri ricavi e proventi",                20,  1, False, 'normal'),
        ("TOT_A",           "TOTALE VALORE DELLA PRODUZIONE (A)",     30,  1, True,  'highlight'),
        ("B_MATERIE",       "Acquisto materie prime e merci",          40, -1, False, 'normal'),
        ("B_SERVIZI",       "Costi per servizi",                      50, -1, False, 'normal'),
        ("B_GODIMENTO",     "Costi per godimento beni di terzi",      60, -1, False, 'normal'),
        ("B_PERSONALE",     "Costi per il personale",                 70, -1, False, 'normal'),
        ("B_AMMORT",        "Ammortamenti e svalutazioni",            80, -1, False, 'normal'),
        ("B_VARIAZ",        "Variazioni rimanenze",                   90, -1, False, 'normal'),
        ("B_ONERI",         "Oneri diversi di gestione",              100,-1, False, 'normal'),
        ("TOT_B",           "TOTALE COSTI DELLA PRODUZIONE (B)",     110, -1, True,  'highlight'),
        ("DIFF_AB",         "DIFFERENZA A - B",                      120,  1, True,  'highlight'),
        ("C_PROVENTI",      "Proventi finanziari",                    130,  1, False, 'normal'),
        ("C_ONERI",         "Oneri finanziari",                       140, -1, False, 'normal'),
        ("EBIT",            "RISULTATO PRIMA DELLE IMPOSTE",          150,  1, True,  'highlight'),
        ("IMPOSTE",         "Imposte sul reddito",                    160, -1, False, 'normal'),
        ("UTILE_NETTO",     "UTILE (PERDITA) DI ESERCIZIO",           170,  1, True,  'highlight'),
    ]
    return {
        cod: {
            'ordine': ord_, 'segno': sgn, 'subtotale': sub,
            'descrizione_override': label, 'style_class': stl, 'formula': ''
        }
        for cod, label, ord_, sgn, sub, stl in voci
    }
