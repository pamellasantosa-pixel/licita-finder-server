# Estágio 1: Instalar o Chrome e o Driver
FROM python:3.11-slim as builder

# Instala dependências do sistema, incluindo o Chrome
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && apt-get clean

# Baixa e instala a versão estável mais recente do Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Baixa e instala o ChromeDriver correspondente
# NOTA: Este link pode precisar ser atualizado no futuro.
RUN CHROME_DRIVER_VERSION=$(wget -q -O - "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" | grep -oP '"linux64":\[{"platform":"linux64","url":"\K[^"]+' ) \
    && wget -q --continue -P /tmp/ ${CHROME_DRIVER_VERSION} \
    && unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver-linux64.zip

# Estágio 2: Construir a aplicação Python
FROM python:3.11-slim

# Copia o Chrome e o Driver do estágio anterior
COPY --from=builder /etc/apt/sources.list.d/google-chrome.list /etc/apt/sources.list.d/google-chrome.list
COPY --from=builder /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/
COPY --from=builder /opt/google/chrome /opt/google/chrome

# Instala as dependências do Chrome
RUN apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && apt-get clean

# Define o diretório de trabalho
WORKDIR /app

# Copia a lista de requisitos e instala as bibliotecas Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto da aplicação
COPY . .

# Expõe a porta que a aplicação vai usar
EXPOSE 8080

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
