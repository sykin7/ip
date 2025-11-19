# 使用轻量级 Python 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到容器内
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 8080 端口
EXPOSE 8080

# 使用 Gunicorn 启动（生产环境更稳定）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
