from flask import Flask, request
import requests
import os
import uuid
from supabase import create_client

app = Flask(__name__)

# ==============================
# Environment Variables
# ==============================
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not CHANNEL_ACCESS_TOKEN:
    raise Exception("Missing CHANNEL_ACCESS_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing SUPABASE credentials")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "line-files"

# ==============================
# Routes
# ==============================

@app.route("/")
def home():
    return "LINE → Supabase Backup Running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json(silent=True)

    if not body or "events" not in body:
        return "OK", 200

    for event in body["events"]:
        if event.get("type") != "message":
            continue

        message = event.get("message", {})
        message_id = message.get("id")
        message_type = message.get("type")

        if not message_id:
            continue

        if message_type not in ["image", "video", "audio", "file"]:
            continue

        download_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"

        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }

        try:
            response = requests.get(
                download_url,
                headers=headers,
                stream=True,
                timeout=20
            )
        except Exception as e:
            print("❌ LINE download error:", e)
            continue

        if response.status_code != 200:
            print("❌ Download failed:", response.status_code)
            continue

        # 🔥 เอาเฉพาะ mime type จริง (ตัด ; charset=binary ออก)
        content_type = response.headers.get(
            "Content-Type",
            "application/octet-stream"
        ).split(";")[0]

        print("📦 Content-Type:", content_type)

        # 🔥 map นามสกุลเองแบบชัวร์
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "application/pdf": ".pdf"
        }

        ext = ext_map.get(content_type, ".bin")

        folder = message_type
        filename = f"{folder}/{uuid.uuid4()}{ext}"

        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                path=filename,
                file=response.content,
                file_options={
                    "content-type": content_type,
                    "upsert": False
                }
            )

            print("✅ Uploaded:", filename)

        except Exception as e:
            print("❌ Upload error:", e)

    return "OK", 200


# ==============================
# Main
# ==============================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
