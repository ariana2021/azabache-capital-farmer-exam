import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
DB_PATH = "database.db"

# --- Función IA mejorada ---
def analizar_con_ia(descripcion, tipo_servicio):
    API_URL = "https://api-inference.huggingface.co/models/nari-labs/Dia-1.6B"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    prompt = f"""
Analiza este caso legal: {descripcion}
Tipo de servicio: {tipo_servicio}

Evalúa:
1. Complejidad (Baja/Media/Alta)
2. Ajuste de precio recomendado (0%, 25%, 50%)
3. Servicios adicionales necesarios
4. Genera propuesta profesional para cliente

Por favor responde en formato JSON con estas claves:
complejidad, ajuste_precio, servicios_adicionales (lista), propuesta_texto
"""

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.7,
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                resultado = data[0]["generated_text"]
            elif isinstance(data, dict) and "generated_text" in data:
                resultado = data["generated_text"]
            else:
                resultado = str(data)

            try:
                start = resultado.find("{")
                end = resultado.rfind("}") + 1
                json_text = resultado[start:end]
                parsed = json.loads(json_text)

                return {
                    "complejidad": parsed.get("complejidad", "Media"),
                    "ajuste_precio": parsed.get("ajuste_precio", 0),
                    "servicios_adicionales": parsed.get("servicios_adicionales", []),
                    "propuesta_texto": parsed.get("propuesta_texto", resultado)
                }
            except Exception:
                return {
                    "complejidad": "Media",
                    "ajuste_precio": 0,
                    "servicios_adicionales": [],
                    "propuesta_texto": resultado
                }
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.Timeout:
        return {"error": "Error: La solicitud a la API tardó demasiado y se agotó el tiempo de espera."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud HTTP: {str(e)}"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}

# --- DB init ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cotizaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE,
                nombre TEXT,
                email TEXT,
                tipo_servicio TEXT,
                precio REAL,
                fecha TEXT,
                complejidad TEXT,
                ajuste_precio INTEGER,
                servicios_adicionales TEXT,
                propuesta_texto TEXT
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Error inicializando DB: {e}")
    finally:
        conn.close()

# --- Generar número único ---
def generar_numero_cotizacion():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cotizaciones WHERE fecha LIKE ?", (f"{datetime.now().strftime('%Y-%m-%d')}%",))
    contador = cursor.fetchone()[0] + 1
    conn.close()
    return f"COT-2025-{contador:04d}"

# --- Precios fijos ---
PRECIOS = {
    "Constitución de empresa": 1500,
    "Defensa laboral": 2000,
    "Consultoría tributaria": 800
}

# --- Rutas ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generar-cotizacion", methods=["POST"])
def generar_cotizacion():
    datos = request.form
    nombre = datos.get("nombre")
    email = datos.get("correo")
    tipo_servicio = datos.get("tipo_servicio")
    descripcion = datos.get("descripcion")

    if not (nombre and email and tipo_servicio and descripcion):
        return jsonify({"error": "Faltan datos obligatorios"}), 400

    precio_base = PRECIOS.get(tipo_servicio, 0)

    resultado_ia = analizar_con_ia(descripcion, tipo_servicio)

    if "error" in resultado_ia:
        return jsonify({"error": resultado_ia["error"]}), 500

    complejidad = resultado_ia.get("complejidad", "Media")
    ajuste_precio = resultado_ia.get("ajuste_precio", 0)
    servicios_adicionales = resultado_ia.get("servicios_adicionales", [])
    propuesta_texto = resultado_ia.get("propuesta_texto", "")

    precio_final = precio_base * (1 + ajuste_precio / 100)

    numero = generar_numero_cotizacion()
    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    servicios_adicionales_json = json.dumps(servicios_adicional)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cotizaciones (
                numero, nombre, email, tipo_servicio, precio, fecha,
                complejidad, ajuste_precio, servicios_adicionales, propuesta_texto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (numero, nombre, email, tipo_servicio, precio_final, fecha_creacion,
              complejidad, ajuste_precio, servicios_adicional_json, propuesta_texto))
        conn.commit()
    except Exception as e:
        return jsonify({"error": f"Error guardando en la base de datos: {str(e)}"}), 500
    finally:
        conn.close()

    return jsonify({
        "numero_cotizacion": numero,
        "nombre": nombre,
        "email": email,
        "tipo_servicio": tipo_servicio,
        "precio_base": precio_base,
        "ajuste_precio": ajuste_precio,
        "precio_final": precio_final,
        "fecha_creacion": fecha_creacion,
        "complejidad": complejidad,
        "servicios_adicionales": servicios_adicionales,
        "propuesta_texto": propuesta_texto
    })

# Nueva ruta para listar cotizaciones
@app.route("/cotizaciones")
def listar_cotizaciones():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT numero, nombre, email, tipo_servicio, precio, fecha FROM cotizaciones ORDER BY fecha DESC")
        filas = cursor.fetchall()
    except Exception as e:
        return f"Error al obtener cotizaciones: {e}", 500
    finally:
        conn.close()

    # Renderizar simple tabla HTML
    tabla_html = """
    <h2>Listado de Cotizaciones</h2>
    <table border="1" cellpadding="5" cellspacing="0">
      <tr>
        <th>Número</th>
        <th>Nombre</th>
        <th>Email</th>
        <th>Tipo de Servicio</th>
        <th>Precio</th>
        <th>Fecha</th>
      </tr>
    """
    for fila in filas:
        tabla_html += f"<tr><td>{fila[0]}</td><td>{fila[1]}</td><td>{fila[2]}</td><td>{fila[3]}</td><td>{fila[4]:.2f}</td><td>{fila[5]}</td></tr>"
    tabla_html += "</table>"

    return tabla_html


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
