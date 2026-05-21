#!/usr/bin/env python3
"""
HIRAKO AUTO LIKE TIKTOK BOT - FIXED VERSION
- No spam
- Single shot langsung like sekali
- Rate limit protection
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
TELEGRAM_BOT_TOKEN = "8794092200:AAFgbuxPLGkUzLhFgFAp0q8plYl9AxmDAig"  # Token dari @BotFather
TELEGRAM_ADMIN_ID = 8440381121  # ID Telegram kamu (angka)

# File untuk menyimpan video
LINKS_FILE = "links.txt"

# File untuk proxy
PREMIUM_PROXY_FILE = "proxy1.txt"
PROXY_LOG_FILE = "used_proxies.json"
PROXY_BLACKLIST_FILE = "blacklisted_proxies.json"

# Rate limiting
MESSAGE_COOLDOWN = 3  # detik
processed_messages = deque(maxlen=50)  # Simpan 50 ID pesan terakhir

# User agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0',
]

# ==================== BANNER ====================

def show_banner():
    banner = """
\033[95m
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗  ██╗██╗██████╗  █████╗ ██╗  ██╗ ██████╗             ║
║     ██║  ██║██║██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗            ║
║     ███████║██║██████╔╝███████║█████╔╝ ██║   ██║            ║
║     ██╔══██║██║██╔══██╗██╔══██║██╔═██╗ ██║   ██║            ║
║     ██║  ██║██║██║  ██║██║  ██║██║  ██╗╚██████╔╝            ║
║     ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝             ║
║                                                              ║
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
        self.is_running = False
        self.mode = "stopped"
        self.target_per_run = 10
        self.like_sent = 0
        self.processing = False  # Cegah proses ganda
        
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
        """Kirim like ke URL tertentu (SINGLE SHOT)"""
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
                return {"success": False, "message": "⚠️ Limit tercapai (video sudah pernah di-like)", "url": target_url}
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
            "mode": self.mode,
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
    """Kirim pesan ke Telegram"""
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
    """Ambil update dari Telegram"""
    global telegram_offset
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return []
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {'offset': telegram_offset, 'timeout': 25, 'allowed_updates': ['message']}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.json().get('result', [])
        return []
    except:
        return []

def is_message_processed(message_id):
    """Cek apakah pesan sudah diproses (anti-spam)"""
    if message_id in processed_messages:
        return True
    processed_messages.append(message_id)
    return False

def handle_message(msg):
    """Handle pesan dari Telegram - FIXED ANTI SPAM"""
    global bot_instance
    
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    message_id = msg['message_id']
    text = msg.get('text', '').strip()
    
    # Cek admin
    if user_id != TELEGRAM_ADMIN_ID:
        send_telegram(chat_id, "❌ Akses ditolak!")
        return
    
    # ANTI SPAM: Cek apakah pesan sudah diproses
    if is_message_processed(message_id):
        print(f"  ⏭️ Skip message {message_id} (already processed)")
        return
    
    print(f"  📨 Process message {message_id}: {text[:50] if text else '(empty)'}")
    
    # ========== SINGLE SHOT - Kirim link langsung ==========
    # Cek apakah pesan mengandung link TikTok (dan bukan command)
    if text and not text.startswith('/'):
        tiktok_urls = extract_tiktok_urls(text)
        if tiktok_urls:
            # Kirim loading message
            send_telegram(chat_id, f"🎯 *SINGLE SHOT!*\n📹 Memproses {len(tiktok_urls)} link...\n⏳ Tunggu sebentar...")
            
            results = []
            for i, url in enumerate(tiktok_urls):
                # Send progress
                send_telegram(chat_id, f"🔄 [{i+1}/{len(tiktok_urls)}] Mengirim like ke:\n`{url[:50]}...`")
                
                # Kirim like
                result = bot_instance.send_like_to_url(url)
                time.sleep(2)  # Jeda antar request
                results.append(result)
            
            # Kirim ringkasan
            success_count = sum(1 for r in results if r['success'])
            fail_count = len(results) - success_count
            
            if success_count > 0:
                summary = f"✅ *SINGLE SHOT BERHASIL!*\n\n"
                summary += f"📊 *Hasil:*\n"
                summary += f"✅ Berhasil: *{success_count}* like\n"
                summary += f"❌ Gagal: *{fail_count}* like\n"
                summary += f"📈 Total Like: *{success_count * 10}* likes\n\n"
                
                for r in results:
                    if r['success']:
                        summary += f"✅ `{r['url'][:40]}...` → +10 Likes!\n"
                    else:
                        summary += f"❌ `{r['url'][:40]}...` → {r['message']}\n"
            else:
                summary = f"❌ *SINGLE SHOT GAGAL!*\n\n"
                summary += f"Tidak ada like yang berhasil.\n\n"
                for r in results:
                    summary += f"❌ `{r['url'][:40]}...` → {r['message']}\n"
                summary += f"\n💡 *Tips:* Mungkin video sudah pernah di-like atau limit tercapai."
            
            send_telegram(chat_id, summary)
            return
    
    # ========== COMMAND HANDLER ==========
    
    # START
    if text == '/start':
        stats = bot_instance.get_stats()
        menu = f"""🤖 *HIRAKO TIKTOK BOT*

🎯 *CARA PAKAI:*
• *Kirim link TikTok* → langsung like (SINGLE SHOT)
• /add url → tambah ke daftar
• /list → lihat daftar video

📊 *STATUS:*
📹 Video: *{stats['videos']}*
✅ Total Like: *{stats['total_likes']}* likes

📋 *PERINTAH:*
/start - Menu ini
/add url - Tambah video
/list - Lihat video
/remove 1 - Hapus video
/clear - Hapus semua
/status - Cek status
/stats - Statistik lengkap
/help - Bantuan

💡 *SINGLE SHOT:* Kirim link TikTok langsung!

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, menu)
    
    # HELP
    elif text == '/help':
        help_msg = """📖 *PANDUAN BOT*

🎯 *SINGLE SHOT (FITUR UTAMA)*
Kirim link TikTok langsung ke bot:
`https://vt.tiktok.com/xxx`
→ Bot akan like SEKALI saja!

📹 *MANAJEMEN VIDEO*
/add https://vt.tiktok.com/xxx
/list - Lihat semua video
/remove 1 - Hapus video nomor 1
/clear - Hapus semua video

📊 *INFORMASI*
/status - Status bot
/stats - Statistik lengkap

💡 *CATATAN:*
• Setiap video hanya bisa di-like sekali
• Jika kena limit, coba video lain

🔥 *HIRAKO BOT*"""
        send_telegram(chat_id, help_msg)
    
    # ADD VIDEO
    elif text.startswith('/add'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_telegram(chat_id, "❌ Gunakan: /add <url>\nContoh: /add https://vt.tiktok.com/xxx")
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
        
        if added > 0:
            send_telegram(chat_id, f"✅ Berhasil menambah *{added}* video!\n📹 Total: *{total}* video")
        else:
            send_telegram(chat_id, f"⚠️ Video sudah ada!\n📹 Total: *{total}* video")
    
    # LIST VIDEO
    elif text == '/list':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 *Belum ada video!*\nGunakan /add untuk menambah")
            return
        
        msg = f"📹 *DAFTAR VIDEO ({len(videos)}):*\n\n"
        for i, url in enumerate(videos, 1):
            short = url[:50] + "..." if len(url) > 50 else url
            msg += f"{i}. {short}\n"
            if len(msg) > 3500:
                msg += f"\n... dan {len(videos)-i} video lainnya"
                break
        send_telegram(chat_id, msg)
    
    # REMOVE VIDEO
    elif text.startswith('/remove'):
        parts = text.split()
        if len(parts) < 2:
            send_telegram(chat_id, "❌ Gunakan: /remove <nomor>\nContoh: /remove 1")
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
    
    # CLEAR VIDEO
    elif text == '/clear':
        videos = load_videos()
        if not videos:
            send_telegram(chat_id, "📹 Tidak ada video untuk dihapus!")
            return
        
        clear_videos()
        send_telegram(chat_id, f"🗑️ *Semua video dihapus!* ({len(videos)} video)")
    
    # STATUS
    elif text == '/status':
        stats = bot_instance.get_stats()
        status_text = "🟢 AKTIF" if stats['running'] else "🔴 BERHENTI"
        
        msg = f"""📊 *STATUS BOT*

Status: *{status_text}*
Mode: *Single Shot Only*
📹 Video: *{stats['videos']}*
✅ Sukses: *{stats['success']}* likes
❌ Gagal: *{stats['fail']}* request
📈 Total: *{stats['total_likes']}* likes
🌐 Proxy: *{stats['proxies_left']}* tersisa"""
        
        if stats['success'] + stats['fail'] > 0:
            rate = stats['success'] / (stats['success'] + stats['fail']) * 100
            msg += f"\n📊 Rate: *{rate:.1f}%*"
        
        send_telegram(chat_id, msg)
    
    # STATISTICS
    elif text == '/stats':
        stats = bot_instance.get_stats()
        proxy_stats = stats['proxy_stats']
        
        msg = f"""📈 *STATISTIK LENGKAP*

*Overall:*
✅ Sukses: *{stats['success']}* likes
❌ Gagal: *{stats['fail']}* request
📈 Total: *{stats['total_likes']}* likes
📡 Request: *{stats['request']}*

*Proxy:*
📝 Dipakai: *{proxy_stats['used']}*
🚫 Blacklist: *{proxy_stats['blacklisted']}*
📡 Sisa: *{stats['proxies_left']}*

*Video:*
📹 Total: *{stats['videos']}* video

💡 *Kirim link langsung untuk single shot!*"""
        send_telegram(chat_id, msg)
    
    # UNKNOWN COMMAND
    elif text.startswith('/'):
        send_telegram(chat_id, f"❌ Perintah *{text}* tidak dikenal!\nKetik /help untuk bantuan\n\n💡 *Atau kirim link langsung untuk single shot!*")
    
    # NON-COMMAND (tanpa link) - kasih tahu cara pakai
    elif text:
        send_telegram(chat_id, f"💡 *Kirim link TikTok untuk langsung like!*\n\nContoh: `https://vt.tiktok.com/xxx`\n\nAtau ketik /help untuk bantuan.")

def telegram_worker():
    """Thread untuk handle Telegram"""
    send_telegram(TELEGRAM_ADMIN_ID, """✅ *HIRAKO BOT ONLINE!*

🎯 *FITUR SINGLE SHOT*
Cukup kirim link TikTok, bot akan langsung like SEKALI!

📋 *Perintah:*
/start - Menu utama
/status - Cek status
/stats - Statistik lengkap
/help - Bantuan

💡 *Contoh:*
Kirim: `https://vt.tiktok.com/xxx`
→ Bot: ✅ +10 Likes!

🔥 *Dibuat oleh HIRAKO*""")
    
    print("\n✅ Telegram Bot Connected!")
    print("   🎯 SINGLE SHOT: Kirim link langsung!")
    print("   📋 Commands: /start, /status, /stats, /add, /list, /remove, /clear, /help")
    
    while telegram_running:
        try:
            updates = get_updates()
            for update in updates:
                if 'message' in update:
                    handle_message(update['message'])
                telegram_offset = update['update_id'] + 1
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Telegram error: {e}")
            time.sleep(5)

# ==================== MAIN ====================

def main():
    global bot_instance, telegram_running
    
    show_banner()
    
    print("\033[93m" + "="*55)
    print("     🤖 HIRAKO SINGLE SHOT BOT 🤖")
    print("="*55 + "\033[0m")
    print("\033[96m   🎯 SINGLE SHOT - Kirim link langsung like!")
    print("   ✅ Anti-Spam Protection")
    print("   ✅ Auto Proxy Rotation\033[0m")
    print("="*55)
    
    # Cek konfigurasi Telegram
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_ADMIN_ID == 123456789:
        print("\n\033[91m❌ TELEGRAM BELUM DIKONFIGURASI!\033[0m")
        print("\n\033[93mEdit script dan isi:\033[0m")
        print("   TELEGRAM_BOT_TOKEN = 'token_dari_botfather'")
        print("   TELEGRAM_ADMIN_ID = 123456789 (ganti dengan ID kamu)")
        return
    
    # Load video
    videos = load_videos()
    print(f"\n\033[92m📹 Load {len(videos)} video dari {LINKS_FILE}\033[0m")
    
    # Buat instance bot
    bot_instance = AutoLikeBot()
    bot_instance.load_proxies()
    
    # Start Telegram thread
    print("\n\033[96m🤟 Menghubungkan ke Telegram...\033[0m")
    telegram_thread = threading.Thread(target=telegram_worker, daemon=True)
    telegram_thread.start()
    
    print("\n\033[92m✅ BOT AKTIF!\033[0m")
    print("\033[96m📱 Buka Telegram dan kirim LINK atau /start\033[0m")
    print("\n\033[93m💡 FITUR SINGLE SHOT: Kirim link TikTok, bot akan like SEKALI!\033[0m")
    print("\033[93m🔒 Anti-Spam: Pesan yang sama tidak akan diproses ulang\033[0m")
    print("\n\033[93mTekan Ctrl+C untuk menghentikan bot\033[0m")
    print("="*55)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        telegram_running = False
        print("\n\n\033[93m" + "="*55)
        print("              📊 STATISTIK FINAL")
        print("="*55 + "\033[0m")
        if bot_instance:
            print(f"\033[96m   ✅ Sukses  : {bot_instance.success_count} likes\033[0m")
            print(f"\033[96m   ❌ Gagal   : {bot_instance.fail_count} request\033[0m")
            print(f"\033[96m   📈 Total   : {bot_instance.success_count * 10} likes\033[0m")
        print("\033[93m" + "="*55 + "\033[0m")
        print("\n\033[95m👋 Bot dihentikan. Terima kasih!\033[0m")
        print("\033[96m   Created by HIRAKO | Single Shot TikTok Bot\033[0m\n")

if __name__ == "__main__":
    main()