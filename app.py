import os, time, json, random, socket, threading, asyncio
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from JwtGen import (
    GeNeRaTeAccEss, EncRypTMajoRLoGin, MajorLogin, DecRypTMajoRLoGin,
    GetLoginData, DecRypTLoGinDaTa, xAuThSTarTuP
)

import requests
import urllib3
from byte import Encrypt_ID, encrypt_api
from xH import gJwt

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- Global data ----------
connected_clients = {}
connected_clients_lock = threading.Lock()
active_spam_targets = {}
active_spam_lock = threading.Lock()

friend_accounts = []
friend_accounts_lock = threading.Lock()
friend_jwt_tokens = {}
friend_jwt_lock = threading.Lock()
friend_spam_running = {}
friend_spam_stats = {}
friend_spam_stats_lock = threading.Lock()

# ============================================================
# PACKET FUNCTIONS
# ============================================================

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

# ============================================================
# FRIEND REQUEST FUNCTIONS
# ============================================================

def Load_Friend_Accounts():
    accounts = []
    try:
        with open("friend.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    parts = line.split(":", 1)
                    uid = parts[0].strip()
                    password = parts[1].strip()
                    accounts.append((uid, password))
    except FileNotFoundError:
        print("friend.txt file not found!")
    except Exception as e:
        print(f"Error reading friend.txt: {e}")
    return accounts

def Friend_UpdateJwt():
    while True:
        with friend_accounts_lock:
            accounts = friend_accounts.copy()
        for uid, pwd in accounts:
            try:
                token = gJwt(uid, pwd)
                if token:
                    with friend_jwt_lock:
                        friend_jwt_tokens[uid] = token
            except Exception:
                pass
        time.sleep(1)

def Friend_SendRequest(target_uid, token):
    try:
        enc_target = Encrypt_ID(target_uid)
        payload = f"08a7c4839f1e10{enc_target}1801"
        enc_payload = encrypt_api(payload)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0"
        }
        response = requests.post(
            "https://clientbp.ggpolarbear.com/RequestAddingFriend",
            headers=headers,
            data=bytes.fromhex(enc_payload),
            verify=False,
            timeout=10
        )
        return response
    except Exception as e:
        return None

def Friend_SpamWorker(target_uid):
    success = 0
    failed = 0
    friend_spam_running[target_uid] = True
    while friend_spam_running.get(target_uid, False):
        with friend_accounts_lock:
            accounts = friend_accounts.copy()
        for uid, _ in accounts:
            if not friend_spam_running.get(target_uid, False):
                break
            with friend_jwt_lock:
                token = friend_jwt_tokens.get(uid)
            if not token:
                failed += 1
                continue
            response = Friend_SendRequest(target_uid, token)
            if response is None:
                failed += 1
            elif response.status_code == 200:
                success += 1
            elif response.status_code == 400 and "BR_FRIEND_ALREADY_SENT_REQUEST" in response.text:
                failed += 1
            else:
                failed += 1
            with friend_spam_stats_lock:
                friend_spam_stats[target_uid] = {"success": success, "failed": failed}
            time.sleep(0.15)
    with friend_spam_stats_lock:
        if target_uid in friend_spam_stats:
            del friend_spam_stats[target_uid]
    if target_uid in friend_spam_running:
        del friend_spam_running[target_uid]

# ============================================================
# UNIFIED SPAM WORKER (Room + Friend Request Together)
# ============================================================

def send_spam_from_all_accounts(target_id):
    with connected_clients_lock:
        clients = list(connected_clients.values())
    for client in clients:
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

def unified_spam_worker(target_id, duration_minutes):
    print(f"Target {target_id} pe UNIFIED spam start (Room + Friend)")
    start_time = datetime.now()

    friend_thread = None
    with friend_accounts_lock:
        if friend_accounts and target_id not in friend_spam_running:
            friend_thread = threading.Thread(target=Friend_SpamWorker, args=(target_id,), daemon=True)
            friend_thread.start()

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

    if target_id in friend_spam_running:
        friend_spam_running[target_id] = False

# ============================================================
# ACCOUNT CLIENT
# ============================================================

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
        if self.online_sock:
            try:
                self.online_sock.close()
            except:
                pass
        self.running = False
        self._connect()

def load_accounts():
    accounts = []
    try:
        with open("room.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and ":" in line and not line.startswith("#"):
                    uid, pwd = line.split(":", 1)
                    accounts.append((uid, pwd))
    except FileNotFoundError:
        print("room.txt nahi mili")
    return accounts

def start_all_accounts():
    for uid, pwd in load_accounts():
        threading.Thread(target=lambda: FF_CLient(uid, pwd), daemon=True).start()
        time.sleep(3)


# ============================================================
# FLASK WEB APP
# ============================================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ ULTRA TERMINAL v4.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Rajdhani:wght@500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        cyberGreen: '#39ff14',
                        matrixGreen: '#00ff66',
                        darkGreen: '#003311',
                        darkSlate: '#020503',
                        neonGold: '#ffd700',
                        textGray: '#6b8e76',
                    }
                }
            }
        }
    </script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Rajdhani', sans-serif; -webkit-font-smoothing: antialiased; }
        body { background: radial-gradient(circle at top, #0f0c20 0%, #06040a 100%); color: #ffffff; min-height: 100vh; overflow-x: hidden; }
        .neon-text-cyan { text-shadow: 0 0 10px rgba(0, 240, 255, 0.6), 0 0 20px rgba(0, 240, 255, 0.3); }
        .green-glow-text { color: #39ff14; text-shadow: 0 0 8px rgba(57, 255, 20, 0.6), 0 0 20px rgba(57, 255, 20, 0.3); }

        .stat-box-1 { 
            background: linear-gradient(135deg, rgba(255, 0, 85, 0.1) 0%, rgba(5, 15, 28, 0.8) 100%); 
            border: 1px solid rgba(255, 0, 85, 0.3); 
            border-radius: 16px; 
            text-align: center; 
            padding: 14px 6px; 
            box-shadow: 0 4px 20px rgba(255, 0, 85, 0.1); 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            min-width: 0;
            flex: 1;
            overflow: hidden;
        }
        .stat-box-1:hover { border-color: #ff0055; box-shadow: 0 0 25px rgba(255, 0, 85, 0.3); transform: translateY(-2px); }
        .stat-box-2 { 
            background: linear-gradient(135deg, rgba(0, 210, 255, 0.1) 0%, rgba(5, 15, 28, 0.8) 100%); 
            border: 1px solid rgba(0, 210, 255, 0.3); 
            border-radius: 16px; 
            text-align: center; 
            padding: 14px 6px; 
            box-shadow: 0 4px 20px rgba(0, 210, 255, 0.1); 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            min-width: 0;
            flex: 1;
            overflow: hidden;
        }
        .stat-box-2:hover { border-color: #00d2ff; box-shadow: 0 0 25px rgba(0, 210, 255, 0.3); transform: translateY(-2px); }
        .stat-box-3 { 
            background: linear-gradient(135deg, rgba(57, 255, 20, 0.1) 0%, rgba(5, 15, 28, 0.8) 100%); 
            border: 1px solid rgba(57, 255, 20, 0.3); 
            border-radius: 16px; 
            text-align: center; 
            padding: 14px 6px; 
            box-shadow: 0 4px 20px rgba(57, 255, 20, 0.1); 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            min-width: 0;
            flex: 1;
            overflow: hidden;
        }
        .stat-box-3:hover { border-color: #39ff14; box-shadow: 0 0 25px rgba(57, 255, 20, 0.3); transform: translateY(-2px); }
        .stat-val-1 { font-size: 1.8rem; font-weight: 800; color: #ff0055; text-shadow: 0 0 15px rgba(255, 0, 85, 0.6); line-height: 1; font-family: 'Orbitron', sans-serif; word-break: break-all; }
        .stat-val-2 { font-size: 1.8rem; font-weight: 800; color: #00d2ff; text-shadow: 0 0 15px rgba(0, 210, 255, 0.6); line-height: 1; font-family: 'Orbitron', sans-serif; word-break: break-all; }
        .stat-val-3 { font-size: 1.8rem; font-weight: 800; color: #39ff14; text-shadow: 0 0 15px rgba(57, 255, 20, 0.6); line-height: 1; font-family: 'Orbitron', sans-serif; word-break: break-all; }
        .stat-lbl { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1.2px; color: #a0aec0; margin-top: 6px; font-weight: 700; }

        .nav-tab { background: linear-gradient(90deg, #7928ca 0%, #ff0080 100%); border: none; color: #ffffff; border-radius: 30px; font-weight: 700; font-size: 0.95rem; letter-spacing: 2px; box-shadow: 0 4px 15px rgba(255, 0, 128, 0.4); text-shadow: 0 1px 2px rgba(0,0,0,0.5); }
        .cyber-link-btn { background: rgba(0, 240, 255, 0.05); border: 1px solid rgba(0, 240, 255, 0.3); color: #00f0ff; font-size: 0.72rem; font-weight: 700; letter-spacing: 1.2px; padding: 10px 14px; border-radius: 25px; transition: all 0.25s ease; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
        .cyber-link-btn:hover { background: linear-gradient(135deg, #00f0ff 0%, #0072ff 100%); color: #000000; box-shadow: 0 0 20px rgba(0, 240, 255, 0.6); border-color: #00f0ff; transform: scale(1.03); }
        .cyber-panel { background: rgba(15, 11, 32, 0.65); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 22px; box-shadow: 0 20px 40px rgba(0,0,0,0.7), inset 0 1px 2px rgba(255,255,255,0.05); position: relative; }
        .panel-title-bar { display: flex; align-items: center; gap: 10px; font-size: 1.05rem; font-weight: 700; letter-spacing: 1.2px; color: #00ffcc; text-shadow: 0 0 12px rgba(0, 255, 204, 0.4); margin-bottom: 18px; flex-wrap: wrap; }
        .panel-indicator { width: 5px; height: 18px; background: #00ffcc; border-radius: 3px; box-shadow: 0 0 12px #00ffcc; }
        .glass-card { background: rgba(4, 12, 6, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(57, 255, 20, 0.18); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6); transition: all 0.35s cubic-bezier(.4,0,.2,1); }
        .avatar-frame { position: relative; border-radius: 1rem; overflow: hidden; flex-shrink: 0; border: 2px solid rgba(57, 255, 20, 0.4); box-shadow: 0 0 20px rgba(57, 255, 20, 0.3); }
        .banner-wrapper { position: relative; width: 100%; height: 110px; overflow: hidden; background-color: #020503; }
        .banner-bg { position: absolute; width: 100%; height: 100%; background-size: cover; background-position: center; }
        .banner-overlay { position: absolute; inset: 0; background: linear-gradient(to bottom, transparent 0%, #020503 100%); }
        .basic-info { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 0 1rem 1.25rem 1rem; position: relative; z-index: 10; }
        .basic-info .avatar-frame { width: 90px; height: 90px; margin-top: -45px; margin-bottom: 0.75rem; }
        .cyber-input { background: rgba(5, 3, 10, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 30px; color: #ffffff; font-size: 1rem; padding: 14px 24px; width: 100%; outline: none; transition: all 0.25s ease; }
        .cyber-input:focus { border-color: #ff0080; box-shadow: 0 0 15px rgba(255, 0, 128, 0.25); }
        .btn-glow-green { background: linear-gradient(135deg, #39ff14 0%, #00ff66 50%, #003311 100%); color: #ffffff; font-weight: 700; border-radius: 30px; font-size: 1.05rem; letter-spacing: 2px; box-shadow: 0 4px 25px rgba(57, 255, 20, 0.35); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .btn-glow-green:hover { transform: translateY(-2px); box-shadow: 0 6px 30px rgba(57, 255, 20, 0.5); }
        .btn-glow-red { background: linear-gradient(135deg, #ff0055 0%, #b3003b 100%); color: #ffffff; font-weight: 700; border-radius: 30px; font-size: 1.05rem; letter-spacing: 2px; box-shadow: 0 4px 25px rgba(255, 0, 85, 0.35); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .btn-glow-red:hover { transform: translateY(-2px); box-shadow: 0 6px 30px rgba(255, 0, 85, 0.5); }
        .vector-card { background: linear-gradient(180deg, #120a2a 0%, #070412 100%); border: 1px solid rgba(0, 255, 204, 0.2); border-radius: 20px; padding: 16px; transition: all 0.3s ease; }
        .vector-stop-btn { background: linear-gradient(135deg, #ff0055 0%, #b3003b 100%); color: #ffffff; font-size: 0.8rem; font-weight: 700; padding: 8px 16px; border-radius: 30px; box-shadow: 0 4px 12px rgba(255, 0, 85, 0.3); white-space: nowrap; }
        .view-more-btn { background: linear-gradient(135deg, #00ff66 0%, #003311 100%); border: 1px solid #39ff14; color: #ffffff; font-size: 0.8rem; font-weight: 700; padding: 8px 16px; border-radius: 30px; box-shadow: 0 0 10px rgba(57, 255, 20, 0.2); transition: all 0.2s ease; white-space: nowrap; }
        .view-more-btn:hover { box-shadow: 0 0 15px #39ff14; transform: scale(1.02); }
        .panel-scroll::-webkit-scrollbar { width: 5px; }
        .panel-scroll::-webkit-scrollbar-track { background: transparent; }
        .panel-scroll::-webkit-scrollbar-thumb { background: #2d1a4d; border-radius: 10px; }
        .toast-box { opacity: 0; transform: translateY(5px); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .toast-box.show { opacity: 1; transform: translateY(0); }
        .animate-fade-in-up { animation: fadeInUp 0.4s cubic-bezier(0.15, 0.85, 0.35, 1) forwards; }
        @keyframes fadeInUp { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }
        .toast-container { position: fixed; top: 1rem; right: 1rem; z-index: 1000; display: flex; flex-direction: column; gap: 0.5rem; }
        .toast { background: rgba(4, 12, 6, 0.95); border: 1px solid rgba(57, 255, 20, 0.3); border-radius: 10px; padding: 0.7rem 1.2rem; font-size: 0.85rem; color: #ecffed; box-shadow: 0 8px 30px rgba(0,0,0,0.6); backdrop-filter: blur(12px); animation: toastIn 0.3s ease; }
        @keyframes toastIn { from { opacity: 0; transform: translateX(30px); } to { opacity: 1; transform: translateX(0); } }
        .font-poppins { font-family: 'Poppins', sans-serif; }
        .cyber-paste-btn { background: linear-gradient(135deg, rgba(0, 255, 204, 0.15) 0%, rgba(0, 114, 255, 0.15) 100%); border: 1px solid rgba(0, 255, 204, 0.4); color: #00ffcc; text-shadow: 0 0 8px rgba(0, 255, 204, 0.5); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .cyber-paste-btn:hover { background: linear-gradient(135deg, #00ffcc 0%, #0072ff 100%); color: #000000; text-shadow: none; box-shadow: 0 0 15px rgba(0, 255, 204, 0.6); transform: scale(1.02); }
        .cyber-paste-btn:active { transform: scale(0.98); }
        @keyframes neonPulse { 0%, 100% { text-shadow: 0 0 10px rgba(57, 255, 20, 0.8), 0 0 20px rgba(57, 255, 20, 0.6), 0 0 30px rgba(57, 255, 20, 0.4), 0 0 40px rgba(57, 255, 20, 0.2); } 50% { text-shadow: 0 0 20px rgba(57, 255, 20, 1), 0 0 40px rgba(57, 255, 20, 0.8), 0 0 60px rgba(57, 255, 20, 0.6), 0 0 80px rgba(57, 255, 20, 0.4); } }
        .neon-title { animation: neonPulse 2s ease-in-out infinite; }

        .side-by-side { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
        .side-by-side .cyber-link-btn { flex: 1; min-width: 130px; justify-content: center; }

        .stats-grid { display: flex; gap: 8px; width: 100%; }

        @media (max-width: 380px) {
            .stat-val-1, .stat-val-2, .stat-val-3 { font-size: 1.4rem; }
            .stat-lbl { font-size: 0.55rem; letter-spacing: 0.8px; }
            .side-by-side .cyber-link-btn { font-size: 0.6rem; padding: 8px 8px; min-width: 110px; }
        }
    </style>
</head>
<body class="py-5 px-3 max-w-xl mx-auto flex flex-col justify-start selection:bg-green-500 selection:text-black">

    <!-- ENJOY Banner -->
    <div class="text-center mb-3 py-2.5 px-3 rounded-2xl" style="background: linear-gradient(135deg, rgba(0, 30, 0, 0.6) 0%, rgba(0, 10, 0, 0.8) 100%); border: 1px solid rgba(57, 255, 20, 0.3);">
        <h2 class="text-base font-black tracking-widest uppercase font-poppins neon-title" style="color: #39ff14;">
            <i class="fa-solid fa-earth-americas mr-2"></i>ENJOY<i class="fa-solid fa-earth-americas ml-2"></i>
        </h2>
    </div>

    <!-- Header -->
    <header class="flex flex-col items-center justify-center my-2 text-center">
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-wider uppercase font-poppins bg-gradient-to-r from-cyan-400 via-pink-500 to-yellow-400 text-transparent bg-clip-text drop-shadow">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ CONTROL PANEL</h1>
        <p class="text-xs font-semibold tracking-widest text-[#a0aec0] uppercase mt-1 mb-3">Premium Cyber Infrastructure v4.0</p>

        <div class="side-by-side w-full max-w-sm px-1">
            <a href="https://t.me/BD_ADMIN_CODER_OFFICIAL" target="_blank" class="cyber-link-btn">
                <i class="fa-brands fa-telegram text-sm"></i> TELEGRAM CHANNEL
            </a>
            <a href="https://t.me/BD_ADMIN_20" target="_blank" class="cyber-link-btn" style="color: #00ffcc; border-color: rgba(0, 255, 204, 0.4); background: rgba(0, 255, 204, 0.05);">
                <i class="fa-solid fa-address-card text-sm"></i> CONTACT DEV
            </a>
        </div>
    </header>

    <!-- Stats Grid -->
    <div class="stats-grid mb-4 px-1">
        <div class="stat-box-1">
            <div class="stat-val-1" id="activeSpamCount">0</div>
            <div class="stat-lbl">Active Spam</div>
        </div>
        <div class="stat-box-2">
            <div class="stat-val-2" id="friendConnectedCount">0</div>
            <div class="stat-lbl">Friend Bots</div>
        </div>
        <div class="stat-box-3">
            <div class="stat-val-3" id="accCount">0</div>
            <div class="stat-lbl">Room Bots</div>
        </div>
    </div>

    <!-- Operational Core -->
    <div class="w-full mb-4 px-1">
        <button class="nav-tab w-full py-3 px-2 flex items-center justify-center gap-2 uppercase shadow-lg">
            <i class="fa-solid fa-gamepad text-sm animate-pulse"></i> Operational Core
        </button>
    </div>

    <div class="space-y-4 px-1">

        <!-- UNIFIED PANEL: Only START, no stats, no stop -->
        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#39ff14; box-shadow:0 0 10px #39ff14;"></div>
                <i class="fa-solid fa-bolt text-[#39ff14]"></i>
                <h2 class="green-glow-text">ROOM SPAM AND FRIEND REQUEST</h2>
            </div>
            <div class="space-y-4">
                <div class="flex items-center gap-2 relative w-full">
                    <input type="text" id="targetUid" class="cyber-input font-poppins text-center tracking-widest flex-1 pr-4" placeholder="Enter Target UID" inputmode="numeric">
                    <button id="pasteUidBtn" class="cyber-paste-btn px-4 py-3.5 rounded-full text-xs font-bold font-poppins flex items-center gap-1 shrink-0 uppercase tracking-wider shadow">
                        <i class="fa-solid fa-paste"></i> Paste
                    </button>
                </div>

                <button id="startBtn" class="btn-glow-green w-full py-4 flex items-center justify-center gap-2 uppercase">
                    <i class="fa-solid fa-play text-xs"></i> Start Unified Attack
                </button>
            </div>

            <div id="startMessage" class="toast-box bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl p-3 mt-3 text-sm font-medium flex items-center gap-2 font-poppins"></div>
        </div>

        <!-- Active Pipeline -->
        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#00d2ff; box-shadow:0 0 10px #00d2ff;"></div>
                <i class="fa-solid fa-satellite-dish text-[#00d2ff]"></i>
                <h2 class="neon-text-cyan">ACTIVE PIPELINE</h2>
            </div>
            <div id="activeTargets" class="space-y-4">
                <div class="text-center text-sm text-gray-500 py-4 flex flex-col items-center justify-center gap-2">
                    <span class="flex items-center gap-2"><i class="fa-solid fa-mailbox opacity-40"></i> No active vectors running</span>
                </div>
            </div>
        </div>

        <!-- Connected Room Bots -->
        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#00ffcc; box-shadow:0 0 10px #00ffcc;"></div>
                <i class="fa-solid fa-robot text-[#00ffcc]"></i>
                <h2>CONNECTED ROOM BOTS</h2>
            </div>
            <div class="panel-scroll overflow-y-auto max-h-[140px] space-y-2" id="accountList">
                <div class="text-center text-sm text-gray-500 py-4 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-circle-notch animate-spin text-xs text-[#00ffcc]"></i> Scanning cluster cores...
                </div>
            </div>
        </div>

        <!-- Connected Friend Bots -->
        <div class="cyber-panel">
            <div class="panel-title-bar">
                <div class="panel-indicator" style="background:#39ff14; box-shadow:0 0 10px #39ff14;"></div>
                <i class="fa-solid fa-user-group text-[#39ff14]"></i>
                <h2 class="green-glow-text">CONNECTED FRIEND BOTS</h2>
            </div>
            <div class="panel-scroll overflow-y-auto max-h-[140px] space-y-2" id="friendAccountList">
                <div class="text-center text-sm text-gray-500 py-4 flex items-center justify-center gap-2">
                    <i class="fa-solid fa-circle-notch animate-spin text-xs text-[#39ff14]"></i> Loading friend accounts...
                </div>
            </div>
        </div>
    </div>

    <!-- Developer Section -->
    <section class="mt-6 text-center border-t border-green-500/10 pt-4 bg-black/20 rounded-xl p-3 mx-1">
        <p class="text-slate-400 font-mono text-[13px] tracking-widest mb-2 uppercase">Developer <span class="text-green-400 font-extrabold">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ</span></p>
        <div class="social-dock flex justify-center">
            <a href="https://t.me/BD_ADMIN_20" target="_blank" class="w-10 h-10 rounded-xl bg-black/60 border border-green-500/30 flex items-center justify-center text-cyberGreen text-lg transition-all active:scale-90" title="Telegram Node Connect">
                <i class="fa-brands fa-telegram"></i>
            </a>
        </div>
    </section>

    <footer class="mt-5 mb-3 text-center text-[11px] font-semibold text-[#a0aec0] tracking-widest uppercase font-poppins px-2">
        System Managed By <span class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-pink-500 font-bold">ᴢᴇɴᴏɴ➺ꫝᴘᴏɴ</span> &copy; 2026
    </footer>

    <div class="toast-container" id="toast-container"></div>

    <script>
        const API_BASE_URL = 'https://player-info-by-ckrpro.vercel.app/get?uid='; 
        const DEFAULT_IMG_URL = 'https://raw.githubusercontent.com/ashqking/FF-Items/main/ICONS/900000013.png';
        const PLACEHOLDER_URL = 'https://via.placeholder.com/150/020503/FFFFFF?text=Player';
        window.profileCache = {};
        window.expandedStates = {}; 
        window.activeSpamTimes = {}; 

        function filterImageUrl(url) {
            if (!url || url === PLACEHOLDER_URL || url.includes('via.placeholder.com')) return DEFAULT_IMG_URL;
            return url;
        }
        function getImageUrl(id) {
            if (!id || id === 0 || id === "0") return DEFAULT_IMG_URL;
            return `https://raw.githubusercontent.com/ashqking/FF-Items/main/ICONS/${id}.png`;
        }
        function formatTimestamp(ts) {
            if (!ts) return "N/A";
            const date = new Date(parseInt(ts) * 1000);
            return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        function calculateAge(ts) {
            if (!ts) return "N/A";
            const created = new Date(parseInt(ts) * 1000);
            const diff = new Date() - created;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            return `${days} Days`;
        }
        function playClickSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                const now = ctx.currentTime;
                osc.type = 'sine';
                osc.frequency.setValueAtTime(950, now);
                osc.frequency.exponentialRampToValueAtTime(450, now + 0.06);
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
                osc.start(now);
                osc.stop(now + 0.06);
            } catch (e) {}
        }
        function showToast(message) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            container.appendChild(toast);
            setTimeout(() => { toast.remove(); }, 3000);
        }
        function parseSignature(text) {
            if (!text || text === "No Signature") return "<i class='text-slate-600 font-normal text-[10px]'>No signature available</i>";
            let parsed = text.replace(/\[b\]/gi, '<span class="font-black">').replace(/\[c\]/gi, '<div class="text-center w-full">').replace(/\[i\]/gi, '<span class="italic">');
            const colorRegex = /\[([a-fA-F0-9]{6})\]/g;
            const parts = parsed.split(colorRegex);
            if (parts.length === 1) return parsed;
            let result = parts[0];
            for (let i = 1; i < parts.length; i += 2) {
                let color = parts[i];
                let content = parts[i + 1];
                result += `<span style="color: #${color};">${content}</span>`;
            }
            if (text.toLowerCase().includes('[c]')) result += '</div>';
            return result;
        }
        function toggleViewMore(uid) {
            playClickSound();
            const panel = document.getElementById(`expanded-block-${uid}`);
            const btn = document.getElementById(`view-btn-${uid}`);
            if (panel.classList.contains('hidden')) {
                panel.classList.remove('hidden');
                panel.classList.add('animate-fade-in-up');
                btn.innerHTML = '<i class="fa-solid fa-chevron-up text-[10px]"></i> View Less';
                window.expandedStates[uid] = true;
                loadOutfitAndWishlist(uid);
            } else {
                panel.classList.add('hidden');
                btn.innerHTML = '<i class="fa-solid fa-chevron-down text-[10px]"></i> View More';
                window.expandedStates[uid] = false;
            }
        }
        function triggerStopOperation(uid) {
            fetch(`/stop_spam?uid=${encodeURIComponent(uid)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) showToastNotification('startMessage', data.error, true);
                    else { showToastNotification('startMessage', `Vector Disconnected: ${data.status}`); fetchStatus(); }
                })
                .catch(err => showToastNotification('startMessage', 'Termination Request Failed', true));
        }

        function buildTargetCardMarkup(uid) {
            return `<div id="card-vector-${uid}" class="vector-card flex flex-col gap-2 relative overflow-hidden">
                <div class="flex flex-wrap items-center justify-between gap-3 bg-black/40 p-2.5 rounded-xl border border-white/5">
                    <div class="flex items-center gap-3 min-w-[120px] flex-1">
                        <div class="w-12 h-12 rounded-xl bg-[#030207] border border-green-500/30 overflow-hidden shrink-0 relative">
                            <img id="pAvatar-${uid}" src="${DEFAULT_IMG_URL}" onerror="this.src='${DEFAULT_IMG_URL}'" class="w-full h-full object-contain" />
                        </div>
                        <div class="flex flex-col font-poppins text-left min-w-0">
                            <span class="text-sm font-bold text-[#00ffcc] tracking-wide truncate" id="name-${uid}">Syncing Name...</span>
                            <div class="flex flex-wrap items-center gap-2 text-xs text-gray-400 font-semibold mt-0.5">
                                <span>UID: <span class="font-mono text-white font-medium">${uid}</span></span>
                                <span class="text-xs font-black tracking-widest text-cyberGreen">LVL <span id="lvl-${uid}">--</span></span>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end w-full sm:w-auto mt-2 sm:mt-0">
                        <button id="view-btn-${uid}" onclick="toggleViewMore('${uid}')" class="view-more-btn flex items-center gap-1"><i class="fa-solid fa-chevron-down text-[10px]"></i> View More</button>
                        <button onclick="triggerStopOperation('${uid}')" class="vector-stop-btn uppercase font-poppins flex items-center gap-1"><i class="fa-solid fa-hand text-[10px]"></i> STOP</button>
                        <div class="w-full text-right mt-1 flex justify-end">
                            <span class="bg-black/60 px-2 py-1 rounded-md text-[11px] text-cyberGreen font-mono font-bold tracking-widest border border-green-500/20 shadow-[0_0_5px_rgba(57,255,20,0.2)]"><i class="fa-solid fa-clock mr-1 text-xs"></i><span id="uptime-${uid}">0d 0h 0m</span></span>
                        </div>
                    </div>
                </div>
                <div id="expanded-block-${uid}" class="hidden space-y-4 mt-2 transition-all duration-300">
                    <div class="glass-card rounded-2xl relative overflow-hidden pb-4">
                        <div class="banner-wrapper"><div id="bannerBg-${uid}" class="banner-bg" style="background-image: url('${DEFAULT_IMG_URL}')"></div><div class="banner-overlay"></div></div>
                        <div class="basic-info">
                            <div class="avatar-frame w-[90px] h-[90px] mt-[-45px] mb-2 relative"><img id="pAvatarFrame-${uid}" src="${DEFAULT_IMG_URL}" onerror="this.src='${DEFAULT_IMG_URL}'" class="w-full h-full object-cover"></div>
                            <div class="flex items-center gap-2 mt-1">
                                <h2 id="pFullName-${uid}" class="text-base font-black green-glow-text font-mono truncate max-w-full">Name</h2>
                                <span id="pRegion-${uid}" class="bg-green-500/10 text-green-400 text-[9px] font-bold px-1.5 py-0.5 rounded border border-green-500/20 uppercase font-mono">N/A</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3 w-full mt-3 font-mono">
                                <div class="bg-green-950/20 backdrop-blur-md rounded-xl p-2 border border-green-500/5 flex flex-col items-center"><i class="fa-solid fa-heart text-green-400 text-base mb-0.5 drop-shadow-[0_0_6px_rgba(57,255,20,0.4)]"></i><span class="text-[8px] text-slate-400 uppercase tracking-widest font-bold">Likes</span><span id="pLikes-${uid}" class="text-sm font-black text-white green-glow-text">0</span></div>
                                <div class="bg-green-950/20 backdrop-blur-md rounded-xl p-2 border border-green-500/5 flex flex-col items-center"><i class="fa-solid fa-star text-emerald-400 text-base mb-0.5 drop-shadow-[0_0_6px_rgba(0,255,102,0.4)]"></i><span class="text-[8px] text-slate-400 uppercase tracking-widest font-bold">Experience</span><span id="pExp-${uid}" class="text-sm font-black text-white green-glow-text">0</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden border border-green-500/10 bg-black/40"><div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-cyberGreen to-matrixGreen"></div><div class="text-[11px] font-bold font-mono text-slate-200 leading-relaxed whitespace-pre-wrap" id="pSignatureHtml-${uid}"></div></div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-trophy text-amber-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Rank Status</h3></div>
                        <div class="grid grid-cols-2 gap-2 font-mono">
                            <div class="bg-green-950/10 p-2 rounded-xl border border-green-500/5 relative overflow-hidden"><span class="text-[9px] font-bold text-slate-400 block">BR Point</span><div id="pBrPoint-${uid}" class="text-sm font-black text-amber-400">0</div><div class="text-[8px] text-slate-500 uppercase truncate">Max: <span id="pBrMax-${uid}">0</span></div></div>
                            <div class="bg-green-950/10 p-2 rounded-xl border border-green-500/5 relative overflow-hidden"><span class="text-[9px] font-bold text-slate-400 block">CS Point</span><div id="pCsPoint-${uid}" class="text-sm font-black green-glow-text">0</div><div class="text-[8px] text-slate-500 uppercase truncate">Max: <span id="pCsMax-${uid}">0</span></div></div>
                        </div>
                    </div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-circle-info text-green-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Account Metrics</h3></div>
                        <div class="grid grid-cols-2 gap-2 mb-2 font-mono text-center">
                            <div class="bg-green-950/10 p-2 rounded-xl border border-green-500/5"><div class="text-[8px] text-slate-400 uppercase font-bold">Gender</div><div id="pGender-${uid}" class="text-xs font-black text-white">N/A</div></div>
                            <div class="bg-green-950/10 p-2 rounded-xl border border-green-500/5"><div class="text-[8px] text-slate-400 uppercase font-bold">Language</div><div id="pLang-${uid}" class="text-xs font-black text-white">N/A</div></div>
                        </div>
                        <div class="space-y-1 bg-black/40 p-2.5 rounded-xl text-[11px] font-mono">
                            <div class="flex justify-between border-b border-green-500/5 pb-1"><span class="text-slate-500">Created:</span><span id="pCreated-${uid}" class="font-bold text-slate-300">N/A</span></div>
                            <div class="flex justify-between border-b border-green-500/5 pb-1"><span class="text-slate-500">Last Login:</span><span id="pLogin-${uid}" class="font-bold text-slate-300">N/A</span></div>
                            <div class="text-right pt-0.5"><span class="text-[8px] text-cyberGreen font-bold uppercase">Timeline Age: <span id="pAccountAge-${uid}" class="text-white font-sans">N/A</span></span></div>
                        </div>
                    </div>
                    <div id="wishlistContainer-${uid}" class="glass-card rounded-xl p-3 relative overflow-hidden hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-gift text-green-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Wishlist Items</h3></div>
                        <div id="wishlistGrid-${uid}" class="grid grid-cols-3 gap-2 font-mono"></div>
                        <div id="wishlistLoader-${uid}" class="flex justify-center py-2"><i class="fa-solid fa-circle-notch fa-spin text-cyberGreen"></i></div>
                        <div id="wishlistEmpty-${uid}" class="text-center py-2 hidden text-slate-500 text-[10px] bg-black/20 rounded-xl font-mono">No items found inside wishlist records.</div>
                    </div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-gavel text-red-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Anti-Cheat Registry Check</h3></div>
                        <div class="flex justify-between bg-green-950/10 p-2 rounded-xl border border-green-500/5 font-mono items-center"><span class="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Current Status</span><span id="pBanStatus-${uid}" class="font-black text-xs text-green-400 drop-shadow-[0_0_6px_rgba(57,255,20,0.4)]">Safe ✔</span></div>
                    </div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-paw text-emerald-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Active Companion</h3></div>
                        <div class="flex items-center gap-3 bg-green-950/10 p-2 rounded-xl border border-green-500/5">
                            <div class="w-12 h-12 bg-black rounded-xl border border-green-500/5 overflow-hidden shrink-0"><img id="pPetImg-${uid}" src="${DEFAULT_IMG_URL}" onerror="this.src='${DEFAULT_IMG_URL}'" class="object-cover w-full h-full"></div>
                            <div class="flex-1 font-mono text-[11px] min-w-0">
                                <div class="flex justify-between items-center mb-1 pb-1 border-b border-green-500/5"><span class="text-slate-400 truncate">ID: <span id="pPetId-${uid}" class="text-white font-bold">0</span></span><span class="bg-emerald-500/10 text-emerald-400 font-black px-1.5 py-0.5 rounded text-[9px] shrink-0">LVL <span id="pPetLevel-${uid}">0</span></span></div>
                                <div class="grid grid-cols-2 gap-1 text-[9px] text-slate-500"><div class="truncate">EXP: <span id="pPetExp-${uid}" class="text-white font-bold">0</span></div><div class="truncate">Skill: <span id="pPetSkill-${uid}" class="text-white font-bold">N/A</span></div></div>
                            </div>
                        </div>
                    </div>
                    <div class="glass-card rounded-xl p-3 relative overflow-hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-shield-halved text-orange-400 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Guild Overview</h3></div>
                        <div class="space-y-2 font-mono">
                            <div class="flex justify-between items-center bg-green-950/10 p-2 rounded-xl border border-green-500/5"><span id="pGuildName-${uid}" class="text-sm font-black text-white truncate uppercase max-w-[150px]">No Guild</span><span class="bg-orange-500/10 text-orange-400 text-[9px] font-black px-2 py-0.5 rounded border border-orange-500/20 shrink-0">LVL <span id="pGuildLvl-${uid}">0</span></span></div>
                            <div class="grid grid-cols-2 gap-2 text-[11px]">
                                <div class="bg-black/40 p-2 rounded-xl border border-green-500/5 overflow-hidden"><div class="text-[8px] text-slate-500 uppercase font-bold truncate">Guild ID</div><div id="pGuildId-${uid}" class="text-white font-bold truncate">0</div></div>
                                <div class="bg-black/40 p-2 rounded-xl border border-green-500/5 overflow-hidden"><div class="text-[8px] text-slate-500 uppercase font-bold truncate">Members</div><div class="font-black text-white truncate"><span id="pGuildMem-${uid}" class="text-cyberGreen">0</span> / <span id="pGuildCap-${uid}">0</span></div></div>
                            </div>
                        </div>
                    </div>
                    <div id="guildLeaderContainer-${uid}" class="glass-card rounded-xl p-3 border-t-4 border-t-amber-500/60 relative overflow-hidden hidden">
                        <div class="flex items-center gap-2 mb-2"><i class="fa-solid fa-crown text-amber-500 text-xs"></i><h3 class="font-black tracking-widest text-white uppercase text-[10px] font-mono">Guild Commander</h3></div>
                        <div class="flex flex-col gap-3 items-center bg-green-950/5 p-2 rounded-xl">
                            <div class="avatar-frame w-14 h-14 relative"><img id="lAvatar-${uid}" src="${DEFAULT_IMG_URL}" onerror="this.src='${DEFAULT_IMG_URL}'" class="w-full h-full object-cover"><div class="absolute bottom-0 inset-x-0 text-center bg-black/80"><span class="text-white text-[8px] font-black font-mono">LVL <span id="lLevel-${uid}">0</span></span></div></div>
                            <div class="w-full text-center">
                                <h2 id="lName-${uid}" class="text-sm font-black green-glow-text font-mono truncate">Name</h2>
                                <div class="text-[9px] font-mono text-slate-400 mt-0.5 truncate">UID: <span id="lUid-${uid}" class="text-white">0</span></div>
                                <div class="grid grid-cols-2 gap-1 font-mono text-[10px] text-left mt-2">
                                    <div class="bg-black/40 p-1.5 rounded-lg border border-white/5 truncate">Likes: <span id="lLikes-${uid}" class="text-white font-bold">0</span></div>
                                    <div class="bg-black/40 p-1.5 rounded-lg border border-white/5 truncate">BR Pt: <span id="lBrRank-${uid}" class="text-amber-400 font-bold">0</span></div>
                                    <div class="bg-black/40 p-1.5 rounded-lg border border-white/5 truncate">CS Pt: <span id="lCsRank-${uid}" class="text-emerald-400 font-bold">0</span></div>
                                    <div class="bg-black/40 p-1.5 rounded-lg border border-white/5 truncate">Log: <span id="lLogin-${uid}" class="text-slate-300 font-bold">N/A</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        }

        async function fetchComprehensiveData(uid) {
            try {
                const response = await fetch(API_BASE_URL + uid);
                const data = await response.json();
                if (!response.ok || !data || !data.AccountInfo) return;
                const accInfo = data.AccountInfo || {};
                const guildInfo = data.GuildInfo || {};
                const captainInfo = data.captainBasicInfo || {};
                const petInfo = data.petInfo || {};
                const socialInfo = data.socialinfo || {};
                const creditInfo = data.creditScoreInfo || {};
                document.getElementById(`name-${uid}`).innerText = accInfo.AccountName || "Unknown Player";
                document.getElementById(`lvl-${uid}`).innerText = accInfo.AccountLevel || "--";
                if (accInfo.AccountAvatarId) {
                    const avatarUrl = filterImageUrl(getImageUrl(accInfo.AccountAvatarId));
                    document.getElementById(`pAvatar-${uid}`).src = avatarUrl;
                    document.getElementById(`pAvatarFrame-${uid}`).src = avatarUrl;
                }
                document.getElementById(`pFullName-${uid}`).innerText = accInfo.AccountName || "N/A";
                document.getElementById(`pLikes-${uid}`).innerText = (accInfo.AccountLikes || 0).toLocaleString();
                document.getElementById(`pExp-${uid}`).innerText = (accInfo.AccountEXP || 0).toLocaleString();
                document.getElementById(`pRegion-${uid}`).innerText = accInfo.AccountRegion || "N/A";
                document.getElementById(`pCreated-${uid}`).innerText = formatTimestamp(accInfo.AccountCreateTime);
                document.getElementById(`pLogin-${uid}`).innerText = formatTimestamp(accInfo.AccountLastLogin);
                document.getElementById(`pGender-${uid}`).innerText = socialInfo.gender ? socialInfo.gender.replace('Gender_', '') : "N/A";
                document.getElementById(`pLang-${uid}`).innerText = socialInfo.language ? socialInfo.language.replace('Language_', '') : "N/A";
                document.getElementById(`pAccountAge-${uid}`).innerText = calculateAge(accInfo.AccountCreateTime);
                document.getElementById(`pSignatureHtml-${uid}`).innerHTML = parseSignature(socialInfo.signature || "No Signature");
                document.getElementById(`pBrPoint-${uid}`).innerText = accInfo.BrRankPoint || 0;
                document.getElementById(`pBrMax-${uid}`).innerText = accInfo.BrMaxRank || 0;
                document.getElementById(`pCsPoint-${uid}`).innerText = accInfo.CsRankPoint || 0;
                document.getElementById(`pCsMax-${uid}`).innerText = accInfo.CsMaxRank || 0;
                if (accInfo.AccountBannerId && accInfo.AccountBannerId !== 0) {
                    document.getElementById(`bannerBg-${uid}`).style.backgroundImage = `url('${filterImageUrl(getImageUrl(accInfo.AccountBannerId))}')`;
                } else {
                    document.getElementById(`bannerBg-${uid}`).style.backgroundImage = `url('${DEFAULT_IMG_URL}')`;
                }
                if (creditInfo.creditScore !== undefined) {
                    document.getElementById(`pBanStatus-${uid}`).innerText = `Safe (Credit: ${creditInfo.creditScore})`;
                }
                document.getElementById(`pPetId-${uid}`).innerText = petInfo.id || "N/A";
                document.getElementById(`pPetLevel-${uid}`).innerText = petInfo.level || 0;
                document.getElementById(`pPetExp-${uid}`).innerText = petInfo.exp || 0;
                document.getElementById(`pPetSkill-${uid}`).innerText = petInfo.selectedSkillId || "N/A";
                if (petInfo.id && petInfo.id !== 0) {
                    document.getElementById(`pPetImg-${uid}`).src = filterImageUrl(getImageUrl(petInfo.id));
                } else {
                    document.getElementById(`pPetImg-${uid}`).src = DEFAULT_IMG_URL;
                }
                if (guildInfo.GuildName) {
                    document.getElementById(`pGuildName-${uid}`).innerText = guildInfo.GuildName;
                    document.getElementById(`pGuildId-${uid}`).innerText = guildInfo.GuildID || "N/A";
                    document.getElementById(`pGuildLvl-${uid}`).innerText = guildInfo.GuildLevel || 0;
                    document.getElementById(`pGuildMem-${uid}`).innerText = guildInfo.GuildMember || 0;
                    document.getElementById(`pGuildCap-${uid}`).innerText = guildInfo.GuildCapacity || 0;
                    document.getElementById(`guildLeaderContainer-${uid}`).classList.remove('hidden');
                }
                if (captainInfo.accountId) {
                    document.getElementById(`lName-${uid}`).innerText = captainInfo.nickname || "N/A";
                    document.getElementById(`lUid-${uid}`).innerText = captainInfo.accountId || "0";
                    document.getElementById(`lLevel-${uid}`).innerText = captainInfo.level || 0;
                    document.getElementById(`lLikes-${uid}`).innerText = (captainInfo.liked || 0).toLocaleString();
                    document.getElementById(`lBrRank-${uid}`).innerText = captainInfo.rankingPoints || 0;
                    document.getElementById(`lCsRank-${uid}`).innerText = captainInfo.csRankingPoints || 0;
                    document.getElementById(`lLogin-${uid}`).innerText = formatTimestamp(captainInfo.lastLoginAt).split(" ")[0];
                    if (captainInfo.headPic) {
                        document.getElementById(`lAvatar-${uid}`).src = filterImageUrl(getImageUrl(captainInfo.headPic));
                    } else {
                        document.getElementById(`lAvatar-${uid}`).src = DEFAULT_IMG_URL;
                    }
                }
                if (window.expandedStates[uid]) {
                    const block = document.getElementById(`expanded-block-${uid}`);
                    const btn = document.getElementById(`view-btn-${uid}`);
                    if(block && btn) {
                        block.classList.remove('hidden');
                        btn.innerHTML = '<i class="fa-solid fa-chevron-up text-[10px]"></i> View Less';
                        loadOutfitAndWishlist(uid, accInfo.AccountRegion || 'IND');
                    }
                }
            } catch (err) {
                console.error("Pipeline full node fetch failed:", err);
            }
        }
        function loadOutfitAndWishlist(uid, region = 'IND') {
            fetchWishlistData(uid, region);
        }
        async function fetchWishlistData(uid, region) {
            const wlContainer = document.getElementById(`wishlistContainer-${uid}`);
            const wlGrid = document.getElementById(`wishlistGrid-${uid}`);
            const wlLoader = document.getElementById(`wishlistLoader-${uid}`);
            const wlEmpty = document.getElementById(`wishlistEmpty-${uid}`);
            if(!wlContainer || !wlGrid) return;
            wlContainer.classList.remove('hidden');
            try {
                const response = await fetch(`/get_wishlist?uid=${uid}&region=${region}`);
                const data = await response.json();
                if(wlLoader) wlLoader.classList.add('hidden');
                if (data.error || !data.wishlist || data.wishlist.length === 0) {
                    if(wlEmpty) wlEmpty.classList.remove('hidden');
                    return;
                }
                wlGrid.innerHTML = '';
                data.wishlist.forEach(item => {
                    const itemHtml = `<div class="bg-black/60 p-1.5 rounded-xl border border-green-500/5 flex flex-col items-center justify-center"><div class="w-8 h-8 mb-1 flex items-center justify-center"><img src="${filterImageUrl(getImageUrl(item.item_id))}" onerror="this.src='${DEFAULT_IMG_URL}'" class="max-w-full max-h-full object-contain"></div><div class="text-[8px] text-slate-400 font-bold truncate w-full text-center">ID: ${item.item_id}</div></div>`;
                    wlGrid.insertAdjacentHTML('beforeend', itemHtml);
                });
            } catch (err) {
                if(wlLoader) wlLoader.classList.add('hidden');
                if(wlEmpty) wlEmpty.classList.remove('hidden');
            }
        }

        function fetchStatus() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('accCount').innerText = data.connected_accounts || data.accounts?.length || 0;
                    document.getElementById('activeSpamCount').innerText = data.active_spam.length;
                    document.getElementById('friendConnectedCount').innerText = data.friend_accounts || 0;
                    if (data.active_times) {
                        window.activeSpamTimes = data.active_times;
                    }
                    const accListDiv = document.getElementById('accountList');
                    if (data.accounts && data.accounts.length) {
                        accListDiv.innerHTML = data.accounts.map(acc => 
                            `<div class="text-xs bg-[#0d091f] border border-purple-900/40 px-4 py-3 rounded-full text-gray-300 flex items-center justify-between font-poppins"><span class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-[#00ffcc] shadow-[0_0_6px_#00ffcc]"></span> ZENON_HPON_NODE</span><span class="text-purple-300 font-mono font-medium">${acc}</span></div>`
                        ).join('');
                    } else {
                        accListDiv.innerHTML = '<div class="text-gray-500 text-sm text-center py-3"><i class="fa-solid fa-robot opacity-40 mr-1.5"></i> No active cluster servers connected</div>';
                    }
                    const friendListDiv = document.getElementById('friendAccountList');
                    if (data.friend_accounts_list && data.friend_accounts_list.length) {
                        friendListDiv.innerHTML = data.friend_accounts_list.map(acc => 
                            `<div class="text-xs bg-[#0d1f0d] border border-green-900/40 px-4 py-3 rounded-full text-gray-300 flex items-center justify-between font-poppins"><span class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-[#39ff14] shadow-[0_0_6px_#39ff14]"></span> FRIEND_NODE</span><span class="text-green-300 font-mono font-medium">${acc}</span></div>`
                        ).join('');
                    } else {
                        friendListDiv.innerHTML = '<div class="text-gray-500 text-sm text-center py-3"><i class="fa-solid fa-user-group opacity-40 mr-1.5"></i> No friend accounts loaded</div>';
                    }
                    const targetsDiv = document.getElementById('activeTargets');
                    if (data.active_spam && data.active_spam.length) {
                        const activeCards = targetsDiv.querySelectorAll('.vector-card');
                        activeCards.forEach(card => {
                            const cardId = card.id.replace('card-vector-', '');
                            if (!data.active_spam.includes(cardId)) {
                                card.remove();
                                delete window.expandedStates[cardId];
                            }
                        });
                        if (targetsDiv.innerHTML.includes('No active vectors running')) {
                            targetsDiv.innerHTML = '';
                        }
                        data.active_spam.forEach(uid => {
                            if (!document.getElementById(`card-vector-${uid}`)) {
                                targetsDiv.insertAdjacentHTML('beforeend', buildTargetCardMarkup(uid));
                                fetchComprehensiveData(uid);
                            }
                        });
                    } else {
                        targetsDiv.innerHTML = '<div class="text-gray-500 text-sm text-center py-4 flex flex-col items-center justify-center gap-2"><span class="flex items-center gap-2"><i class="fa-solid fa-envelope-open opacity-40"></i> No active pipeline clusters running</span></div>';
                        window.expandedStates = {};
                    }
                })
                .catch(err => console.error("Cluster transmission loop error:", err));
        }
        function showToastNotification(elementId, text, isError = false) {
            const el = document.getElementById(elementId);
            if(!el) return;
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
        document.getElementById('pasteUidBtn').onclick = async () => {
            playClickSound();
            try {
                const text = await navigator.clipboard.readText();
                if(text) {
                    const cleanText = text.trim();
                    if(/^\d+$/.test(cleanText)) {
                        document.getElementById('targetUid').value = cleanText;
                        showToast("UID successfully pasted!");
                    } else {
                        showToast("Clipboard text is not a valid UID numeric!");
                    }
                } else {
                    showToast("Clipboard is empty!");
                }
            } catch (err) {
                showToast("Permission denied to access clipboard.");
            }
        };
        document.getElementById('startBtn').onclick = () => {
            const uid = document.getElementById('targetUid').value.trim();
            if (!uid) {
                showToastNotification('startMessage', 'Please enter target UID!', true);
                return;
            }
            if (!/^\d+$/.test(uid)) {
                showToastNotification('startMessage', 'UID must be numeric!', true);
                return;
            }
            fetch(`/start_spam?uid=${encodeURIComponent(uid)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        showToastNotification('startMessage', data.error, true);
                    } else {
                        showToastNotification('startMessage', 'Unified Attack Deployed: Room + Friend Active');
                        document.getElementById('targetUid').value = '';
                        fetchStatus();
                    }
                })
                .catch(err => showToastNotification('startMessage', 'Server Transmission Failed', true));
        };
        setInterval(() => {
            for (const uid in window.activeSpamTimes) {
                const el = document.getElementById(`uptime-${uid}`);
                if (el) {
                    const startTime = window.activeSpamTimes[uid];
                    const now = Math.floor(Date.now() / 1000);
                    let diff = now - startTime;
                    if (diff < 0) diff = 0;
                    const d = Math.floor(diff / 86400);
                    const h = Math.floor((diff % 86400) / 3600);
                    const m = Math.floor((diff % 3600) / 60);
                    el.innerText = `${d}d ${h}h ${m}m`;
                }
            }
        }, 1000);
        fetchStatus();
        setInterval(fetchStatus, 3000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    with active_spam_lock:
        active = list(active_spam_targets.keys())
        active_times = {
            uid: (active_spam_targets[uid] if isinstance(active_spam_targets[uid], float) else datetime.now().timestamp()) 
            for uid in active_spam_targets
        }
    with connected_clients_lock:
        acc_list = list(connected_clients.keys())
    with friend_accounts_lock:
        friend_acc_list = [acc[0] for acc in friend_accounts]
        friend_count = len(friend_accounts)
    with friend_spam_stats_lock:
        stats = dict(friend_spam_stats)
    return jsonify({
        'connected_accounts': len(connected_clients),
        'accounts': acc_list,
        'active_spam': active,
        'active_times': active_times,
        'friend_accounts': friend_count,
        'friend_accounts_list': friend_acc_list,
        'friend_spam_stats': stats
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
        active_spam_targets[target] = datetime.now().timestamp()
        threading.Thread(target=unified_spam_worker, args=(target, duration), daemon=True).start()
    return jsonify({
        'status': 'Unified spam shuru kar diya',
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
            if target in friend_spam_running:
                friend_spam_running[target] = False
            return jsonify({'status': f'{target} ka unified spam band kar diya'})
        else:
            return jsonify({'error': f'{target} pe koi spam nahi chal raha'}), 404

if __name__ == '__main__':
    friend_accounts = Load_Friend_Accounts()
    if friend_accounts:
        print(f"Loaded {len(friend_accounts)} friend accounts from friend.txt")
        threading.Thread(target=Friend_UpdateJwt, daemon=True).start()
    else:
        print("No friend accounts loaded. friend.txt may be missing or empty.")

    threading.Thread(target=start_all_accounts, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
