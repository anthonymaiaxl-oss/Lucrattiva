# Agendamento no Windows (Tarefas Agendadas)

Duas tarefas, criadas uma vez. Use o **Agendador de Tarefas**, não um serviço
com watchdog: se o processo cair, o agendador simplesmente volta na próxima
rodada; um serviço parado fica parado.

## Tarefa 1 — processar

| Campo | Valor |
|---|---|
| Nome | `docauto - processar entrada` |
| Disparador | Diariamente, repetir a cada **10 minutos**, por tempo indeterminado |
| Ação | Iniciar programa → `C:\CONTABIL\docauto\scripts\processar.bat` |
| Conta | Usuário de serviço **com acesso ao compartilhamento de rede** |
| Opções | "Executar estando o usuário conectado ou não" · "Não iniciar nova instância se já estiver em execução" |

## Tarefa 2 — enviar ao Express

| Campo | Valor |
|---|---|
| Nome | `docauto - enviar Express` |
| Disparador | modo `pasta_monitorada`: a cada **15 minutos** · modo `lote_manual`: **1x por dia, 08h00** |
| Ação | `C:\CONTABIL\docauto\scripts\enviar.bat` |

## Antes de agendar

1. Rode os dois `.bat` **na mão**, com o usuário que vai executar a tarefa.
   O erro mais comum é a tarefa rodar com uma conta sem acesso ao
   `\\SERVIDOR\...` — o script funciona no seu login e falha no agendador.
2. Confira `data\registro\processar.log` e `envio.log` depois da primeira
   execução automática.
3. Só ligue a Tarefa 2 depois do teste de 30 minutos do `docs/11`.
