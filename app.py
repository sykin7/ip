from flask import Flask, request, render_template, jsonify
import requests
import os
import threading
import ipaddress
import json

app = Flask(__name__)

TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return not ip.is_private and not ip.is_loopback
    except:
        return False

def get_real_ip():
    # 调试模式：优先找公网IP，找不到就找内网
    headers = ['CF-Connecting-IP', 'X-Client-IP', 'X-Real-IP', 'X-Forwarded-For']
    for h in headers:
        val = request.headers.get(h)
        if val:
            for ip in val.split(','):
                if is_public_ip(ip.strip()):
                    return ip.strip()
    return request.remote_addr

def get_ip_info(ip):
    if not is_public_ip(ip):
        return {'isp': '内网环境(Local)', 'country': 'Local', 'city': 'Internal', 'org': 'Debug Mode'}
    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting,query"
        return requests.get(url, timeout=3).json()
    except:
        return {}

# 简单的 TG 通知
def send_telegram_alert(ip, data, ua):
    if not TG_BOT_TOKEN or not TG_CHAT_ID or not is_public_ip(ip): return
    msg = f"🚨 新访问\nIP: {ip}\n位置: {data.get('country')} {data.get('city')}"
    try:
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg})
    except: pass

@app.route('/')
def index():
    ip = get_real_ip()
    data = get_ip_info(ip)
    ua = request.headers.get('User-Agent')
    threading.Thread(target=send_telegram_alert, args=(ip, data, ua)).start()
    
    # 收集调试信息，显示在网页上
    debug_info = {k: v for k, v in request.headers.items()}
    
    return render_template('index.html', ip=ip, data=data, ua=ua, debug_info=json.dumps(debug_info, indent=2))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
