import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import time

# --- Configuración desde variables de entorno ---
GMAIL_USER = os.getenv("GMAIL_USER")   # Tu correo Gmail para enviar emails
GMAIL_PASS = os.getenv("GMAIL_PASS")   # Contraseña de aplicación de Gmail
EMAIL_TO = os.getenv("EMAIL_TO")       # Correo destinatario que recibirá el email

def obtener_url_market_wrap():
    url = "https://www.bloomberg.com/markets"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")

    for a in soup.find_all("a", href=True):
        texto = a.get_text(strip=True).lower()
        href = a["href"]
        if "market wrap" in texto:
            if href.startswith("/news/articles/"):
                return "https://www.bloomberg.com" + href
    return None

def archivar_url(url):
    archive_url = f"https://archive.ph/?run=1&url={url}"
    time.sleep(15)  # Espera para que archive.ph procese el archivado
    return archive_url

def enviar_email(original, archivado):
    msg = EmailMessage()
    msg['Subject'] = "Market Wrap Bloomberg Diario"
    msg['From'] = GMAIL_USER
    msg['To'] = EMAIL_TO

    contenido = f"""
    Hola,

    Aquí tienes el artículo Market Wrap de Bloomberg de hoy:

    Artículo Original:
    {original}

    Artículo Archivado (sin muro de pago):
    {archivado}

    Saludos,
    Tu bot automático
    """
    msg.set_content(contenido)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.send_message(msg)

def main():
    url = obtener_url_market_wrap()
    if url:
        print(f"Artículo encontrado: {url}")
        archivada = archivar_url(url)
        print(f"URL archivada: {archivada}")
        enviar_email(url, archivada)
        print("Correo enviado con éxito.")
    else:
        print("No se encontró artículo Market Wrap.")

if __name__ == "__main__":
    main()
