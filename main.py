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
            init_db()
            # Pequena pausa para garantir que o front-end carregou o "loading"
            time.sleep(0.8)

            res = check_license()

            # Guarda o resultado na API para o Front-end consultar via JS
            api.license_info = res

            if not res["valid"]:
                expired_path = os.path.abspath(os.path.join(base_dir, 'gui', 'blocked', 'license_expired.html'))
                file_url = 'file:///' + expired_path.replace('\\', '/')
                window.load_url(file_url)
        except Exception:
            pass

    # Inicia a thread em modo daemon (morre se o app fechar)
    threading.Thread(target=tarefa, daemon=True).start()

def run():
    # Identificação de pasta base (Garante funcionamento no .EXE --onefile)
    if getattr(sys, 'frozen', False):
        # Pasta temporária onde o PyInstaller extrai os arquivos internos
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    api = Api()
    
    # Caminho do Index (Convertido para Absolute Path)
    index_path = os.path.abspath(os.path.join(base_dir, 'gui', 'main', 'index.html'))

    if not os.path.exists(index_path):
        sys.exit(1)

    index_url = 'file:///' + index_path.replace('\\', '/')

    window = webview.create_window(
        'Sistema de Gestão Serrana', 
        url=index_url, 
        js_api=api,
        width=1000, 
        height=750, 
        background_color='#ffffff'
    )
    
    api._window = window

    # Inicia o app em modo produção (debug=False esconde o DevTools)
    webview.start(
        verificar_em_segundo_plano, 
        (window, api, base_dir), 
        debug=False, 
    )

if __name__ == '__main__':
    run()