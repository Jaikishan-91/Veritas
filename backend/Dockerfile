FROM python:3.11-slim
ARG WITH_OCR=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# PaddleOCR pulls in non-headless OpenCV, which needs libGL
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
        $(if [ "$WITH_OCR" = "1" ]; then echo libgl1; fi) \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
# Dependencies first, against a stub package, so code changes don't reinstall them (PaddleOCR takes minutes)
RUN mkdir app && touch app/__init__.py \
    && pip install "$(if [ "$WITH_OCR" = "1" ]; then echo '.[ocr]'; else echo .; fi)" \
    && pip uninstall -y veritas-backend && rm -rf app build *.egg-info
COPY app ./app
RUN pip install --no-deps .
RUN useradd -m veritas
USER veritas
# OCR model cache; mounted as a volume in docker-compose so models download once, not per container
RUN mkdir -p /home/veritas/.paddlex
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
