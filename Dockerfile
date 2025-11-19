FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# 使用 Shell 模式启动，这种写法对特殊字符 '*' 最兼容，绝对不会报错
CMD gunicorn --forwarded-allow-ips="*" -w 4 -b 0.0.0.0:8080 app:app
