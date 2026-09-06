import http.server
import socketserver
import threading
import os
import asyncio
import re
import time
from datetime import datetime
from telethon import TelegramClient
from deep_translator import GoogleTranslator

API_ID = 28532454
API_HASH = 'd337fbe06d209ed2feecfb26f9df8df3'
SESSION_NAME = 'anon'
PORT = 10000

TARGET_CHANNELS = ["Data Trader", "VinaFunder", "Trader Gauls", "GBPJPY EURUSD", "Hệ thống"]
translator = GoogleTranslator(source='auto', target='vi')

# Lưu lịch sử tối đa 5 bài viết cho mỗi kênh
channel_posts = {ch: [] for ch in TARGET_CHANNELS}

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html_path = os.path.join(os.path.dirname(__file__), 'giao-dien', self.path.lstrip('/'))
        if self.path == '/' or not os.path.exists(html_path):
            html_path = os.path.join(os.path.dirname(__file__), 'giao-dien', 'index.html')
            
        if os.path.exists(html_path):
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.wfile.write('<h1>Hệ thống đang tải...</h1>'.encode('utf-8'))

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('0.0.0.0', PORT), CustomHandler) as httpd:
        print(f"Web Server running on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

def cleanup_old_images(img_dir, days_limit=30):
    if not os.path.exists(img_dir):
        return
    now = time.time()
    cutoff_time = now - (days_limit * 86400)
    
    for filename in os.listdir(img_dir):
        file_path = os.path.join(img_dir, filename)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < cutoff_time:
                try:
                    os.remove(file_path)
                    print(f"[CLEANUP] Xóa ảnh quá 30 ngày: {filename}")
                except Exception as e:
                    print(f"[- CLEANUP ERROR] {e}")

def process_and_translate(text):
    if not text:
        return ""
    try:
        translated = translator.translate(text)
    except Exception:
        translated = text

    translated = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', translated)
    
    keywords = ["Entry", "Stop loss", "Take profit", "TP", "SL", "Breakout", "Overbought", "Oversold", "Kháng cự", "Hỗ trợ"]
    for kw in keywords:
        pattern = re.compile(rf'({kw})', re.IGNORECASE)
        translated = pattern.sub(r'<span style="background: rgba(240, 185, 11, 0.2); color: #f0b90b; padding: 2px 5px; border-radius: 3px; font-weight: bold;">\1</span>', translated)

    return translated

async def update_dashboard(client):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quét bài viết mới (Giữ 5 bài gần nhất)...")
    base_dir = os.path.dirname(__file__)
    html_path = os.path.join(base_dir, 'giao-dien', 'index.html')
    img_dir = os.path.join(base_dir, 'giao-dien', 'images')
    
    os.makedirs(img_dir, exist_ok=True)
    cleanup_old_images(img_dir, days_limit=30)
    
    if not os.path.exists(html_path):
        return

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        dialogs = await client.get_dialogs()
        channel_dict = {dialog.name: dialog for dialog in dialogs}
        has_update = False
        
        for ch_name in TARGET_CHANNELS:
            target = None
            for name, dialog in channel_dict.items():
                if ch_name.lower() in name.lower():
                    target = dialog
                    break
            
            if target:
                msgs = await client.get_messages(target, limit=1)
                if msgs and (msgs[0].text or msgs[0].media):
                    msg = msgs[0]
                    
                    # Kiểm tra nếu bài viết đã tồn tại trong danh sách
                    existing_ids = [p['id'] for p in channel_posts.get(ch_name, [])]
                    if msg.id in existing_ids:
                        continue

                    has_update = True
                    msg_time = msg.date.strftime('%H:%M - %d/%m/%Y')
                    processed_text = process_and_translate(msg.text or "")
                    
                    img_html = ""
                    if msg.media and hasattr(msg.media, 'photo'):
                        clean_ch_name = re.sub(r'\W+', '_', ch_name)
                        img_filename = f"{clean_ch_name}_{msg.id}.jpg"
                        img_save_path = os.path.join(img_dir, img_filename)
                        
                        await client.download_media(msg.media, file=img_save_path)
                        img_html = f'<div style="margin-top: 10px;"><img src="images/{img_filename}" style="max-width:100%; border-radius:8px; border:1px solid #2a2e3d;" alt="Biểu đồ phân tích"></div>'
                    
                    post_item = {
                        'id': msg.id,
                        'html': f'<div class="post-item" style="border-bottom: 1px dashed #2a2e3d; padding-bottom: 16px; margin-bottom: 16px;"><div class="update-time" style="color:#848e9c; font-size:12px; margin-bottom:6px;">🕒 {msg_time}</div><div class="content-body">{processed_text}{img_html}</div></div>'
                    }

                    # Thêm bài viết mới lên ĐẦU danh sách
                    channel_posts[ch_name].insert(0, post_item)
                    
                    # Giới hạn giữ tối đa 5 bài
                    if len(channel_posts[ch_name]) > 5:
                        channel_posts[ch_name] = channel_posts[ch_name][:5]

                    # Ghép 5 bài thành 1 chuỗi HTML
                    full_posts_html = "".join([p['html'] for p in channel_posts[ch_name]])

                    pattern_content = rf'(<span class="channel-name">{re.escape(ch_name)}</span>.*?<div class="content">).*?(</div>\s*</div>)'
                    html_content = re.sub(pattern_content, rf'\g<1>{full_posts_html}\2', html_content, flags=re.DOTALL)
                    print(f"[+ SUCCESS] Thêm bài mới cho {ch_name} (Tổng: {len(channel_posts[ch_name])}/5 bài)")

        if has_update:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
    except Exception as e:
        print(f"[- ERROR] {e}")

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Lỗi: File session không hợp lệ!")
        return
        
    print("Telethon Client kết nối thành công!")
    while True:
        await update_dashboard(client)
        await asyncio.sleep(900)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
