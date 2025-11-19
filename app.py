from flask import Flask, request, render_template, jsonify
import requests
import os
import threading
import json

app = Flask(__name__)

TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def get_real_ip():
    # 1. 最高优先级：Cloudflare 传递的真实 IP (这是最准的)
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip

    # 2. 次优先级：X-Forwarded-For 的第一个 IP
    # 格式通常是: "真实IP, 代理1, 代理2"
    # 我们只取第一个，因为那是发起的源头
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        try:
            # 分割并取第一个，去掉空格
            return x_forwarded.split(',')[0].strip()
        except:
            pass
            
    # 3. 再次优先级：X-Real-IP
    x_real = request.headers.get('X-Real-IP')
    if x_real:
        return x_real

    # 4. 最后没办法了才用直连 IP (通常是内网或网关IP)
    return request.remote_addr

def get_ip_info(ip):
    # 过滤掉内网 IP，避免查不到数据
    if ip.startswith('10.') or ip.startswith('172.') or ip.startswith('192.'):
        return {'isp': '内网/代理转发中', 'country': 'Local', 'city': 'Check Config'}
        
    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting,query"
        return requests.get(url, timeout=3).json()
    except:
        return {}

def send_telegram_alert(ip, data, ua):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    # 简单防抖：如果是内网IP就不发通知
    if ip.startswith('10.') or ip.startswith('127.'): return
    
    country = f"{data.get('country', '未知')} {data.get('city', '')}"
    msg = f"🚨 <b>新访客到达</b>\nIP: <code>{ip}</code>\n位置: {country}\nISP: {data.get('isp')}"
    try:
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

@app.route('/')
def index():
    ip = get_real_ip()
    data = get_ip_info(ip)
    ua = request.headers.get('User-Agent')
    threading.Thread(target=send_telegram_alert, args=(ip, data, ua)).start()
    
    # 这里的 debug_info 会把所有头打印在网页最下面，方便我们查错
    debug_info = {k: v for k, v in request.headers.items()}
    
    return render_template('index.html', ip=ip, data=data, ua=ua, debug_info=json.dumps(debug_info, indent=2))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
