"""
configurazione.py — Configurazione Schema di Riclassificazione.
Supporta: import schema da file, voci contabili, subtotali calcolati, totali, separatori.
"""
import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column, smart_load
from services.riclassifica import get_label_map

C = {
    'gold':   '#C9A84C',
    'navy':   '#0A1628',
    'blue':   '#1E3A6E',
    'green':  '#10B981',
    'red':    '#EF4444',
    'amber':  '#F59E0B',
    'text':   '#1A202C',
    'muted':  '#4A5568',
    'surf':   '#FFFFFF',
    'surf2':  '#F7FAFC',
    'border': '#E2E8F0',
    'head_bg': '#0A1628',
    'head_text': '#F1F5F9',
}

TIPI_VOCE = {
    'contabile': 'Voce contabile (somma conti mappati)',
    'subtotale': 'Subtotale (somma di voci precedenti)',
    'totale':    'Totale (somma di tutte le voci fino a qui)',
    'separatore': 'Separatore / riga vuota',
}

KPI_ROLES = {
    '':            '— nessuno —',
    'ricavi':      '📈 Ricavi',
    'ebitda':      '💹 EBITDA / MOL',
    'ebit':        '📊 EBIT',
    'utile_netto': '🏆 Utile Netto',
    'personale':   '👥 Costo Personale',
    'acquisti':    '🛒 Acquisti / Materie',
}


def render_configurazione():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("Seleziona un cliente dalla sidebar.")
        return

    cliente    = get_cliente()
    df_ricl    = cliente.get('df_ricl')
    schemi     = cliente.get('schemi', {})
    schema_att = cliente.get('schema_attivo', '')

    # Header
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,{C["head_bg"]} 0%,{C["blue"]} 100%);
                border-radius:14px;padding:20px 28px;margin-bottom:24px;
                border:1px solid rgba(201,168,76,0.15)'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:3px;
                    color:{C["gold"]};font-weight:700;margin-bottom:6px'>CONFIGURAZIONE</div>
        <h2 style='color:{C["head_text"]};margin:0;font-size:1.4rem;font-weight:700'>
            ⚙️ Schema di Riclassificazione — {ca}
        </h2>
        <p style='color:#94A3B8;margin:6px 0 0 0;font-size:0.82rem'>
            Gestisci schemi, importa da file, configura voci, subtotali e totali calcolati
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🗂️ Gestione Schemi", "⚙️ Configurazione Voci"])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: GESTIONE SCHEMI
    # ═══════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Schemi Disponibili")

        if schemi:
            for nome_schema, config in schemi.items():
                is_active = nome_schema == schema_att
                border_c  = C['gold'] if is_active else C['border']
                badge     = "● ATTIVO" if is_active else ""
                badge_clr = C['gold'] if is_active else 'transparent'

                col_a, col_b, col_c, col_d = st.columns([4, 1, 1, 1])
                with col_a:
                    n_contabili  = len([v for v in config.values() if v.get('tipo','contabile') == 'contabile'])
                    n_subtotali  = len([v for v in config.values() if v.get('tipo') in ('subtotale','totale')])
                    st.markdown(
                        f"<div style='background:{C['surf2']};border:1px solid {border_c};"
                        f"border-radius:10px;padding:12px 16px'>"
                        f"<b style='color:{C['text']};font-size:0.92rem'>{nome_schema}</b>"
                        f"&nbsp;&nbsp;<span style='color:{badge_clr};font-size:0.72rem;font-weight:700'>{badge}</span>"
                        f"<span style='color:{C['muted']};font-size:0.76rem;margin-left:12px'>"
                        f"{n_contabili} voci · {n_subtotali} subtotali/totali"
                        f"</span></div>",
                        unsafe_allow_html=True)
                with col_b:
                    if not is_active and st.button("Attiva", key=f"act_{nome_schema}"):
                        save_cliente({'schema_attivo': nome_schema})
                        st.rerun()
                with col_c:
                    if st.button("Copia", key=f"copy_{nome_schema}"):
                        schemi[f"{nome_schema} (copia)"] = dict(config)
                        save_cliente({'schemi': schemi})
                        st.rerun()
                with col_d:
                    if st.button("🗑️", key=f"del_{nome_schema}"):
                        del schemi[nome_schema]
                        new_att = schema_att if schema_att != nome_schema else ''
                        save_cliente({'schemi': schemi, 'schema_attivo': new_att})
                        st.rerun()
        else:
            st.info("Nessuno schema configurato. Creane uno qui sotto.")

        st.markdown("---")

        # ── CREA DA ZERO ──────────────────────────────────────────────────
        with st.expander("➕ Crea Nuovo Schema (da zero o da Schema Riclassifica caricato)"):
            with st.form("form_nuovo_schema"):
                nome_nuovo = st.text_input("Nome schema:", placeholder="es. CE Gestionale 2024")
                pre_fill   = st.checkbox("Pre-popola con le voci dello Schema Riclassifica caricato",
                                         value=True, disabled=(df_ricl is None))
                crea = st.form_submit_button("Crea Schema", type="primary")
                if crea:
                    n = nome_nuovo.strip()
                    if not n:
                        st.error("Inserisci un nome.")
                    elif n in schemi:
                        st.error("Nome già esistente.")
                    else:
                        config_init = {}
                        if pre_fill and df_ricl is not None:
                            label_map = get_label_map(df_ricl)
                            for i, (cod, desc) in enumerate(label_map.items()):
                                config_init[cod] = {
                                    'ordine': (i + 1) * 10,
                                    'tipo': 'contabile',
                                    'segno': 1,
                                    'descrizione_override': desc,
                                    'formula': '',
                                }
                        schemi[n] = config_init
                        save_cliente({'schemi': schemi, 'schema_attivo': n})
                        st.success(f"✅ Schema '{n}' creato con {len(config_init)} voci")
                        st.rerun()

        # ── IMPORT DA FILE ────────────────────────────────────────────────
        with st.expander("📥 Importa Schema da File CSV/Excel"):
            st.markdown("""
            <div style='font-size:0.82rem;color:#4A5568;margin-bottom:12px'>
            Il file deve avere queste colonne:<br>
            <b>Codice</b> · <b>Descrizione</b> · <b>Tipo</b> (contabile/subtotale/totale/separatore) ·
            <b>Segno</b> (1 o -1) · <b>Ordine</b> (opzionale)<br>
            Puoi scaricare un template qui sotto.
            </div>""", unsafe_allow_html=True)

            # Template download
            template_rows = [
                {'Codice': 'RIC001', 'Descrizione': 'Ricavi delle Vendite',    'Tipo': 'contabile',  'Segno': 1,  'Ordine': 10},
                {'Codice': 'RIC002', 'Descrizione': 'Altri Ricavi',             'Tipo': 'contabile',  'Segno': 1,  'Ordine': 20},
                {'Codice': 'TOT_RIC','Descrizione': 'TOTALE RICAVI',            'Tipo': 'subtotale',  'Segno': 1,  'Ordine': 30},
                {'Codice': 'ACQ001', 'Descrizione': 'Acquisti Materie Prime',   'Tipo': 'contabile',  'Segno': -1, 'Ordine': 40},
                {'Codice': 'PER001', 'Descrizione': 'Costi del Personale',      'Tipo': 'contabile',  'Segno': -1, 'Ordine': 50},
                {'Codice': 'EBITDA', 'Descrizione': 'EBITDA',                   'Tipo': 'subtotale',  'Segno': 1,  'Ordine': 60},
                {'Codice': 'SEP1',   'Descrizione': '',                         'Tipo': 'separatore', 'Segno': 1,  'Ordine': 70},
                {'Codice': 'AMM001', 'Descrizione': 'Ammortamenti',             'Tipo': 'contabile',  'Segno': -1, 'Ordine': 80},
                {'Codice': 'EBIT',   'Descrizione': 'EBIT',                     'Tipo': 'totale',     'Segno': 1,  'Ordine': 90},
            ]
            df_tpl = pd.DataFrame(template_rows)
            csv_tpl = df_tpl.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button("📋 Scarica template CSV", data=csv_tpl,
                               file_name="template_schema.csv", mime="text/csv")

            nome_imp = st.text_input("Nome per lo schema importato:", placeholder="es. CE Importato 2024",
                                      key="nome_import_schema")
            f_schema = st.file_uploader("Carica schema", type=["csv","xlsx","xls"],
                                         key="import_schema_file", label_visibility="collapsed")
            if f_schema and nome_imp.strip():
                df_imp = smart_load(f_schema)
                if df_imp is not None and not df_imp.empty:
                    col_cod  = find_column(df_imp, ['Codice','codice','ID','id'])
                    col_desc = find_column(df_imp, ['Descrizione','descrizione','Nome','nome'])
                    col_tipo = find_column(df_imp, ['Tipo','tipo','Type','type'])
                    col_sgn  = find_column(df_imp, ['Segno','segno','Sign','sign'])
                    col_ord  = find_column(df_imp, ['Ordine','ordine','Order','order'])
                    if not col_cod:
                        st.error(f"Colonna 'Codice' non trovata. Colonne trovate: {list(df_imp.columns)}")
                    else:
                        if st.button("✅ Conferma Import", type="primary", key="btn_imp_schema"):
                            config_imp = {}
                            for i, row in df_imp.iterrows():
                                cod  = str(row[col_cod]).strip()
                                if not cod or cod.lower() in ('nan','none'):
                                    continue
                                desc = str(row[col_desc]).strip() if col_desc else cod
                                tipo = str(row[col_tipo]).strip().lower() if col_tipo else 'contabile'
                                tipo = tipo if tipo in TIPI_VOCE else 'contabile'
                                try:
                                    segno = int(float(str(row[col_sgn]))) if col_sgn else 1
                                    segno = -1 if segno < 0 else 1
                                except Exception:
                                    segno = 1
                                try:
                                    ordine = int(float(str(row[col_ord]))) if col_ord else (i + 1) * 10
                                except Exception:
                                    ordine = (i + 1) * 10
                                config_imp[cod] = {
                                    'ordine': ordine,
                                    'tipo': tipo,
                                    'segno': segno,
                                    'descrizione_override': desc,
                                    'formula': '',
                                }
                            n = nome_imp.strip()
                            schemi[n] = config_imp
                            save_cliente({'schemi': schemi, 'schema_attivo': n})
                            st.success(f"✅ Schema '{n}' importato con {len(config_imp)} voci")
                            st.rerun()

        # ── EXPORT SCHEMA ──────────────────────────────────────────────────
        if schemi:
            with st.expander("📤 Esporta Schema Attivo"):
                schema_exp_sel = st.selectbox("Schema da esportare:", list(schemi.keys()),
                                               key="schema_exp_sel")
                if schema_exp_sel:
                    cfg_exp = schemi[schema_exp_sel]
                    rows_e = []
                    for cod, v in sorted(cfg_exp.items(), key=lambda x: x[1].get('ordine', 999)):
                        rows_e.append({
                            'Codice': cod,
                            'Descrizione': v.get('descrizione_override', cod),
                            'Tipo': v.get('tipo', 'contabile'),
                            'Segno': v.get('segno', 1),
                            'Ordine': v.get('ordine', 0),
                        })
                    df_e = pd.DataFrame(rows_e)
                    csv_e = df_e.to_csv(index=False, sep=';').encode('utf-8-sig')
                    st.download_button(f"⬇️ Esporta '{schema_exp_sel}'", data=csv_e,
                                       file_name=f"schema_{schema_exp_sel}.csv", mime="text/csv")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: CONFIGURAZIONE VOCI
    # ═══════════════════════════════════════════════════════════════════════
    with tab2:
        if not schemi:
            st.info("Crea prima uno schema nel tab 'Gestione Schemi'.")
            return

        schema_sel = st.selectbox(
            "Schema da configurare:",
            list(schemi.keys()),
            index=list(schemi.keys()).index(schema_att) if schema_att in schemi else 0,
            key="conf_schema_sel"
        )
        config    = schemi.get(schema_sel, {})
        label_map = get_label_map(df_ricl) if df_ricl is not None else {}

        # Legenda tipi
        st.markdown(f"""
        <div style='background:{C["surf2"]};border:1px solid {C["border"]};
                    border-radius:8px;padding:12px 16px;font-size:0.81rem;
                    color:{C["muted"]};margin-bottom:16px'>
        <b style='color:{C["text"]}'>Tipi di riga:</b>&nbsp;&nbsp;
        🔵 <b>Contabile</b> = somma conti mappati &nbsp;|&nbsp;
        🟡 <b>Subtotale</b> = evidenziato in grassetto (es. EBITDA) &nbsp;|&nbsp;
        🔴 <b>Totale</b> = riga totale finale &nbsp;|&nbsp;
        ⬜ <b>Separatore</b> = riga vuota di separazione<br>
        <b style='color:{C["text"]}'>Segno:</b>&nbsp;
        +1 = mantieni segno contabile &nbsp;|&nbsp; -1 = inverti (mostra costi come positivi)
        </div>""", unsafe_allow_html=True)

        if not config:
            st.info("Schema vuoto. Aggiungi voci qui sotto.")
        else:
            # Header
            border_val = C['border']
            muted_val = C['muted']
            cols_h = st.columns([1, 2, 3, 2, 1, 1])
            for col, lbl in zip(cols_h, ['Ordine', 'Codice', 'Descrizione Display', 'Tipo', 'Segno', 'Del.']):
                col.markdown(
                    "<div style='font-size:0.7rem;font-weight:700;color:" + muted_val + ";"
                    "text-transform:uppercase;letter-spacing:0.8px;padding:6px 0;"
                    "border-bottom:2px solid " + border_val + "'>" + lbl + "</div>",
                    unsafe_allow_html=True)

            config_updated = {}
            voci_ordinate  = sorted(config.keys(), key=lambda v: config[v].get('ordine', 999))

            for voce in voci_ordinate:
                cfg = config[voce]
                tipo_voce = cfg.get('tipo', 'contabile')

                # Colore riga per tipo
                tipo_colors = {
                    'contabile':  ('rgba(255,255,255,0.02)', '#64748B'),
                    'subtotale':  ('rgba(255,255,255,0.05)', '#E2E8F0'),
                    'totale':     ('rgba(201,168,76,0.10)',  '#C9A84C'),
                    'separatore': ('transparent',            '#334155'),
                }
                row_bg, row_accent = tipo_colors.get(tipo_voce, ('transparent', '#475569'))

                desc_display = cfg.get('descrizione_override') or label_map.get(voce) or voce
                config_updated[voce] = dict(cfg)

                cols = st.columns([1, 2, 3, 2, 1, 1])

                with cols[0]:
                    new_ord = st.number_input("", value=int(cfg.get('ordine', 0)), step=10,
                                               label_visibility="collapsed",
                                               key=f"ord_{schema_sel}_{voce}")
                    config_updated[voce]['ordine'] = new_ord

                with cols[1]:
                    tipo_icon = {'contabile':'🔵','subtotale':'🟡','totale':'🔴','separatore':'⬜'}.get(tipo_voce,'')
                    # Mostra descrizione (display), codice in piccolo sotto
                    st.markdown(
                        f"<div style='padding:6px 4px;'>"
                        f"<div style='font-size:0.82rem;color:{row_accent};font-weight:600'>{tipo_icon} {desc_display}</div>"
                        f"<div style='font-size:0.68rem;color:#334155;font-family:monospace'>{voce}</div>"
                        f"</div>",
                        unsafe_allow_html=True)

                with cols[2]:
                    lbl_ov = st.text_input("", value=cfg.get('descrizione_override', desc_display),
                                            label_visibility="collapsed",
                                            key=f"lbl_{schema_sel}_{voce}")
                    config_updated[voce]['descrizione_override'] = lbl_ov

                with cols[3]:
                    tipo_options = list(TIPI_VOCE.keys())
                    tipo_sel = st.selectbox("", tipo_options,
                                             index=tipo_options.index(tipo_voce) if tipo_voce in tipo_options else 0,
                                             format_func=lambda x: TIPI_VOCE[x],
                                             label_visibility="collapsed",
                                             key=f"tipo_{schema_sel}_{voce}")
                    config_updated[voce]['tipo'] = tipo_sel
                    config_updated[voce]['subtotale'] = (tipo_sel in ('subtotale', 'totale'))

                    # ── voci_include: scegli quali voci contabili sommare ──
                    if tipo_sel in ('subtotale', 'totale'):
                        voci_contabili_disponibili = [
                            k for k, v in config.items()
                            if v.get('tipo', 'contabile') == 'contabile' and k != voce
                        ]
                        cur_include = cfg.get('voci_include', [])
                        # "Tutte le precedenti" = lista vuota (default)
                        with st.expander("🔗 Voci incluse", expanded=bool(cur_include)):
                            st.caption("Lascia vuoto = somma automatica di tutte le voci precedenti")
                            sel_include = st.multiselect(
                                "Voci specifiche",
                                options=voci_contabili_disponibili,
                                default=[v for v in cur_include if v in voci_contabili_disponibili],
                                key=f"vinc_{schema_sel}_{voce}",
                                label_visibility="collapsed"
                            )
                        config_updated[voce]['voci_include'] = sel_include

                with cols[4]:
                    segno = st.selectbox("", [1, -1],
                                          index=0 if cfg.get('segno', 1) == 1 else 1,
                                          format_func=lambda x: "+1" if x == 1 else "-1",
                                          label_visibility="collapsed",
                                          key=f"sgn_{schema_sel}_{voce}",
                                          disabled=(tipo_sel == 'separatore'))
                    config_updated[voce]['segno'] = segno

                    # Ruolo KPI (solo per contabile, subtotale, totale)
                    if tipo_sel != 'separatore':
                        cur_role = cfg.get('kpi_role', '')
                        role_opts = list(KPI_ROLES.keys())
                        role_idx  = role_opts.index(cur_role) if cur_role in role_opts else 0
                        new_role  = st.selectbox(
                            "🔑 Ruolo KPI",
                            role_opts,
                            index=role_idx,
                            format_func=lambda x: KPI_ROLES.get(x, x),
                            key=f"kpirole_{schema_sel}_{voce}"
                        )
                        config_updated[voce]['kpi_role'] = new_role

                with cols[5]:
                    if st.button("✕", key=f"del_voce_{schema_sel}_{voce}", help="Rimuovi voce"):
                        schemi[schema_sel] = {k: v for k, v in config_updated.items() if k != voce}
                        save_cliente({'schemi': schemi})
                        st.rerun()

            # ── LEGENDA RUOLI KPI ──────────────────────────────────────────
            if any(config.get(v, {}).get('kpi_role') for v in config):
                st.caption("🔑 Ruoli KPI assegnati: " + " · ".join(
                    f"`{KPI_ROLES.get(config[v].get('kpi_role',''),'?')}` → {v}"
                    for v in voci_ordinate if config.get(v, {}).get('kpi_role')
                ))

            # Salva
            st.markdown("---")
            if st.button("💾 Salva Configurazione", type="primary", key="save_conf"):
                schemi[schema_sel] = config_updated
                save_cliente({'schemi': schemi, 'schema_attivo': schema_sel})
                st.success(f"✅ Schema '{schema_sel}' salvato — {len(config_updated)} voci")
                st.rerun()

        # ── AGGIUNGI VOCE ─────────────────────────────────────────────────
        st.markdown("---")
        with st.expander("➕ Aggiungi riga allo schema", expanded=(not config)):
            with st.form(f"form_add_voce_{schema_sel}"):
                c1, c2, c3, c4, c5 = st.columns(5)
                cod_v   = c1.text_input("Codice *", placeholder="es. EBITDA")
                label_v = c2.text_input("Descrizione", placeholder="es. EBITDA")
                tipo_v  = c3.selectbox("Tipo", list(TIPI_VOCE.keys()),
                                        format_func=lambda x: TIPI_VOCE[x])
                segno_v = c4.selectbox("Segno", [1, -1],
                                        format_func=lambda x: "+1" if x == 1 else "-1")
                ord_v   = c5.number_input("Ordine", value=int(
                    max([v.get('ordine', 0) for v in config.values()], default=0) + 10
                ), step=10)

                if st.form_submit_button("➕ Aggiungi voce", type="primary"):
                    cod = cod_v.strip()
                    if not cod:
                        st.error("Codice obbligatorio.")
                    elif cod in config:
                        st.error("Codice già presente.")
                    else:
                        config[cod] = {
                            'ordine': ord_v,
                            'tipo': tipo_v,
                            'segno': segno_v,
                            'kpi_role': '',
                            'subtotale': (tipo_v in ('subtotale', 'totale')),
                            'descrizione_override': label_v.strip() or cod,
                            'formula': '',
                        }
                        schemi[schema_sel] = config
                        save_cliente({'schemi': schemi})
                        st.success(f"✅ Voce '{cod}' aggiunta.")
                        st.rerun()
