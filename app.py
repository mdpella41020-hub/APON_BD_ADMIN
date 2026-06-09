import os, time, json, random, socket, threading, asyncio
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Import authentication functions
from JwtGen import (
    GeNeRaTeAccEss, EncRypTMajoRLoGin, MajorLogin, DecRypTMajoRLoGin,
    GetLoginData, DecRypTLoGinDaTa, xAuThSTarTuP
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------- Global data ----------
connected_clients = {}
connected_clients_lock = threading.Lock()

# Per-user spam targets: user_id -> {target_uid: {start_time, duration}}
user_spam_targets = {}
user_spam_lock = threading.Lock()

# Admin password
ADMIN_PASSWORD = "apon1020"

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
            1: 1, 2: 15, 3: 5, 4: "[FFFF00]BD ADMIN", 5: "1", 6: 12, 7: 1, 8: 1, 9: 1,
            11: 1, 12: 2, 14: 36981056,
            15: {1: "IDC3", 2: 126, 3: "ME"},
            16: bytes([1,3,4,7,9,10,11,18,15,14,22,25,26,32,29]).decode('latin-1'),
            18: 2368584, 27: 1, 34: bytes([0,1]).decode('latin-1'), 40: "en", 48: 1,
            49: {1: 21}, 50: {1: 36981056, 2: 2368584, 5: 2}
        }
    }
    return GeneRaTePk(CrEaTe_ProTo(fields).hex(), '0E15', K, V)

def spmroom(K, V, uid):
    fields = {1: 22, 2: {1: int(uid)}}
    return GeneRaTePk(CrEaTe_ProTo(fields).hex(), '0E15', K, V)

# ---------- Spam worker ----------
def send_spam_from_all_accounts(target_id):
    with connected_clients_lock:
        clients = list(connected_clients.values())
    for client in clients:
        if not client.online_sock or client._need_reconnect:
            print("[" + str(client.uid) + "] Reconnecting...")
            client.reconnect()
            if not client.online_sock:
                continue
        try:
            client.online_sock.send(openroom(client.key, client.iv))
            print("[" + str(client.uid) + "] Room opened")
            time.sleep(1.5)
            for i in range(10):
                client.online_sock.send(spmroom(client.key, client.iv, target_id))
                print("[" + str(client.uid) + "] Spam sent to " + str(target_id) + " - " + str(i+1))
                time.sleep(0.2)
        except (BrokenPipeError, OSError) as e:
            print("[" + str(client.uid) + "] Error: " + str(e) + " -> reconnecting")
            client._need_reconnect = True
        except Exception as e:
            print("[" + str(client.uid) + "] Other error: " + str(e))

def spam_worker(user_id, target_id, duration_minutes):
    print("Spam started on target " + str(target_id) + " by user " + str(user_id))
    start_time = datetime.now()
    while True:
        with user_spam_lock:
            if user_id not in user_spam_targets or target_id not in user_spam_targets[user_id]:
                break
            if duration_minutes:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration_minutes * 60:
                    if target_id in user_spam_targets[user_id]:
                        del user_spam_targets[user_id][target_id]
                    break
        try:
            send_spam_from_all_accounts(target_id)
            time.sleep(60)
        except Exception as e:
            print("Spam error: " + str(e))
            time.sleep(1)
    print("Spam stopped on target " + str(target_id) + " by user " + str(user_id))

# ---------- Account client ----------
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
        print("[+] " + str(self.uid) + " Online connected")
        return sock

    def _reader(self, sock):
        while self.running:
            try:
                data = sock.recv(4096)
                if not data:
                    break
            except Exception as e:
                print("[" + str(self.uid) + "] Reader error: " + str(e))
                break
        self.running = False
        self._need_reconnect = True

    def _connect(self):
        if not self._full_auth():
            print("[-] " + str(self.uid) + " Auth failed")
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
            print("Account " + str(self.uid) + " is online. Total: " + str(len(connected_clients)))

    def reconnect(self):
        if self.online_sock:
            try:
                self.online_sock.close()
            except:
                pass
        self.running = False
        self._connect()

# ---------- Load accounts ----------
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
        print("Eren.txt not found")
    return accounts

def start_all_accounts():
    for uid, pwd in load_accounts():
        threading.Thread(target=lambda: FF_CLient(uid, pwd), daemon=True).start()
        time.sleep(3)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD ADMIN ULTRA TERMINAL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Rajdhani', sans-serif; }
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a0000 25%, #001a00 50%, #0a0a1a 75%, #1a0a00 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            color: #ffffff;
            min-height: 100vh;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        body::before {
            content: '';
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(255,0,0,0.08) 0%, transparent 50%),
                        radial-gradient(circle at 80% 50%, rgba(0,255,0,0.08) 0%, transparent 50%),
                        radial-gradient(circle at 50% 80%, rgba(255,215,0,0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }
        .brand-name {
            background: linear-gradient(90deg, #ff0000, #ff6b00, #ffd700, #00ff00, #00d2ff, #ff00ff, #ff0000);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: rainbowFlow 3s linear infinite;
            font-weight: 900;
            letter-spacing: 2px;
            filter: drop-shadow(0 0 10px rgba(255,0,0,0.5));
        }
        @keyframes rainbowFlow {
            0% { background-position: 0% center; }
            100% { background-position: 200% center; }
        }
        .brand-name-small {
            background: linear-gradient(90deg, #ff3333, #ffaa00, #ffdd44);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700;
        }
        .stat-box {
            background: linear-gradient(145deg, rgba(20,0,0,0.8), rgba(0,20,0,0.8));
            border: 1px solid rgba(255,0,0,0.3);
            border-radius: 16px;
            text-align: center;
            padding: 15px 10px;
            box-shadow: 0 0 20px rgba(255,0,0,0.1), inset 0 0 15px rgba(0,255,0,0.05);
            transition: all 0.3s ease;
        }
        .stat-box:hover {
            border-color: rgba(255,215,0,0.5);
            box-shadow: 0 0 30px rgba(255,215,0,0.2);
            transform: translateY(-2px);
        }
        .stat-val {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(180deg, #ff3333, #ffaa00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            filter: drop-shadow(0 0 8px rgba(255,50,50,0.6));
        }
        .stat-lbl {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #ff8888;
            margin-top: 4px;
            font-weight: 600;
        }
        .nav-tab {
            background: linear-gradient(145deg, #1a0000, #001a00);
            border: 1px solid rgba(255,0,0,0.3);
            color: #ff6b6b;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 1px;
            transition: all 0.25s ease;
        }
        .nav-tab.active {
            background: linear-gradient(90deg, #ff0000, #ff6b00);
            color: #ffffff;
            box-shadow: 0 0 25px rgba(255,0,0,0.5), 0 0 50px rgba(255,100,0,0.3);
            border-color: #ff6b00;
        }
        .cyber-link-btn {
            background: linear-gradient(145deg, rgba(255,0,0,0.1), rgba(0,255,0,0.05));
            border: 1px solid rgba(255,0,0,0.3);
            color: #ff6b6b;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 6px 16px;
            border-radius: 20px;
            transition: all 0.25s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .cyber-link-btn:hover {
            background: linear-gradient(90deg, #ff0000, #ff6b00);
            color: #ffffff;
            box-shadow: 0 0 20px rgba(255,0,0,0.5);
            border-color: #ff6b00;
            transform: scale(1.05);
        }
        .cyber-panel {
            background: linear-gradient(145deg, rgba(20,0,0,0.6), rgba(0,10,0,0.6), rgba(10,0,20,0.6));
            border: 1px solid rgba(255,0,0,0.2);
            border-radius: 20px;
            padding: 22px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 30px rgba(255,0,0,0.05);
            position: relative;
            overflow: hidden;
        }
        .cyber-panel::before {
            content: '';
            position: absolute;
            top: -2px; left: -2px; right: -2px; bottom: -2px;
            background: linear-gradient(45deg, #ff0000, #00ff00, #ffd700, #ff0000);
            border-radius: 22px;
            z-index: -1;
            opacity: 0.3;
            filter: blur(10px);
        }
        .panel-title-bar {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: 1px;
            color: #ff6b6b;
            text-shadow: 0 0 10px rgba(255,0,0,0.3);
            margin-bottom: 20px;
        }
        .panel-indicator {
            width: 4px;
            height: 18px;
            background: linear-gradient(180deg, #ff0000, #ff6b00);
            border-radius: 2px;
            box-shadow: 0 0 8px #ff0000;
        }
        .cyber-input {
            background: linear-gradient(145deg, #0a0000, #000a00);
            border: 1px solid rgba(255,0,0,0.3);
            border-radius: 30px;
            color: #ffffff;
            font-size: 1rem;
            padding: 14px 24px;
            width: 100%;
            outline: none;
            transition: all 0.25s ease;
        }
        .cyber-input:focus {
            border-color: #ff6b00;
            box-shadow: inset 0 0 8px rgba(255,100,0,0.2), 0 0 15px rgba(255,0,0,0.2);
        }
        .cyber-input::placeholder { color: #664444; }
        .btn-glow-cyan {
            background: linear-gradient(90deg, #ff0000, #ff6b00);
            color: #ffffff;
            font-weight: 700;
            border-radius: 30px;
            font-size: 1rem;
            letter-spacing: 1px;
            box-shadow: 0 0 20px rgba(255,0,0,0.4);
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
        }
        .btn-glow-cyan:hover {
            transform: scale(1.02);
            box-shadow: 0 0 35px rgba(255,0,0,0.7), 0 0 60px rgba(255,100,0,0.4);
            background: linear-gradient(90deg, #ff3333, #ff8800);
        }
        .btn-glow-pink {
            background: linear-gradient(90deg, #ff0055, #ff00aa);
            color: #ffffff;
            font-weight: 700;
            border-radius: 30px;
            font-size: 1rem;
            letter-spacing: 1px;
            box-shadow: 0 0 20px rgba(255,0,85,0.4);
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
        }
        .btn-glow-pink:hover {
            transform: scale(1.02);
            box-shadow: 0 0 35px rgba(255,0,85,0.7), 0 0 60px rgba(255,0,150,0.4);
            background: linear-gradient(90deg, #ff3388, #ff33cc);
        }
        .inline-stop-btn {
            background: linear-gradient(145deg, rgba(255,0,85,0.2), rgba(255,0,150,0.1));
            border: 1px solid #ff0055;
            color: #ff5588;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .inline-stop-btn:hover {
            background: linear-gradient(90deg, #ff0055, #ff00aa);
            color: #ffffff;
            box-shadow: 0 0 15px #ff0055;
            transform: scale(1.1);
        }
        .panel-scroll::-webkit-scrollbar { width: 4px; }
        .panel-scroll::-webkit-scrollbar-track { background: transparent; }
        .panel-scroll::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #ff0000, #00ff00);
            border-radius: 10px;
        }
        .toast-box {
            opacity: 0;
            transform: translateY(5px);
            transition: all 0.3s ease;
            pointer-events: none;
        }
        .toast-box.show {
            opacity: 1;
            transform: translateY(0);
        }
        .header-title {
            background: linear-gradient(90deg, #ff0000, #ffd700, #00ff00, #00d2ff, #ff00ff, #ff0000);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: rainbowFlow 4s linear infinite;
            font-weight: 900;
        }
        .footer-brand {
            background: linear-gradient(90deg, #ff3333, #ffaa00, #ffdd44);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 900;
            animation: rainbowFlow 3s linear infinite;
            background-size: 200% auto;
        }
        .subtitle-text { color: #ff8888; }
        @keyframes multiColorPulse {
            0%, 100% { box-shadow: 0 0 5px rgba(255,0,0,0.5); }
            25% { box-shadow: 0 0 15px rgba(0,255,0,0.5); }
            50% { box-shadow: 0 0 10px rgba(255,215,0,0.5); }
            75% { box-shadow: 0 0 15px rgba(255,0,255,0.5); }
        }
        .multi-pulse { animation: multiColorPulse 2s infinite; }
        .admin-badge {
            background: linear-gradient(90deg, #ffd700, #ffaa00);
            color: #000;
            font-weight: 900;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7rem;
        }
        .warning-note {
            background: linear-gradient(145deg, rgba(255,0,0,0.1), rgba(255,100,0,0.1));
            border: 1px solid rgba(255,0,0,0.3);
            border-radius: 12px;
            padding: 10px 15px;
            color: #ff8888;
            font-size: 0.85rem;
            text-align: center;
            margin-top: 10px;
        }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active { display: flex; }
        .modal-box {
            background: linear-gradient(145deg, #1a0000, #001a00);
            border: 1px solid rgba(255,0,0,0.5);
            border-radius: 20px;
            padding: 30px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 0 50px rgba(255,0,0,0.3);
        }
    </style>
</head>
<body class="py-6 px-4 max-w-xl mx-auto flex flex-col justify-start">

    <header class="flex flex-col items-center justify-center my-4 text-center">
        <h1 class="text-3xl font-extrabold tracking-wider uppercase text-shadow">
            <span class="brand-name">BD ADMIN</span> CONTROL PANEL
        </h1>
        <p class="text-xs font-semibold tracking-widest subtitle-text uppercase mt-1 mb-3">
            Premium Cyber Infrastructure v3.0
        </p>
        <div class="flex items-center gap-3 mt-1 mb-2">
            <a href="https://t.me/BD_ADMIN_CODER_OFFICIAL" target="_blank" class="cyber-link-btn">
                <i class="fa-brands fa-telegram text-base"></i> TELEGRAM CHANNEL
            </a>
            <a href="https://t.me/BD_ADMIN_20" target="_blank" class="cyber-link-btn" style="color: #00ff88; border-color: rgba(0,255,136,0.3); background: linear-gradient(145deg, rgba(0,255,136,0.1), rgba(0,200,100,0.05));">
                <i class="fa-solid fa-address-card text-base"></i> CONTACT DEVELOPER
            </a>
        </div>
    </header>

    <div class="grid grid-cols-3 gap-3 mb-6">
        <div class="stat-box">
            <div class="stat-val" id="activeSpamCount">0</div>
            <div class="stat-lbl">Active Spam</div>
        </div>
        <div class="stat-box">
            <div class="stat-val" id="autoSpamCount">0</div>
            <div class="stat-lbl">Auto Spam</div>
        </div>
        <div class="stat-box">
            <div class="stat-val" id="accCount">0</div>
            <div class="stat-lbl">Connected</div>
        </div>
    </div>

    <div class="w-full mb-6">
        <button class="nav-tab active w-full py-2.5 px-2 flex items-center justify-center gap-1.5">
            <i class="fa-solid fa-gamepad text-xs"></i> SPAM
        </button>
    </div>

    <div class="space-y-6">

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator"></div>
                <i class="fa-solid fa-crosshairs text-[#ff3366]"></i>
                <h2><span class="brand-name-small">BD ADMIN</span> UNLIMITED MODE</h2>
            </div>
            <div class="space-y-4">
                <input type="text" id="targetUid" class="cyber-input" placeholder="Enter Target UID">
                <input type="number" id="duration" class="cyber-input" placeholder="Enter Duration (Minutes) - Optional">
                <button id="startBtn" class="btn-glow-cyan w-full py-3.5 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-play text-xs"></i> START OPERATION
                </button>
            </div>
            <div id="startMessage" class="toast-box bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-3 mt-3 text-sm font-medium flex items-center gap-2"></div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:linear-gradient(180deg, #ff0055, #ff00aa); box-shadow:0 0 8px #ff0055;"></div>
                <i class="fa-solid fa-octagon-xmark text-red-500"></i>
                <h2>TERMINATION SYSTEM</h2>
            </div>
            <div class="space-y-4">
                <input type="text" id="stopTargetUid" class="cyber-input" placeholder="Enter UID to Stop">
                <button id="stopBtn" class="btn-glow-pink w-full py-3.5 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-square text-xs"></i> STOP OPERATION
                </button>
            </div>
            <div class="warning-note">
                <i class="fa-solid fa-triangle-exclamation mr-2"></i>
                Spam will take approximately 5 minutes to fully stop
            </div>
            <div id="stopMessage" class="toast-box bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-3 mt-3 text-sm font-medium flex items-center gap-2"></div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:linear-gradient(180deg, #ff0000, #ffd700); box-shadow:0 0 8px #ff0000;"></div>
                <i class="fa-solid fa-satellite-dish"></i>
                <h2><span class="brand-name-small">BD ADMIN</span> ACTIVE PIPELINE</h2>
            </div>
            <div id="activeTargets" class="text-center text-sm text-gray-500 py-2 flex flex-col items-center gap-3">
                <span class="flex items-center gap-2"><i class="fa-solid fa-envelope-open"></i> No active vectors</span>
            </div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator"></div>
                <i class="fa-solid fa-robot"></i>
                <h2>CONNECTED <span class="brand-name-small">BD ADMIN</span> BOTS</h2>
            </div>
            <div class="panel-scroll overflow-y-auto max-h-[110px] space-y-2" id="accountList">
                <div class="text-center text-sm text-gray-500 py-2 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-circle-notch animate-spin text-xs"></i> Scanning cluster cores...
                </div>
            </div>
        </div>

        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:linear-gradient(180deg, #ffd700, #ffaa00); box-shadow:0 0 8px #ffd700;"></div>
                <i class="fa-solid fa-shield-halved text-yellow-500"></i>
                <h2>ADMIN ACCESS</h2>
            </div>
            <div class="space-y-4">
                <button id="adminBtn" class="btn-glow-cyan w-full py-3.5 flex items-center justify-center gap-2" style="background: linear-gradient(90deg, #ffd700, #ffaa00);">
                    <i class="fa-solid fa-key text-xs"></i> ENTER ADMIN PANEL
                </button>
            </div>
        </div>

    </div>

    <div id="adminModal" class="modal-overlay">
        <div class="modal-box">
            <h3 class="text-xl font-bold text-center mb-4" style="color: #ff6b6b;">
                <i class="fa-solid fa-shield-halved mr-2"></i>ADMIN LOGIN
            </h3>
            <input type="password" id="adminPassword" class="cyber-input mb-4" placeholder="Enter Admin Password">
            <div class="flex gap-3">
                <button id="adminLoginBtn" class="btn-glow-cyan flex-1 py-3">LOGIN</button>
                <button id="adminCancelBtn" class="btn-glow-pink flex-1 py-3" style="background: linear-gradient(90deg, #666, #999);">CANCEL</button>
            </div>
            <div id="adminError" class="text-red-400 text-sm mt-3 text-center hidden">Wrong Password!</div>
        </div>
    </div>

    <div id="adminPanel" class="hidden space-y-6 mt-6">
        <div class="cyber-panel" style="border-color: rgba(255, 215, 0, 0.5);">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:linear-gradient(180deg, #ffd700, #ffaa00); box-shadow:0 0 8px #ffd700;"></div>
                <i class="fa-solid fa-crown text-yellow-500"></i>
                <h2>ADMIN DASHBOARD <span class="admin-badge">FULL ACCESS</span></h2>
            </div>
            <div id="adminTargets" class="text-center text-sm text-gray-500 py-2 flex flex-col items-center gap-3">
                <span class="flex items-center gap-2"><i class="fa-solid fa-spinner fa-spin"></i> Loading admin data...</span>
            </div>
            <div class="mt-4 flex gap-3">
                <button id="adminRefreshBtn" class="btn-glow-cyan flex-1 py-2.5" style="background: linear-gradient(90deg, #00aa00, #00ff00);">
                    <i class="fa-solid fa-rotate mr-2"></i>REFRESH
                </button>
                <button id="adminLogoutBtn" class="btn-glow-pink flex-1 py-2.5">
                    <i class="fa-solid fa-right-from-bracket mr-2"></i>LOGOUT
                </button>
            </div>
        </div>
    </div>

    <footer class="mt-8 text-center text-[11px] font-semibold text-[#ff8888] tracking-widest uppercase">
        System Managed & Engineered By <span class="footer-brand">BD ADMIN</span> &copy; 2026
    </footer>

    <script>
        let isAdmin = false;

        function triggerStopFromTarget(uid) {
            document.getElementById('stopTargetUid').value = uid;
            document.getElementById('stopBtn').click();
        }

        function triggerAdminStop(userId, targetUid) {
            fetch('/admin_stop_spam?user_id=' + encodeURIComponent(userId) + '&uid=' + encodeURIComponent(targetUid))
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        alert('Stopped spam for user ' + userId + ' on target ' + targetUid);
                        fetchAdminData();
                    }
                })
                .catch(err => console.error(err));
        }

        function fetchStatus() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('accCount').innerText = data.connected_accounts;
                    document.getElementById('activeSpamCount').innerText = data.active_spam.length;
                    document.getElementById('autoSpamCount').innerText = data.active_spam.length ? "1" : "0";

                    const accListDiv = document.getElementById('accountList');
                    if (data.accounts && data.accounts.length) {
                        accListDiv.innerHTML = data.accounts.map(acc => `
                            <div class="text-xs account-node px-4 py-2.5 rounded-full text-gray-300 flex items-center justify-between">
                                <span class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full account-node-dot"></span> <span class="brand-name-small">BD ADMIN</span>_NODE</span>
                                <span class="text-gray-400 font-mono">${acc}</span>
                            </div>
                        `).join('');
                    } else {
                        accListDiv.innerHTML = '<div class="text-gray-500 text-sm text-center py-2"><i class="fa-solid fa-robot opacity-40 mr-1.5"></i> No active bot servers linked</div>';
                    }

                    const targetsDiv = document.getElementById('activeTargets');
                    if (data.active_spam.length) {
                        targetsDiv.innerHTML = data.active_spam.map(t => `
                            <div class="w-full bg-[#091926] border border-[#ff0055]/20 px-4 py-2 rounded-full flex items-center justify-between shadow-inner multi-pulse">
                                <span class="flex items-center gap-2 text-xs text-gray-300 font-mono">
                                    <span class="w-1.5 h-1.5 rounded-full bg-[#ff0055] animate-pulse"></span> PIPELINE UID: ${t}
                                </span>
                                <button onclick="triggerStopFromTarget('${t}')" class="inline-stop-btn">
                                    <i class="fa-solid fa-stop text-[8px] mr-1"></i> STOP
                                </button>
                            </div>
                        `).join('');
                    } else {
                        targetsDiv.innerHTML = '<span class="text-gray-500 text-sm flex items-center gap-2 py-2"><i class="fa-solid fa-envelope-open opacity-40"></i> No active vectors running</span>';
                    }
                })
                .catch(err => console.error(err));
        }

        function fetchAdminData() {
            if (!isAdmin) return;
            fetch('/admin_data')
                .then(res => res.json())
                .then(data => {
                    const adminDiv = document.getElementById('adminTargets');
                    if (data.all_spam && Object.keys(data.all_spam).length > 0) {
                        let html = '';
                        let total = 0;
                        for (const [userId, targets] of Object.entries(data.all_spam)) {
                            for (const target of Object.keys(targets)) {
                                total++;
                                html += `
                                    <div class="w-full bg-[#1a1a00] border border-[#ffd700]/30 px-4 py-2 rounded-full flex items-center justify-between mb-2">
                                        <span class="flex items-center gap-2 text-xs text-gray-300 font-mono">
                                            <span class="w-1.5 h-1.5 rounded-full bg-[#ffd700] animate-pulse"></span>
                                            USER: ${userId} -> TARGET: ${target}
                                        </span>
                                        <button onclick="triggerAdminStop('${userId}', '${target}')" class="inline-stop-btn" style="border-color: #ffd700; color: #ffd700;">
                                            <i class="fa-solid fa-stop text-[8px] mr-1"></i> STOP
                                        </button>
                                    </div>
                                `;
                            }
                        }
                        html += '<div class="text-yellow-400 text-sm mt-2">Total Active Spam: ' + total + '</div>';
                        adminDiv.innerHTML = html;
                    } else {
                        adminDiv.innerHTML = '<span class="text-gray-500 text-sm flex items-center gap-2 py-2"><i class="fa-solid fa-envelope-open opacity-40"></i> No active spam across all users</span>';
                    }
                })
                .catch(err => console.error(err));
        }

        function showMessage(elementId, text, isError) {
            const el = document.getElementById(elementId);
            if (isError) {
                el.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> <span>' + text + '</span>';
                el.classList.remove('bg-emerald-500/10', 'border-emerald-500/30', 'text-emerald-400');
                el.classList.add('bg-red-500/10', 'border-red-500/30', 'text-red-400');
            } else {
                el.innerHTML = '<i class="fa-solid fa-circle-check"></i> <span>' + text + '</span>';
                el.classList.remove('bg-red-500/10', 'border-red-500/30', 'text-red-400');
                el.classList.add('bg-emerald-500/10', 'border-emerald-500/30', 'text-emerald-400');
            }
            el.classList.add('show');
            setTimeout(function() { el.classList.remove('show'); }, 3500);
        }

        document.getElementById('startBtn').onclick = function() {
            const uid = document.getElementById('targetUid').value.trim();
            const duration = document.getElementById('duration').value.trim();
            if (!uid) {
                showMessage('startMessage', 'Please enter a target UID!', true);
                return;
            }
            const url = '/start_spam?uid=' + encodeURIComponent(uid) + (duration ? '&duration=' + parseInt(duration) : '');
            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showMessage('startMessage', data.error, true);
                    } else {
                        showMessage('startMessage', 'BD ADMIN Core Deploy: ' + data.status, false);
                        document.getElementById('targetUid').value = '';
                        fetchStatus();
                    }
                })
                .catch(err => showMessage('startMessage', 'Server Transmission Failed', true));
        };

        document.getElementById('stopBtn').onclick = function() {
            const uid = document.getElementById('stopTargetUid').value.trim();
            if (!uid) {
                showMessage('stopMessage', 'Please enter a UID to stop!', true);
                return;
            }
            fetch('/stop_spam?uid=' + encodeURIComponent(uid))
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showMessage('stopMessage', data.error, true);
                    } else {
                        showMessage('stopMessage', 'BD ADMIN Core Aborted: ' + data.status, false);
                        document.getElementById('stopTargetUid').value = '';
                        fetchStatus();
                    }
                })
                .catch(err => showMessage('stopMessage', 'Server Transmission Failed', true));
        };

        document.getElementById('adminBtn').onclick = function() {
            document.getElementById('adminModal').classList.add('active');
        };

        document.getElementById('adminCancelBtn').onclick = function() {
            document.getElementById('adminModal').classList.remove('active');
            document.getElementById('adminError').classList.add('hidden');
        };

        document.getElementById('adminLoginBtn').onclick = function() {
            const password = document.getElementById('adminPassword').value.trim();
            fetch('/admin_login?password=' + encodeURIComponent(password))
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        isAdmin = true;
                        document.getElementById('adminModal').classList.remove('active');
                        document.getElementById('adminPanel').classList.remove('hidden');
                        document.getElementById('adminPassword').value = '';
                        document.getElementById('adminError').classList.add('hidden');
                        fetchAdminData();
                    } else {
                        document.getElementById('adminError').classList.remove('hidden');
                    }
                })
                .catch(err => console.error(err));
        };

        document.getElementById('adminLogoutBtn').onclick = function() {
            isAdmin = false;
            document.getElementById('adminPanel').classList.add('hidden');
            fetch('/admin_logout');
        };

        document.getElementById('adminRefreshBtn').onclick = function() {
            fetchAdminData();
        };

        fetchStatus();
        setInterval(fetchStatus, 3000);
        setInterval(function() { if (isAdmin) fetchAdminData(); }, 5000);
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    user_id = request.remote_addr
    with user_spam_lock:
        user_active = list(user_spam_targets.get(user_id, {}).keys())
    with connected_clients_lock:
        acc_list = list(connected_clients.keys())
    return jsonify({
        'connected_accounts': len(connected_clients),
        'accounts': acc_list,
        'active_spam': user_active
    })

@app.route('/start_spam')
def start_spam_route():
    user_id = request.remote_addr
    target = request.args.get('uid')
    duration = request.args.get('duration', type=int)

    if not target:
        return jsonify({'error': 'UID parameter is required'}), 400
    if not connected_clients:
        return jsonify({'error': 'No bots are currently online'}), 500

    with user_spam_lock:
        if user_id not in user_spam_targets:
            user_spam_targets[user_id] = {}
        if target in user_spam_targets[user_id]:
            return jsonify({'error': 'Spam already running on this target'}), 409

        user_spam_targets[user_id][target] = {
            'start_time': datetime.now(),
            'duration': duration
        }

        threading.Thread(target=spam_worker, args=(user_id, target, duration), daemon=True).start()

    return jsonify({
        'status': 'Spam started successfully',
        'target': target,
        'duration_minutes': duration
    })

@app.route('/stop_spam')
def stop_spam_route():
    user_id = request.remote_addr
    target = request.args.get('uid')

    if not target:
        return jsonify({'error': 'UID parameter is required'}), 400

    with user_spam_lock:
        if user_id in user_spam_targets and target in user_spam_targets[user_id]:
            del user_spam_targets[user_id][target]
            if not user_spam_targets[user_id]:
                del user_spam_targets[user_id]
            return jsonify({'status': 'Spam stopped for ' + target})
        else:
            return jsonify({'error': 'No spam running on this target'}), 404

@app.route('/admin_login')
def admin_login():
    password = request.args.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return jsonify({'success': True})

@app.route('/admin_data')
def admin_data():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    with user_spam_lock:
        all_data = {}
        for user_id, targets in user_spam_targets.items():
            all_data[user_id] = {}
            for target, info in targets.items():
                all_data[user_id][target] = {
                    'start_time': info['start_time'].isoformat(),
                    'duration': info['duration']
                }

    return jsonify({'all_spam': all_data})

@app.route('/admin_stop_spam')
def admin_stop_spam():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    target_user = request.args.get('user_id')
    target_uid = request.args.get('uid')

    if not target_user or not target_uid:
        return jsonify({'error': 'Missing parameters'}), 400

    with user_spam_lock:
        if target_user in user_spam_targets and target_uid in user_spam_targets[target_user]:
            del user_spam_targets[target_user][target_uid]
            if not user_spam_targets[target_user]:
                del user_spam_targets[target_user]
            return jsonify({'status': 'Stopped spam for user ' + target_user + ' on target ' + target_uid})
        else:
            return jsonify({'error': 'Spam not found'}), 404

if __name__ == '__main__':
    threading.Thread(target=start_all_accounts, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
