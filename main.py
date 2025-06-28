import os
import smtplib
from email.message import EmailMessage
import time
import pdfkit
from playwright.sync_api import sync_playwright, TimeoutError
import requests
from bs4 import BeautifulSoup # Se necesita para la función de archivar

# --- Cargar variables de entorno ---
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Variables de entorno cargadas desde .env")
except ImportError:
    print("dotenv no instalado, se usarán las variables del sistema (ideal para GitHub Actions).")
    pass

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_PASS = os.environ.get("GMAIL_PASS")
EMAIL_TO = os.environ.get("EMAIL_TO")
HISTORIAL_ARCHIVO = "ultima_url.txt"

if not all([GMAIL_USER, GMAIL_PASS, EMAIL_TO]):
    raise EnvironmentError("CRÍTICO: Faltan variables de entorno: GMAIL_USER, GMAIL_PASS o EMAIL_TO")

# ==============================================================================
# FUNCIÓN DE BÚSQUEDA MEJORADA (ANTI-BANNERS)
# ==============================================================================
def obtener_url_market_wrap():
    url_bloomberg = "https://www.bloomberg.com/markets"
    print(f"Accediendo a {url_bloomberg} con Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url_bloomberg, timeout=90000, wait_until='domcontentloaded')

            # --- NUEVO: INTENTO DE CERRAR BANNER DE COOKIES ---
            print("Buscando banner de cookies para cerrarlo...")
            try:
                # Bloomberg usa varios textos. Intentamos con los más comunes.
                # 'button:has-text("Accept")' o similar. El selector de abajo es para Bloomberg.
                banner_button_selector = 'button[id="truste-consent-button"]'
                # Esperamos un máximo de 7 segundos a que aparezca el botón
                page.locator(banner_button_selector).wait_for(state='visible', timeout=7000)
                page.click(banner_button_selector)
                print("Banner de cookies encontrado y cerrado.")
                # Esperar un poco a que la página se reajuste tras cerrar el banner
                time.sleep(3)
            except TimeoutError:
                print("No se encontró un banner de cookies (o ya estaba aceptado). Continuando...")
            except Exception as e:
                print(f"Error menor al intentar cerrar banner: {e}. Continuando de todas formas.")

            # --- BÚSQUEDA DEL ARTÍCULO ---
            selector_articulo = 'a:has-text("Markets Wrap")'
            print(f"Buscando el artículo con el selector: '{selector_articulo}'")
            
            link_element = page.locator(selector_articulo).first
            link_element.wait_for(state='visible', timeout=20000) # Aumentamos un poco el timeout
            
            href = link_element.get_attribute("href")
            
            if href and "/news/articles/" in href:
                enlace_completo = "https://www.bloomberg.com" + href if href.startswith("/") else href
                print(f"¡Éxito! Artículo encontrado: {enlace_completo}")
                browser.close()
                return enlace_completo
            else:
                print("Elemento encontrado, pero su 'href' no es un artículo válido.")

        except TimeoutError:
            print("Error de TIMEOUT: La página tardó mucho en cargar o el selector del ARTÍCULO no encontró nada.")
            page.screenshot(path='screenshot_error_timeout.png')
            print("Se guardó una captura de pantalla del error en 'screenshot_error_timeout.png' para depuración.")
        except Exception as e:
            print(f"Ocurrió un error inesperado con Playwright: {e}")
            page.screenshot(path='screenshot_error_general.png')
            print("Se guardó una captura de pantalla del error en 'screenshot_error_general.png' para depuración.")
        
        browser.close()
        print("Búsqueda finalizada. No se pudo encontrar el artículo Market Wrap.")
        return None

# ==============================================================================
# OTRAS FUNCIONES (sin cambios)
# ==============================================================================
def archivar_url(url):
    print(f"Enviando URL a archive.ph para archivar: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        res = requests.post("https://archive.ph/submit/", data={"url": url}, headers=headers, timeout=60, allow_redirects=True)
        if res.history:
            url_archivada = res.url
            print(f"URL archivada detectada por redirección: {url_archivada}")
            return url_archivada
        else:
            soup = BeautifulSoup(res.text, "html.parser")
            meta_tag = soup.find("meta", {"property": "og:url"})
            if meta_tag and meta_tag.get("content"):
                 url_archivada = meta_tag.get("content")
                 print(f"URL archivada encontrada en meta tag: {url_archivada}")
                 return url_archivada
    except Exception as e:
        print(f"Error al archivar la URL: {e}")
    return None

def descargar_pdf(archive_url, nombre_pdf="market_wrap.pdf"):
    print(f"Descargando PDF desde: {archive_url}")
    try:
        options = {'page-size': 'A4', 'margin-top': '0.75in', 'margin-right': '0.75in', 'margin-bottom': '0.75in', 'margin-left': '0.75in', 'encoding': "UTF-8", 'no-outline': None, 'enable-smart-shrinking': '', 'javascript-delay': 2000}
        pdfkit.from_url(archive_url, nombre_pdf, options=options)
        print(f"PDF generado con éxito: {nombre_pdf}")
        return nombre_pdf
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        return None

def enviar_email(original, archivado, pdf_path):
    print("Preparando el correo electrónico...")
    msg = EmailMessage()
    msg['Subject'] = "Bloomberg Markets Wrap Diario"
    msg['From'] = GMAIL_USER
    msg['To'] = EMAIL_TO
    contenido = f"Hola,\n\nAquí tienes el resumen \"Markets Wrap\" de Bloomberg de hoy.\n\nEnlace original (puede caducar o requerir suscripción):\n{original}\n\nEnlace archivado (permanente y de libre acceso):\n{archivado}\n\nSe adjunta el artículo completo en formato PDF para tu comodidad.\n\nSaludos,\nTu Asistente Automático"
    msg.set_content(contenido)
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))
        print("PDF adjuntado al correo.")
    else:
        print("Advertencia: No se encontró el archivo PDF para adjuntar.")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print("Correo electrónico enviado con éxito.")
    except Exception as e:
        print(f"Error CRÍTICO al enviar el correo: {e}")

def url_ya_enviada(url):
    if not os.path.exists(HISTORIAL_ARCHIVO): return False
    with open(HISTORIAL_ARCHIVO, "r") as f:
        return url == f.read().strip()

def guardar_url(url):
    with open(HISTORIAL_ARCHIVO, "w") as f: f.write(url)
    print(f"URL actualizada en el historial: {url}")

def main():
    print("\n--- INICIANDO SCRIPT DE BLOOMBERG WRAP ---")
    url_original = obtener_url_market_wrap()
    if not url_original:
        print("--- SCRIPT FINALIZADO: No se encontró artículo. ---")
        return
    if url_ya_enviada(url_original):
        print("Este artículo ya fue procesado y enviado anteriormente.\n--- SCRIPT FINALIZADO: Sin novedades. ---")
        return
    print(f"Artículo nuevo encontrado: {url_original}")
    url_archivada = archivar_url(url_original)
    if not url_archivada:
        print("No se pudo archivar la URL.\n--- SCRIPT FINALIZADO: Fallo en el archivado. ---")
        return
    print("Esperando 10 segundos para que el enlace archivado se propague...")
    time.sleep(10)
    pdf_path = descargar_pdf(url_archivada)
    if not pdf_path: print("No se pudo generar el PDF. El correo se enviará sin el adjunto.")
    enviar_email(url_original, url_archivada, pdf_path)
    guardar_url(url_original)
    print("--- SCRIPT COMPLETADO CON ÉXITO ---")

if __name__ == "__main__":
    main()
