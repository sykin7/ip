from flask import Flask, request, render_template, jsonify
import requests
import os
import threading
import time

app = Flask(__name__)

# 从环境变量获取配置
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def get_real_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def get_ip_info(ip):
    try:
        # 请求包含 mobile, proxy, hosting 等高级字段
        # fields=66846719 代表所有主要字段
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting,query"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

# 异步发送 Telegram 通知，避免网页加载变慢
def send_telegram_alert(ip, data, user_agent):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    # 分析 IP 类型
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
        requests.post(api_url, json={
            "chat_id": TG_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"TG 发送失败: {e}")

@app.route('/')
def index():
    ip = get_real_ip()
    data = get_ip_info(ip)
    user_agent = request.headers.get('User-Agent')
    
    # 开启一个新线程去发通知，这样用户网页打开速度不受影响
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
