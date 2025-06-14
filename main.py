import os
import smtplib
from email.message import EmailMessage

# --- Variables de entorno (desde GitHub Secrets o .env local) ---
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

def enviar_email_prueba():
    msg = EmailMessage()
    msg['Subject'] = "✅ Prueba de Envío de Email desde GitHub Actions"
    msg['From'] = GMAIL_USER
    msg['To'] = EMAIL_TO

    contenido = """
    Hola,

    Este es un correo de prueba enviado automáticamente desde GitHub Actions.

    Si recibes este mensaje, la configuración de SMTP y Secrets funciona correctamente.

    ¡Saludos!
    """
    msg.set_content(contenido)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.send_message(msg)

    print("✅ Correo enviado con éxito.")

if __name__ == "__main__":
    enviar_email_prueba()
