import os
import time
import shutil
import psutil
from flask import Flask, render_template, jsonify, request, Response
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_tts_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# In-Memory Usage Tracking
usage_stats = {
    "requests": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "cost_today": 0.0,
    "cost_month": 0.0,
}


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
        usage = completion.usage

        if usage:
            usage_stats["requests"] += 1
            usage_stats["input_tokens"] += usage.prompt_tokens
            usage_stats["output_tokens"] += usage.completion_tokens
            usage_stats["total_tokens"] += usage.total_tokens
            
            # Simple estimated cost (DeepSeek Flash roughly 0.14$ Input / 0.28$ Output per 1M)
            in_cost = (usage.prompt_tokens / 1_000_000) * 0.14
            out_cost = (usage.completion_tokens / 1_000_000) * 0.28
            usage_stats["cost_today"] += (in_cost + out_cost)
            usage_stats["cost_month"] += (in_cost + out_cost)

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


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    
    if not text:
        return jsonify({"ok": False, "error": "Kein Text übergeben."}), 400
        
    if not openai_tts_client:
        return jsonify({"ok": False, "error": "Kein OPENAI_API_KEY konfiguriert."}), 501
        
    try:
        response = openai_tts_client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )
        return Response(response.content, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/usage")
def api_usage():
    credit = None
    credit_display = "nicht verfügbar"
    if OPENROUTER_API_KEY:
        import requests
        try:
            resp = requests.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                timeout=3
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                limit = data.get("limit")
                used = data.get("usage", 0)
                if limit is not None:
                    credit = max(0.0, limit - used)
                    credit_display = f"$ {credit:.2f}"
        except Exception as e:
            print(f"Warnung: Konnte OpenRouter-Guthaben nicht abrufen - {e}")

    return jsonify({
        "model": OPENROUTER_MODEL,
        "provider": "OpenRouter",
        "requests": usage_stats["requests"],
        "input_tokens": usage_stats["input_tokens"],
        "output_tokens": usage_stats["output_tokens"],
        "total_tokens": usage_stats["total_tokens"],
        "cost_today": usage_stats["cost_today"],
        "cost_month": usage_stats["cost_month"],
        "credit": credit,
        "credit_display": credit_display
    })


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