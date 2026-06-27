import os
import time
import shutil
import psutil
import requests
from flask import Flask, render_template, jsonify
from dotenv import dotenv_values

app = Flask(__name__)

HERMES_START_TIME = time.time()
HERMES_ENV_PATH = r"\\wsl$\Ubuntu\home\ramses\.hermes\.env"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/system")
def api_system():
    system_uptime_seconds = int(time.time() - psutil.boot_time())
    hermes_uptime_seconds = int(time.time() - HERMES_START_TIME)

    disk = shutil.disk_usage("C:\\")
    disk_used_percent = round((disk.used / disk.total) * 100, 1)

    return jsonify({
        "status": "online",
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": disk_used_percent,
        "disk_total_gb": round(disk.total / (1024 ** 3), 1),
        "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        "system_uptime_seconds": system_uptime_seconds,
        "system_uptime_text": format_uptime(system_uptime_seconds),
        "hermes_uptime_seconds": hermes_uptime_seconds,
        "hermes_uptime_text": format_uptime(hermes_uptime_seconds),
        "model": "DeepSeek Flash",
        "provider": "OpenRouter"
    })


@app.route("/api/openrouter")
def api_openrouter():
    api_key = get_openrouter_key()

    if not api_key:
        return jsonify({
            "status": "error",
            "message": "OPENROUTER_API_KEY nicht gefunden",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "credit": None
        }), 500

    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/credits",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "provider": "OpenRouter",
                "model": OPENROUTER_MODEL,
                "http_status": response.status_code,
                "message": response.text[:300],
                "credit": None
            }), 500

        data = response.json()
        credits = data.get("data", {})
        total = credits.get("total_credits")
        usage = credits.get("total_usage")

        return jsonify({
            "status": "online",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "credit": total,
            "usage": usage,
            "remaining": total - usage if total is not None and usage is not None else None
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "provider": "OpenRouter",
            "model": OPENROUTER_MODEL,
            "message": str(error),
            "credit": None
        }), 500


@app.route("/api/business-scout")
def api_business_scout():
    api_key = get_openrouter_key()

    if not api_key:
        return jsonify({
            "status": "error",
            "message": "OPENROUTER_API_KEY nicht gefunden"
        }), 500

    prompt = """
Du bist der Business Scout des RentenPilot-Projekts.

Aufgabe:
Erstelle 10 priorisierte Content-Ideen für RentenPilot.

Fokus:
- Rente
- früher in Rente
- GdB 50
- Schwerbehindertenrente
- Rentensteuer
- Rentenbescheid
- häufige Fehler
- Social-Media-taugliche Themen

Ausgabe bitte kompakt und strukturiert:

1. Titel
2. Warum relevant
3. Formatvorschlag: Blog / TikTok / YouTube Short / FAQ
4. Priorität: hoch / mittel / niedrig
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "RentenPilot Command Center"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Du bist Hermes, Chief AI Officer des RentenPilot-Projekts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 1200
            },
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "http_status": response.status_code,
                "message": response.text[:1000]
            }), 500

        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        return jsonify({
            "status": "online",
            "agent": "Business Scout",
            "model": OPENROUTER_MODEL,
            "result": answer
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "agent": "Business Scout",
            "message": str(error)
        }), 500


def get_openrouter_key():
    values = dotenv_values(HERMES_ENV_PATH)
    return values.get("OPENROUTER_API_KEY")


def format_uptime(seconds):
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)