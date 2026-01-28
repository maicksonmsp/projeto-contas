# Usa Python Slim (Leve, mas com Debian por baixo)
FROM python:3.9-slim

# Define diretório de trabalho
WORKDIR /app

# --- PASSO CRÍTICO ---
# Instala compiladores e drivers de sistema necessários para mysqlclient e cryptography
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala requisitos Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código (Templates, Static, App.py, .db se houver)
COPY . .

# Expõe a porta 5000 (Confirmada por você)
EXPOSE 5000

# Comando de execução
CMD ["python", "app.py"]