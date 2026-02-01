"""
Funções auxiliares para a aplicação BMO
"""
import hashlib
from datetime import datetime
import pandas as pd

DEFAULT_PASS = "1234"

def hash_password(password):
    """Cria hash SHA256 da password"""
    return hashlib.sha256(str(password).encode()).hexdigest()

def converter_data_robusta(valor):
    """
    Converte vários formatos de data para date object
    Aceita: datetime, string ISO, string PT, timestamps
    """
    if not valor or str(valor) in ['None', 'nan', '', 'NaT']:
        return None
    
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.date()
    
    str_data = str(valor).strip()
    
    # Tentar vários formatos
    formatos = [
        '%Y-%m-%d',           # 2026-02-01
        '%d/%m/%Y',           # 01/02/2026
        '%Y-%m-%d %H:%M:%S',  # 2026-02-01 14:30:00
        '%d-%m-%Y',           # 01-02-2026
    ]
    
    for fmt in formatos:
        try:
            data_limpa = str_data.split(' ')[0].split('T')[0]
            return datetime.strptime(data_limpa, fmt).date()
        except:
            continue
    
    return None

def formatar_data_pt(valor):
    """Formata data para formato português DD/MM/YYYY"""
    dt = converter_data_robusta(valor)
    return dt.strftime('%d/%m/%Y') if dt else "---"

def validar_email(email):
    """Validação básica de email"""
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, str(email)) is not None

def validar_telefone(telefone):
    """Validação básica de telefone português"""
    tel = str(telefone).replace(' ', '').replace('-', '')
    return len(tel) == 9 and tel.isdigit()
