import os
import sys
import logging
import webview
import threading
import time

from app.api import Api
from app.core.database import init_db
from app.core.license_check import check_license

# Configurações de Performance e Silenciamento de Logs
logging.getLogger('pywebview').setLevel(logging.CRITICAL)
os.environ["WEBVIEW_DISABLE_ACCESSIBILITY"] = "1"

def verificar_em_segundo_plano(window, api, base_dir):
    def tarefa():
        try:
            start = time.time()
            print("🚀 Início do background")

            # 1. Inicializa Banco de Dados
            init_db()
            print(f"⏱️ Tempo DB: {time.time() - start:.2f}s")

            # Pequena pausa para garantir que o front-end carregou o "loading"
            time.sleep(0.5)

            # 2. Verificação da Licença (NTP)
            res = check_license()
            print(f"⏱️ Tempo Licença: {time.time() - start:.2f}s")

            # Guarda o resultado na API para o Front-end consultar via JS
            api.license_info = res

            if not res["valid"]:
                # Caminho absoluto para a tela de bloqueio
                expired_path = os.path.abspath(os.path.join(base_dir, 'gui', 'blocked', 'license_expired.html'))
                file_url = 'file:///' + expired_path.replace('\\', '/')
                
                print("❌ Licença Inválida. Redirecionando...")
                print(f"DEBUG - Caminho absoluto: {expired_path}")
                print(f"DEBUG - O arquivo existe? {os.path.exists(expired_path)}")
                window.load_url(file_url)
            else:
                print("✅ Sistema validado e pronto")
        except Exception as e:
            print(f"❌ ERRO CRÍTICO NO BACKGROUND: {e}")
            import traceback
            traceback.print_exc()

    # Inicia a thread em modo daemon (morre se o app fechar)
    threading.Thread(target=tarefa, daemon=True).start()

def run():
    # Identificação de pasta base (Garante funcionamento no .EXE)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    api = Api()
    
    # Caminho do Index (Convertido para Absolute Path)
    index_path = os.path.abspath(os.path.join(base_dir, 'gui', 'main', 'index.html'))

    # --- LOG DE DEPURAÇÃO ---
    print(f"DEBUG: Procurando arquivo em: {index_path}")
    if not os.path.exists(index_path):
        print("❌ ERRO CRÍTICO: O arquivo index.html NÃO existe nesse caminho!")

    index_url = 'file:///' + index_path.replace('\\', '/')

    window = webview.create_window(
        'Sistema de Gestão Serrana', 
        url=index_url, # Usando a URL formatada
        js_api=api,
        width=1000, 
        height=750, 
        background_color='#ffffff'
    )
    
    api._window = window

    # Inicia o app e chama a verificação logo após a abertura da janela
    webview.start(
        verificar_em_segundo_plano, 
        (window, api, base_dir), 
        debug=True, 
    )

if __name__ == '__main__':
    run()