"""
report_generator.py — Report HTML professionali per email e download.
Design: Bloomberg Terminal × McKinsey Deck — dark premium.
"""
from datetime import datetime


REPORT_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Playfair+Display:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --gold:    #C9A84C;
    --gold-l:  #E8C96A;
    --navy:    #0A1220;
    --blue:    #1E3A6E;
    --blue2:   #162D54;
    --surf:    #0F1923;
    --surf2:   #152030;
    --green:   #10B981;
    --red:     #EF4444;
    --amber:   #F59E0B;
    --violet:  #8B5CF6;
    --text:    #E2E8F0;
    --text-m:  #94A3B8;
    --text-s:  #64748B;
    --border:  rgba(255,255,255,0.06);
    --border2: rgba(201,168,76,0.2);
  }

  html { scroll-behavior: smooth; }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #080E18;
    color: var(--text);
    line-height: 1.65;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Layout ── */
  .report-container {
    max-width: 920px;
    margin: 0 auto;
    padding: 0 24px 60px;
  }

  /* ── Header ── */
  .report-header {
    background: linear-gradient(135deg, #060D1C 0%, #0F2040 40%, #1A3A6E 70%, #0F2040 100%);
    border-bottom: 1px solid var(--border2);
    padding: 44px 48px 40px;
    margin: 0 -24px 36px;
    position: relative;
    overflow: hidden;
  }
  .report-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%);
    border-radius: 50%;
  }
  .report-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold), transparent);
  }
  .brand-line {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 4px;
    color: var(--gold);
    font-weight: 700;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .brand-line::before { content: ''; display: block; width: 24px; height: 1px; background: var(--gold); }
  .report-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 30px;
    color: #F8FAFC;
    font-weight: 700;
    letter-spacing: -0.5px;
    line-height: 1.2;
    margin-bottom: 16px;
  }
  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    font-size: 12px;
    color: var(--text-m);
  }
  .meta-item { display: flex; align-items: center; gap: 6px; }
  .meta-item .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); }

  /* ── Sections ── */
  .section {
    background: var(--surf);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 26px 30px;
    margin-bottom: 20px;
    position: relative;
    transition: border-color 0.2s;
  }
  .section:hover { border-color: rgba(201,168,76,0.15); }
  .section-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: var(--gold);
    font-weight: 700;
    margin-bottom: 18px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(201,168,76,0.15);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-title .icon { font-size: 14px; }

  h2, h3, h4 { color: var(--text); font-weight: 600; }
  h2 { font-size: 17px; margin: 18px 0 10px; }
  h3 { font-size: 14px; margin: 14px 0 8px; }
  p  { color: var(--text-m); font-size: 13.5px; margin-bottom: 12px; line-height: 1.75; }
  ul, ol { padding-left: 20px; }
  li { color: var(--text-m); font-size: 13.5px; margin-bottom: 6px; line-height: 1.65; }
  strong { color: var(--text); font-weight: 600; }
  em { color: var(--gold-l); font-style: normal; font-weight: 500; }

  /* ── KPI Grid ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 14px;
    margin: 18px 0;
  }
  .kpi-card {
    background: var(--surf2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    border-top: 3px solid var(--gold);
    position: relative;
    overflow: hidden;
  }
  .kpi-card::after {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 60px; height: 60px;
    background: radial-gradient(circle at top right, rgba(201,168,76,0.06), transparent);
  }
  .kpi-card.green { border-top-color: var(--green); }
  .kpi-card.red   { border-top-color: var(--red);   }
  .kpi-card.blue  { border-top-color: #3B82F6;       }
  .kpi-card.purple{ border-top-color: var(--violet); }
  .kpi-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-s); font-weight: 600; margin-bottom: 6px; }
  .kpi-value { font-size: 23px; font-weight: 700; color: #F8FAFC; letter-spacing: -0.8px; line-height: 1; }
  .kpi-delta { font-size: 11.5px; margin-top: 6px; font-weight: 500; }
  .kpi-delta.pos { color: var(--green); }
  .kpi-delta.neg { color: var(--red);   }
  .kpi-delta.neu { color: var(--text-s); }
  .kpi-benchmark { font-size: 10.5px; color: var(--text-s); margin-top: 3px; }

  /* ── Alerts ── */
  .alert {
    border-radius: 8px;
    padding: 13px 16px;
    margin: 10px 0;
    font-size: 13px;
    line-height: 1.6;
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }
  .alert-icon { font-size: 16px; flex-shrink: 0; margin-top: 1px; }
  .alert.red    { background: rgba(239,68,68,0.07);  border-left: 3px solid var(--red);   }
  .alert.yellow { background: rgba(245,158,11,0.07); border-left: 3px solid var(--amber); }
  .alert.green  { background: rgba(16,185,129,0.07); border-left: 3px solid var(--green); }
  .alert.blue   { background: rgba(59,130,246,0.07); border-left: 3px solid #3B82F6;      }
  .alert p { margin: 0; color: var(--text-m); }
  .alert strong { color: var(--text); }

  /* ── Tables ── */
  .table-wrapper { overflow-x: auto; margin: 14px 0; border-radius: 8px; border: 1px solid var(--border); }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  thead tr { background: rgba(30,58,110,0.6); }
  th {
    padding: 10px 14px;
    text-align: right;
    color: var(--text-s);
    font-weight: 500;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    white-space: nowrap;
  }
  th:first-child { text-align: left; }
  td {
    padding: 9px 14px;
    text-align: right;
    color: var(--text-m);
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }
  td:first-child { text-align: left; font-family: 'Inter', sans-serif; color: var(--text-s); font-size: 12.5px; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  tr.total td { background: rgba(201,168,76,0.06); color: var(--gold-l) !important; font-weight: 700; border-top: 1px solid rgba(201,168,76,0.2); }
  .td-pos { color: var(--green) !important; font-weight: 600; }
  .td-neg { color: var(--red)   !important; font-weight: 600; }
  .td-muted { color: var(--text-s) !important; }

  /* ── Action items ── */
  .action-list { display: flex; flex-direction: column; gap: 0; }
  .action-item {
    display: flex;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
    align-items: flex-start;
  }
  .action-item:last-child { border-bottom: none; }
  .action-badge {
    min-width: 80px;
    padding: 4px 10px;
    border-radius: 5px;
    font-size: 9.5px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    text-align: center;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .badge-urgent { background: rgba(239,68,68,0.12);  color: var(--red);   border: 1px solid rgba(239,68,68,0.25); }
  .badge-short  { background: rgba(245,158,11,0.12); color: var(--amber); border: 1px solid rgba(245,158,11,0.25); }
  .badge-medium { background: rgba(59,130,246,0.12); color: #60A5FA;      border: 1px solid rgba(59,130,246,0.25); }
  .action-text { flex: 1; }
  .action-title { font-weight: 600; color: var(--text); font-size: 13.5px; margin-bottom: 4px; }
  .action-impact { color: var(--green); font-size: 11.5px; font-weight: 600; margin-bottom: 4px; }
  .action-desc { color: var(--text-m); font-size: 12.5px; line-height: 1.6; }

  /* ── Scenario grid ── */
  .scenario-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 14px;
    margin: 16px 0;
  }
  .scenario-card {
    background: var(--surf2);
    border-radius: 10px;
    padding: 18px 16px;
    text-align: center;
    border: 1px solid var(--border);
  }
  .scenario-base { border-top: 3px solid #3B82F6; }
  .scenario-opt  { border-top: 3px solid var(--green); }
  .scenario-pess { border-top: 3px solid var(--red); }
  .s-label { font-size: 9.5px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-s); margin-bottom: 8px; font-weight: 600; }
  .s-prob  { font-size: 10px; color: var(--text-s); margin-bottom: 4px; }
  .s-value { font-size: 20px; font-weight: 700; margin-bottom: 8px; letter-spacing: -0.5px; }
  .s-note  { font-size: 11px; color: var(--text-s); line-height: 1.5; }

  /* ── Risk matrix ── */
  .risk-item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 11px 14px;
    border-radius: 8px;
    margin-bottom: 8px;
    border: 1px solid var(--border);
  }
  .risk-high   { background: rgba(239,68,68,0.04);  }
  .risk-medium { background: rgba(245,158,11,0.04); }
  .risk-low    { background: rgba(16,185,129,0.04); }
  .risk-badge { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 2px 8px; border-radius: 3px; flex-shrink: 0; margin-top: 3px; }
  .badge-high   { background: rgba(239,68,68,0.15);  color: var(--red);   }
  .badge-medium { background: rgba(245,158,11,0.15); color: var(--amber); }
  .badge-low    { background: rgba(16,185,129,0.15); color: var(--green); }

  /* ── Divider & misc ── */
  hr { border: none; border-top: 1px solid var(--border); margin: 22px 0; }
  code { font-family: 'JetBrains Mono', monospace; background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px; font-size: 12px; color: #C9A84C; }
  .muted { color: var(--text-s); }
  .gold  { color: var(--gold-l); }
  .green { color: var(--green); }
  .red   { color: var(--red); }

  /* ── Highlight bar ── */
  .highlight-bar {
    display: flex;
    gap: 0;
    border-radius: 8px;
    overflow: hidden;
    margin: 14px 0;
  }
  .hb-item { flex: 1; padding: 14px 16px; }
  .hb-label { font-size: 9.5px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-s); margin-bottom: 4px; font-weight: 600; }
  .hb-value { font-size: 18px; font-weight: 700; color: var(--text); }

  /* ── Footer ── */
  .report-footer {
    margin-top: 48px;
    padding: 20px 0 0;
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: var(--text-s);
  }
  .footer-brand { font-weight: 600; color: var(--text-m); }
  .footer-conf { background: rgba(201,168,76,0.08); padding: 3px 10px; border-radius: 4px; font-size: 9.5px; text-transform: uppercase; letter-spacing: 1px; color: var(--gold); }

  /* ── Print ── */
  @media print {
    body { background: white; color: #1a1a1a; }
    .report-header { background: #1E3A6E; }
    .section { border: 1px solid #e2e8f0; background: white; }
  }
</style>
"""


def wrap_report(content_html: str, title: str, cliente: str, tipo: str, periodo: str) -> str:
    """Avvolge il contenuto HTML nel template completo del report."""
    now = datetime.now().strftime('%d %B %Y, %H:%M')
    now_short = datetime.now().strftime('%d/%m/%Y')
    return f"""<!DOCTYPE html>
<html lang="it" dir="ltr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{title} — {cliente}">
  <title>{title} · {cliente} · AI-Manager</title>
  {REPORT_CSS}
</head>
<body>
  <div class="report-container">

    <div class="report-header">
      <div class="brand-line">AI-Manager · Virtual CFO Platform · Confidenziale</div>
      <h1 class="report-title">{title}</h1>
      <div class="meta-row">
        <div class="meta-item"><div class="dot"></div><span>🏢 {cliente}</span></div>
        <div class="meta-item"><div class="dot"></div><span>📅 Periodo: {periodo}</span></div>
        <div class="meta-item"><div class="dot"></div><span>📊 {tipo}</span></div>
        <div class="meta-item"><div class="dot"></div><span>⏱ Generato il {now}</span></div>
      </div>
    </div>

    {content_html}

    <div class="report-footer">
      <div>
        <span class="footer-brand">AI-Manager</span> · Piattaforma di Controllo di Gestione · {now_short}
      </div>
      <div class="footer-conf">Documento Confidenziale</div>
    </div>

  </div>
</body>
</html>"""


def format_ce_for_prompt(pivot, mesi_sel: list, include_totale: bool = True) -> str:
    """Formatta il CE come testo strutturato per il prompt AI."""
    if pivot is None:
        return "Dati CE non disponibili"
    cols = [c for c in mesi_sel if c in pivot.columns]
    if not cols:
        cols = [c for c in pivot.columns if c != 'TOTALE']
    if not cols:
        return "Nessun dato mensile"

    lines = []
    col_header = " | ".join(f"{c:>10}" for c in cols)
    lines.append(f"{'Voce CE':<38} | {col_header} | {'TOTALE':>10}")
    lines.append("─" * (38 + 14 * len(cols) + 14))

    for voce in pivot.index:
        row_vals = []
        for c in cols:
            v = float(pivot.loc[voce, c]) if c in pivot.columns else 0
            row_vals.append(f"{v:>10,.0f}")
        totale = sum(float(pivot.loc[voce, c]) for c in cols if c in pivot.columns)
        val_str = " | ".join(row_vals)
        tot_str = f"{totale:>10,.0f}" if include_totale else ""
        lines.append(f"{str(voce):<38} | {val_str} | {tot_str}")

    return "\n".join(lines)


def format_kpi_for_prompt(kpi: dict) -> str:
    """Formatta KPI come testo strutturato per il prompt AI."""
    if not kpi:
        return "KPI non disponibili"
    lines = []
    label_map = {
        'ricavi':           ('Ricavi netti',            '€',  ','),
        'ebitda':           ('EBITDA',                  '€',  ','),
        'ebit':             ('EBIT',                    '€',  ','),
        'utile_netto':      ('Utile netto',              '€',  ','),
        'costi_personale':  ('Costi personale',          '€',  ','),
        'ebitda_margin':    ('Margine EBITDA',           '%',  '.1f'),
        'ebit_margin':      ('Margine EBIT',             '%',  '.1f'),
        'net_margin':       ('Margine netto',            '%',  '.1f'),
        'gross_margin':     ('Margine lordo',            '%',  '.1f'),
        'cost_labor_pct':   ('Costo personale/Ricavi',  '%',  '.1f'),
        'ricavi_mensili_avg': ('Media mensile ricavi',   '€', ','),
        'ebitda_mensile_avg': ('Media mensile EBITDA',   '€', ','),
    }
    for k, (label, unit, fmt) in label_map.items():
        if k in kpi and kpi[k] is not None:
            v = kpi[k]
            if unit == '%':
                val_str = f"{v:.1f}%"
            else:
                val_str = f"{v:,.0f} €"
            lines.append(f"  {label:<30}: {val_str}")
    return "\n".join(lines) if lines else "KPI non calcolabili"


def format_budget_variance_for_prompt(pivot, budget: dict, mesi_sel: list) -> str:
    """Formatta confronto Budget vs Effettivo per il prompt AI."""
    if not budget:
        return ""
    lines = [
        f"{'Voce':<35} | {'Effettivo':>12} | {'Budget':>12} | {'Scostam.':>10} | {'Scost.%':>7}"
    ]
    lines.append("─" * 85)
    for voce in pivot.index:
        if voce not in budget:
            continue
        eff = sum(float(pivot.loc[voce, m]) for m in mesi_sel if m in pivot.columns)
        bud = sum(budget[voce].get(m, 0) for m in mesi_sel)
        if bud == 0:
            continue
        scost = eff - bud
        pct   = scost / abs(bud) * 100
        flag  = "🟢 F" if pct >= 0 else "🔴 U"
        lines.append(
            f"{str(voce)[:35]:<35} | {eff:>12,.0f} | {bud:>12,.0f} | "
            f"{scost:>+10,.0f} | {pct:>+6.1f}% {flag}"
        )
    return "\n".join(lines)
