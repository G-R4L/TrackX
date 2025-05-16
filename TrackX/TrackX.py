import customtkinter as ctk
import requests, socket, folium, webbrowser, os, sqlite3, dns.resolver, re, json
from datetime import datetime
from ipwhois import IPWhois
import pytz

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

if not os.path.exists("maps"):
    os.makedirs("maps")

conn = sqlite3.connect("ip_tracker_logs.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT,
    domain TEXT,
    country TEXT,
    city TEXT,
    isp TEXT,
    date TEXT
)''')
conn.commit()

def whois_lookup(ip):
    try:
        obj = IPWhois(ip)
        res = obj.lookup_rdap()
        return res.get("asn_description", "Tidak tersedia")
    except:
        return "Tidak tersedia"

def reverse_dns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return "Tidak tersedia"

def is_proxy(ip):
    try:
        resp = requests.get(f"https://ip-api.io/json/{ip}", timeout=5).json()
        return resp.get("is_proxy", False)
    except:
        return False

def extract_domain(text):
    text = text.strip()
    text = re.sub(r'^https?://', '', text)
    text = re.sub(r'/.*', '', text)
    return text

def resolve_domain(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '1.1.1.1']
            answer = resolver.resolve(domain, 'A')
            return answer[0].to_text()
        except:
            return None

def get_dns_servers(ip):
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ip]
        answer = resolver.resolve('example.com', 'NS')
        return ', '.join([str(rdata.target).strip('.') for rdata in answer])
    except:
        return "Tidak tersedia"

def get_local_time(timezone):
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S (UTC)')

class IPTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TrackX - Powered by EraldHQ")
        self.geometry("740x510")
        self.resizable(False, False)

        self.result_data = {}

        self.title_label = ctk.CTkLabel(self, text="🌍 GEO IP & DOMAIN TRACKER", font=("Arial Black", 20))
        self.title_label.place(x=200, y=10)
        self.fade_in(self.title_label, 0)

        self.input = ctk.CTkEntry(self, width=500, placeholder_text="Masukkan IP address atau domain...")
        self.input.place(x=40, y=60)

        self.track_button = ctk.CTkButton(self, text="LACAK SEKARANG", width=150, command=self.track_ip)
        self.track_button.place(x=550, y=60)

        self.output_box = ctk.CTkTextbox(self, width=660, height=270, font=("Consolas", 12))
        self.output_box.place(x=40, y=110)

        btn_width = 150
        btn_y = 410
        btn_gap = 20
        start_x = 40

        self.export_btn = ctk.CTkButton(self, text="SIMPAN HASIL", width=btn_width, command=self.export_result, fg_color="#1E90FF", hover_color="#3399FF")
        self.export_btn.place(x=start_x, y=btn_y)

        self.map_btn = ctk.CTkButton(self, text="BUKA PETA BROWSER", width=btn_width, command=self.open_map, fg_color="#1E90FF", hover_color="#3399FF")
        self.map_btn.place(x=start_x + (btn_width + btn_gap) * 1, y=btn_y)

        self.gmaps_btn = ctk.CTkButton(self, text="LIHAT GOOGLE MAPS", width=btn_width, command=self.open_google_maps, fg_color="#1E90FF", hover_color="#3399FF")
        self.gmaps_btn.place(x=start_x + (btn_width + btn_gap) * 2, y=btn_y)

        self.clear_btn = ctk.CTkButton(self, text="HAPUS LOGS", width=btn_width, command=self.clear_logs, fg_color="#1E90FF", hover_color="#3399FF")
        self.clear_btn.place(x=start_x + (btn_width + btn_gap) * 3, y=btn_y)

    def fade_in(self, widget, alpha):
        if alpha < 1.0:
            widget.configure(text_color=("gray", f"#{int(255*alpha):02x}{255:02x}{int(255*alpha):02x}"))
            self.after(30, lambda: self.fade_in(widget, alpha + 0.03))

    def track_ip(self):
        query_raw = self.input.get().strip()
        domain = extract_domain(query_raw)
        self.output_box.delete("1.0", ctk.END)

        ip = resolve_domain(domain)
        if not ip:
            self.output_box.insert(ctk.END, f"[!] Gagal resolve domain/IP: {domain}\n")
            return

        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,message,query,country,regionName,city,zip,lat,lon,timezone,isp,org,as,currency,reverse,proxy,hosting,mobile"
            res = requests.get(url, timeout=10).json()

            if res["status"] != "success":
                self.output_box.insert(ctk.END, f"[!] Gagal lacak: {res['message']}\n")
                return

            whois_info = whois_lookup(ip)
            reverse = reverse_dns(ip)
            proxy_status = "Ya" if is_proxy(ip) else "Tidak"
            dns_servers = get_dns_servers(ip)
            local_time = get_local_time(res.get("timezone", "UTC"))

            self.result_data = {
                "ip": ip,
                "country": res['country'],
                "region": res['regionName'],
                "city": res['city'],
                "zip": res['zip'],
                "lat": res['lat'],
                "lon": res['lon'],
                "timezone": res['timezone'],
                "isp": res['isp'],
                "org": res['org'],
                "as": res['as'],
                "currency": res.get("currency", "Tidak tersedia"),
                "hosting": res.get("hosting", False),
                "mobile": res.get("mobile", False),
                "whois": whois_info,
                "reverse_dns": reverse,
                "proxy": proxy_status,
                "dns_servers": dns_servers,
                "local_time": local_time
            }

            output = f"""[✓] Berikut hasil pelacakan IP/Domain:

IP Address        : {ip}
Negara            : {res['country']}
Kota/Region       : {res['city']} ({res['regionName']})
Kode Pos          : {res['zip']}
Koordinat         : {res['lat']}, {res['lon']}
Zona Waktu        : {res['timezone']} (Lokal: {local_time})
Mata Uang         : {self.result_data['currency']}
ISP               : {res['isp']}
Organisasi        : {res['org']}
ASN               : {res['as']}
Hosting Provider  : {"Ya" if self.result_data['hosting'] else "Tidak"}
Mobile IP         : {"Ya" if self.result_data['mobile'] else "Tidak"}
Proxy/VPN         : {proxy_status}
DNS Server        : {dns_servers}

WHOIS ASN         : {whois_info}
Reverse DNS       : {reverse}
"""

            self.output_box.insert(ctk.END, output, "green")
            self.output_box.tag_config("green", foreground="lime")

            # Generate map with accuracy
            folium_map = folium.Map(location=[res["lat"], res["lon"]], zoom_start=12)
            folium.CircleMarker(
                location=[res["lat"], res["lon"]],
                radius=10,
                popup=f"{ip} - {res['city']}",
                color='red',
                fill=True,
                fill_opacity=0.6
            ).add_to(folium_map)
            folium_map.save("maps/map.html")

            cursor.execute("INSERT INTO logs (ip, domain, country, city, isp, date) VALUES (?, ?, ?, ?, ?, ?)", (
                ip, domain, res["country"], res["city"], res["isp"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()

        except Exception as e:
            self.output_box.insert(ctk.END, f"[!] Error saat melacak: {str(e)}\n")

    def export_result(self):
        if self.result_data:
            with open("hasil_lacak.txt", "w", encoding="utf-8") as f:
                for k, v in self.result_data.items():
                    f.write(f"{k.upper()}: {v}\n")
            self.output_box.insert(ctk.END, "\n[✓] Hasil disimpan di 'hasil_lacak.txt'\n", "green")

    def open_map(self):
        map_path = os.path.abspath("maps/map.html")
        if os.path.exists(map_path):
            webbrowser.open(f"file://{map_path}")
        else:
            self.output_box.insert(ctk.END, "[!] Peta belum tersedia. Lakukan pelacakan terlebih dahulu.\n")

    def open_google_maps(self):
        if self.result_data:
            lat = self.result_data.get("lat")
            lon = self.result_data.get("lon")
            if lat and lon:
                webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}")
            else:
                self.output_box.insert(ctk.END, "[!] Lokasi tidak ditemukan.\n")
        else:
            self.output_box.insert(ctk.END, "[!] Data belum tersedia. Lakukan pelacakan terlebih dahulu.\n")

    def clear_logs(self):
        self.output_box.delete("1.0", ctk.END)
        self.result_data.clear()
        if os.path.exists("hasil_lacak.txt"):
            os.remove("hasil_lacak.txt")
        if os.path.exists("maps/map.html"):
            os.remove("maps/map.html")
        self.output_box.insert(ctk.END, "[✓] Log dan peta berhasil dihapus\n", "green")

if __name__ == "__main__":
    app = IPTrackerApp()
    app.mainloop()
