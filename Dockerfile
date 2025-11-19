FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# 修复版：去掉了 * 两边的单引号，Gunicorn 才能正确识别
CMD ["gunicorn", "--forwarded-allow-ips=*", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
