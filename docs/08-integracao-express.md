# 08 — Integração com o Domínio Processos Express

> **Aviso, e ele é o mais importante deste documento:** nada aqui afirma o que o
> Express faz. Tudo que segue é (a) o que você me informou, (b) o que consta em
> páginas públicas, e (c) **o que precisa ser confirmado com a Thomson Reuters
> antes de virar código**. Este projeto foi construído para funcionar **sem**
> nenhuma integração — a Fase 3 é um ganho, não um pré-requisito.

## O que foi verificado publicamente (setembro/2026)

| Achado | Onde | O que significa para nós |
|---|---|---|
| Existe artigo oficial no Portal do Cliente: **"Como utilizar Express?"** (código 9146) | [suporte.dominioatendimento.com](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146) | **É a primeira coisa a ler.** Fonte oficial sobre formatos aceitos, limites de upload e comportamento quando há mais de uma tarefa candidata. |
| Existe **Central do Desenvolvedor** da Domínio e uma **Onvio BR Accounting API** com portal de documentação | [Central do Desenvolvedor](https://www.dominiosistemas.com.br/lp-centraldodesenvolvedor-api/) · [Developer Portal](https://developerportal.thomsonreuters.com/onvio-br-accounting-api/documents/documentao-api) | Existe caminho oficial de API. **Porém**, a documentação pública que encontrei trata de **documentos fiscais de ERP (XML/TXT)** e rubricas de folha. **Não encontrei confirmação de endpoint para vincular documento a tarefa do Processos/Express.** É exatamente isso que precisa ser perguntado. |
| Existe artigo **"Documentação Integração API para ERPs"** (código 8476) | [suporte.dominioatendimento.com](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=8476) | Segundo ponto de leitura. |
| Páginas de terceiros citam liberação de chave de API por e-mail para `api.dominio@tr.com` | fontes não oficiais | **Não confirmado.** Trate como pista para a pergunta, nunca como procedimento. |
| **Pasta monitorada pelo Express** | — | **Não encontrei confirmação pública.** O resultado de busca sobre "pasta monitorada" refere-se ao **Legal One**, produto jurídico diferente. A informação que você tem pode estar certa e vir do seu consultor — mas **precisa ser confirmada antes de virar arquitetura**. |

## Cenário A — Existe API oficial que cobre Processos/Express

**Como saber:** perguntas 1 a 4 da lista abaixo.

**Se existir, o fluxo vira:**

```
automação classifica e nomeia
   → POST do documento + metadados (CNPJ, competência, tributo, código de receita)
   → API responde: tarefa vinculada | várias candidatas | nenhuma
   → automação grava o retorno no registro.csv
   → arquiva a cópia no servidor
   → só o caso "várias candidatas" vai para a fila humana
```

**O que muda no código:** um módulo novo (`express_api.py`) chamado no fim do
`pipeline.py`, onde hoje existe a cópia para pasta. Nada mais muda — foi
desenhado assim de propósito.

**Cuidados:** ambiente de homologação antes de produção; nunca reenviar documento
já vinculado (usar o hash SHA-256 que o `registro` já guarda como chave de
idempotência); tratar erro de rede sem perder o arquivo.

## Cenário B — Sem API, mas com importação oficial (pasta monitorada / aplicativo)

**É o cenário mais provável e o mais adequado ao projeto**, se confirmado.

```
automação classifica e nomeia
   → copia para \\SERVIDOR\EXPRESS_UPLOAD\
   → Express (aplicativo oficial) sobe sozinho e analisa
   → automação arquiva a cópia no servidor, em paralelo
   → o que o Express não conseguir vincular, a pessoa resolve dentro do Domínio
```

Já está implementado: em `config.yaml`, `envio.modo: "pasta_monitorada"` +
`envio.pasta_monitorada`. Nada acontece enquanto `envio.habilitado` for `false`.
O roteiro de ativação, com o teste de 30 minutos, está em
[docs/11](11-express-esta-semana.md).

**Cuidados obrigatórios quando ligar:**
- A pasta monitorada recebe **cópia**, nunca o único exemplar do arquivo.
- Ligue **para uma empresa só**, por uma semana, antes de estender.
- Confirme se o Express **remove** o arquivo depois de processar. Se não remover,
  defina quem limpa — pasta monitorada que só cresce vira reenvio infinito.
- Confirme o limite de arquivos por lote e o horário de varredura.

## Cenário C — Não existe integração oficial nenhuma

Nesta ordem, e só nesta ordem:

1. **Upload manual em lote, com o trabalho pesado já feito.** A automação entrega
   uma pasta por competência, com nomes padronizados, planilha de conferência e o
   que é duvidoso já separado. A pessoa arrasta a pasta inteira para o Express.
   Elimina a maior parte do esforço e **não tem risco nenhum**.
   **Já está implementado** (`envio.modo: "lote_manual"`) e não depende de
   confirmação nenhuma — é por onde começar mesmo que A ou B venham a existir.
2. **Importação por planilha/arquivo**, se o Domínio aceitar algum formato de
   carga em lote — perguntas 5 e 6.
3. **RPA (simulação de cliques)** — **última opção, e com data para acabar.** Só
   se A, B e o item 1 forem descartados por escrito. Quebra a cada atualização de
   tela, roda em máquina dedicada e destravada, e cria dependência invisível.
   Se for inevitável: escopo mínimo (apenas o upload), execução fora do horário
   comercial, log de tela, e revisão a cada atualização do Domínio.

## As 10 perguntas para abrir o chamado (copie e cole)

> Assunto: Integração de automação própria com Domínio Processos / Express
>
> Somos escritório contábil usuário do Domínio Processos e estamos desenvolvendo
> uma automação interna para pré-classificar e arquivar documentos tributários
> (DAS, DARF de PIS, COFINS, IRPJ/IRRF e CSLL). Precisamos entender qual é o
> caminho **oficialmente suportado** de integração. Perguntas:
>
> 1. Existe API oficial que permita **enviar um documento e vinculá-lo a uma
>    tarefa** do Domínio Processos? Se sim, qual a documentação e como se obtém
>    a credencial?
> 2. A Onvio BR Accounting API cobre o módulo **Processos/Express**, ou apenas
>    documentos fiscais de ERP (XML/TXT) e folha?
> 3. É possível **consultar por API** as tarefas em aberto de uma empresa
>    (competência, obrigação, situação)? Isso permitiria pré-identificar a tarefa
>    antes do envio.
> 4. Existe ambiente de **homologação** para teste?
> 5. O Express possui recurso de **monitoramento de pasta local** com upload
>    automático? Se sim: como se configura, qual a frequência de varredura, qual
>    o limite de arquivos por lote, e o arquivo é **removido** da pasta após o
>    processamento?
> 6. Existe **importação em lote** por planilha ou arquivo de índice, informando
>    previamente CNPJ, competência e tipo de documento?
> 7. Enviando metadados junto (CNPJ, competência, código de receita), o Express
>    **melhora** a identificação da tarefa, ou a análise é sempre só do conteúdo?
> 8. Qual a lista oficial e atual de **formatos e limites** aceitos pelo Express
>    (tamanho máximo, nº de páginas, PDF protegido por senha, PDF assinado)?
> 9. Existe forma de **consultar o resultado** do processamento (documento
>    vinculado / pendente / com múltiplas tarefas) fora da tela do sistema?
> 10. Há **parceiro homologado** que já faça esse tipo de integração, e o uso de
>     integração própria fere alguma cláusula contratual ou de suporte?

**Registre a resposta por escrito** (e-mail ou protocolo do chamado) e guarde
junto do projeto. Decisão de arquitetura tomada por conversa de telefone é
decisão que ninguém consegue defender seis meses depois.

## Regra de ouro

Enquanto a resposta não chegar, **o projeto roda inteiro sem o Express**. É o
motivo de o arquivamento no servidor e o envio ao Express serem dois caminhos
separados no código: se a integração mudar, quebrar ou nunca existir, a
organização do servidor continua funcionando.

---
Fontes consultadas: [Como utilizar Express? — Portal do Cliente](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=9146) · [Central do Desenvolvedor — Soluções Domínio](https://www.dominiosistemas.com.br/lp-centraldodesenvolvedor-api/) · [Onvio BR Accounting API — Developer Portal](https://developerportal.thomsonreuters.com/onvio-br-accounting-api/documents/documentao-api) · [Documentação Integração API para ERPs (8476)](https://suporte.dominioatendimento.com/central/faces/solucao.html?codigo=8476) · [Domínio Processos](https://www.dominiosistemas.com.br/solucoes/dominio-processos/)
