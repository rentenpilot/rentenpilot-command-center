import os
import time
import shutil
import psutil
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
HERMES_START_TIME = time.time()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


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
        "model": OPENROUTER_MODEL,
        "provider": "OpenRouter"
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "Keine Nachricht erhalten."}), 400

    if not OPENROUTER_API_KEY:
        return jsonify({"ok": False, "error": "OPENROUTER_API_KEY fehlt in .env."}), 500

    try:
        completion = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist Hermes, der Chief AI Officer des Projekts RentenPilot. "
                        "Antworte präzise, praktisch und auf Deutsch."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0.4,
            max_tokens=900,
        )

        answer = completion.choices[0].message.content

        return jsonify({
            "ok": True,
            "answer": answer,
            "model": OPENROUTER_MODEL,
            "provider": "OpenRouter"
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 500


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