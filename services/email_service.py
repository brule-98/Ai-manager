"""
email_service.py — Invio report via email (SMTP).
Supporta Gmail, Outlook, e server SMTP custom.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime


PROVIDER_PRESETS = {
    'Gmail':   {'host': 'smtp.gmail.com',   'port': 587, 'tls': True},
    'Outlook': {'host': 'smtp.office365.com', 'port': 587, 'tls': True},
    'Yahoo':   {'host': 'smtp.mail.yahoo.com', 'port': 587, 'tls': True},
    'Custom':  {'host': '',                  'port': 587, 'tls': True},
}


def send_report_email(
    smtp_config: dict,
    destinatari: list,
    oggetto: str,
    body_html: str,
    allegato_html: str = None,
    allegato_nome: str = "report.html",
    cc: list = None
) -> tuple[bool, str]:
    """
    Invia report HTML via email.

    smtp_config: {host, port, tls, user, password}
    Returns: (success: bool, message: str)
    """
    if not destinatari:
        return False, "Nessun destinatario specificato."
    if not smtp_config.get('user') or not smtp_config.get('password'):
        return False, "Credenziali SMTP non configurate."
    if not smtp_config.get('host'):
        return False, "Host SMTP non configurato."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = oggetto
        msg['From']    = smtp_config['user']
        msg['To']      = ', '.join(destinatari)
        if cc:
            msg['Cc']  = ', '.join(cc)

        # Plain text fallback
        plain = "Questo report è ottimizzato per client email che supportano HTML."
        msg.attach(MIMEText(plain, 'plain', 'utf-8'))
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        # Allegato HTML opzionale
        if allegato_html:
            att = MIMEApplication(allegato_html.encode('utf-8'), Name=allegato_nome)
            att['Content-Disposition'] = f'attachment; filename="{allegato_nome}"'
            msg.attach(att)

        # Connessione SMTP
        tutti = destinatari + (cc or [])
        with smtplib.SMTP(smtp_config['host'], int(smtp_config.get('port', 587))) as server:
            server.ehlo()
            if smtp_config.get('tls', True):
                server.starttls()
                server.ehlo()
            server.login(smtp_config['user'], smtp_config['password'])
            server.sendmail(smtp_config['user'], tutti, msg.as_string())

        return True, f"Email inviata a {', '.join(destinatari)}"

    except smtplib.SMTPAuthenticationError:
        return False, "Autenticazione SMTP fallita. Verifica user/password. Per Gmail usa App Password."
    except smtplib.SMTPConnectError:
        return False, f"Impossibile connettersi a {smtp_config.get('host')}:{smtp_config.get('port')}."
    except Exception as e:
        return False, f"Errore invio: {str(e)}"


def build_email_body(
    cliente: str,
    tipo_report: str,
    periodo: str,
    summary_html: str,
    sender_name: str = "AI-Manager"
) -> str:
    """Crea il body HTML dell'email (preview del report)."""
    now = datetime.now().strftime('%d/%m/%Y')
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:#f8f9fb; margin:0; padding:0; }}
    .wrapper {{ max-width:680px; margin:0 auto; }}
    .header {{ background:linear-gradient(135deg,#0F2044,#1A3A7A); padding:28px 36px; }}
    .header h2 {{ color:white; margin:0; font-size:20px; font-weight:600; }}
    .header p  {{ color:#90AEE8; margin:6px 0 0 0; font-size:13px; }}
    .content {{ background:white; padding:28px 36px; }}
    .badge {{ display:inline-block; background:#EEF2FF; color:#1A3A7A; padding:4px 12px;
              border-radius:4px; font-size:12px; font-weight:600; margin-bottom:16px; }}
    .divider {{ border:none; border-top:1px solid #E2E8F0; margin:20px 0; }}
    .footer {{ background:#F8F9FB; padding:16px 36px; font-size:11px; color:#9CA3AF;
               border-top:1px solid #E2E8F0; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h2>📊 {tipo_report}</h2>
      <p>{cliente} · {periodo} · Generato il {now}</p>
    </div>
    <div class="content">
      <div class="badge">{tipo_report}</div>
      {summary_html}
      <hr class="divider">
      <p style="font-size:12px;color:#9CA3AF;">
        Il report completo è disponibile in allegato.<br>
        Questo messaggio è stato generato automaticamente da <strong>AI-Manager</strong>
        su richiesta del tuo CFO virtuale.
      </p>
    </div>
    <div class="footer">
      <p>AI-Manager · Piattaforma di Controllo di Gestione · {now}</p>
      <p>Non rispondere a questa email. Per supporto: usa la piattaforma AI-Manager.</p>
    </div>
  </div>
</body>
</html>"""


def validate_smtp_config(config: dict) -> tuple[bool, str]:
    """Testa la connessione SMTP senza inviare email."""
    if not config.get('host'):
        return False, "Host SMTP mancante"
    if not config.get('user') or not config.get('password'):
        return False, "Credenziali mancanti"
    try:
        with smtplib.SMTP(config['host'], int(config.get('port', 587)), timeout=10) as s:
            s.ehlo()
            if config.get('tls', True):
                s.starttls()
                s.ehlo()
            s.login(config['user'], config['password'])
        return True, "Connessione SMTP OK ✅"
    except smtplib.SMTPAuthenticationError:
        return False, "Autenticazione fallita. Per Gmail usa una App Password (non la password normale)."
    except Exception as e:
        return False, f"Connessione fallita: {e}"
