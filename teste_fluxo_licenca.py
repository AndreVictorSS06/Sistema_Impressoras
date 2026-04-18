import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import app.core.license_check as license_check

class TesteFluxoRealSerrana(unittest.TestCase):

    def setUp(self):
        # Define a senha correta (a mesma que está no seu license_check)
        self.senha_valida = "Serrana@2026"
        # Garante que a data base de expiração é 01/07/2026
        license_check.EXPIRY_DATE = datetime(2026, 7, 1, tzinfo=timezone.utc)

    @patch('license_check._get_ntp_time')
    @patch('license_check._save_ext')
    @patch('license_check._load_ext')
    def test_fluxo_bloqueio_e_renovacao(self, mock_load_ext, mock_save_ext, mock_ntp):
        """
        SIMULAÇÃO:
        1. O sistema acorda em 10/07/2026 (Já venceu).
        2. O sistema deve retornar 'valid': False.
        3. O usuário insere a senha de liberação.
        4. O sistema deve renovar e calcular a nova data (Janeiro/2027).
        """
        
        # --- PASSO 1: O BLOQUEIO ---
        # Simulando que hoje é 10 de Julho de 2026 (9 dias após o vencimento)
        data_vencida = datetime(2026, 7, 10, tzinfo=timezone.utc)
        mock_ntp.return_value = data_vencida
        mock_load_ext.return_value = None # Nenhuma renovação prévia
        
        status_inicial = license_check.check_license()
        
        print(f"\n[TESTE] Data Atual Simulada: {status_inicial['current_date']}")
        print(f"[TESTE] Status da Licença: {'BLOQUEADA' if not status_inicial['valid'] else 'ATIVA'}")
        
        self.assertFalse(status_inicial['valid'], "A licença deveria estar vencida!")

        # --- PASSO 2: A LIBERAÇÃO ---
        print(f"[TESTE] Tentando liberar com a senha...")
        
        # Chamando sua função de renovação
        resultado_renovacao = license_check.renovar_licenca(self.senha_valida)
        
        print(f"[TESTE] Resultado: {resultado_renovacao['message']}")
        
        # Verificações
        self.assertTrue(resultado_renovacao['ok'])
        # A nova data deve ser 10/07/2026 + 180 dias = 06/01/2027
        data_esperada = (data_vencida + timedelta(days=180)).strftime("%d/%m/%Y")
        self.assertEqual(resultado_renovacao['nova_expiracao'], data_esperada)
        
        print(f"[TESTE] Nova validade confirmada para: {resultado_renovacao['nova_expiracao']}")

if __name__ == '__main__':
    unittest.main()