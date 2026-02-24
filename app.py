from flask import Flask, request
import requests
import os
import uuid
import mimetypes
from supabase import create_client

app = Flask(__name__)

# ===== Environment Variables =====
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not CHANNEL_ACCESS_TOKEN:
    raise Exception("Missing CHANNEL_ACCESS_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing SUPABASE credentials")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "line-files"


@app.route("/")
def home():
    return "LINE → Supabase Backup Running"


@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json

    if not body or "events" not in body:
        return "OK", 200

    for event in body["events"]:
        if event.get("type") != "message":
            continue

        message = event.get("message", {})
        message_id = message.get("id")
        message_type = message.get("type")

        if message_type not in ["image", "video", "audio", "file"]:
            continue

        headers = {
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
        }

        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print("❌ Download failed:", response.status_code)
            continue

        # ✅ อ่าน Content-Type จริงจาก LINE
        content_type = response.headers.get("Content-Type", "application/octet-stream")

        # เดานามสกุลจาก content-type
        ext = mimetypes.guess_extension(content_type)

        if not ext:
            ext = ".bin"

        # 🔥 สร้างโฟลเดอร์ตามประเภทไฟล์
        folder = message_type  # image / video / audio / file
        filename = f"{folder}/{uuid.uuid4()}{ext}"

        try:
            result = supabase.storage.from_(BUCKET_NAME).upload(
                filename,
                response.content,
                {
                    "content-type": content_type
                }
            )

            print("✅ Uploaded:", filename, "| type:", content_type)

        except Exception as e:
            print("❌ Upload error:", str(e))

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



