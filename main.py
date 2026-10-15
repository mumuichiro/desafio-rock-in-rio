import time
import uuid
from fastapi import FastAPI, HTTPException
import redis

# Conexão ao Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

app = FastAPI(title="Sistema de Venda de Ingressos - Rock in Rio")

TOTAL_INGRESSOS = 100
TEMPO_RESERVA_SEGUNDOS = 600  # 10 minutos


@app.on_event("startup")
def setup_inicial():
    """Inicializa o stock de ingressos no Redis."""
    if not r.exists("ingressos_disponiveis"):
        r.set("ingressos_disponiveis", TOTAL_INGRESSOS)


def validar_posicao_fila(user_id: str):
    """Garante ordem justa de atendimento (FIFO) sem furos na fila."""
    proximo_da_fila = r.lindex("fila_de_espera", 0)
    if proximo_da_fila and proximo_da_fila != user_id:
        raise HTTPException(
            status_code=429, 
            detail="Ainda não é a sua vez na fila virtual."
        )


@app.post("/entrar-na-fila")
def entrar_na_fila(user_id: str):
    """Adiciona o utilizador à fila por ordem de chegada."""
    r.rpush("fila_de_espera", user_id)
    posicao = r.llen("fila_de_espera")
    return {"status": "Na fila", "posicao": posicao, "user_id": user_id}


@app.post("/reservar-ingresso")
def reservar_ingresso(user_id: str):
    """Garante reserva atómica usando Lua script (sem overselling)."""
    validar_posicao_fila(user_id)

    lua_script = """
    local disponiveis = tonumber(redis.call('get', KEYS[1]))
    if disponiveis > 0 then
        redis.call('decr', KEYS[1])
        return 1
    else
        return 0
    end
    """
    reserva_sucesso = r.eval(lua_script, 1, "ingressos_disponiveis")

    if not reserva_sucesso:
        r.lrem("fila_de_espera", 1, user_id)
        raise HTTPException(status_code=400, detail="Ingressos esgotados!")

    r.lpop("fila_de_espera")

    reserva_id = str(uuid.uuid4())
    chave_reserva = f"reserva:{reserva_id}"
    
    r.hset(chave_reserva, mapping={
        "user_id": user_id,
        "status": "PENDENTE_PAGAMENTO",
        "criado_em": time.time()
    })
    r.expire(chave_reserva, TEMPO_RESERVA_SEGUNDOS)

    return {
        "status": "Reserva realizada com sucesso!",
        "reserva_id": reserva_id,
        "expira_em_segundos": TEMPO_RESERVA_SEGUNDOS
    }


@app.post("/confirmar-pagamento")
def confirmar_pagamento(reserva_id: str):
    """Confirma o pagamento dentro do tempo limite da reserva."""
    chave_reserva = f"reserva:{reserva_id}"
    reserva = r.hgetall(chave_reserva)

    if not reserva:
        raise HTTPException(
            status_code=400, 
            detail="Reserva expirada ou inexistente. O ingresso foi devolvido ao stock."
        )

    r.hset(chave_reserva, "status", "PAGO")
    r.persist(chave_reserva)

    return {"status": "Compra efetuada com sucesso!", "reserva_id": reserva_id}