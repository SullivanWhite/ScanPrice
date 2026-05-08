from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
import re

app = Flask(__name__, static_folder=".")
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DATA_FILE = "productos.json"


def cargar_productos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_productos(productos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)


def limpiar_precio(texto):
    texto = re.sub(r"[^\d,\.]", "", texto.strip())
    texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def scrape_goblintrader(url, soup):
    # Precio en GoblinTrader
    precio_tag = soup.find("span", class_="price")
    if not precio_tag:
        precio_tag = soup.find("p", class_="price")
    if not precio_tag:
        precio_tag = soup.find(class_=re.compile(r"price"))
    if precio_tag:
        texto = precio_tag.get_text()
        return limpiar_precio(texto)
    return None


def scrape_dungeonmarvels(url, soup):
    precio_tag = soup.find("span", itemprop="price")
    if precio_tag:
        content = precio_tag.get("content")
        if content:
            return limpiar_precio(content)
        return limpiar_precio(precio_tag.get_text())
    return None


def scrape_mathom(url, soup):
    # Selector confirmado manualmente: span.current-price-value con atributo content="XX.XX"
    # Mathom usa PrestaShop, no WooCommerce
    precio_tag = soup.find("span", class_="current-price-value")
    if precio_tag:
        # El precio está limpio en el atributo content, sin símbolos ni formato
        content = precio_tag.get("content")
        if content:
            return limpiar_precio(content)
        # Fallback: leer el texto visible
        return limpiar_precio(precio_tag.get_text())
    return None


def obtener_precio(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        # Nombre del producto
        nombre = None
        og_title = soup.find("meta", property="og:title")
        if og_title:
            nombre = og_title.get("content", "").strip()
        elif soup.find("h1"):
            nombre = soup.find("h1").get_text().strip()

        # Imagen del producto
        imagen = None
        og_img = soup.find("meta", property="og:image")
        if og_img:
            imagen = og_img.get("content", "").strip()

        # Scraper por tienda
        precio = None
        tienda = "desconocida"

        if "goblintrader" in url:
            precio = scrape_goblintrader(url, soup)
            tienda = "GoblinTrader"
        elif "dungeonmarvels" in url:
            precio = scrape_dungeonmarvels(url, soup)
            tienda = "Dungeon Marvels"
        elif "mathom" in url:
            precio = scrape_mathom(url, soup)
            tienda = "Mathom"

        return {
            "precio": precio,
            "nombre_scrapeado": nombre,
            "imagen": imagen,
            "tienda": tienda,
            "ok": precio is not None
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "precio": None}


# ── API endpoints ──────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "URL vacía"})
    resultado = obtener_precio(url)
    return jsonify(resultado)


@app.route("/api/productos", methods=["GET"])
def get_productos():
    return jsonify(cargar_productos())


@app.route("/api/productos", methods=["POST"])
def add_producto():
    producto = request.json
    productos = cargar_productos()
    # Evitar duplicados por URL
    for p in productos:
        if p["url"] == producto["url"]:
            return jsonify({"ok": False, "error": "Producto ya existe"})
    productos.append(producto)
    guardar_productos(productos)
    return jsonify({"ok": True})


@app.route("/api/productos/<int:idx>", methods=["DELETE"])
def delete_producto(idx):
    productos = cargar_productos()
    if 0 <= idx < len(productos):
        eliminado = productos.pop(idx)
        guardar_productos(productos)
        return jsonify({"ok": True, "nombre": eliminado.get("nombre")})
    return jsonify({"ok": False, "error": "Índice inválido"})


@app.route("/api/scan-all", methods=["GET"])
def scan_all():
    productos = cargar_productos()
    resultados = []
    for p in productos:
        r = obtener_precio(p["url"])
        resultados.append({
            **p,
            "precio_actual": r.get("precio"),
            "imagen": r.get("imagen") or p.get("imagen"),
            "tienda": r.get("tienda", p.get("tienda", "?")),
            "ok": r.get("ok", False)
        })
    return jsonify(resultados)


if __name__ == "__main__":
    print("🎲 ScanPrice arrancando en http://localhost:5000")
    app.run(debug=True, port=5000)
