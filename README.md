# ScanPrice — Las Ofertas mas cerca que nunca.

> Herramienta personal de seguimiento de precios en tiendas online de juegos de mesa, desarrollada con Python y HTML mediante *vibe coding* asistido por IA.

---

## ¿Qué es ScanPrice?

ScanPrice nació de una necesidad concreta: encontrar el mejor precio posible para juegos de mesa en las tiendas online más habituales sin tener que revisar cada web manualmente cada día.

La idea es sencilla. Añades un juego con su enlace y el precio que estás dispuesto a pagar. A partir de ese momento, con un solo clic, la aplicación recorre todas tus listas y compara los precios actuales contra tu objetivo, señalando visualmente cuándo una oferta merece atención.

No es un producto comercial ni pretende serlo. Es una herramienta de uso personal, construida con criterios de practicidad: código legible, tecnologías accesibles y un resultado funcional desde el primer día.

---

## Tecnologías utilizadas

### Backend — Python

El servidor está escrito en Python, elegido por su legibilidad y su ecosistema de librerías para scraping. Las dependencias principales son:

| Librería | Uso |
|---|---|
| `Flask` | Servidor web ligero que sirve la interfaz y expone la API REST |
| `flask-cors` | Gestión de cabeceras CORS para permitir las llamadas desde el navegador |
| `requests` | Peticiones HTTP a las tiendas para obtener el HTML de cada página |
| `beautifulsoup4` | Análisis y extracción de datos del HTML descargado (scraping) |
| `lxml` | Parser HTML de alto rendimiento usado por BeautifulSoup |

### Frontend — HTML / CSS / JavaScript

La interfaz es un único archivo `index.html` sin dependencias externas ni frameworks. El diseño sigue una estética dark mode con tarjetas estilo Netflix, desarrollada mediante *vibe coding* en Claude (Anthropic).

---

## Arquitectura

```
scanprice/
├── server.py        # Backend Flask: API REST + scrapers por tienda
├── index.html       # Frontend: interfaz completa en un solo archivo
├── productos.json   # Base de datos local (se genera automáticamente)
└── requirements.txt # Dependencias Python
```

La arquitectura es intencionadamente simple: el frontend hace llamadas REST al backend local, que actúa como proxy para evitar los bloqueos CORS del navegador. No hay base de datos externa, no hay autenticación, no hay servicios en la nube. Todo corre en local.

```
Navegador (index.html)
        │
        │  llamadas REST (localhost:5000)
        ▼
  Backend Flask (server.py)
        │
        │  requests HTTP + BeautifulSoup
        ▼
  Tiendas online (GoblinTrader, Dungeon Marvels, Mathom...)
```

---

## Tiendas soportadas

| Tienda | Selector utilizado | Estado |
|---|---|---|
| [GoblinTrader](https://goblintrader.es) | `span.price` | Operativo |
| [Dungeon Marvels](https://dungeonmarvels.com) | `span[itemprop="price"][content]` | Operativo |
| [Mathom](https://mathom.es) | `span.current-price-value[content]` | Operativo |

### Decisiones técnicas relevantes

**¿Por qué un servidor Python y no scraping directo desde el navegador?**
Los navegadores bloquean las peticiones a dominios externos por política CORS. Un script JavaScript no puede hacer `fetch("https://goblintrader.es/...")` directamente. El servidor Flask actúa como intermediario: el navegador le pide al servidor local que busque el precio, y el servidor lo hace sin restricciones.

**¿Por qué `content` y no el texto visible del precio?**
En PrestaShop (Mathom) y otras plataformas, el precio aparece en un atributo `content` del elemento HTML con el valor limpio en formato numérico (`content="17.99"`), mientras que el texto visible incluye símbolos de moneda, espacios especiales y formato localizado (`17,99 €`). Leer el atributo `content` es más robusto y evita parsear texto.

---

## Cómo usar la aplicación

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/scanprice.git
cd scanprice

# Instalar dependencias
pip install -r requirements.txt

# Arrancar el servidor
python server.py
```

Abrir el navegador en **http://localhost:5000**

### Flujo de uso

1. **Pegar la URL** del producto en la tienda online
2. Pulsar **⚡ Testear** — la app extrae automáticamente el precio actual, el nombre y la imagen del producto
3. Ajustar el **nombre** si es necesario e introducir el **precio objetivo**
4. Pulsar **+ Guardar** para añadirlo a la lista
5. Cualquier día siguiente, pulsar **↻ Escanear todos** para actualizar todos los precios de golpe

Las tarjetas en verde indican que el precio actual está por debajo del objetivo. Las tarjetas en rojo indican que todavía no es el momento de comprar.

---

## 🔭 Proyección y próximos pasos

El proyecto está en fase funcional pero tiene margen de evolución en varias direcciones:

**Más tiendas**
Añadir soporte para Zacatrus, Philibert, El Dragón Azul u otras tiendas de referencia en España y Europa. Cada tienda nueva requiere identificar el selector CSS del precio, lo que suele llevar menos de 30 minutos.

**Historial de precios**
Guardar el precio cada vez que se escanea y mostrar una gráfica de evolución por producto. Permitiría detectar tendencias y confirmar si un precio "en oferta" es realmente una ganga o simplemente el precio habitual.

**Notificaciones**
Un sistema de alertas por email o Telegram cuando un producto alcanza el precio objetivo, sin necesidad de abrir la aplicación manualmente.

**Despliegue en servidor**
Mover el backend a un servidor en la nube (Railway, Render, Fly.io) y programar escaneos automáticos periódicos, eliminando la necesidad de tener el ordenador encendido.

**Integración con BGG**
Cruzar los datos de precios con la base de datos de BoardGameGeek para mostrar la valoración de la comunidad junto al precio, ayudando a decidir si un juego barato merece la pena.

---

## Consideraciones sobre el scraping

El scraping debe realizarse de manera responsable:

- Las peticiones se hacen con límite de tiempo (`timeout=10s`) para no sobrecargar los servidores
- La herramienta está diseñada para uso personal, no para scraping masivo o automatizado en bucle
- Antes de scrapear cualquier web, conviene revisar su `robots.txt` y Términos de Servicio
- El uso indebido del scraping puede tener consecuencias legales en algunas jurisdicciones

---

## Sobre el proceso de desarrollo

Este proyecto ha sido desarrollado mediante **vibe coding**: una metodología de desarrollo asistido por IA donde el desarrollador define la intención, los requisitos y las decisiones de negocio, y delega la implementación técnica en un modelo de lenguaje (en este caso, Claude de Anthropic).

El resultado es un código funcional obtenido en una fracción del tiempo que requeriría la implementación manual, manteniendo el control sobre la arquitectura y las decisiones de diseño. El vibe coding no elimina la necesidad de entender el código generado — de hecho, durante el desarrollo se identificaron y resolvieron problemas no triviales como el bypass del WAF de Cloudflare en Mathom, que requirió análisis del DOM inspeccionado manualmente para encontrar el selector correcto.

---

## Licencia

Proyecto personal de uso libre. Sin licencia formal.
