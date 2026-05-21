#!/usr/bin/env python3
"""
HIRAKO AUTO LIKE TIKTOK BOT - PERSISTENT OFFSET VERSION
- No spam
- Single shot langsung like sekali
- Rate limit protection
- Offset tersimpan (TIDAK BACA ULANG PESAN LAMA)
"""

import requests
import time
import random
import json
import os
import threading
import re
from datetime import datetime
from collections import deque
from bs4 import BeautifulSoup

# Nonaktifkan warning SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== KONFIGURASI ====================

# 🔥 GANTI DENGAN DATA TELEGRAM KAMU 🔥
TELEGRAM_BOT_TOKEN = "8794092200:AAETRBGzQjUhGc2Ot-_QJBB42PwEtcYie4Q"
TELEGRAM_ADMIN_ID = 8440381121

# File untuk menyimpan data
LINKS_FILE = "links.txt"
PREMIUM_PROXY_FILE = "proxy1.txt"
PROXY_LOG_FILE = "used_proxies.json"
PROXY_BLACKLIST_FILE = "blacklisted_proxies.json"
OFFSET_FILE = "telegram_offset.json"  # FILE UNTUK MENYIMPAN OFFSET

# Rate limiting
processed_messages = deque(maxlen=100)

# User agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0',
]

# ==================== PERSISTENT OFFSET ====================

def save_offset(offset):
    """Simpan offset ke file"""
    try:
        with open(OFFSET_FILE, 'w') as f:
            json.dump({'offset': offset}, f)
        return True
    except:
        return False

def load_offset():
    """Load offset dari file"""
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, 'r') as f:
                data = json.load(f)
                return data.get('offset', 0)
        except:
            return 0
    return 0

# ==================== BANNER ====================

def show_banner():
    banner = """
\033[95m
╔══════════════════════════════════════════════════════════════╗
║           🤖 HIRAKO AUTO LIKE TIKTOK BOT 🤖                 ║
║              ANTI-SPAM - SINGLE SHOT                        ║
╚══════════════════════════════════════════════════════════════╝
\033[0m
"""
    print(banner)

# ==================== MANAJEMEN VIDEO ====================

def load_videos():
    urls = []
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ('tiktok.com' in line or 'vt.tiktok.com' in line):
                        urls.append(line)
        except:
            pass
    return urls

def save_videos(urls):
    try:
        with open(LINKS_FILE, 'w') as f:
            for url in urls:
                f.write(url + '\n')
        return True
    except:
        return False

def add_video(url):
    urls = load_videos()
    if url not in urls:
        urls.append(url)
        save_videos(urls)
        return True, len(urls)
    return False, len(urls)

def remove_video(index):
    urls = load_videos()
    if 1 <= index <= len(urls):
        removed = urls.pop(index - 1)
        save_videos(urls)
        return True, removed, len(urls)
    return False, None, len(urls)

def clear_videos():
    save_videos([])
    return True

def extract_tiktok_urls(text):
    pattern = r'https?://(?:vt\.tiktok\.com/|www\.tiktok\.com/|tiktok\.com/)[^\s]+'
    return re.findall(pattern, text)

# ==================== PROXY LOGGER ====================

class ProxyLogger:
    def __init__(self):
        self.used_proxies = self.load_json(PROXY_LOG_FILE)
        self.blacklisted = self.load_json(PROXY_BLACKLIST_FILE)
    
    def load_json(self, file):
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_json(self, file, data):
        try:
            with open(file, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def log_used(self, proxy, status, video=""):
        if proxy not in self.used_proxies:
            self.used_proxies[proxy] = {'count': 0, 'status': [], 'videos': []}
        self.used_proxies[proxy]['count'] += 1
        self.used_proxies[proxy]['status'].append({'time': str(datetime.now()), 'status': status, 'video': video})
        if video and video not in self.used_proxies[proxy]['videos']:
            self.used_proxies[proxy]['videos'].append(video)
        self.save_json(PROXY_LOG_FILE, self.used_proxies)
    
    def blacklist(self, proxy, reason=""):
        if proxy not in self.blacklisted:
            self.blacklisted[proxy] = {'time': str(datetime.now()), 'reason': reason}
        self.save_json(PROXY_BLACKLIST_FILE, self.blacklisted)
    
    def is_blacklisted(self, proxy):
        return proxy in self.blacklisted
    
    def get_stats(self):
        return {'used': len(self.used_proxies), 'blacklisted': len(self.blacklisted)}

# ==================== AUTO LIKE BOT ====================

class AutoLikeBot:
    def __init__(self):
        self.proxies = []
        self.request_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.logger = ProxyLogger()
        self.is_running = True
        self.processing = False
        
    def load_proxies(self):
        proxies = []
        if os.path.exists(PREMIUM_PROXY_FILE):
            try:
                with open(PREMIUM_PROXY_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            proxy = f"http://{line}"
                            if not self.logger.is_blacklisted(proxy):
                                proxies.append(proxy)
            except:
                pass
        
        if not proxies:
            fallback = [
                "http://45.155.221.114:80",
                "http://45.156.196.106:80",
                "http://194.113.111.126:80",
            ]
            proxies.extend(fallback)
        
        random.shuffle(proxies)
        self.proxies = proxies
        return len(proxies)
    
    def get_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies.pop(0)
        self.proxies.append(proxy)
        return {'http': proxy, 'https': proxy}
    
    def get_service_id(self, session):
        try:
            response = session.post(
                'https://jasatambahfollowers.com/ajax/order/services.php',
                data={'category': 'tiktok'},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15,
                verify=False
            )
            soup = BeautifulSoup(response.text, 'html.parser')
            for option in soup.find_all('option'):
                text = option.text.lower()
                if 'like' in text and ('gratis' in text or 'free' in text):
                    return option.get('value')
            return None
        except:
            return None
    
    def send_like_to_url(self, target_url):
        if self.processing:
            return {"success": False, "message": "Sedang memproses request lain"}
        
        self.processing = True
        
        try:
            if not target_url:
                self.processing = False
                return {"success": False, "message": "URL tidak valid"}
            
            proxy = self.get_proxy()
            if not proxy:
                self.load_proxies()
                proxy = self.get_proxy()
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': random.choice(USER_AGENTS),
                'Referer': 'https://jasatambahfollowers.com/',
                'Origin': 'https://jasatambahfollowers.com',
            })
            session.proxies = proxy
            session.verify = False
            
            proxy_url = proxy.get('http', '')
            
            service_id = self.get_service_id(session)
            if not service_id:
                self.logger.log_used(proxy_url, "FAILED", target_url)
                self.processing = False
                return {"success": False, "message": "Gagal dapat service ID"}
            
            response = session.post(
                'https://jasatambahfollowers.com/',
                data={'service': service_id, 'target': target_url, 'jumlah': '10'},
                timeout=20,
                allow_redirects=True,
                verify=False
            )
            
            text = response.text.lower()
            
            if 'sukses' in text or 'berhasil' in text:
                self.success_count += 1
                self.request_count += 1
                self.logger.log_used(proxy_url, "SUCCESS", target_url)
                self.processing = False
                return {"success": True, "message": "✅ +10 Likes!", "url": target_url}
            elif 'limit' in text or 'maksimal' in text or 'sudah pernah' in text:
                self.fail_count += 1
                self.request_count += 1
                self.logger.log_used(proxy_url, "LIMIT", target_url)
                self.logger.blacklist(proxy_url, "Limit reached")
                self.processing = False
                return {"success": False, "message": "⚠️ Limit tercapai", "url": target_url}
            else:
                self.fail_count += 1
                self.request_count += 1
                self.logger.log_used(proxy_url, "FAILED", target_url)
                self.processing = False
                return {"success": False, "message": "❌ Gagal", "url": target_url}
                
        except Exception as e:
            self.fail_count += 1
            self.processing = False
            return {"success": False, "message": f"❌ Error: {str(e)[:30]}", "url": target_url}
    
    def get_stats(self):
        return {
            "running": self.is_running,
            "request": self.request_count,
            "success": self.success_count,
            "fail": self.fail_count,
            "total_likes": self.success_count * 10,
            "videos": len(load_videos()),
            "proxies_left": len(self.proxies),
            "proxy_stats": self.logger.get_stats()
        }

# ==================== TELEGRAM HANDLER ====================

telegram_offset = 0
bot_instance = None
telegram_running = True

def send_telegram(chat_id, text):
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

def get_updates():
    """Ambil update dari Telegram dengan PERSISTENT OFFSET"""
    global telegram_offset
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {'offset': telegram_offset, 'timeout': 25}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            results = r.json().get('result', [])
            
            # Update offset berdasarkan update_id terbaru
            for update in results:
                update_id = update['update_id']
                if update_id >= telegram_offset:
                    telegram_offset = update_id + 1
                    save_offset(telegram_offset)  # SIMPAN KE FILE!
                    print(f"  💾 Offset saved: {telegram_offset}")
            
            return results
        return []
    except Exception as e:
        print(f"  ⚠️ Get updates error: {e}")
        return []

def handle_message(msg):
    global bot_instance
    
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    message_id = msg['message_id']
    text = msg.get('text', '').strip()
    
    # Cek admin
    if user_id != TELEGRAM_ADMIN_ID:
        send_telegram(chat_id, "❌ Akses ditolak!")
        return
    
    # Anti-spam berdasarkan message_id
    if message_id in processed_messages:
        print(f"  ⏭️ Skip message {message_id} (sudah diproses)")
        return
    processed_messages.append(message_id)
    
    print(f"  📨 Process message {message_id}: {text[:50] if text else '(empty)'}")
    
    # ========== SINGLE SHOT ==========
    if text and not text.startswith('/'):
        tiktok_urls = extract_tiktok_urls(text)
        if tiktok_urls:
            send_telegram(chat_id, f"🎯 *SINGLE SHOT!*\n📹 Memproses {len(tiktok_urls)} link...")
            
            results = []
            for i, url in enumerate(tiktok_urls):
                send_telegram(chat_id, f"🔄 [{i+1}/{len(tiktok_urls)}] Memproses...")
                result = bot_instance.send_like_to_url(url)
                time.sleep(2)
                results.append(result)
            
            success_count = sum(1 for r in results if r['success'])
            
            if success_count > 0:
                summary = f"✅ *BERHASIL!*\n✅ Berhasil: *{success_count}* like\n📈 Total Like: *{success_count * 10}* likes"
            else:
                summary = f"❌ *GAGAL!*\n{results[0]['message'] if results else 'Error'}"
            
            send_telegram(chat_id, summary)
            return
    
    # ========== COMMANDS ==========
    
    if text == '/start':
        stats = bot_instance.get_stats()
        menu = f"""🤖 *HIRAKO TIKTOK BOT*

📊 *STATUS:*
📹 Video: *{stats['videos']}*
✅ Total Like: *{stats['total_likes']}*

📋 *PERINTAH:*
/start - Menu ini
/add url - Tambah video
/list - Lihat video
/remove 1 - Hapus video
/clear - Hapus semua
/status - Cek status
/stats - Statistik
/skip - Skip semua pesan lama
/help - Bantuan

💡 *Kirim link TikTok langsung!*"""
        send_telegram(chat_id, menu)
    
    elif text == '/help':
        help_msg = """📖 *PANDUAN BOT*

🎯 *SINGLE SHOT*
Kirim link TikTok → langsung like!

📹 *MANAJEMEN VIDEO*
/add url - Tambah video
/list - Lihat semua
/remove 1 - Hapus nomor 1
/clear - Hapus semua

🛠️ *UTILITY*
/skip - Skip semua pesan lama (STOP SPAM!)
/status - Status bot
/stats - Statistik lengkap

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, help_msg)
    
    elif text == '/skip':
        global telegram_offset
        telegram_offset = 999999999
        save_offset(telegram_offset)
        send_telegram(chat_id, "✅ *BERHASIL SKIP SEMUA PESAN LAMA!*\n\nBot sekarang hanya akan membaca pesan baru.\n\nRestart bot jika perlu.")
    
    elif text.startswith('/add'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_telegram(chat_id, "❌ Gunakan: /add <url>")
            return
        
        urls_input = parts[1].strip()
        tiktok_urls = extract_tiktok_urls(urls_input)
        
        if not tiktok_urls:
            send_telegram(chat_id, "❌ Tidak ada link TikTok valid!")
            return
        
        added = 0
        for url in tiktok_urls:
            success, total = add_video(url)
            if success:
                added += 1
        
        send_telegram(chat_id, f"✅ Berhasil menambah *{added}* video!\n📹 Total: *{total}* video")
    
    elif text == '/list':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 *Belum ada video!*")
            return
        
        msg = f"📹 *DAFTAR VIDEO ({len(videos)}):*\n\n"
        for i, url in enumerate(videos, 1):
            short = url[:50] + "..." if len(url) > 50 else url
            msg += f"{i}. {short}\n"
            if len(msg) > 3500:
                msg += f"\n... dan {len(videos)-i} video lainnya"
                break
        send_telegram(chat_id, msg)
    
    elif text.startswith('/remove'):
        parts = text.split()
        if len(parts) < 2:
            send_telegram(chat_id, "❌ Gunakan: /remove <nomor>")
            return
        
        try:
            index = int(parts[1])
            success, removed, total = remove_video(index)
            if success:
                send_telegram(chat_id, f"✅ Hapus video nomor *{index}*\n📹 Sisa: *{total}* video")
            else:
                send_telegram(chat_id, f"❌ Nomor *{index}* tidak valid!")
        except ValueError:
            send_telegram(chat_id, "❌ Masukkan nomor yang valid!")
    
    elif text == '/clear':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 Tidak ada video!")
            return
        
        clear_videos()
        send_telegram(chat_id, f"🗑️ *Semua video dihapus!* ({len(videos)} video)")
    
    elif text == '/status':
        stats = bot_instance.get_stats()
        msg = f"""📊 *STATUS BOT*

✅ Sukses: *{stats['success']}* likes
❌ Gagal: *{stats['fail']}* request
📈 Total: *{stats['total_likes']}* likes
🌐 Proxy: *{stats['proxies_left']}* tersisa
📌 Offset: `{telegram_offset}`"""
        send_telegram(chat_id, msg)
    
    elif text == '/stats':
        stats = bot_instance.get_stats()
        proxy_stats = stats['proxy_stats']
        
        msg = f"""📈 *STATISTIK LENGKAP*

✅ Sukses: *{stats['success']}* likes
❌ Gagal: *{stats['fail']}* request
📈 Total: *{stats['total_likes']}* likes

📝 Proxy dipakai: *{proxy_stats['used']}*
🚫 Blacklist: *{proxy_stats['blacklisted']}*
📡 Sisa: *{stats['proxies_left']}*

📌 Offset: `{telegram_offset}`"""
        send_telegram(chat_id, msg)
    
    elif text.startswith('/'):
        send_telegram(chat_id, f"❌ Perintah tidak dikenal!\nKetik /help")
    
    elif text:
        send_telegram(chat_id, f"💡 *Kirim link TikTok untuk like!*\nContoh: `https://vt.tiktok.com/xxx`")

def telegram_worker():
    global telegram_offset
    time.sleep(2)
    
    send_telegram(TELEGRAM_ADMIN_ID, f"""✅ *HIRAKO BOT ONLINE!*

📌 *Current Offset:* `{telegram_offset}`

🛠️ *Jika bot masih spam pesan lama, kirim:*
`/skip`

💡 *Kirim link TikTok langsung untuk like!*""")
    
    print(f"\n✅ Telegram Bot Connected!")
    print(f"   📌 Current Offset: {telegram_offset}")
    print(f"   💾 Offset file: {OFFSET_FILE}")
    
    while telegram_running:
        try:
            updates = get_updates()
            for update in updates:
                if 'message' in update:
                    handle_message(update['message'])
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
            time.sleep(5)

# ==================== MAIN ====================

def main():
    global bot_instance, telegram_running, telegram_offset
    
    show_banner()
    
    print("="*55)
    print("     🤖 HIRAKO SINGLE SHOT BOT 🤖")
    print("="*55)
    
    # LOAD OFFSET YANG TERSIMPAN
    telegram_offset = load_offset()
    print(f"\n📌 Load offset from file: {telegram_offset}")
    
    # Buat instance bot
    bot_instance = AutoLikeBot()
    bot_instance.load_proxies()
    
    # Start Telegram thread
    print("\n🤟 Menghubungkan ke Telegram...")
    telegram_thread = threading.Thread(target=telegram_worker, daemon=True)
    telegram_thread.start()
    
    print("\n✅ BOT AKTIF!")
    print("📱 Buka Telegram dan kirim /skip untuk skip pesan lama")
    print("\nTekan Ctrl+C untuk menghentikan bot\n")
    print("="*55)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        telegram_running = False
        print("\n\n📊 STATISTIK FINAL")
        print(f"   ✅ Sukses: {bot_instance.success_count} likes")
        print(f"   📌 Final Offset: {telegram_offset}")
        print("\n👋 Bot dihentikan.\n")

if __name__ == "__main__":
    main()
