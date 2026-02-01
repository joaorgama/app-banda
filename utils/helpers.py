import hashlib
from datetime import datetime
import pandas as pd

DEFAULT_PASS = "1234"

def hash_password(password):
    """Cria hash SHA256 da password"""
    return hashlib.sha256(str(password).encode()).hexdigest()

def converter_data_robusta(valor):
    """Converte vários formatos de data para date object"""
    if not valor or str(valor) in ['None', 'nan', '']:
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.date()
    
    str_data = str(valor).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(str_data.split(' ')[0].split('T')[0], fmt).date()
        except:
            continue
    return None

def formatar_data_pt(valor):
    """Formata data para DD/MM/YYYY"""
    dt = converter_data_robusta(valor)
    return dt.strftime('%d/%m/%Y') if dt else "---"
