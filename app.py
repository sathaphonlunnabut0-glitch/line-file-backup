from flask import Flask, request, send_from_directory
import requests
import os

app = Flask(__name__)

# ใช้ Environment Variable แทนการใส่ token ตรง ๆ
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")

@app.route("/")
def home():
    return "LINE File Backup Bot is running"

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.json

    if not body or 'events' not in body:
        return "No events", 200

    events = body['events']

    for event in events:
        if event.get('type') == 'message':
            message = event.get('message', {})
            message_id = message.get('id')
            message_type = message.get('type')

            if message_type in ['image', 'file', 'video', 'audio']:

                headers = {
                    'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
                }

                url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
                r = requests.get(url, headers=headers)

                if r.status_code != 200:
                    print("Download failed:", r.status_code, r.text)
                    continue

                # สร้างโฟลเดอร์ถ้ายังไม่มี
                if not os.path.exists("downloads"):
                    os.makedirs("downloads")

                # ตั้งชื่อไฟล์
                if message_type == 'image':
                    filename = f"{message_id}.jpg"
                elif message_type == 'video':
                    filename = f"{message_id}.mp4"
                elif message_type == 'audio':
                    filename = f"{message_id}.m4a"
                elif message_type == 'file':
                    filename = message.get('fileName', message_id)
                else:
                    filename = message_id

                filepath = os.path.join("downloads", filename)

                with open(filepath, 'wb') as f:
                    f.write(r.content)

                print(f"Saved file: {filepath}")

    return "OK", 200


# Route สำหรับโหลดไฟล์จาก browser
@app.route("/files/<filename>")
def get_file(filename):
    return send_from_directory("downloads", filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
