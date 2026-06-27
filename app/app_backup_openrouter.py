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
            "model": "deepseek/deepseek-v4-flash",
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
                "model": "deepseek/deepseek-v4-flash",
                "http_status": response.status_code,
                "message": response.text[:300],
                "credit": None
            }), 500

        data = response.json()
        credits = data.get("data", {})

        return jsonify({
            "status": "online",
            "provider": "OpenRouter",
            "model": "deepseek/deepseek-v4-flash",
            "credit": credits.get("total_credits"),
            "usage": credits.get("total_usage"),
            "remaining": (
                credits.get("total_credits") - credits.get("total_usage")
                if credits.get("total_credits") is not None and credits.get("total_usage") is not None
                else None
            )
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "provider": "OpenRouter",
            "model": "deepseek/deepseek-v4-flash",
            "message": str(error),
            "credit": None
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