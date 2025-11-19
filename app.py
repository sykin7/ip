from flask import Flask, request, render_template, jsonify
import requests
import os
import threading
import json

app = Flask(__name__)

TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def get_real_ip():
    # 优先 Cloudflare
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip: return cf_ip
    
    # 其次 X-Forwarded-For
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        try: return x_forwarded.split(',')[0].strip()
        except: pass
            
    return request.remote_addr

def get_ip_info(ip):
    # 过滤内网
    if ip.startswith('10.') or ip.startswith('172.') or ip.startswith('192.'):
        return {'isp': 'Local Network', 'country': 'Internal', 'city': 'LAN'}
        
    try:
        # 增加了 lat,lon,currency,timezone 等字段
        fields = "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,currency,isp,org,as,mobile,proxy,hosting,query"
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields={fields}"
        return requests.get(url, timeout=5).json()
    except:
        return {}

def calculate_score(data):
    # 模拟计算 IP 信任分 (0-100)
    score = 100
    if data.get('proxy'): score -= 40  # 是代理扣40分
    if data.get('hosting'): score -= 30 # 是机房扣30分
    if data.get('mobile'): score = 100  # 是手机直接满分
    return max(0, score)

def send_telegram_alert(ip, data, ua):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    if ip.startswith('10.') or ip.startswith('127.'): return
    
    score = calculate_score(data)
    msg = (
        f"🚨 <b>新访客侦测</b>\n"
        f"IP: <code>{ip}</code>\n"
        f"位置: {data.get('country')} {data.get('city')}\n"
        f"ISP: {data.get('isp')}\n"
        f"信任分: {score}/100"
    )
    try:
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

@app.route('/')
def index():
    ip = get_real_ip()
    data = get_ip_info(ip)
    ua = request.headers.get('User-Agent')
    score = calculate_score(data)
    
    threading.Thread(target=send_telegram_alert, args=(ip, data, ua)).start()
    
    # 调试信息保留，方便查错
    debug_info = {k: v for k, v in request.headers.items()}
    
    return render_template('index.html', ip=ip, data=data, ua=ua, score=score, debug_info=json.dumps(debug_info))

if __name__ == '__main__':
    # 使用 Shell 模式最稳
    app.run(host='0.0.0.0', port=8080)
