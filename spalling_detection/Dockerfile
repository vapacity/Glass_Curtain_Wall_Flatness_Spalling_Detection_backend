FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip3 install torch torchvision torchaudio

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip

COPY resnet34_model.pth .

COPY script.py .

COPY app.py .

EXPOSE 8080

CMD ["python", "app.py"]