from flask import Flask, request
import requests
import os

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = "SlaCavEOcI49IE3BFZlnuRMY2yaXwzyct2hWhkplD4P6lLOt/50Rt9eJRl+juvj6hYewqk5IH90+IcewWh2UY4gsztO6Q0GgoWLdTurAU0ER2yEHwXaEUN2Lu0xhoHJ+TiePyzyKGLriYrqMzKzXrAdB04t89/1O/w1cDnyilFU="

@app.route("/webhook", methods=['POST'])
def webhook():
    events = request.json['events']
    for event in events:
        if event['type'] == 'message':
            message = event['message']
            message_id = message['id']
            message_type = message['type']

            if message_type in ['image', 'file', 'video', 'audio']:

                headers = {
                    'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
                }

                url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
                r = requests.get(url, headers=headers)

                if not os.path.exists("downloads"):
                    os.makedirs("downloads")

                # กำหนดชื่อไฟล์
                if message_type == 'image':
                    filename = f"{message_id}.jpg"
                elif message_type == 'video':
                    filename = f"{message_id}.mp4"
                elif message_type == 'audio':
                    filename = f"{message_id}.m4a"
                elif message_type == 'file':
                    original_name = message.get('fileName', message_id)
                    filename = original_name
                else:
                    filename = message_id

                with open(f"downloads/{filename}", 'wb') as f:
                    f.write(r.content)

    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
# if __name__ == "__main__":
#     app.run(port=5000)