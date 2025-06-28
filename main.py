import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import time
import pdfkit
from playwright.sync_api import sync_playwright

# --- Cargar variables de entorno ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass  # Ignora si dotenv no está disponible (funciona igual en GitHub)

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
EMAIL_TO = os.environ.get("EMAIL_TO")
HISTORIAL_ARCHIVO = "ultima_url.txt"

# Verificar variables
if not all([GMAIL_USER, GMAIL_PASS, EMAIL_TO]):
    raise EnvironmentError("Faltan variables de entorno: GMAIL_USER, GMAIL_PASS o EMAIL_TO")

def obtener_url_market_wrap():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.bloomberg.com/markets", timeout=60000)
        page.wait_for_timeout(5000)

        # Buscar bloques que contengan "Markets Wrap"
        bloques = page.locator("div:has-text('Markets Wrap')").all()
        print(f"Se encontraron {len(bloques)} bloques con 'Markets Wrap'")

        for bloque in bloques:
            try:
                # Buscar un <a> dentro del mismo bloque
                enlace = bloque.locator("a").first
                href = enlace.get_attribute("href")
                if href and href.startswith("/news/articles/"):
                    browser.close()
                    return "https://www.bloomberg.com" + href
            except Exception as e:
                print(f"Error al buscar enlace: {e}")
                continue

        browser.close()
    return None

def archivar_url(url):
    print("Enviando URL a archive.ph...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://archive.ph/"
    }

    try:
        res = requests.post("https://archive.ph/submit/", data={"url": url}, headers=headers, timeout=60)
        time.sleep(20)
        with open("respuesta_archiveph.html", "w", encoding="utf-8") as f:
            f.write(res.text)

        soup = BeautifulSoup(res.text, "html.parser")
        link_input = soup.find("input", {"id": "SHARE_LONGLINK"})
        if link_input:
            return link_input.get("value")
        meta_tag = soup.find("meta", {"property": "og:url"})
        if meta_tag:
            return meta_tag.get("content")

    except Exception as e:
        print(f"Error al archivar: {e}")
    return None

def descargar_pdf(archive_url, nombre_pdf="market_wrap.pdf"):
    try:
        pdfkit.from_url(archive_url, nombre_pdf)
        return nombre_pdf
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        return None

def enviar_email(original, archivado, pdf_path):
    msg = EmailMessage()
    msg['Subject'] = "Market Wrap Bloomberg Diario"
    msg['From'] = GMAIL_USER
    msg['To'] = EMAIL_TO

    contenido = f"""
    Hola,

    Aquí tienes el artículo Market Wrap de Bloomberg de hoy.

    Enlace original:
    {original}

    Enlace archivado:
    {archivado}

    Se adjunta el PDF del artículo.

    Saludos,
    Tu bot automático
    """
    msg.set_content(contenido)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print("Correo enviado con éxito.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

def url_ya_enviada(url):
    if os.path.exists(HISTORIAL_ARCHIVO):
        with open(HISTORIAL_ARCHIVO, "r") as f:
            return url == f.read().strip()
    return False

def guardar_url(url):
    with open(HISTORIAL_ARCHIVO, "w") as f:
        f.write(url)

def main():
    url = obtener_url_market_wrap()
    if not url:
        print("No se encontró el artículo Market Wrap.")
        return

    if url_ya_enviada(url):
        print("Esta URL ya fue enviada anteriormente.")
        return

    print(f"Artículo encontrado: {url}")
    archivado = archivar_url(url)
    if not archivado:
        print("No se pudo archivar la URL.")
        return

    print(f"URL archivada: {archivado}")
    pdf_path = descargar_pdf(archivado)

    if pdf_path:
        enviar_email(url, archivado, pdf_path)
        guardar_url(url)
    else:
        print("No se pudo generar el PDF.")

if __name__ == "__main__":
    main()
