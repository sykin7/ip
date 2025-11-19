from flask import Flask, request, render_template, jsonify
import requests
import os
import threading
import ipaddress

app = Flask(__name__)

# 从环境变量获取配置
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

# 核心辅助函数：判断是否为内网IP
def is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        # 排除内网(is_private) 和 本地回环(is_loopback)
        return not ip.is_private and not ip.is_loopback
    except ValueError:
        return False

# 增强型 IP 获取：暴力扫描所有可能的头，剔除内网IP
def get_real_ip():
    # 定义所有可能包含真实IP的头部，按优先级排序
    headers_to_check = [
        'CF-Connecting-IP',      # Cloudflare
        'X-Client-IP',           # 通用
        'X-Real-IP',             # Nginx/通用
        'X-Forwarded-For',       # 标准代理头
        'Forwarded-For',
        'True-Client-IP'
    ]

    for header in headers_to_check:
        val = request.headers.get(header)
        if val:
            # 有些头包含多个IP，用逗号分隔 (例如: client, proxy1, proxy2)
            # 我们拆分后，逐个检查，只要发现是公网IP，立马返回
            ip_list = [x.strip() for x in val.split(',')]
            for ip in ip_list:
                if is_public_ip(ip):
                    return ip
    
    # 如果上面都没找到公网IP，只能返回直连IP (虽然可能是内网IP，但也没办法了)
    return request.remote_addr

def get_ip_info(ip):
    # 再次防御：如果是内网 IP，直接不查询，避免显示空白
    if not is_public_ip(ip):
        return {
            'isp': '内网环境(Local)', 
            'country': '内部网络', 
            'city': 'Leaflow内部',
            'org': 'Private Network',
            'as': 'N/A'
        }

    try:
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,message,country,regionName,city,isp,org,as,mobile,proxy,hosting,query"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

# TG 通知逻辑 (保持不变)
def send_telegram_alert(ip, data, user_agent):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    # 如果是内网IP，不发通知，避免刷屏
    if not is_public_ip(ip):
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
