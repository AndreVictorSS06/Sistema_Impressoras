import csv
import sqlite3
from datetime import datetime

def gerar_csv_final():
    nome_arquivo = f"Relatorio_Serrana_{datetime.now().strftime('%d-%m-%Y')}.csv"
    conn = sqlite3.connect("gestao_impressoras.db")
    cursor = conn.cursor()

    # Busca registros e comandas
    registros = cursor.execute("SELECT * FROM registros").fetchall()
    comandas = cursor.execute("SELECT * FROM comandas").fetchall()
    
    total_registros = sum(r[7] for r in registros) # Coluna total_mensal
    total_comandas = sum(c[2] for c in comandas)   # Coluna valor
    
    with open(nome_arquivo, mode="w", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.writer(arquivo, delimiter=';')
        
        # Cabeçalho baseado no seu original
        writer.writerow(["Impressora", "Série", "Setor", "Mês Ant.", "Mês Atual", "Qtd", "Total Mensal"])
        for r in registros:
            writer.writerow([r[1], r[2], r[3], r[4], r[5], r[6], f"R$ {r[7]:.2f}"])

        writer.writerow([])
        writer.writerow(["--- COMANDAS ---"])
        for c in comandas:
            writer.writerow([c[1], f"R$ {c[2]:.2f}"])

        writer.writerow([])
        writer.writerow(["RESUMO GERAL"])
        writer.writerow(["Total Impressoras", f"R$ {total_registros:.2f}"])
        writer.writerow(["Total Comandas", f"R$ {total_comandas:.2f}"])
        writer.writerow(["TOTAL GERAL", f"R$ {total_registros + total_comandas:.2f}"])

    conn.close()
    return nome_arquivo