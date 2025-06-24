# Usar una imagen base con Python 3.10
FROM python:3.10-slim

# Configurar el directorio de trabajo
WORKDIR /workspace

# Instalar git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente, necesario para el deploy en DO.
COPY . .

# Copiar el código fuente
EXPOSE 8080

ENTRYPOINT stre