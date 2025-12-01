import psutil, sqlite3, time, datetime, platform, socket, requests
from ping3 import ping

def get_host_info():
    return socket.gethostname(), platform.system()
hostname, os_system = get_host_info()

SCENARIO_NAME = "Scenario_Base_NoRules"
INTERVAL = 1.0
DB_NAME = f"metriques_{hostname}.db"

TARGETS = [
    {
        "name": "Gateway",
        "host": "172.18.11.254",       
        "url": None                  
    },
    {
        "name": "Google_DNS",
        "host": "8.8.8.8",           
        "url": "https://www.google.com" 
    }
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            hostname TEXT,
            os_system TEXT,
            scenario TEXT,
            cpu_percent REAL,
            ram_percent REAL,
            target_name TEXT,
            ping_latency_ms REAL,
            http_latency_ms REAL,
            http_status_code INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def measure_ping(host):
    if not host: return None
    try:
        latency_sec = ping(host, timeout=0.8) 
        if latency_sec is None or latency_sec is False: return None
        return round(latency_sec * 1000, 2)
    except: return None

def measure_http(url):
    if not url: return None, None
    try:
        resp = requests.get(url, timeout=0.8)
        return round(resp.elapsed.total_seconds() * 1000, 2), resp.status_code
    except: return None, 0

def collect_metrics():
    hostname, os_system = get_host_info()
    
    print(f"\n{'='*80}")
    print(f" MONITORING ACTIF : {hostname} ({os_system}) | SCENARIO : {SCENARIO_NAME}")
    print(f"{'='*80}\n")

    header = f"{'HEURE':<10} | {'CPU':<6} | {'RAM':<6} | {'CIBLE':<15} | {'PING (ms)':<10} | {'HTTP (ms)':<10} | {'CODE':<5}"
    print(header)
    print("-" * len(header))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        while True:
            start_time = time.time()
            now = datetime.datetime.now()
            timestamp_db = now.isoformat()
            time_display = now.strftime("%H:%M:%S")
            
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            for target in TARGETS:
                ping_ms = measure_ping(target['host'])
                http_ms, status = measure_http(target['url'])

                cursor.execute('''
                    INSERT INTO metrics 
                    (timestamp, hostname, os_system, scenario, cpu_percent, ram_percent, 
                     target_name, ping_latency_ms, http_latency_ms, http_status_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp_db, hostname, os_system, SCENARIO_NAME, cpu, ram, target['name'], ping_ms, http_ms, status)
                )
                
                d_ping = f"{ping_ms}" if ping_ms is not None else "T/O"
                d_http = f"{http_ms}" if http_ms is not None else "-"
                d_code = f"{status}" if status and status != 0 else "-"
                
                print(f"{time_display:<10} | {cpu:<5}% | {ram:<5}% | {target['name']:<15} | {d_ping:<10} | {d_http:<10} | {d_code:<5}")

            conn.commit()
            
            elapsed = time.time() - start_time
            sleep_time = max(0, INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n{'-'*80}")
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    collect_metrics()