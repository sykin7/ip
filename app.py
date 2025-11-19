from flask import Flask, request, render_template, jsonify
import requests
import os
import threading

app = Flask(__name__)

# 从环境变量获取配置
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# 核心修复：增强型 IP 获取逻辑
def get_real_ip():
    # 1. 优先尝试 Cloudflare 传递的真实 IP (很多云平台通用)
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    
    # 2. 尝试标准的 X-Real-IP
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # 3. 尝试 X-Forwarded-For (取第一个)
    if request.headers.get('X-Forwarded-For'):
        try:
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        except:
            pass
            
    # 4. 如果都失败，才使用直接连接的 IP (虽然在 Docker 里通常是内网 IP)
    return request.remote_addr

def get_ip_info(ip):
    # 如果获取到的是内网 IP (10.x.x.x, 172.16-31.x.x, 192.168.x.x), 直接不查询，防止报错
    if ip.startswith('10.') or ip.startswith('192.168.') or (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31):
        return {'isp': '内网IP(无法定位)', 'country': 'Local Network', 'org': 'Local', 'as': 'N/A'}

    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting,query"
        resp = requests.get(url, timeout=4) # 超时缩短一点，避免卡顿
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

# 发送 TG 通知 (逻辑不变)
def send_telegram_alert(ip, data, user_agent):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    ip_type = "🏠 家庭宽带/移动网络"
    if data.get('hosting') is True:
        ip_type = "🏢 数据中心/机房 (解锁能力差)"
    elif data.get('proxy') is True:
        ip_type = "😈 代理/VPN IP"
    
    country = f"{data.get('country', '未知')} {data.get('city', '')}"
    isp = data.get('isp', '未知')
    
    msg = (
        f"🚨 <b>IP 哨兵检测到新访问</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>IP:</b> <code>{ip}</code>\n"
        f"🏳️ <b>位置:</b> {country}\n"
        f"🏢 <b>运营商:</b> {isp}\n"
        f"🕵️ <b>类型:</b> {ip_type}\n"
        f"📱 <b>设备:</b> {user_agent}\n"
        f"━━━━━━━━━━━━━━━━"
    )
    
    try:
        api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        requests.post(api_url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except:
        pass

@app.route('/')
def index():
    ip = get_real_ip()
    data = get_ip_info(ip)
    user_agent = request.headers.get('User-Agent')
    
    threading.Thread(target=send_telegram_alert, args=(ip, data, user_agent)).start()
    
    return render_template('index.html', ip=ip, data=data, ua=user_agent)

@app.route('/raw')
def raw_ip():
    return get_real_ip()

@app.route('/json')
def json_ip():
    ip = get_real_ip()
    data = get_ip_info(ip)
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
