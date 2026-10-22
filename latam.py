import os
import re
import time
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 🔒 Lendo as credenciais de forma segura (Secrets do GitHub)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PRECO_MAXIMO = 1000.00

URL_FLIGHTS = (
    "https://www.google.com/travel/flights/search?tfs=CBwQAhoyEgoyMDI2LTEyLTI2OgJBRD"
    "oCQVY6AkczQA5IF1AAWBdqBwgBEgNHUlVyBwgBEgNNQ1BAAUgBcAGCAQsI____________AZgBAg&tfu"
    "=EgYIABAAGAA&hl=pt-BR&gl=BR"
)

def enviar_mensagem_telegram(mensagem: str):
    """Envia uma mensagem de texto formatada para o seu Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Token ou Chat ID do Telegram não configurados nas variáveis de ambiente.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✉️ Alerta enviado para o Telegram com sucesso!")
        else:
            print(f"⚠️ Erro ao enviar Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Falha de conexão ao enviar para o Telegram: {e}")

def extrair_valor_float(texto_preco: str) -> float:
    """Converte strings de preço para float."""
    texto_limpo = texto_preco.replace('.', '').replace('\xa0', ' ').strip()
    match = re.search(r'(\d+)', texto_limpo)
    if match:
        return float(match.group(1))
    return 0.0

def verificar_preco_flights():
    print(f"\n🔍 Consultando preço do voo das 17:55 via Google Flights (Modo GitHub Actions)...")
    
    with sync_playwright() as p:
        # No GitHub Actions, headless DEVE ser True obrigatoriamente
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo"
        )
        
        page = context.new_page()
        
        try:
            print("🌐 Acessando a página...")
            page.goto(URL_FLIGHTS, wait_until="commit", timeout=30000)
            
            try:
                btn_aceitar = page.locator("button:has-text('Aceitar tudo'), button:has-text('Concordo')").first
                if btn_aceitar.is_visible(timeout=3000):
                    btn_aceitar.click()
            except Exception:
                pass

            print("⏳ Aguardando renderização do voo da LATAM...")
            page.wait_for_selector("text=LATAM", timeout=20000)
            time.sleep(2)

            elementos = page.locator("li, div[role='button'], div[class*='Grid']").all()
            
            preco_encontrado = None
            for el in elementos:
                try:
                    texto = el.inner_text()
                    if "LATAM" in texto and "R$" in texto:
                        match_preco = re.search(r'R\$\s*(\d{1,3}(?:\.\d{3})*)', texto)
                        if match_preco:
                            valor = extrair_valor_float(match_preco.group(1))
                            if valor > 100:
                                preco_encontrado = valor
                                break
                except Exception:
                    continue

            if preco_encontrado:
                print(f"✈️ Voo LATAM encontrado!")
                print(f"💰 Preço atual: R$ {preco_encontrado:.2f}")
                
                if preco_encontrado < PRECO_MAXIMO:
                    mensagem = (
                        f"🎉 *ALERTA DE PASSAGEM BARATA!* 🎉\n\n"
                        f"✈️ *Voo:* GRU ➔ MCP (LATAM)\n"
                        f"📅 *Data:* 26/12/2026 às *17:55*\n"
                        f"💵 *Preço:* R$ {preco_encontrado:.2f}\n"
                        f"🚨 *Sua Meta:* Abaixo de R$ {PRECO_MAXIMO:.2f}\n\n"
                        f"🔗 [Clique aqui para comprar no Google Flights]({URL_FLIGHTS})"
                    )
                    enviar_mensagem_telegram(mensagem)
                else:
                    diferenca = preco_encontrado - PRECO_MAXIMO
                    print(f"📉 Ainda acima do planejado. Faltam R$ {diferenca:.2f} para atingir a meta.")
            else:
                print("⚠️ Voo localizado na tela, mas não conseguimos extrair o preço.")

        except PlaywrightTimeoutError:
            print("❌ Tempo esgotado ao tentar localizar o texto 'LATAM' na tela.")
        except Exception as e:
            print(f"❌ Ocorreu um erro: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    verificar_preco_flights()
