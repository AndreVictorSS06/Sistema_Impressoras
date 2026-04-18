import base64
import sqlite3
import webview
import os
import sys
import threading
from pathlib import Path
import time
from datetime import datetime

# Imports do seu projeto
from app.core.database import DB_PATH, salvar_no_banco
from app.core.license_check import renovar_licenca as renovar_no_disco


class Api:
    def __init__(self):
        self._window = None
        self.license_info = None
        
        # Centralização das configurações das impressoras
        self.config_impressoras = {
            "Impressora Faturamento": {"serie": "VR92Y07575", "setor": "FATURAMENTO", "taxa": 0.03},
            "Impressora Corredor": {"serie": "VR91788881", "setor": "CORREDOR", "taxa": 0.03},
            "Impressora Financeiro": {"serie": "VR92198259", "setor": "FINANCEIRO", "taxa": 0.03},
            "Impressora Compras": {"serie": "VR92Y08441", "setor": "COMPRAS", "taxa": 0.03},
            "Impressora Contabilidade": {"serie": "VR91Z94334", "setor": "CONTABILIDADE", "taxa": 0.03},
        }

    def voltar_inicio(self):
        """Retorna para a interface principal do sistema."""
        try:
            raiz = self._get_root_path()
            index_path = raiz / "gui" / "main" / "index.html"
            
            if index_path.exists() and self._window:
                self._window.load_url(index_path.as_uri())
        except Exception as e:
            print(f"❌ Erro ao voltar para o início: {e}")

    # --- LÓGICA DE NAVEGAÇÃO E LICENÇA ---

    def _get_root_path(self):
        """Busca a raiz do projeto de forma absoluta e robusta."""
        if getattr(sys, 'frozen', False):
            raiz = Path(sys.executable).parent
        else:
            # Pega o caminho absoluto do api.py e sobe 2 níveis (app -> raiz)
            raiz = Path(os.path.abspath(__file__)).parent.parent
        
        print(f"DEBUG RAIZ: {raiz}")
        return raiz

    def renovar_licenca(self, senha_digitada):
        resultado = renovar_no_disco(senha_digitada)
        
        if isinstance(resultado, dict) and resultado.get("ok"):
            def execute_redirect():
                try:
                    raiz = self._get_root_path()
                    
                    # Tentativa 1: Caminho padrão (gui/main/index.html)
                    index_path = raiz / "gui" / "main" / "index.html"
                    
                    # Tentativa 2: Fallback (gui/index.html) caso a pasta 'main' não exista
                    if not index_path.exists():
                        index_path = raiz / "gui" / "index.html"

                    print(f"🔎 DEBUG - Verificando arquivo em: {index_path}")

                    if index_path.exists() and self._window:
                        url_final = index_path.as_uri() 
                        print(f"🚀 Carregando interface: {url_final}")
                        self._window.load_url(url_final)
                    else:
                        print(f"❌ Erro fatal: Arquivo index.html não localizado em {raiz}")
                        
                except Exception as e:
                    print(f"❌ Erro crítico no redirecionamento: {e}")

            # O Timer de 0.5s é essencial para não travar a comunicação RPC
            threading.Timer(0.5, execute_redirect).start()
        
        return resultado

    # --- LÓGICA DE BANCO DE DADOS ---

    def salvar_lote_no_banco(self, registros):
        """Salva múltiplos registros de impressoras em uma única transação."""
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                for item in registros:
                    salvar_no_banco(item, conn=conn)
                conn.commit()
                return {"status": "success", "message": "Relatório salvo com sucesso!"}
            except Exception as e:
                conn.rollback()
                return {"status": "error", "message": f"Erro ao salvar lote: {str(e)}"}

    def get_historico(self, mes_ano=None):
        """Recupera histórico unificado de impressoras e comandas."""
        if not mes_ano:
            mes_ano = datetime.now().strftime('%Y-%m')

        query = '''
            -- Mudamos 'data_registro' para 'mes_referencia' no filtro WHERE
            SELECT 'Impressora', impressora, serie, setor, leitura_anterior, leitura_atual, custo, '', data_registro
            FROM registros WHERE mes_referencia = ?
            UNION ALL
            SELECT 'Comanda', descricao, '', setor, 0, 0, valor, tipo_consumo, data_registro
            FROM comandas WHERE mes_referencia = ?
            ORDER BY data_registro DESC
        '''
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (mes_ano, mes_ano))
            return [list(row) for row in cursor.fetchall()]

    def get_resumo_mes(self, mes_ano):
        """Calcula totais financeiros e de páginas do mês baseando-se no mês de referência."""
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            cursor = conn.cursor()
            
            # Mudamos o filtro de strftime('%Y-%m', data_registro) para mes_referencia
            # Isso garante que os cards mostrem o que está na tabela
            imp = cursor.execute("SELECT SUM(custo) FROM registros WHERE mes_referencia = ?", (mes_ano,)).fetchone()[0] or 0
            com = cursor.execute("SELECT SUM(valor) FROM comandas WHERE mes_referencia = ?", (mes_ano,)).fetchone()[0] or 0
            pag = cursor.execute("SELECT SUM(leitura_atual - leitura_anterior) FROM registros WHERE mes_referencia = ?", (mes_ano,)).fetchone()[0] or 0
            
            return {
                "total_impressoras": float(imp),
                "total_comandas": float(com),
                "total_geral": float(imp + com),
                "total_paginas": int(pag)
            }
    # --- FUNÇÕES DE UTILITÁRIOS E EXPORTAÇÃO ---

    def get_impressoras(self):
        return list(self.config_impressoras.keys())

    def get_info_impressora(self, nome):
        return self.config_impressoras.get(nome, {"serie": "N/A", "setor": "N/A"})

    def get_ultima_leitura(self, nome_impressora):
        """Busca a última leitura_atual registrada para uma impressora específica."""
        query = "SELECT leitura_atual FROM registros WHERE impressora = ? ORDER BY data_registro DESC LIMIT 1"
        try:
            with sqlite3.connect(DB_PATH, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (nome_impressora,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"❌ Erro ao buscar última leitura: {e}")
            return 0

    def get_license_info(self):
        return self.license_info

    def salvar_arquivo_excel(self, conteudo_base64, nome_sugerido):
        """Abre diálogo do SO para salvar arquivo convertido de Base64."""
        try:
            if not self._window:
                return False
                
            res = self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=nome_sugerido)
            if not res:
                return False

            save_path = res[0] if isinstance(res, (list, tuple)) else res
            
            # Limpa cabeçalho data:image/xlsx;base64, se existir
            if "," in conteudo_base64:
                conteudo_base64 = conteudo_base64.split(",")[1]
            
            with open(save_path, 'wb') as f:
                f.write(base64.b64decode(conteudo_base64))
            return True
        except Exception as e:
            print(f"❌ Erro ao exportar Excel: {e}")
            return False


    def preparar_impressao_pdf(self, dados):
        """Função unificada para gerar o PDF do histórico com limpeza automática."""
        try:
            root_dir = self._get_root_path()
            
            # 1. Caminhos absolutos baseados na estrutura real
            template_path = root_dir / "gui" / "templates" / "relatorio" / "index_rel.html"
            css_path = root_dir / "gui" / "templates" / "relatorio" / "style_rel.css"
            logo_path = root_dir / "gui" / "assets" / "LogoSerrana.jpg"
            temp_file = root_dir / "temp_print.html"

            # Limpeza preventiva: se houver lixo de uma execução travada anterior, removemos agora
            try:
                if temp_file.exists():
                    os.remove(temp_file)
            except:
                pass

            # 2. Validação de existência
            if not template_path.exists():
                print(f"❌ ERRO: Template não encontrado em: {template_path}")
                return False

            # 3. Leitura e processamento
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()

            with open(logo_path, "rb") as img_file:
                logo_b64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            css_url = "file:///" + str(css_path).replace("\\", "/")

            # 4. Montagem da Tabela com tratamento de dados nulos
            rows_html = ""
            for item in dados['itens']:
                rows_html += f"""
                <tr>
                    <td>{item.get('tipo', '-')}</td>
                    <td>{item.get('desc', item.get('descricao', '-'))}</td>
                    <td>{item.get('tipo_consumo', '-')}</td>
                    <td>{item.get('setor', '-')}</td>
                    <td>{item.get('serie', '-')}</td>
                    <td class='text-right'>{item.get('anterior', '-')}</td>
                    <td class='text-right'>{item.get('atual', '-')}</td>
                    <td class='text-right'>{item.get('consumo', '-')}</td>
                    <td class='text-right'>R$ {item.get('valor', '0.00')}</td>
                </tr>"""

            # 5. Formatação Amigável do Mês
            mes_amigavel = dados['mes']
            try:
                dt = datetime.strptime(dados['mes'], "%Y-%m")
                meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                mes_amigavel = f"{meses[dt.month - 1]} / {dt.year}"
            except:
                pass

            # 6. Substituição de Placeholders
            replacements = {
                "{{MES_REFERENCIA}}": mes_amigavel,
                "{{LOGO_BASE64}}": f"data:image/jpeg;base64,{logo_b64}",
                "{{ESTILO_CSS}}": css_url,
                "{{TOTAL_IMP}}": dados['total_imp'],
                "{{TOTAL_COM}}": dados['total_com'],
                "{{TOTAL_PAGINAS}}": dados['total_paginas'],
                "{{TOTAL_GERAL}}": dados['total_geral'],
                "{{TABELA_ROWS}}": rows_html
            }

            for placeholder, value in replacements.items():
                html = html.replace(placeholder, str(value))

            # 7. Escrita do arquivo temporário
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(html)

            target_url = "file:///" + str(temp_file).replace("\\", "/")
            self._window.load_url(target_url)
            
            # 8. Trigger de Impressão e Limpeza em Background
            def disparar_e_limpar():
                # Delay necessário para o Webview carregar o CSS/Imagens antes do print
                time.sleep(1.5)
                if self._window:
                    self._window.evaluate_js("window.print();")
                
                # Aguarda 15 segundos para garantir que o usuário interagiu com a caixa de diálogo
                # e o sistema operacional já processou o arquivo.
                time.sleep(15)
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"🧹 Limpeza concluída: {temp_file} removido.")
                except Exception as e:
                    print(f"⚠️ Falha na limpeza (arquivo pode estar aberto): {e}")

            threading.Thread(target=disparar_e_limpar, daemon=True).start()
            
            return True

        except Exception as e:
            print(f"❌ Erro crítico ao gerar PDF: {e}")
            return False
