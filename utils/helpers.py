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
    
def calcular_aniversarios(musicos_list, dias=15):
    """
    Calcula aniversários nos próximos X dias
    
    Args:
        musicos_list: lista de músicos da base de dados
        dias: número de dias para procurar (default 15)
    
    Returns:
        lista de dicionários com músicos que fazem anos
    """
    from datetime import datetime, timedelta
    
    hoje = datetime.now().date()
    data_limite = hoje + timedelta(days=dias)
    
    aniversarios = []
    
    for m in musicos_list:
        data_nasc = converter_data_robusta(m.get('Data de Nascimento'))
        
        if not data_nasc:
            continue
        
        # Criar data do aniversário no ano atual
        try:
            aniversario_este_ano = data_nasc.replace(year=hoje.year)
        except ValueError:
            # Caso especial: 29 de fevereiro em ano não bissexto
            aniversario_este_ano = data_nasc.replace(year=hoje.year, day=28)
        
        # Se o aniversário já passou este ano, considerar o próximo ano
        if aniversario_este_ano < hoje:
            try:
                aniversario_este_ano = data_nasc.replace(year=hoje.year + 1)
            except ValueError:
                aniversario_este_ano = data_nasc.replace(year=hoje.year + 1, day=28)
        
        # Verificar se está dentro dos próximos X dias
        if hoje <= aniversario_este_ano <= data_limite:
            dias_faltam = (aniversario_este_ano - hoje).days
            idade = hoje.year - data_nasc.year
            
            aniversarios.append({
                'nome': m.get('Nome', 'Desconhecido'),
                'data_nascimento': data_nasc,
                'data_aniversario': aniversario_este_ano,
                'dias_faltam': dias_faltam,
                'idade': idade,
                'instrumento': m.get('Instrumento', 'N/D')
            })
    
    # Ordenar por dias faltantes
    aniversarios.sort(key=lambda x: x['dias_faltam'])
    
    return aniversarios
