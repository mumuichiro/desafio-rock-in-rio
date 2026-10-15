 # Arquitetura do Sistema de Venda de Ingressos - Rock in Rio

Solução desenvolvida para tratar acessos concorrentes em massa, evitar *overselling* (venda sem stock) e garantir justiça no atendimento aos utilizadores independentemente da velocidade da conexão à internet.

---

## 🖼️ Diagrama de Arquitetura

![Diagrama da Arquitetura](./diagrama.png)

---

## ⚙️ Principais Soluções Adotadas

### 1. Fila Virtual FIFO (Justiça no Acesso)
- Utilização de uma **Fila Virtual Baseada em Redis (`RPUSH` / `LPOP`)**.
- A requisição do utilizador recebe um identificador sequencial na chegada. Utilizadores com conexões de alta velocidade não conseguem ultrapassar quem chegou primeiro à fila.

### 2. Controle de Estoque Atómico (Sem Overselling)
- Utilização de **Script Lua executado nativamente no Redis**.
- As operações de verificação de saldo e decremento ocorrem no mesmo ciclo de processamento atómico em memória. Isso impede *race conditions* mesmo com milhares de requisições por segundo.

### 3. Liberação Automática de Reservas Não Pagas
- As reservas possuem tempo de vida definido via TTL (`EXPIRE` do Redis).
- Se a confirmação do pagamento não for concluída no prazo limite, o ingresso regressa de forma automática e segura ao stock.

---

## 🚀 Como Executar o Projeto Localmente

1. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt