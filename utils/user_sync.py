"""
Sincronização de utilizadores - Portal BMO
"""
import bcrypt
from unidecode import unidecode

def gerar_username(nome):
    """Gera username a partir do nome completo"""
    if not nome:
        return None
    
    # Remover acentos e converter para minúsculas
    nome_limpo = unidecode(str(nome)).lower()
    
    # Dividir nome
    partes = nome_limpo.split()
    
    if len(partes) == 0:
        return None
    elif len(partes) == 1:
        return partes[0]
    else:
        # Primeiro nome + último apelido
        return f"{partes[0]}_{partes[-1]}"

def limpar_duplicados_utilizadores(base):
    """
    Remove duplicados da tabela Utilizadores
    Mantém a versão com password encriptada se existir
    """
    try:
        utilizadores = base.list_rows("Utilizadores")
        
        if not utilizadores:
            return {"removidos": 0, "erro": None}
        
        # Agrupar por username
        usuarios_por_username = {}
        
        for u in utilizadores:
            username = str(u.get('Username', '')).lower().strip()
            
            if not username:
                continue
            
            if username not in usuarios_por_username:
                usuarios_por_username[username] = []
            
            usuarios_por_username[username].append(u)
        
        # Remover duplicados
        removidos = 0
        
        for username, lista_users in usuarios_por_username.items():
            if len(lista_users) > 1:
                # Ordenar: passwords encriptadas primeiro (começam com $2b$)
                lista_users.sort(
                    key=lambda x: (
                        0 if str(x.get('Password', '')).startswith('$2b$') else 1,
                        x.get('_id', '')
                    )
                )
                
                # Manter o primeiro (password encriptada ou mais antigo)
                manter = lista_users[0]
                
                # Remover os outros
                for u in lista_users[1:]:
                    try:
                        base.delete_row("Utilizadores", u['_id'])
                        removidos += 1
                    except Exception as e:
                        print(f"Erro ao remover {u.get('Username')}: {e}")
        
        return {"removidos": removidos, "erro": None}
    
    except Exception as e:
        return {"removidos": 0, "erro": str(e)}

def sincronizar_novos_utilizadores(base):
    """
    Cria utilizadores para músicos que ainda não têm conta
    Password padrão: 1234 (será encriptada)
    """
    try:
        musicos = base.list_rows("Musicos")
        utilizadores = base.list_rows("Utilizadores")
        
        if not musicos:
            return {"criados": 0, "erro": "Nenhum músico encontrado"}
        
        # Criar set de usernames existentes
        usernames_existentes = set()
        for u in utilizadores:
            username = str(u.get('Username', '')).lower().strip()
            if username:
                usernames_existentes.add(username)
        
        # Verificar músicos sem conta
        criados = 0
        erros = []
        
        for m in musicos:
            nome = m.get('Nome', '')
            username_musico = str(m.get('Username', '')).lower().strip()
            
            # Se músico já tem username definido, usar esse
            if username_musico:
                username = username_musico
            else:
                # Gerar username a partir do nome
                username = gerar_username(nome)
            
            if not username:
                continue
            
            # Se já existe, skip
            if username in usernames_existentes:
                continue
            
            # Criar novo utilizador
            try:
                # Password padrão: 1234 (encriptada)
                password_hash = bcrypt.hashpw("1234".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                base.append_row("Utilizadores", {
                    "Nome": nome,
                    "Username": username,
                    "Password": password_hash,
                    "Funcao": "Musico"
                })
                
                # Atualizar username no músico se não tinha
                if not username_musico:
                    base.update_row("Musicos", m['_id'], {"Username": username})
                
                criados += 1
                usernames_existentes.add(username)
            
            except Exception as e:
                erros.append(f"{nome}: {str(e)}")
        
        resultado = {"criados": criados, "erro": None}
        
        if erros:
            resultado["erro"] = "; ".join(erros[:5])  # Mostrar só primeiros 5 erros
        
        return resultado
    
    except Exception as e:
        return {"criados": 0, "erro": str(e)}
