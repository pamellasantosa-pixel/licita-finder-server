# app.py - Versão 14.0 (Fênix - Servidor)

from flask import Flask, render_template, jsonify, request
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# --- Configuração Inicial ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Dicionários ---
PALAVRAS_CHAVE_POR_NICHO = {
    "pesquisa": ["pesquisa", "diagnóstico", "mapeamento", "estudo", "avaliação", "censo", "relatório", "levantamento de dados", "análise de dados", "monitoramento", "estudo de impacto", "EIA", "RIMA", "análise de vulnerabilidade", "viabilidade socioambiental", "indicadores sociais"],
    "treinamento": ["formação", "capacitação", "treinamento", "oficina", "curso", "workshop", "desenvolvimento profissional", "educação ambiental", "palestra", "seminário", "qualificação profissional"],
    "consultoria": ["consultoria", "assessoria", "apoio técnico", "suporte técnico", "plano de gestão", "licenciamento ambiental", "gestão de projetos", "facilitação", "mediação de conflitos", "plano diretor", "regularização fundiária"],
    "edicao": ["edital de publicação", "livros", "cartilhas", "material didático", "editoração", "revisão de texto", "produção de conteúdo", "comunicação social"],
    "ciencias_sociais": ["ciências sociais", "humanas", "antropologia", "sociologia", "desenvolvimento social", "projetos sociais", "inclusão social", "diversidade", "equidade", "geração de renda", "economia solidária"],
    "psicologia": ["saúde mental", "psicologia", "psicossocial", "acolhimento", "atendimento a vulneráveis", "suporte a migrantes", "migrante", "imigrante", "refugiado", "população de rua", "direitos humanos", "violência de gênero", "apoio a vítimas", "criança e adolescente", "ECA"]
}
NICHOS_DE_BUSCA = {"todos": "Todos os Nichos", "pesquisa": "Pesquisa e Diagnóstico", "treinamento": "Treinamento e Capacitação", "consultoria": "Consultoria e Serviços Técnicos", "edicao": "Edição e Publicação", "ciencias_sociais": "Ciências Sociais e Humanas", "psicologia": "Psicologia e Apoio Psicossocial"}
UFS_BRASIL = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# --- Configuração do Selenium para Servidor (Linux) ---
def setup_driver():
    logging.info("Configurando o driver do Selenium para ambiente de servidor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    
    # No ambiente de servidor, o Selenium geralmente encontra o driver automaticamente se estiver no PATH
    driver = webdriver.Chrome(options=chrome_options)
    logging.info("Driver configurado com sucesso.")
    return driver

def coletar_filtros(req):
    filtros = {"nicho": req.args.get("nicho", "todos"), "uf": req.args.get("uf", "")}
    filtros["palavras_chave"] = []
    if filtros["nicho"] != "todos":
        filtros["palavras_chave"] = PALAVRAS_CHAVE_POR_NICHO.get(filtros["nicho"], [])
    return filtros

def buscar_no_pncp_selenium(filtros):
    logging.info("Iniciando busca no PNCP com Selenium...")
    driver = None
    resultados = []
    try:
        driver = setup_driver()
        driver.get("https://pncp.gov.br/app/editais" )
        wait = WebDriverWait(driver, 30)
        logging.info("Página do PNCP carregada. Aguardando botão de busca avançada...")

        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Busca avançada')]"))).click()
        logging.info("Clicou em 'Busca avançada'.")
        time.sleep(2)

        termo_busca = " ".join(filtros['palavras_chave']) if filtros['palavras_chave'] else "serviços"
        logging.info(f"Preenchendo termo de busca: '{termo_busca}'")
        campo_busca = wait.until(EC.visibility_of_element_located((By.ID, "termo")))
        campo_busca.send_keys(termo_busca)

        if filtros['uf']:
            logging.info(f"Selecionando UF: {filtros['uf']}")
            driver.find_element(By.ID, "uf").click()
            wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'q-item__label') and text()='{filtros['uf']}']"))).click()

        logging.info("Clicando no botão 'Buscar' final.")
        driver.find_element(By.XPATH, "//button[contains(., 'Buscar')]").click()
        
        logging.info("Aguardando resultados carregarem...")
        time.sleep(10) # Espera extra para a renderização dos resultados

        soup = BeautifulSoup(driver.page_source, 'lxml')
        cards = soup.find_all('div', class_='contratacao-item')
        logging.info(f"Encontrados {len(cards)} cards de licitação na página.")

        for card in cards:
            objeto_tag = card.find('p', class_='contratacao-item-titulo')
            link_tag = card.find('a', href=True)
            if objeto_tag and link_tag:
                resultados.append({
                    "fonte": "PNCP (Servidor)",
                    "objeto": objeto_tag.get_text(strip=True),
                    "orgao": card.find('p', class_='contratacao-item-orgao').get_text(strip=True),
                    "modalidade": card.find('span', class_='contratacao-item-modalidade').get_text(strip=True),
                    "data_abertura_proposta": card.find('span', class_='contratacao-item-data').get_text(strip=True),
                    "link": "https://pncp.gov.br" + link_tag['href'],
                    "uf": card.find('span', class_='contratacao-item-local' ).get_text(strip=True),
                })
        logging.info(f"Processados {len(resultados)} resultados válidos.")
    except Exception as e:
        logging.error(f"Erro catastrófico na busca com Selenium no PNCP: {e}")
        if driver:
            # Salva um screenshot para depuração em caso de erro
            driver.save_screenshot('error_screenshot.png')
    finally:
        if driver:
            driver.quit()
            logging.info("Driver do Selenium finalizado.")
    return resultados

@app.route('/')
def index():
    return render_template('index.html', nichos=NICHOS_DE_BUSCA, ufs=UFS_BRASIL)

@app.route('/buscar')
def buscar_api():
    filtros = coletar_filtros(request)
    resultados = buscar_no_pncp_selenium(filtros)
    return jsonify({"success": True, "data": resultados})

if __name__ == '__main__':
    # A porta é definida por uma variável de ambiente no servidor, com 8080 como padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
