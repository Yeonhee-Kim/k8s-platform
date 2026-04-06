FROM python:3.9-slim

# 필요한 패키지 설치
RUN pip install flask pymysql kubernetes requests

WORKDIR /app
COPY . .

# Flask 포트 개방
EXPOSE 5000

CMD ["python", "app.py"]
