from flask import Flask, request
import requests
import os
import uuid
import re
import unicodedata
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
# Helper: sanitize filename
# ==============================
def sanitize_filename(name):
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r"[^\w.\-]", "_", name)
    name = name.strip("._")
    if len(name) > 120:
        name = name[:120]
    return name

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
                timeout=20
            )
        except Exception as e:
            print("❌ LINE download error:", e)
            continue

        if response.status_code != 200:
            print("❌ Download failed:", response.status_code)
            continue

        content_type = response.headers.get(
            "Content-Type",
            "application/octet-stream"
        ).split(";")[0]

        print("📦 Content-Type:", content_type)

        # ==============================
        # ดึงชื่อไฟล์จาก LINE event (เฉพาะ type=file)
        # ==============================
        original_filename = None
        if message_type == "file":
            original_filename = message.get("fileName")

        # ==============================
        # map นามสกุล
        # ==============================
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

        # ==============================
        # ตั้งชื่อไฟล์แบบปลอดภัย 100%
        # ==============================
        if original_filename:
            safe_name = sanitize_filename(original_filename)
            name_part, extension = os.path.splitext(safe_name)

            # ถ้าไม่มี extension ให้ใช้จาก content-type
            if not extension:
                extension = ext

            filename = f"{folder}/{name_part}_{uuid.uuid4().hex}{extension}"
        else:
            filename = f"{folder}/{uuid.uuid4().hex}{ext}"

        # ==============================
        # Upload
        # ==============================
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
