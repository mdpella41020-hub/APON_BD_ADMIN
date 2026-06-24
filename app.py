import os, time, json, random, socket, threading, asyncio
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Import authentication functions
from JwtGen import (
    GeNeRaTeAccEss, EncRypTMajoRLoGin, MajorLogin, DecRypTMajoRLoGin,
    GetLoginData, DecRypTLoGinDaTa, xAuThSTarTuP
)

# ---------- Global data ----------
connected_clients = {}          # uid -> client object
connected_clients_lock = threading.Lock()
active_spam_targets = {}        # target uid -> True
active_spam_lock = threading.Lock()

# ---------- Packet functions ----------
def EnC_Uid(H):
    e, H = [], int(H)
    while H:
        e.append((H & 0x7F) | (0x80 if H > 0x7F else 0))
        H >>= 7
    return bytes(e).hex()

def CrEaTe_ProTo(fields):
    def EnC_Vr(N):
        if N < 0:
            return b''
        H = []
        while True:
            b = N & 0x7F
            N >>= 7
            if N:
                b |= 0x80
            H.append(b)
            if not N:
                break
        return bytes(H)
    def CrEaTe_VarianT(field_number, value):
        field_header = (field_number << 3) | 0
        return EnC_Vr(field_header) + EnC_Vr(value)
    def CrEaTe_LenGTh(field_number, value):
        field_header = (field_number << 3) | 2
        encoded_value = value.encode() if isinstance(value, str) else value
        return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet

def GeneRaTePk(Pk, N, K, V):
    def EnC_PacKeT(HeX, K, V):
        return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()
    def DecodE_HeX(H):
        return hex(H)[2:].zfill(2)
    PkEnc = EnC_PacKeT(Pk, K, V)
    _ = DecodE_HeX(len(PkEnc) // 2)
    if len(_) == 2:
        HeadEr = N + "000000"
    elif len(_) == 3:
        HeadEr = N + "00000"
    elif len(_) == 4:
        HeadEr = N + "0000"
    elif len(_) == 5:
        HeadEr = N + "000"
    else:
        HeadEr = N + "000000"
    return bytes.fromhex(HeadEr + _ + PkEnc)

def openroom(K, V):
    fields = {
        1: 2,
        2: {
            1: 1, 2: 15, 3: 5, 4: "[FFFF00]ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ", 5: "1", 6: 12, 7: 1, 8: 1, 9: 1,
            11: 1, 12: 2, 14: 36981056,
            15: {1: "IDC3", 2: 126, 3: "ME"},
            16: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000f\u000e\u0016\u0019\u001a \u001d",
            18: 2368584, 27: 1, 34: "\u0000\u0001", 40: "en", 48: 1,
            49: {1: 21}, 50: {1: 36981056, 2: 2368584, 5: 2}
        }
    }
    return GeneRaTePk(CrEaTe_ProTo(fields).hex(), '0E15', K, V)

def spmroom(K, V, uid):
    fields = {1: 22, 2: {1: int(uid)}}
    return GeneRaTePk(CrEaTe_ProTo(fields).hex(), '0E15', K, V)

# ---------- Spam worker with reconnection ----------
def send_spam_from_all_accounts(target_id):
    with connected_clients_lock:
        clients = list(connected_clients.values())
    for client in clients:
        # If socket is dead, try to reconnect
        if not client.online_sock or client._need_reconnect:
            print(f"[{client.uid}] Reconnecting...")
            client.reconnect()
            if not client.online_sock:
                continue
        try:
            client.online_sock.send(openroom(client.key, client.iv))
            print(f"[{client.uid}] Room khola")
            time.sleep(1.5)
            for i in range(10):
                client.online_sock.send(spmroom(client.key, client.iv, target_id))
                print(f"[{client.uid}] {target_id} ko spam bheja - {i+1}")
                time.sleep(0.2)
        except (BrokenPipeError, OSError) as e:
            print(f"[{client.uid}] Error: {e} -> reconnecting")
            client._need_reconnect = True
        except Exception as e:
            print(f"[{client.uid}] Other error: {e}")

def spam_worker(target_id, duration_minutes):
    print(f"Target {target_id} pe spam start ({duration_minutes} min)")
    start_time = datetime.now()
    while True:
        with active_spam_lock:
            if target_id not in active_spam_targets:
                break
            if duration_minutes:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration_minutes * 60:
                    del active_spam_targets[target_id]
                    break
        try:
            send_spam_from_all_accounts(target_id)
            time.sleep(60)
        except Exception as e:
            print(f"Spam error: {e}")
            time.sleep(1)

# ---------- Account client with auto-reconnect ----------
class FF_CLient:
    def __init__(self, uid, password):
        self.uid = uid
        self.password = password
        self.key = None
        self.iv = None
        self.auth_token = None
        self.online_sock = None
        self.running = False
        self._need_reconnect = False
        self._connect()

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _full_auth(self):
        open_id, access_token = self._run_async(GeNeRaTeAccEss(self.uid, self.password))
        if not open_id or not access_token:
            return False
        payload = self._run_async(EncRypTMajoRLoGin(open_id, access_token))
        login_res = self._run_async(MajorLogin(payload))
        if not login_res:
            return False
        dec = self._run_async(DecRypTMajoRLoGin(login_res))
        self.key = dec.key
        self.iv = dec.iv
        token = dec.token
        timestamp = dec.timestamp
        account_uid = dec.account_uid
        login_data = self._run_async(GetLoginData(dec.url, payload, token))
        if not login_data:
            return False
        ports = self._run_async(DecRypTLoGinDaTa(login_data))
        online_ip, online_port = ports.Online_IP_Port.split(":")
        self.online_ip = online_ip
        self.online_port = int(online_port)
        self.auth_token = self._run_async(xAuThSTarTuP(
            int(account_uid), token, int(timestamp), self.key, self.iv
        ))
        return True

    def _connect_online(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.online_ip, self.online_port))
        sock.send(bytes.fromhex(self.auth_token))
        resp = sock.recv(4096)
        if not resp:
            sock.close()
            return None
        print(f"[+] {self.uid} Online connected")
        return sock

    def _reader(self, sock):
        while self.running:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                # Optionally handle responses (not needed for spam)
            except Exception as e:
                print(f"[{self.uid}] Reader error: {e}")
                break
        self.running = False
        self._need_reconnect = True

    def _connect(self):
        if not self._full_auth():
            print(f"[-] {self.uid} Auth failed")
            return
        sock = self._connect_online()
        if not sock:
            return
        self.online_sock = sock
        self.running = True
        self._need_reconnect = False
        threading.Thread(target=self._reader, args=(sock,), daemon=True).start()
        with connected_clients_lock:
            connected_clients[self.uid] = self
            print(f"Account {self.uid} online aa gaya. Total: {len(connected_clients)}")

    def reconnect(self):
        """Close old socket and reconnect."""
        if self.online_sock:
            try:
                self.online_sock.close()
            except:
                pass
        self.running = False
        self._connect()

# ---------- Load accounts from Eren.txt ----------
def load_accounts():
    accounts = []
    try:
        with open("Eren.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and ":" in line and not line.startswith("#"):
                    uid, pwd = line.split(":", 1)
                    accounts.append((uid, pwd))
    except FileNotFoundError:
        print("Eren.txt nahi mili")
    return accounts

def start_all_accounts():
    for uid, pwd in load_accounts():
        threading.Thread(target=lambda: FF_CLient(uid, pwd), daemon=True).start()
        time.sleep(3)

# ---------- Flask Web App (Hinglish, Eren Yeager) ----------
app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ ULTRA TERMINAL v3.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Rajdhani:wght@500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        /* 120FPS Smooth Premium Cyberpunk Layout */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Rajdhani', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background: radial-gradient(circle at top, #0f0c20 0%, #06040a 100%);
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Neon Text Glow Effect */
        .neon-text-cyan {
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.6), 0 0 20px rgba(0, 240, 255, 0.3);
        }
        .neon-text-magenta {
            text-shadow: 0 0 10px rgba(255, 0, 127, 0.6), 0 0 20px rgba(255, 0, 127, 0.3);
        }
        .neon-text-yellow {
            text-shadow: 0 0 10px rgba(234, 179, 8, 0.6), 0 0 20px rgba(234, 179, 8, 0.3);
        }

        /* Top Grid Neon Counters - Vibrant Colors */
        .stat-box-1 {
            background: linear-gradient(135deg, rgba(255, 0, 85, 0.1) 0%, rgba(5, 15, 28, 0.8) 100%);
            border: 1px solid rgba(255, 0, 85, 0.3);
            border-radius: 16px;
            text-align: center;
            padding: 18px 12px;
            box-shadow: 0 4px 20px rgba(255, 0, 85, 0.1);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .stat-box-1:hover {
            border-color: #ff0055;
            box-shadow: 0 0 25px rgba(255, 0, 85, 0.3);
            transform: translateY(-2px);
        }
        
        .stat-box-2 {
            background: linear-gradient(135deg, rgba(0, 210, 255, 0.1) 0%, rgba(5, 15, 28, 0.8) 100%);
            border: 1px solid rgba(0, 210, 255, 0.3);
            border-radius: 16px;
            text-align: center;
            padding: 18px 12px;
            box-shadow: 0 4px 20px rgba(0, 210, 255, 0.1);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .stat-box-2:hover {
            border-color: #00d2ff;
            box-shadow: 0 0 25px rgba(0, 210, 255, 0.3);
            transform: translateY(-2px);
        }

        .stat-val-1 {
            font-size: 2.6rem;
            font-weight: 800;
            color: #ff0055;
            text-shadow: 0 0 15px rgba(255, 0, 85, 0.6);
            line-height: 1;
            font-family: 'Orbitron', sans-serif;
        }
        .stat-val-2 {
            font-size: 2.6rem;
            font-weight: 800;
            color: #00d2ff;
            text-shadow: 0 0 15px rgba(0, 210, 255, 0.6);
            line-height: 1;
            font-family: 'Orbitron', sans-serif;
        }

        .stat-lbl {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #a0aec0;
            margin-top: 8px;
            font-weight: 700;
        }

        /* Pill Navigation Tabs */
        .nav-tab {
            background: linear-gradient(90deg, #7928ca 0%, #ff0080 100%);
            border: none;
            color: #ffffff;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 2px;
            box-shadow: 0 4px 15px rgba(255, 0, 128, 0.4);
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }

        /* Glowing Link Buttons */
        .cyber-link-btn {
            background: rgba(0, 240, 255, 0.05);
            border: 1px solid rgba(0, 240, 255, 0.3);
            color: #00f0ff;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 10px 18px;
            border-radius: 25px;
            transition: all 0.25s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .cyber-link-btn:hover {
            background: linear-gradient(135deg, #00f0ff 0%, #0072ff 100%);
            color: #000000;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.6);
            border-color: #00f0ff;
            transform: scale(1.03);
        }

        /* Glowing Cyber Container Cards */
        .cyber-panel {
            background: rgba(15, 11, 32, 0.65);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 26px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.7), inset 0 1px 2px rgba(255,255,255,0.05);
            position: relative;
        }
        .cyber-panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            border-radius: 24px;
            padding: 1px;
            background: linear-gradient(135deg, rgba(0,255,204,0.3), rgba(255,0,128,0.1), rgba(0,210,255,0.3));
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
            pointer-events: none;
        }

        .panel-title-bar {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: #00ffcc;
            text-shadow: 0 0 12px rgba(0, 255, 204, 0.4);
            margin-bottom: 22px;
        }
        .panel-indicator {
            width: 5px;
            height: 18px;
            background: #00ffcc;
            border-radius: 3px;
            box-shadow: 0 0 12px #00ffcc;
        }

        /* Rounded Deep Inputs */
        .cyber-input {
            background: rgba(5, 3, 10, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 30px;
            color: #ffffff;
            font-size: 1rem;
            padding: 14px 24px;
            width: 100%;
            outline: none;
            transition: all 0.25s ease;
            letter-spacing: 0.5px;
        }
        .cyber-input:focus {
            border-color: #ff0080;
            box-shadow: 0 0 15px rgba(255, 0, 128, 0.25), inset 0 0 8px rgba(255, 0, 128, 0.1);
        }

        /* Action Buttons with Multi-Color Gradient */
        .btn-glow-cyan {
            background: linear-gradient(135deg, #00f0ff 0%, #7928ca 50%, #ff0080 100%);
            color: #ffffff;
            font-weight: 700;
            border-radius: 30px;
            font-size: 1.05rem;
            letter-spacing: 2px;
            box-shadow: 0 4px 25px rgba(255, 0, 128, 0.35);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            will-change: transform, box-shadow;
            text-shadow: 0 1px 3px rgba(0,0,0,0.6);
        }
        .btn-glow-cyan:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 30px rgba(0, 240, 255, 0.5);
        }

        /* High Resolution Vector Target Card Style */
        .vector-card {
            background: linear-gradient(180deg, #120a2a 0%, #070412 100%);
            border: 1px solid rgba(0, 255, 204, 0.3);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            padding: 18px;
            transition: all 0.3s ease;
        }
        .vector-card:hover {
            border-color: #00ffcc;
            box-shadow: 0 12px 35px rgba(0, 255, 204, 0.25);
        }
        
        /* High Resolution Crisp Image Viewport */
        .vector-image-frame {
            width: 100%;
            height: 150px;
            border-radius: 14px;
            background-color: #030207;
            border: 1px solid rgba(255, 255, 255, 0.05);
            overflow: hidden;
            position: relative;
        }
        .vector-image-frame img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .vector-stop-btn {
            background: linear-gradient(135deg, #ff0055 0%, #b3003b 100%);
            color: #ffffff;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 9px 22px;
            border-radius: 30px;
            box-shadow: 0 4px 15px rgba(255, 0, 85, 0.4);
            transition: all 0.2s ease;
        }
        .vector-stop-btn:hover {
            box-shadow: 0 6px 25px rgba(255, 0, 85, 0.7);
            transform: scale(1.05);
        }

        /* Seamless Custom Scrollbars for Bot List */
        .panel-scroll::-webkit-scrollbar {
            width: 5px;
        }
        .panel-scroll::-webkit-scrollbar-track {
            background: transparent;
        }
        .panel-scroll::-webkit-scrollbar-thumb {
            background: #2d1a4d;
            border-radius: 10px;
        }
        .panel-scroll::-webkit-scrollbar-thumb:hover {
            background: #ff0080;
        }

        /* Message Toasts Animations */
        .toast-box {
            opacity: 0;
            transform: translateY(5px);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
        }
        .toast-box.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        .font-poppins { font-family: 'Poppins', sans-serif; }
    </style>
</head>
<body class="py-6 px-4 max-w-xl mx-auto flex flex-col justify-start">

    <header class="flex flex-col items-center justify-center my-4 text-center">
        <h1 class="text-3xl font-extrabold tracking-wider uppercase font-poppins bg-gradient-to-r from-cyan-400 via-pink-500 to-yellow-400 text-transparent bg-clip-text drop-shadow">
            ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ CONTROL PANEL
        </h1>
        <p class="text-xs font-semibold tracking-widest text-[#a0aec0] uppercase mt-1 mb-5">
            Premium Cyber Infrastructure v3.0
        </p>
        
        <div class="flex items-center gap-3 mt-1 mb-2">
            <a href="https://t.me/BD_ADMIN_CODER_OFFICIAL" class="cyber-link-btn">
                <i class="fa-brands fa-telegram text-base"></i> TELEGRAM CHANNEL
            </a>
            <a href="https://t.me/BD_ADMIN_20" target="_blank" class="cyber-link-btn" style="color: #00ffcc; border-color: rgba(0, 255, 204, 0.4); background: rgba(0, 255, 204, 0.05);">
                <i class="fa-solid fa-address-card text-base"></i> CONTACT DEVELOPER
            </a>
        </div>
    </header>

    <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="stat-box-1">
            <div class="stat-val-1" id="activeSpamCount">0</div>
            <div class="stat-lbl">Active Spam</div>
        </div>
        <div class="stat-box-2">
            <div class="stat-val-2" id="accCount">0</div>
            <div class="stat-lbl">Connected Bots</div>
        </div>
    </div>

    <div class="w-full mb-6">
        <button class="nav-tab w-full py-3.5 px-2 flex items-center justify-center gap-2 uppercase shadow-lg">
            <i class="fa-solid fa-gamepad text-sm animate-pulse"></i> Operational Core
        </button>
    </div>

    <div class="space-y-6">

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#ff0080; box-shadow:0 0 10px #ff0080;"></div>
                <i class="fa-solid fa-crosshairs text-[#ff3366]"></i>
                <h2 class="neon-text-magenta">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ UNLIMITED MODE</h2>
            </div>
            
            <div class="space-y-4">
                <input type="text" id="targetUid" class="cyber-input font-poppins text-center tracking-widest" placeholder="Enter Target UID" inputmode="numeric">
                <input type="number" id="duration" class="cyber-input hidden" placeholder="Enter Duration (Minutes)">
                
                <button id="startBtn" class="btn-glow-cyan w-full py-4 flex items-center justify-center gap-2 uppercase">
                    <i class="fa-solid fa-play text-xs"></i> Start Operation
                </button>
            </div>
            
            <div id="startMessage" class="toast-box bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl p-3 mt-3 text-sm font-medium flex items-center gap-2 font-poppins"></div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#00d2ff; box-shadow:0 0 10px #00d2ff;"></div>
                <i class="fa-solid fa-satellite-dish text-[#00d2ff]"></i>
                <h2 class="neon-text-cyan">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ ACTIVE PIPELINE</h2>
            </div>
            <div id="activeTargets" class="space-y-4">
                <div class="text-center text-sm text-gray-500 py-4 flex flex-col items-center justify-center gap-2">
                    <span class="flex items-center gap-2"><i class="fa-solid fa-mailbox opacity-40"></i> No active vectors running</span>
                </div>
            </div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#00ffcc; box-shadow:0 0 10px #00ffcc;"></div>
                <i class="fa-solid fa-robot text-[#00ffcc]"></i>
                <h2>CONNECTED ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ BOTS</h2>
            </div>
            <div class="panel-scroll overflow-y-auto max-h-[140px] space-y-2" id="accountList">
                <div class="text-center text-sm text-gray-500 py-4 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-circle-notch animate-spin text-xs text-[#00ffcc]"></i> Scanning cluster cores...
                </div>
            </div>
        </div>

        <div class="cyber-panel border border-yellow-500/20 shadow-[0_0_20px_rgba(234,179,8,0.05)]">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#eab308; box-shadow:0 0 10px #eab308;"></div>
                <i class="fa-solid fa-chart-line text-yellow-500"></i>
                <h2 class="neon-text-yellow">LIVE ANALYTICS</h2>
            </div>
            <div class="grid grid-cols-2 gap-3 text-center font-poppins">
                <div class="bg-[#0b0816] p-3 rounded-xl border border-white/5">
                    <div class="text-xs text-gray-400 font-medium mb-1">
                        <i class="fa-solid fa-eye text-emerald-400 mr-1"></i> Total Views
                    </div>
                    <span id="fbTotalViews" class="text-xl font-bold text-emerald-400 font-mono">0</span>
                </div>
                <div class="bg-[#0b0816] p-3 rounded-xl border border-white/5">
                    <div class="text-xs text-gray-400 font-medium mb-1">
                        <i class="fa-solid fa-calendar-day text-cyan-400 mr-1"></i> Today Views
                    </div>
                    <span id="fbTodayViews" class="text-xl font-bold text-cyan-400 font-mono">0</span>
                </div>
                <div class="bg-[#0b0816] p-3 rounded-xl border border-white/5">
                    <div class="text-xs text-gray-400 font-medium mb-1">
                        <i class="fa-solid fa-play text-pink-500 mr-1"></i> Total Spams
                    </div>
                    <span id="fbTotalSpamRun" class="text-xl font-bold text-pink-500 font-mono">0</span>
                </div>
                <div class="bg-[#0b0816] p-3 rounded-xl border border-white/5">
                    <div class="text-xs text-gray-400 font-medium mb-1">
                        <i class="fa-solid fa-circle-stop text-red-400 mr-1"></i> Stopped Spams
                    </div>
                    <span id="fbTotalSpamStop" class="text-xl font-bold text-red-400 font-mono">0</span>
                </div>
            </div>
        </div>

    </div>

    <footer class="mt-10 mb-4 text-center text-[11px] font-semibold text-[#a0aec0] tracking-widest uppercase font-poppins">
        System Managed & Engineered By <span class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-pink-500 font-bold">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ</span> &copy; 2026
    </footer>

    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { getDatabase, ref, onValue, set, runTransaction, onDisconnect, push, remove } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

        const firebaseConfig = {
            apiKey: "AIzaSyDOIBkl6p_HY3QBR4uwE5Z0ze2VIQ1oQPc",
            authDomain: "like-bd-penal.firebaseapp.com",
            databaseURL: "https://like-bd-penal-default-rtdb.firebaseio.com",
            projectId: "like-bd-penal",
            storageBucket: "like-bd-penal.firebasestorage.app",
            messagingSenderId: "119813395495",
            appId: "1:119813395495:web:7a992c24d32053514aaa02"
        };

        const app = initializeApp(firebaseConfig);
        const db = getDatabase(app);

        let allUsers = [];
        let allCategories = [];
        let currentAdminPin = "1234";

        // --- AUTH LOGIC ---
        onValue(ref(db, 'app_settings/admin_pin'), s => {
            if(s.exists()) currentAdminPin = String(s.val());
        });

        const todayStr = new Date().toISOString().split('T')[0];

        // ১. প্রতি রিফ্রেশ বা পেজ লোডে Today Views ও Total Views ১ করে বাড়বে
        const todayViewsRef = ref(db, `analytics/views/${todayStr}`);
        runTransaction(todayViewsRef, (currentValue) => (currentValue || 0) + 1);

        const totalViewsRef = ref(db, 'analytics/total_views');
        runTransaction(totalViewsRef, (currentValue) => (currentValue || 0) + 1);

        // ২. রিয়েলটাইম লাইভ ভিউয়ার ট্র্যাকিং ব্যাকএন্ডে কাজ করবে
        const activeBrowsersListRef = ref(db, 'analytics/active_browsers_list');
        const newPresenceRef = push(activeBrowsersListRef);
        set(newPresenceRef, true);
        onDisconnect(newPresenceRef).remove();

        // ৩. লাইভ ড্যাশবোর্ড আপডেট লিসেনার
        onValue(ref(db, 'analytics'), (snapshot) => {
            if (snapshot.exists()) {
                const data = snapshot.val();
                
                document.getElementById('fbTotalViews').innerText = data.total_views || 0;
                document.getElementById('fbTodayViews').innerText = (data.views && data.views[todayStr]) ? data.views[todayStr] : 0;
                document.getElementById('fbTotalSpamRun').innerText = data.total_spam_started || 0;
                document.getElementById('fbTotalSpamStop').innerText = data.total_spam_stopped || 0;
            }
        });

        window.logSpamStart = function() {
            runTransaction(ref(db, 'analytics/total_spam_started'), (val) => (val || 0) + 1);
        };
        window.logSpamStop = function() {
            runTransaction(ref(db, 'analytics/total_spam_stopped'), (val) => (val || 0) + 1);
        };
    </script>

    <script>
        window.profileCache = {};

        function fetchPlayerInfo(uid, callback) {
            if (window.profileCache[uid]) {
                callback(window.profileCache[uid]);
                return;
            }

            fetch(`https://dark-aura-info-api-v2.vercel.app/player-info?uid=${uid}`)
                .then(res => res.json())
                .then(data => {
                    const basic = data.basicInfo || data.playerInfo || data.data || {};
                    const nickname = basic.nickname || basic.name || 'Unknown Player';
                    const level = basic.level !== undefined ? basic.level : '—';
                    
                    fetch(`https://banner-api-g7sh.vercel.app/profile?uid=${uid}`)
                        .then(imgRes => {
                            if(imgRes.ok && imgRes.headers.get('content-type')?.startsWith('image/')) {
                                return imgRes.blob().then(blob => URL.createObjectURL(blob));
                            }
                            return imgRes.json().then(imgData => imgData.profilePic || imgData.avatar || null).catch(() => null);
                        })
                        .catch(() => null)
                        .then(imgUrl => {
                            const profileData = {
                                nickname: nickname,
                                level: level,
                                banner: imgUrl || 'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=500&q=80'
                            };
                            window.profileCache[uid] = profileData;
                            callback(profileData);
                        });
                })
                .catch(err => {
                    console.error("API Profile Fetch Error:", err);
                    callback({ nickname: 'Target Node', level: '—', banner: 'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=500&q=80' });
                });
        }

        function triggerStopOperation(uid) {
            fetch(`/stop_spam?uid=${encodeURIComponent(uid)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showToastNotification('startMessage', data.error, true);
                    } else {
                        showToastNotification('startMessage', `Vector Disconnected: ${data.status}`);
                        if(typeof window.logSpamStop === 'function') window.logSpamStop();
                        fetchStatus();
                    }
                })
                .catch(err => showToastNotification('startMessage', 'Termination Request Failed', true));
        }

        function fetchStatus() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('accCount').innerText = data.connected_accounts || data.accounts?.length || 0;
                    document.getElementById('activeSpamCount').innerText = data.active_spam.length;
                    
                    const accListDiv = document.getElementById('accountList');
                    if (data.accounts && data.accounts.length) {
                        accListDiv.innerHTML = data.accounts.map(acc => `
                            <div class="text-xs bg-[#0d091f] border border-purple-900/40 px-4 py-3 rounded-full text-gray-300 flex items-center justify-between font-poppins">
                                <span class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-[#00ffcc] shadow-[0_0_6px_#00ffcc]"></span> ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ_NODE</span>
                                <span class="text-purple-300 font-mono font-medium">${acc}</span>
                            </div>
                        `).join('');
                    } else {
                        accListDiv.innerHTML = '<div class="text-gray-500 text-sm text-center py-3"><i class="fa-solid fa-robot opacity-40 mr-1.5"></i> No active cluster servers connected</div>';
                    }

                    const targetsDiv = document.getElementById('activeTargets');
                    const activeSpam = data.active_spam || [];

                    if (activeSpam.length > 0) {
                        const placeholder = targetsDiv.querySelector('.text-center.text-gray-500');
                        if (placeholder) placeholder.remove();

                        const currentCards = targetsDiv.querySelectorAll('.vector-card');
                        currentCards.forEach(card => {
                            const cardUid = card.id.replace('card-vector-', '');
                            if (!activeSpam.includes(cardUid)) {
                                card.remove();
                            }
                        });

                        activeSpam.forEach(uid => {
                            const cardId = `card-vector-${uid}`;
                            let cardEl = document.getElementById(cardId);
                            
                            if (!cardEl) {
                                const newCardHtml = `
                                    <div id="${cardId}" class="vector-card flex flex-col gap-4">
                                        <div class="vector-image-frame flex items-center justify-center">
                                            <div id="loader-${uid}" class="absolute inset-0 flex items-center justify-center bg-[#02060b] text-[#00ffcc] text-xs font-poppins gap-2">
                                                <i class="fa-solid fa-circle-notch animate-spin text-sm"></i> Rendering Clear Viewport...
                                            </div>
                                            <img id="img-view-${uid}" src="" alt="Player Banner Asset" style="display:none;" />
                                        </div>
                                        
                                        <div class="flex items-center justify-between mt-1 pt-1 border-t border-white/5">
                                            <div class="flex flex-col font-poppins text-left">
                                                <span class="text-base font-bold text-[#00ffcc] tracking-wide" id="name-${uid}">Syncing Name...</span>
                                                <div class="flex items-center gap-3 text-xs text-gray-400 font-semibold mt-1">
                                                    <span>UID: <span class="font-mono text-white font-medium">${uid}</span></span>
                                                    <span>•</span>
                                                    <span>LEVEL: <span id="lvl-${uid}" class="text-white font-bold">--</span></span>
                                                </div>
                                            </div>
                                            
                                            <button onclick="triggerStopOperation('${uid}')" class="vector-stop-btn uppercase font-poppins flex items-center gap-1.5">
                                                <i class="fa-solid fa-hand text-[10px]"></i> Abort
                                            </button>
                                        </div>
                                    </div>
                                `;
                                targetsDiv.insertAdjacentHTML('beforeend', newCardHtml);

                                fetchPlayerInfo(uid, (profile) => {
                                    const nameEl = document.getElementById(`name-${uid}`);
                                    const lvlEl = document.getElementById(`lvl-${uid}`);
                                    const imgEl = document.getElementById(`img-view-${uid}`);
                                    const loaderEl = document.getElementById(`loader-${uid}`);

                                    if (nameEl) nameEl.innerText = profile.nickname;
                                    if (lvlEl) lvlEl.innerText = profile.level;
                                    if (imgEl && profile.banner) {
                                        imgEl.src = profile.banner;
                                        imgEl.onload = () => {
                                            if (loaderEl) loaderEl.style.display = 'none';
                                            imgEl.style.display = 'block';
                                        };
                                        imgEl.onerror = () => {
                                            if (loaderEl) loaderEl.innerHTML = `<i class="fa-solid fa-image-user text-gray-600 text-lg"></i>`;
                                        };
                                    }
                                });
                            }
                        });
                        
                        if (targetsDiv.children.length === 0) {
                            showEmptyPipelinePlaceholder(targetsDiv);
                        }
                    } else {
                        showEmptyPipelinePlaceholder(targetsDiv);
                    }
                })
                .catch(err => console.error(err));
        }

        function showEmptyPipelinePlaceholder(container) {
            container.innerHTML = '<div class="text-center text-sm text-gray-500 py-4 flex flex-col items-center justify-center gap-2"><span class="flex items-center gap-2"><i class="fa-solid fa-envelope-open opacity-40"></i> No active pipeline clusters running</span></div>';
        }

        function showToastNotification(elementId, text, isError = false) {
            const el = document.getElementById(elementId);
            el.innerHTML = isError 
                ? `<i class="fa-solid fa-triangle-exclamation"></i> <span>${text}</span>` 
                : `<i class="fa-solid fa-circle-check"></i> <span>${text}</span>`;
            
            if(isError) {
                el.classList.remove('bg-emerald-500/10', 'border-emerald-500/30', 'text-emerald-400');
                el.classList.add('bg-red-500/10', 'border-red-500/30', 'text-red-400');
            } else {
                el.classList.remove('bg-red-500/10', 'border-red-500/30', 'text-red-400');
                el.classList.add('bg-emerald-500/10', 'border-emerald-500/30', 'text-emerald-400');
            }

            el.classList.add('show');
            setTimeout(() => { el.classList.remove('show'); }, 3500);
        }

        document.getElementById('startBtn').onclick = () => {
            const uid = document.getElementById('targetUid').value.trim();
            const duration = document.getElementById('duration').value.trim();
            if (!uid) {
                showToastNotification('startMessage', 'Bhai, please target UID input karo!', true);
                return;
            }
            if (!/^\d+$/.test(uid)) {
                showToastNotification('startMessage', 'UID oboshshoi number hote hobe!', true);
                return;
            }
            
            const url = `/start_spam?uid=${encodeURIComponent(uid)}` + (duration ? `&duration=${parseInt(duration)}` : '');
            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showToastNotification('startMessage', data.error, true);
                    } else {
                        showToastNotification('startMessage', `ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ Core Deploy Success: Active`);
                        document.getElementById('targetUid').value = '';
                        if(typeof window.logSpamStart === 'function') window.logSpamStart();
                        fetchStatus();
                    }
                })
                .catch(err => showToastNotification('startMessage', 'Server Transmission Failed', true));
        };

        fetchStatus();
        setInterval(fetchStatus, 3000);
    </script>
</body>
</html>




'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    with active_spam_lock:
        active = list(active_spam_targets.keys())
    with connected_clients_lock:
        acc_list = list(connected_clients.keys())
    return jsonify({
        'connected_accounts': len(connected_clients),
        'accounts': acc_list,
        'active_spam': active
    })

@app.route('/start_spam')
def start_spam_route():
    target = request.args.get('uid')
    duration = request.args.get('duration', type=int)
    if not target:
        return jsonify({'error': 'uid parameter chahiye'}), 400
    if not connected_clients:
        return jsonify({'error': 'Koi bot online nahi hai'}), 500
    with active_spam_lock:
        if target in active_spam_targets:
            return jsonify({'error': f'{target} pe already spam chal raha hai'}), 409
        active_spam_targets[target] = True
        threading.Thread(target=spam_worker, args=(target, duration), daemon=True).start()
    return jsonify({
        'status': 'Spam shuru kar diya',
        'target': target,
        'duration_minutes': duration
    })

@app.route('/stop_spam')
def stop_spam_route():
    target = request.args.get('uid')
    if not target:
        return jsonify({'error': 'uid parameter chahiye'}), 400
    with active_spam_lock:
        if target in active_spam_targets:
            del active_spam_targets[target]
            return jsonify({'status': f'{target} ka spam band kar diya'})
        else:
            return jsonify({'error': f'{target} pe koi spam nahi chal raha'}), 404

import os

if __name__ == '__main__':
    # ব্যাকগ্রাউন্ড থ্রেড স্টার্ট করা
    threading.Thread(target=start_all_accounts, daemon=True).start()
    
    # Render-এর দেওয়া PORT খুঁজে নেওয়া, না থাকলে ডিফল্ট ৫০০০ ব্যবহার করা
    port = int(os.environ.get("PORT", 5000))
    
    # পোর্ট ভেরিয়েবলটি এখানে পাস করুন
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
