import sqlite3
import os
import sys
from datetime import datetime, timedelta

def get_db_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        from pathlib import Path
        # Garante a subida correta de níveis até a raiz
        base_path = Path(__file__).resolve().parents[2]
    
    target_dir = os.path.join(base_path, "data")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    return os.path.join(target_dir, "gestao_impressoras.db")

DB_PATH = get_db_path()

def init_db():
    """Inicializa o banco e aplica as colunas de competência (WinThor Style)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    # Melhora performance de escrita
    conn.execute("PRAGMA journal_mode=WAL")
    
    cursor = conn.cursor()
    
    # Tabela de Impressoras com mes_referencia
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        impressora TEXT, serie TEXT, setor TEXT,
        leitura_anterior INTEGER DEFAULT 0, 
        leitura_atual INTEGER DEFAULT 0,
        custo REAL, 
        data_registro TEXT,
        mes_referencia TEXT)''')

    # Tabela de Comandas com mes_referencia
    cursor.execute('''CREATE TABLE IF NOT EXISTS comandas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        descricao TEXT, valor REAL, setor TEXT, 
        tipo_consumo TEXT DEFAULT '', 
        data_registro TEXT,
        mes_referencia TEXT)''')
    
    # MIGRAÇÕES (Adiciona a coluna de referência se ela não existir em bancos antigos)
    try: cursor.execute("ALTER TABLE registros ADD COLUMN mes_referencia TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE comandas ADD COLUMN mes_referencia TEXT")
    except: pass

    conn.commit()
    conn.close()

def salvar_no_banco(item, conn=None):
    """Salva o item calculando o mês de competência (Mês Anterior)."""
    db_conn = conn if conn else sqlite3.connect(DB_PATH, timeout=10)
    cursor = db_conn.cursor()
    
    agora = datetime.now()
    # Data exata do clique (Hoje)
    data_hoje = agora.strftime('%Y-%m-%d %H:%M:%S')
    
    # CÁLCULO DO MÊS DE REFERÊNCIA (Mês Passado)
    # Ex: Se hoje é 02/04, o primeiro dia de Abril - 1 dia = 31/03.
    primeiro_dia_mes_atual = agora.replace(day=1)
    mes_passado = primeiro_dia_mes_atual - timedelta(days=1)
    competencia = mes_passado.strftime('%Y-%m') # Resultado: "2026-03"

    if item['tipo'] == 'Impressora':
        cursor.execute('''INSERT INTO registros 
            (impressora, serie, setor, custo, leitura_anterior, leitura_atual, data_registro, mes_referencia) 
            VALUES (?,?,?,?,?,?,?,?)''',
            (item['impressora'], item['serie'], item['setor'], item.get('custo', 0),
             item.get('leitura_anterior', 0), item.get('leitura_atual', 0), data_hoje, competencia))
             
    elif item['tipo'] == 'Comanda':
        cursor.execute('''INSERT INTO comandas 
            (descricao, valor, setor, tipo_consumo, data_registro, mes_referencia)
            VALUES (?,?,?,?,?,?)''', 
            (item['descricao'], item['valor'], item['setor'], 
             item.get('tipo_consumo', ''), data_hoje, competencia))
    
    if not conn:
        db_conn.commit()
        db_conn.close()