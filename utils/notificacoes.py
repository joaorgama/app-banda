"""
utils/notificacoes.py — Integração ntfy.sh
"""
import requests
import uuid

NTFY_BASE = "https://ntfy.sh"
TOPICO_GERAL = "amo-bmo-geral"


def gerar_topico_unico():
    return f"bmo-user-{uuid.uuid4().hex[:12]}"


def enviar_notificacao(topico, titulo, mensagem, prioridade="default", tags="musical_note"):
    try:
        r = requests.post(
            f"{NTFY_BASE}/{topico}",
            data=mensagem.encode("utf-8"),
            headers={
                "Title": titulo,
                "Priority": prioridade,
                "Tags": tags
            },
            timeout=5
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_topico(utilizadores, username):
    u = next((x for x in utilizadores if str(x.get("Username", "")).lower() == username.lower()), None)
    if not u:
        return None
    return u.get("Ntfy_Topic", "") or None


def enviar_para_todos(base, titulo, mensagem, prioridade="default"):
    from cache import get_utilizadores_cached
    utilizadores = get_utilizadores_cached()
    enviados = 0
    for u in utilizadores:
        topico = u.get("Ntfy_Topic", "")
        if topico:
            if enviar_notificacao(topico, titulo, mensagem, prioridade):
                enviados += 1
    enviar_notificacao(TOPICO_GERAL, titulo, mensagem, prioridade)
    return enviados


def enviar_para_utilizador(base, username, titulo, mensagem, prioridade="default"):
    from cache import get_utilizadores_cached
    utilizadores = get_utilizadores_cached()
    topico = _get_topico(utilizadores, username)
    if not topico:
        return False
    return enviar_notificacao(topico, titulo, mensagem, prioridade)


def enviar_para_naipe(base, naipe, titulo, mensagem, prioridade="default"):
    from cache import get_musicos_cached, get_utilizadores_cached
    musicos = get_musicos_cached()
    utilizadores = get_utilizadores_cached()
    usernames = [
        str(m.get("Username", "")).lower()
        for m in musicos
        if str(m.get("Naipe", "")).strip() == naipe
    ]
    enviados = 0
    for username in usernames:
        topico = _get_topico(utilizadores, username)
        if topico:
            if enviar_notificacao(topico, titulo, mensagem, prioridade):
                enviados += 1
    return enviados


def enviar_para_instrumento(base, instrumento, titulo, mensagem, prioridade="default"):
    from cache import get_musicos_cached, get_utilizadores_cached
    musicos = get_musicos_cached()
    utilizadores = get_utilizadores_cached()
    usernames = [
        str(m.get("Username", "")).lower()
        for m in musicos
        if str(m.get("Instrumento", "")).strip() == instrumento
    ]
    enviados = 0
    for username in usernames:
        topico = _get_topico(utilizadores, username)
        if topico:
            if enviar_notificacao(topico, titulo, mensagem, prioridade):
                enviados += 1
    return enviados


def listar_naipes(base):
    from cache import get_musicos_cached
    musicos = get_musicos_cached()
    return sorted(set(
        str(m.get("Naipe", "")).strip()
        for m in musicos
        if m.get("Naipe")
    ))


def listar_instrumentos(base):
    from cache import get_musicos_cached
    musicos = get_musicos_cached()
    return sorted(set(
        str(m.get("Instrumento", "")).strip()
        for m in musicos
        if m.get("Instrumento")
    ))
