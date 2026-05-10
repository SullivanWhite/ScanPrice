from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import sqlite3
from datetime import datetime

app = Flask(__name__, static_folder=".")
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DATA_FILE = "productos.json"
DB_FILE   = "historial.db"


# ── SQLite ─────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT NOT NULL,
            url     TEXT NOT NULL,
            precio  REAL NOT NULL,
            tienda  TEXT,
            fecha   TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def guardar_en_historial(nombre, url, precio, tienda):
    """
    Solo inserta una nueva fila si el precio cambió respecto al último registro.
    Si el precio es idéntico al último, no hace nada.
    """
    con = sqlite3.connect(DB_FILE)
    cur = con.execute(
        "SELECT precio FROM historial WHERE url=? ORDER BY fecha DESC LIMIT 1",
        (url,)
    )
    ultimo = cur.fetchone()
    if ultimo is None or round(ultimo[0], 2) != round(precio, 2):
        con.execute(
            "INSERT INTO historial (nombre, url, precio, tienda, fecha) VALUES (?,?,?,?,?)",
            (nombre, url, precio, tienda, datetime.now().isoformat())
        )
        con.commit()
    con.close()


def obtener_historial(nombre):
    con = sqlite3.connect(DB_FILE)
    cur = con.execute(
        "SELECT fecha, precio, tienda FROM historial WHERE nombre=? ORDER BY fecha ASC",
        (nombre,)
    )
    rows = [{"fecha": r[0], "precio": r[1], "tienda": r[2]} for r in cur.fetchall()]
    con.close()
    return rows


def stats_historial(nombre):
    con = sqlite3.connect(DB_FILE)
    cur = con.execute(
        "SELECT MIN(precio), MAX(precio), AVG(precio), COUNT(*) FROM historial WHERE nombre=?",
        (nombre,)
    )
    row = cur.fetchone()
    con.close()
    if not row or row[3] == 0:
        return None
    return {
        "min":   round(row[0], 2),
        "max":   round(row[1], 2),
        "media": round(row[2], 2),
        "n":     row[3]
    }


# ── Productos JSON ─────────────────────────────────────────────

def cargar_productos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_productos(productos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)


# ── Scrapers ───────────────────────────────────────────────────

def limpiar_precio(texto):
    if not texto:
        return None
    texto = re.sub(r"[^\d,\.]", "", str(texto).strip())
    texto = texto.replace(",", ".")
    partes = texto.split(".")
    if len(partes) > 2:
        texto = "".join(partes[:-1]) + "." + partes[-1]
    try:
        return float(texto)
    except ValueError:
        return None


def scrape_goblintrader(soup):
    tag = soup.find("span", class_="price") or soup.find("p", class_="price")
    if not tag:
        tag = soup.find(class_=re.compile(r"price"))
    return limpiar_precio(tag.get_text()) if tag else None


def scrape_dungeonmarvels(soup):
    tag = soup.find("span", itemprop="price")
    if tag:
        return limpiar_precio(tag.get("content") or tag.get_text())
    return None


def scrape_mathom(soup):
    tag = soup.find("span", class_="current-price-value")
    if tag:
        return limpiar_precio(tag.get("content") or tag.get_text())
    return None


def obtener_precio(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        og_title = soup.find("meta", property="og:title")
        nombre   = og_title.get("content", "").strip() if og_title else (
            soup.find("h1").get_text().strip() if soup.find("h1") else None
        )
        og_img = soup.find("meta", property="og:image")
        imagen = og_img.get("content", "").strip() if og_img else None

        precio, tienda = None, "desconocida"
        if "goblintrader" in url:
            precio, tienda = scrape_goblintrader(soup), "GoblinTrader"
        elif "dungeonmarvels" in url:
            precio, tienda = scrape_dungeonmarvels(soup), "Dungeon Marvels"
        elif "mathom" in url:
            precio, tienda = scrape_mathom(soup), "Mathom"

        return {"precio": precio, "nombre_scrapeado": nombre,
                "imagen": imagen, "tienda": tienda, "ok": precio is not None}
    except Exception as e:
        return {"ok": False, "error": str(e), "precio": None}


# ── Endpoints ──────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json
    url  = data.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "URL vacía"})
    return jsonify(obtener_precio(url))


@app.route("/api/productos", methods=["GET"])
def get_productos():
    return jsonify(cargar_productos())


@app.route("/api/productos", methods=["POST"])
def add_producto():
    producto  = request.json
    productos = cargar_productos()
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
    productos  = cargar_productos()
    resultados = []
    for p in productos:
        r             = obtener_precio(p["url"])
        precio_actual = r.get("precio")

        # Guardar cada precio obtenido en el historial
        if precio_actual is not None:
            guardar_en_historial(
                p["nombre"], p["url"], precio_actual,
                r.get("tienda", p.get("tienda", "?"))
            )

        resultados.append({
            **p,
            "precio_actual": precio_actual,
            "imagen":        r.get("imagen") or p.get("imagen"),
            "tienda":        r.get("tienda", p.get("tienda", "?")),
            "ok":            r.get("ok", False)
        })
    return jsonify(resultados)


@app.route("/api/historial/<path:nombre>", methods=["GET"])
def get_historial(nombre):
    """
    Devuelve el historial de precios propio de un producto.
    La base de datos se construye automáticamente con cada escaneo.
    """
    return jsonify({
        "registros": obtener_historial(nombre),
        "stats":     stats_historial(nombre)
    })



@app.route("/api/ultimos-anyadidos", methods=["GET"])
def ultimos_anyadidos():
    """
    Devuelve los últimos 50 registros únicos añadidos a la BD,
    ordenados por fecha descendente (los más recientes primero).
    """
    limite = int(request.args.get("limite", 50))
    con = sqlite3.connect(DB_FILE)
    cur = con.execute("""
        SELECT nombre, precio, tienda, fecha
        FROM historial
        GROUP BY url
        ORDER BY fecha DESC
        LIMIT ?
    """, (limite,))
    rows = [{"nombre": r[0], "precio": r[1], "tienda": r[2], "fecha": r[3]}
            for r in cur.fetchall()]
    con.close()
    return jsonify(rows)

if __name__ == "__main__":
    init_db()
    print("🎲 ScanPrice arrancando en http://localhost:5000")
    app.run(debug=True, port=5000)
