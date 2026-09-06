import http.server
import socketserver
import threading
import os
import asyncio
from datetime import datetime
from telethon import TelegramClient

API_ID = 28532454
API_HASH = 'd337fbe06d209ed2feecfb26f9df8df3'
SESSION_NAME = 'anon'
PORT = 10000

TARGET_CHANNELS = ["Data Trader", "VinaFunder", "Trader Gauls", "GBPJPY EURUSD", "Hệ thống"]

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html_path = os.path.join(os.path.dirname(__file__), 'giao-dien', 'index.html')
        if os.path.exists(html_path):
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.wfile.write('<h1>Hệ thống đang tải giao diện...</h1>'.encode('utf-8'))

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('0.0.0.0', PORT), CustomHandler) as httpd:
        print(f"Web Server running on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

async def update_dashboard(client):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dang quet tin nhan Telegram...")
    try:
        dialogs = await client.get_dialogs()
        channel_dict = {dialog.name: dialog for dialog in dialogs}
        
        for ch_name in TARGET_CHANNELS:
            target = None
            for name, dialog in channel_dict.items():
                if ch_name.lower() in name.lower():
                    target = dialog
                    break
            if target:
                msgs = await client.get_messages(target, limit=1)
                if msgs and msgs[0].text:
                    print(f"[+ SUCCESS] {ch_name}: {msgs[0].text[:30]}...")
    except Exception as e:
        print(f"[- ERROR] {e}")

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Loi: File session khong hop le!")
        return
        
    print("Telethon Client ket noi thanh cong!")
    while True:
        await update_dashboard(client)
        await asyncio.sleep(1800)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
