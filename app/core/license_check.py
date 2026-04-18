from pathlib import Path

import ntplib
import os
import json
import hashlib
import sys
from datetime import datetime, timezone, timedelta

# ============================================================
#  Configuração de Caminhos (Local - Mesma pasta do EXE)
# ============================================================
def get_storage_path():
    """Define a pasta 'data' na raiz do projeto, independente de onde o script esteja."""
    if getattr(sys, 'frozen', False):
        # Se for um executável (.exe), a pasta 'data' fica ao lado dele
        base_path = Path(sys.executable).parent
    else:
        # Se for script (.py) em app/core/license_check.py:
        # .parent é 'core/'
        # .parent.parent é 'app/'
        # .parent.parent.parent é a RAIZ do projeto
        base_path = Path(__file__).resolve().parent.parent.parent
    
    # Define o caminho final para a pasta 'data' na raiz
    storage_path = os.path.join(base_path, "data")
    
    # Cria a pasta na raiz se ela não existir
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
        
    return storage_path

_STORAGE = get_storage_path()
_STAMP_FILE = os.path.join(_STORAGE, ".lic_stamp") # Arquivo oculto de timestamp
_EXT_FILE   = os.path.join(_STORAGE, ".lic_ext")   # Arquivo oculto de extensão
_SECRET = "serrana_gestao_2024"

# ============================================================
#  Data base de expiracao do sistema
# ============================================================
EXPIRY_DATE = datetime(2026, 4, 10, tzinfo=timezone.utc)
_SENHA_HASH = hashlib.sha256("Serrana@2026".encode()).hexdigest()
_EXTENSION_DAYS = 180

# --- FUNÇÕES INTERNAS AUXILIARES ---

def _hmac(ts: float) -> str:
    raw = f"{ts:.0f}{_SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()

def _save_stamp(dt: datetime):
    ts = dt.timestamp()
    try:
        with open(_STAMP_FILE, "w") as f:
            json.dump({"ts": ts, "sig": _hmac(ts)}, f)
    except: pass

def _load_stamp():
    try:
        if not os.path.exists(_STAMP_FILE): return None
        with open(_STAMP_FILE) as f:
            d = json.load(f)
        ts = d["ts"]
        if d.get("sig") != _hmac(ts): return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except: return None

def _save_ext(new_expiry: datetime):
    ts = new_expiry.timestamp()
    try:
        with open(_EXT_FILE, "w") as f:
            json.dump({"ts": ts, "sig": _hmac(ts + 1)}, f)
    except: pass

def _load_ext():
    try:
        if not os.path.exists(_EXT_FILE): return None
        with open(_EXT_FILE) as f:
            d = json.load(f)
        ts = d["ts"]
        if d.get("sig") != _hmac(ts + 1): return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except: return None

def _get_ntp_time():
    import time
    import ntplib
    from datetime import datetime, timezone

    print("\n🌐 Iniciando verificação NTP...")

    servers = ["a.st1.ntp.br", "pool.ntp.org"]

    for server in servers:
        try:
            print(f"⏳ Tentando servidor: {server}")
            inicio = time.time()

            client = ntplib.NTPClient()
            response = client.request(server, version=3, timeout=1)

            fim = time.time()
            tempo = fim - inicio

            data = datetime.fromtimestamp(response.tx_time, tz=timezone.utc)

            print(f"✅ Sucesso com {server}")
            print(f"⏱️ Tempo resposta: {tempo:.2f}s")
            print(f"🕒 Data recebida: {data.strftime('%d/%m/%Y %H:%M:%S')}")
            
            return data

        except Exception as e:
            print(f"❌ Erro com {server}: {str(e)}")

    print("⚠️ Nenhum servidor NTP respondeu, usando hora local.")
    return None

def _effective_expiry() -> datetime:
    print("\n🔍 DEBUG LICENÇA")

    print("📅 EXPIRY_DATE:", EXPIRY_DATE)

    ext = _load_ext()
    print("📦 EXTENSÃO (.lic_ext):", ext)

    if ext and ext > EXPIRY_DATE:
        print("✅ Usando EXTENSÃO")
        return ext

    print("⚠️ Usando EXPIRY_DATE")
    return EXPIRY_DATE

# --- FUNÇÕES PÚBLICAS ---

def check_license() -> dict:
    result = {
        "valid": False,
        "source": "unknown",
        "offline": False,
        "clock_tampered": False,
        "current_date": "",
        "expiry_date": "",
        "message": "",
    }

    effective = _effective_expiry()
    result["expiry_date"] = effective.strftime("%d/%m/%Y")

    ntp_time = _get_ntp_time()

    if ntp_time:
        _save_stamp(ntp_time)
        current = ntp_time
        result["source"] = "internet"
        result["offline"] = False
    else:
        result["offline"] = True
        stamp = _load_stamp()
        local_time = datetime.now(timezone.utc)

        if stamp and local_time < (stamp - timedelta(minutes=5)):
            result["clock_tampered"] = True
            result["source"] = "stamp"
            current = stamp
            result["message"] = "Inconsistência no relógio detectada."
        else:
            current = local_time
            result["source"] = "local"
            # Atualiza o carimbo com a hora local válida para evitar retrocessos futuros
            _save_stamp(current)

    result["current_date"] = current.strftime("%d/%m/%Y")
    # Margem de tolerância até o fim do dia de expiração
    result["valid"] = current <= (effective + timedelta(hours=23, minutes=59))

    if not result["valid"] and not result["message"]:
        result["message"] = f"Licença expirada em {result['expiry_date']}."

    return result

def renovar_licenca(senha: str) -> dict:
    if hashlib.sha256(senha.encode()).hexdigest() != _SENHA_HASH:
        return {"ok": False, "message": "Senha incorreta.", "nova_expiracao": ""}

    agora = _get_ntp_time() or datetime.now(timezone.utc)
    expiracao_atual = _effective_expiry()
    
    base_calculo = max(agora, expiracao_atual)
    nova = base_calculo + timedelta(days=_EXTENSION_DAYS)
    
    _save_ext(nova)

    return {
        "ok": True,
        "message": f"Licença renovada até {nova.strftime('%d/%m/%Y')}!",
        "nova_expiracao": nova.strftime("%d/%m/%Y"),
    }