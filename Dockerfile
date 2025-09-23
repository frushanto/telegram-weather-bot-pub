FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 1. Устанавливаем только runtime зависимости (dev пакеты вынесены)
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# 2. Создаём непривилегированного пользователя заранее
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

# 3. Копируем исходники (dev файлы, тесты и артефакты исключаются .dockerignore)
COPY . .

# 4. Переходим под пользователя приложения
USER appuser

# 5. Точка входа
CMD ["python", "app.py"]