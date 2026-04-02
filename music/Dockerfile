FROM python:3.9-slim

# # 直接使用默认源安装时区包，坚决不换源，避免版本冲突！
# RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

# 设置时区
ENV TZ=Asia/Shanghai

WORKDIR /app

# 复制脚本
COPY . .

CMD ["python", "simulator.py"]