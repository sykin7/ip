FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# 关键修改：添加 --forwarded-allow-ips='*' 允许接收代理头
CMD ["gunicorn", "--forwarded-allow-ips='*'", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
