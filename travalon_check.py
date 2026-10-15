#!/usr/bin/env python3
"""
Una sola pasada: busca menciones de "travalón" y avisa por Telegram de las NUEVAS.
Pensado para ejecutarse cada pocos minutos en GitHub Actions (sin ordenador propio).

Lee TELEGRAM_TOKEN y TELEGRAM_CHAT_ID de variables de entorno (Secrets de GitHub).
NO pongas el token dentro de este archivo.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEEN_FILE = Path(__file__).with_name("travalon_seen.json")

QUERY = '"travalón" OR "travalon"'
q = urllib.parse.quote(QUERY)
FEEDS = {
    "Google News": f"https://news.google.com/rss/search?q={q}&hl=es&gl=ES&ceid=ES:es",
    "Bing News": f"https://www.bing.com/news/search?q={q}&format=rss&setlang=es",
    "Alicante Plaza": "https://alicanteplaza.es/rss/?i=51&dominio=alicanteplaza.es",
}
UA = {"User-Agent": "Mozilla/5.0 (compatible; TravalonBot/1.0)"}


def http_get(url, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def leer_feed(nombre, url):
    try:
        root = ET.fromstring(http_get(url))
    except Exception as e:
        print(f"[aviso] {nombre} falló: {e}", file=sys.stderr)
        return []
    items = []
    for it in root.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        enlace = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or enlace or titulo).strip()
        if titulo and enlace:
            items.append((guid, titulo, enlace, nombre))
    return items


def enviar(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    datos = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": texto}).encode()
    http_get(url, data=datos)


def main():
    if not TOKEN or not CHAT_ID:
        sys.exit("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID.")

    primera_vez = not SEEN_FILE.exists()
    vistos = set() if primera_vez else set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))

    nuevos = []
    for nombre, url in FEEDS.items():
        for guid, titulo, enlace, fuente in leer_feed(nombre, url):
            if guid not in vistos:
                vistos.add(guid)
                nuevos.append((titulo, enlace, fuente))

    if primera_vez:
        enviar("✅ Bot activo. Te avisaré de nuevas menciones de «travalón».")
        print(f"Línea base: {len(vistos)} resultados existentes ignorados.")
    else:
        for titulo, enlace, fuente in nuevos:
            enviar(f"🔔 Nueva mención de travalón ({fuente})\n\n{titulo}\n{enlace}")
        print(f"{len(nuevos)} avisos enviados.")

    SEEN_FILE.write_text(json.dumps(sorted(vistos)), encoding="utf-8")


if __name__ == "__main__":
    main()
