import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")

def analizar_con_ia(descripcion, tipo_servicio):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

    prompt = f"""
Analiza este caso legal: {descripcion}
Tipo de servicio: {tipo_servicio}

Evalúa:
1. Complejidad (Baja/Media/Alta)
2. Ajuste de precio recomendado (0%, 25%, 50%)
3. Servicios adicionales necesarios
4. Genera propuesta profesional para cliente

Por favor responde en formato JSON con las claves:
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

            resultado = resultado.strip()

            # Intentar extraer JSON del texto generado
            try:
                start = resultado.index("{")
                end = resultado.rindex("}") + 1
                json_text = resultado[start:end]
                parsed = json.loads(json_text)
                return {"resultado_ia": parsed}
            except (ValueError, json.JSONDecodeError):
                # Si no es posible extraer JSON, devolver texto plano
                return {"resultado_ia": resultado}
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.Timeout:
        return {"error": "Error: La solicitud a la API tardó demasiado y se agotó el tiempo de espera."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud HTTP: {str(e)}"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}
