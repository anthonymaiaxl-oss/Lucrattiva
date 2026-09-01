# Fontes oficiais coladas à mão

O ambiente onde esta documentação é escrita **não tem acesso de rede** a
`suporte.dominioatendimento.com` nem a `thomsonreuters.com` (bloqueio de saída,
403 no CONNECT — não é falta de link nem de permissão da sua conta).

Por isso os rótulos exatos de menu e botão do Onvio **não estão transcritos** na
documentação: onde eles importam, o texto descreve a ação e manda conferir na
tela.

## Como resolver isso em 2 minutos

Abra o artigo, selecione tudo, copie e cole num arquivo aqui, com o número do
artigo no nome:

```
docs/fontes/express-12392.md      <- Onvio Express (artigo 12392)
docs/fontes/express-9146.md       <- Como utilizar Express? (artigo 9146)
```

Prints também servem (`.png` na mesma pasta). Com o conteúdo aqui dentro, dá
para transformar em passo a passo literal no `docs/12` e, se o artigo descrever
a pasta local de envio automático, já configurar
`envio.modo: "pasta_monitorada"` com os caminhos e limites certos.

## Artigos que interessam

| Artigo | Assunto | Onde |
|---|---|---|
| **12392** | Onvio Express (o mais completo) | `solucao-onvio.html?codigo=12392` |
| 9146 | Como utilizar Express? | `solucao.html?codigo=9146` |
| 12304 | Integração Domínio Processos para Onvio | `solucao.html?codigo=12304` |
| 7462 | Onvio Processos | `solucao.html?codigo=7462` |
| 8476 | Documentação Integração API para ERPs | `solucao.html?codigo=8476` |

## O que procurar ao colar

1. **Pasta local / envio automático**: existe? como se baixa? onde se configura?
   **O arquivo é removido da pasta depois de enviado?** (essa é a pergunta que
   decide entre `pasta_monitorada` e `lote_manual`)
2. **Formatos e limites**: tamanho máximo, nº de arquivos por lote, PDF com
   senha, PDF assinado.
3. **Comportamento**: o que a tela mostra quando acha uma tarefa, várias, ou
   nenhuma.
4. **Nomes exatos** de menu e botão, para o procedimento da equipe.
