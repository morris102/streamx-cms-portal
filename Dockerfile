# Sử dụng Python slim để giảm dung lượng image
FROM python:3.14-slim

# Ngăn Python tạo file .pyc và giúp log hiển thị ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (ví dụ cho PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy và cài đặt thư viện Python trước để tận dụng Docker layer cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn dự án vào container
COPY . .

# Mở cổng 8000
EXPOSE 8000

# Chạy server phát triển của Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
