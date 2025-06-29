# Usar una imagen base con Python 3.10
FROM python:3.10-slim

# Configurar el directorio de trabajo
WORKDIR /workspace

# Instalar git, wget y unzip
RUN apt-get update && apt-get install -y \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Descargar ngrok
RUN wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-stable-linux-amd64.zip \
    && unzip ngrok-stable-linux-amd64.zip \
    && mv ngrok /usr/local/bin/ngrok \
    && rm ngrok-stable-linux-amd64.zip

# Exponer el puerto donde correrá FastAPI
EXPOSE 8080

#ENTRYPOINT 