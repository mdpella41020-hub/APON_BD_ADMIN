#!/usr/bin/env python3
"""
BD ADMIN - Standalone Admin Panel
Can be integrated with main.py or run separately for admin operations.
Admin User: @apon
Admin Password: 1020
"""

import os, json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------- CONFIG ----------
ADMIN_USER = "@apon"
ADMIN_PASS = "1020"
USERS_FILE = "users.json"

# ---------- HELPERS ----------
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------- ADMIN LOGIN PAGE ----------
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login - BD ADMIN</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
<style>
body{background:linear-gradient(135deg,#001a33 0%,#000d1a 100%);min-height:100vh;font-family:'Poppins',sans-serif}
.glass-card{background:rgba(0,20,40,0.8);backdrop-filter:blur(20px);border:1px solid rgba(0,212,255,0.2);box-shadow:0 0 40px rgba(0,212,255,0.15)}
.ocean-input{background:rgba(0,10,25,0.8);border:1px solid rgba(0,212,255,0.2);border-radius:16px;color:#fff;padding:16px 20px 16px 50px;width:100%;outline:none;transition:all 0.3s ease;font-family:'Poppins',sans-serif}
.ocean-input:focus{border-color:#00d4ff;box-shadow:0 0 20px rgba(0,212,255,0.25)}
.ocean-btn{background:linear-gradient(135deg,#00d4ff 0%,#0066cc 100%);color:#fff;font-weight:700;border-radius:16px;font-size:1.1rem;letter-spacing:2px;box-shadow:0 4px 25px rgba(0,212,255,0.4);transition:all 0.3s;border:none;cursor:pointer;font-family:'Orbitron',sans-serif}
.ocean-btn:hover{transform:translateY(-2px);box-shadow:0 6px 35px rgba(0,212,255,0.6)}
.input-icon{position:absolute;left:18px;top:50%;transform:translateY(-50%);color:rgba(0,212,255,0.5);font-size:1.1rem}
.toast-msg{opacity:0;transform:translateY(10px);transition:all 0.4s ease}
.toast-msg.show{opacity:1;transform:translateY(0)}
</style>
</head>
<body class="flex items-center justify-center min-h-screen px-4">
<div class="glass-card rounded-3xl p-8 text-center max-w-sm w-full">
<div class="w-16 h-16 rounded-full bg-cyan-500/10 border-2 border-cyan-400/30 flex items-center justify-center mx-auto mb-4">
<i class="fa-solid fa-shield-halved text-2xl text-cyan-400"></i>
</div>
<h1 class="text-xl font-black text-white font-['Orbitron'] tracking-wider mb-1">ADMIN PANEL</h1>
<p class="text-cyan-400/60 text-xs mb-6">Secure Access Required</p>
<form id="adminForm" class="space-y-4">
<div class="relative">
<i class="fa-solid fa-user-shield input-icon"></i>
<input type="text" id="adminUser" class="ocean-input" placeholder="Admin Username" value="@apon">
</div>
<div class="relative">
<i class="fa-solid fa-key input-icon"></i>
<input type="password" id="adminPass" class="ocean-input" placeholder="Admin Password">
</div>
<button type="submit" class="ocean-btn w-full py-3 flex items-center justify-center gap-2">
<span>ACCESS PANEL</span><i class="fa-solid fa-arrow-right"></i>
</button>
</form>
<div id="toast" class="toast-msg mt-4 text-center text-sm font-semibold rounded-xl p-3 hidden"></div>
</div>
<script>
document.getElementById('adminForm').addEventListener('submit',async(e)=>{
e.preventDefault();
const username=document.getElementById('adminUser').value.trim();
const password=document.getElementById('adminPass').value.trim();
const toast=document.getElementById('toast');
if(!username||!password){
toast.className='toast-msg show mt-4 text-center text-sm font-semibold rounded-xl p-3 bg-red-500/10 border border-red-500/30 text-red-400';
toast.innerHTML='<i class="fa-solid fa-triangle-exclamation mr-1"></i> Enter credentials!';
toast.classList.remove('hidden');return;
}
try{
const res=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})});
const data=await res.json();
if(data.success){
toast.className='toast-msg show mt-4 text-center text-sm font-semibold rounded-xl p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400';
toast.innerHTML='<i class="fa-solid fa-circle-check mr-1"></i> Access Granted! Redirecting...';
toast.classList.remove('hidden');
setTimeout(()=>window.location.href='/dashboard',1000);
}else{
toast.className='toast-msg show mt-4 text-center text-sm font-semibold rounded-xl p-3 bg-red-500/10 border border-red-500/30 text-red-400';
toast.innerHTML='<i class="fa-solid fa-triangle-exclamation mr-1"></i> '+data.message;
toast.classList.remove('hidden');
}
}catch(err){
toast.className='toast-msg show mt-4 text-center text-sm font-semibold rounded-xl p-3 bg-red-500/10 border border-red-500/30 text-red-400';
toast.innerHTML='<i class="fa-solid fa-triangle-exclamation mr-1"></i> Server Error!';
toast.classList.remove('hidden');
}
});
</script>
</body>
</html>
"""

# ---------- ADMIN DASHBOARD (INLINE from admin_dashboard.html) ----------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Panel - BD ADMIN</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#001a33 0%,#000d1a 100%);min-height:100vh;color:#fff;font-family:'Poppins',sans-serif}
.glass-panel{background:rgba(0,20,40,0.8);backdrop-filter:blur(20px);border:1px solid rgba(0,212,255,0.2);border-radius:20px;box-shadow:0 0 40px rgba(0,212,255,0.1)}
.ocean-text{text-shadow:0 0 20px rgba(0,212,255,0.5)}
.user-card{background:rgba(0,30,60,0.6);border:1px solid rgba(0,212,255,0.15);border-radius:16px;padding:16px;transition:all 0.3s ease}
.user-card:hover{border-color:rgba(0,212,255,0.4);box-shadow:0 0 20px rgba(0,212,255,0.15)}
.status-badge{padding:4px 12px;border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:1px}
.status-approved{background:rgba(57,255,20,0.15);border:1px solid rgba(57,255,20,0.3);color:#39ff14}
.status-pending{background:rgba(255,170,0,0.15);border:1px solid rgba(255,170,0,0.3);color:#ffaa00}
.ocean-btn{background:linear-gradient(135deg,#00d4ff 0%,#0066cc 100%);color:#fff;font-weight:700;border-radius:12px;padding:8px 16px;font-size:0.8rem;letter-spacing:1px;box-shadow:0 4px 15px rgba(0,212,255,0.3);transition:all 0.3s;border:none;cursor:pointer}
.ocean-btn:hover{transform:translateY(-2px);box-shadow:0 6px 25px rgba(0,212,255,0.5)}
.danger-btn{background:linear-gradient(135deg,#ff0055 0%,#b3003b 100%);color:#fff;font-weight:700;border-radius:12px;padding:8px 16px;font-size:0.8rem;letter-spacing:1px;box-shadow:0 4px 15px rgba(255,0,85,0.3);transition:all 0.3s;border:none;cursor:pointer}
.danger-btn:hover{transform:translateY(-2px);box-shadow:0 6px 25px rgba(255,0,85,0.5)}
.success-btn{background:linear-gradient(135deg,#39ff14 0%,#00ff66 100%);color:#000;font-weight:700;border-radius:12px;padding:8px 16px;font-size:0.8rem;letter-spacing:1px;box-shadow:0 4px 15px rgba(57,255,20,0.3);transition:all 0.3s;border:none;cursor:pointer}
.success-btn:hover{transform:translateY(-2px);box-shadow:0 6px 25px rgba(57,255,20,0.5)}
.stat-box{background:rgba(0,20,40,0.6);border:1px solid rgba(0,212,255,0.2);border-radius:16px;padding:20px;text-align:center}
.stat-value{font-size:2rem;font-weight:800;color:#00d4ff;font-family:'Orbitron',sans-serif;text-shadow:0 0 15px rgba(0,212,255,0.5)}
.stat-label{font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;color:#a0aec0;margin-top:4px}
.activity-box{background:rgba(0,10,25,0.8);border:1px solid rgba(0,212,255,0.1);border-radius:12px;padding:12px;margin-top:8px}
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(10px);display:none;align-items:center;justify-content:center;z-index:1000}
.modal-overlay.show{display:flex}
.modal-content{background:rgba(0,20,40,0.95);border:1px solid rgba(0,212,255,0.3);border-radius:24px;padding:24px;max-width:400px;width:90%}
.toast-msg{position:fixed;top:1rem;right:1rem;background:rgba(0,20,40,0.95);border:1px solid rgba(0,212,255,0.3);border-radius:12px;padding:12px 20px;color:#fff;font-size:0.85rem;box-shadow:0 8px 30px rgba(0,0,0,0.6);transform:translateX(120%);transition:all 0.4s ease;z-index:2000}
.toast-msg.show{transform:translateX(0)}
</style>
</head>
<body class="p-4">

<div class="max-w-6xl mx-auto">
<div class="flex items-center justify-between mb-6">
<div>
<h1 class="text-3xl font-black text-white font-['Orbitron'] tracking-wider ocean-text">ADMIN PANEL</h1>
<p class="text-cyan-400/60 text-sm mt-1">BD ADMIN Paid Spam Tools - Management Console</p>
</div>
<div class="flex items-center gap-3">
<div class="glass-panel px-4 py-2 rounded-full">
<span class="text-xs text-cyan-400/60 uppercase tracking-widest">Admin</span>
<span class="text-sm font-bold text-white ml-2">@apon</span>
</div>
<a href="/logout" class="danger-btn text-xs"><i class="fa-solid fa-power-off mr-1"></i> LOGOUT</a>
</div>
</div>

<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
<div class="stat-box">
<div class="stat-value" id="totalUsers">{{ total }}</div>
<div class="stat-label">Total Users</div>
</div>
<div class="stat-box">
<div class="stat-value" id="approvedUsers">{{ approved }}</div>
<div class="stat-label">Approved</div>
</div>
<div class="stat-box">
<div class="stat-value" id="pendingUsers">{{ pending }}</div>
<div class="stat-label">Pending</div>
</div>
<div class="stat-box">
<div class="stat-value" id="activeSpam">{{ active_spam|length }}</div>
<div class="stat-label">Active Spam</div>
</div>
</div>

<div class="glass-panel p-6 mb-6">
<h2 class="text-lg font-bold text-cyan-400 mb-4 font-['Orbitron'] tracking-wider"><i class="fa-solid fa-server mr-2"></i>SYSTEM STATUS</h2>
<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
<div class="bg-black/40 rounded-xl p-4 border border-cyan-500/10">
<div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Room Bots</div>
<div class="text-xl font-black text-cyan-400 font-['Orbitron']">{{ connected }}</div>
</div>
<div class="bg-black/40 rounded-xl p-4 border border-cyan-500/10">
<div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Friend Bots</div>
<div class="text-xl font-black text-emerald-400 font-['Orbitron']">{{ friends }}</div>
</div>
<div class="bg-black/40 rounded-xl p-4 border border-cyan-500/10">
<div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Active Targets</div>
<div class="text-xl font-black text-amber-400 font-['Orbitron']">{{ active_spam|length }}</div>
</div>
</div>
</div>

<div class="glass-panel p-6 mb-6">
<h2 class="text-lg font-bold text-cyan-400 mb-4 font-['Orbitron'] tracking-wider"><i class="fa-solid fa-users mr-2"></i>USER MANAGEMENT</h2>
<div class="space-y-3" id="userList">
{% for username, user_data in users.items() %}
<div class="user-card" id="user-card-{{ username }}">
<div class="flex flex-wrap items-center justify-between gap-3">
<div class="flex items-center gap-3">
<div class="w-10 h-10 rounded-full bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center">
<i class="fa-solid fa-user text-cyan-400"></i>
</div>
<div>
<h3 class="font-bold text-white text-sm">{{ username }}</h3>
<p class="text-xs text-slate-400">Created: {{ user_data.created_at|default('N/A') }}</p>
</div>
</div>
<div class="flex items-center gap-2 flex-wrap">
<span class="status-badge {{ 'status-approved' if user_data.approved else 'status-pending' }}" id="status-{{ username }}">
{{ 'APPROVED' if user_data.approved else 'PENDING' }}
</span>
{% if not user_data.approved %}
<button onclick="approveUser('{{ username }}')" class="success-btn text-xs"><i class="fa-solid fa-check mr-1"></i> APPROVE</button>
{% else %}
<button onclick="rejectUser('{{ username }}')" class="ocean-btn text-xs" style="background:linear-gradient(135deg,#ffaa00 0%,#cc7700 100%)"><i class="fa-solid fa-ban mr-1"></i> REJECT</button>
{% endif %}
<button onclick="showChangePassword('{{ username }}')" class="ocean-btn text-xs"><i class="fa-solid fa-key mr-1"></i> PASS</button>
<button onclick="deleteUser('{{ username }}')" class="danger-btn text-xs"><i class="fa-solid fa-trash mr-1"></i> DEL</button>
</div>
</div>
{% if username in activities and activities[username].targets %}
<div class="activity-box mt-3">
<div class="flex items-center justify-between mb-2">
<span class="text-xs text-cyan-400 font-bold uppercase tracking-wider"><i class="fa-solid fa-crosshairs mr-1"></i> Active Targets</span>
<button onclick="stopUserSpam('{{ username }}')" class="danger-btn text-xs py-1 px-3"><i class="fa-solid fa-stop mr-1"></i> STOP ALL</button>
</div>
<div class="flex flex-wrap gap-2">
{% for target in activities[username].targets %}
<span class="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3 py-1 rounded-full font-mono">{{ target }}</span>
{% endfor %}
</div>
</div>
{% endif %}
</div>
{% else %}
<div class="text-center text-slate-500 py-8">
<i class="fa-solid fa-users-slash text-3xl mb-2 opacity-40"></i>
<p class="text-sm">No users registered yet</p>
</div>
{% endfor %}
</div>
</div>

<div class="glass-panel p-6">
<h2 class="text-lg font-bold text-cyan-400 mb-4 font-['Orbitron'] tracking-wider"><i class="fa-solid fa-satellite-dish mr-2"></i>ACTIVE SPAM MONITOR</h2>
<div class="grid grid-cols-2 md:grid-cols-4 gap-3" id="spamMonitor">
{% for target in active_spam %}
<div class="bg-black/40 rounded-xl p-3 border border-red-500/20 text-center">
<div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Target</div>
<div class="text-lg font-black text-red-400 font-['Orbitron']">{{ target }}</div>
<div class="text-[10px] text-slate-500 mt-1">Running</div>
</div>
{% else %}
<div class="col-span-full text-center text-slate-500 py-6">
<i class="fa-solid fa-circle-check text-2xl mb-2 opacity-40"></i>
<p class="text-sm">No active spam operations</p>
</div>
{% endfor %}
</div>
</div>
</div>

<div class="modal-overlay" id="passwordModal">
<div class="modal-content">
<h3 class="text-xl font-black text-white font-['Orbitron'] mb-4">Change Password</h3>
<p class="text-sm text-slate-400 mb-4">User: <span id="modalUsername" class="text-cyan-400 font-bold"></span></p>
<input type="password" id="newPassword" class="w-full bg-black/40 border border-cyan-500/20 rounded-xl p-3 text-white text-sm mb-4 outline-none focus:border-cyan-400" placeholder="Enter new password">
<div class="flex gap-3">
<button onclick="closeModal()" class="flex-1 py-2 rounded-xl bg-slate-700/50 text-white text-sm font-bold hover:bg-slate-700 transition-all">CANCEL</button>
<button onclick="confirmChangePassword()" class="flex-1 py-2 rounded-xl ocean-btn text-sm">UPDATE</button>
</div>
</div>
</div>

<div class="toast-msg" id="toast"></div>

<script>
let currentUser = '';
function showToast(message, isError = false) {
const toast = document.getElementById('toast');
toast.textContent = message;
toast.style.borderColor = isError ? 'rgba(255,0,85,0.3)' : 'rgba(0,212,255,0.3)';
toast.classList.add('show');
setTimeout(() => toast.classList.remove('show'), 3000);
}
async function approveUser(username) {
try {
const res = await fetch('/api/approve', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
const data = await res.json();
if(data.success){showToast(`User ${username} approved!`);setTimeout(()=>location.reload(),1000);}
else{showToast(data.message,true);}
}catch(e){showToast('Server error',true);}
}
async function rejectUser(username) {
try {
const res = await fetch('/api/reject', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
const data = await res.json();
if(data.success){showToast(`User ${username} rejected!`);setTimeout(()=>location.reload(),1000);}
else{showToast(data.message,true);}
}catch(e){showToast('Server error',true);}
}
async function deleteUser(username) {
if(!confirm(`Delete user ${username}? This cannot be undone!`)) return;
try {
const res = await fetch('/api/delete', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
const data = await res.json();
if(data.success){showToast(`User ${username} deleted!`);document.getElementById(`user-card-${username}`).remove();}
else{showToast(data.message,true);}
}catch(e){showToast('Server error',true);}
}
function showChangePassword(username) {
currentUser = username;
document.getElementById('modalUsername').textContent = username;
document.getElementById('passwordModal').classList.add('show');
}
function closeModal() {
document.getElementById('passwordModal').classList.remove('show');
document.getElementById('newPassword').value = '';
currentUser = '';
}
async function confirmChangePassword() {
const newPass = document.getElementById('newPassword').value.trim();
if(!newPass){showToast('Enter a password!',true);return;}
try {
const res = await fetch('/api/change_password', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:currentUser,new_password:newPass})});
const data = await res.json();
if(data.success){showToast(`Password changed for ${currentUser}!`);closeModal();}
else{showToast(data.message,true);}
}catch(e){showToast('Server error',true);}
}
async function stopUserSpam(username) {
if(!confirm(`Stop all spam for ${username}?`)) return;
try {
const res = await fetch('/api/stop_user_spam', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
const data = await res.json();
if(data.success){showToast(`All spam stopped for ${username}!`);setTimeout(()=>location.reload(),1000);}
else{showToast(data.message,true);}
}catch(e){showToast('Server error',true);}
}
setInterval(()=>{
fetch('/api/status').then(r=>r.json()).then(data=>{document.getElementById('activeSpam').textContent=data.active_spam.length;});
},5000);
</script>

</body>
</html>
"""

# ---------- ROUTES ----------

@app.route('/')
def login():
    if 'admin' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid admin credentials'})

@app.route('/dashboard')
@require_admin
def dashboard():
    users = load_users()
    total = len(users)
    approved = sum(1 for u in users.values() if u.get('approved', False))
    pending = total - approved

    # Get system status from shared data (if available)
    active_spam = []
    connected = 0
    friends = 0
    activities = {}

    return render_template_string(DASHBOARD_HTML, 
        users=users, total=total, approved=approved, pending=pending,
        active_spam=active_spam, connected=connected, friends=friends, activities=activities)

@app.route('/api/approve', methods=['POST'])
@require_admin
def api_approve():
    data = request.get_json()
    username = data.get('username', '').strip()
    users = load_users()
    if username in users:
        users[username]['approved'] = True
        save_users(users)
        return jsonify({'success': True, 'message': f'User {username} approved'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/reject', methods=['POST'])
@require_admin
def api_reject():
    data = request.get_json()
    username = data.get('username', '').strip()
    users = load_users()
    if username in users:
        users[username]['approved'] = False
        save_users(users)
        return jsonify({'success': True, 'message': f'User {username} rejected'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/delete', methods=['POST'])
@require_admin
def api_delete():
    data = request.get_json()
    username = data.get('username', '').strip()
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        return jsonify({'success': True, 'message': f'User {username} deleted'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/change_password', methods=['POST'])
@require_admin
def api_change_password():
    data = request.get_json()
    username = data.get('username', '').strip()
    new_password = data.get('new_password', '').strip()
    users = load_users()
    if username in users:
        users[username]['password'] = new_password
        save_users(users)
        return jsonify({'success': True, 'message': f'Password changed for {username}'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/stop_user_spam', methods=['POST'])
@require_admin
def api_stop_user_spam():
    data = request.get_json()
    username = data.get('username', '').strip()
    return jsonify({'success': True, 'message': f'All spam stopped for {username}'})

@app.route('/api/status')
@require_admin
def api_status():
    return jsonify({'active_spam': []})

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

# ---------- MAIN ----------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    print(f"BD ADMIN Panel starting on port {port}")
    print(f"Admin User: {ADMIN_USER}")
    print(f"Admin Password: {ADMIN_PASS}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
