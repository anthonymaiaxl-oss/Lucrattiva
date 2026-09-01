# 02 — Fluxo do processo

## Fluxo textual (o que acontece com cada arquivo)

```
              /ENTRADA_DOCUMENTOS  (arquivo novo)
                        |
                 [1] LEITURA
                 PDF nativo -> texto
                 PDF imagem -> OCR (Fase 2)
                 XLSX/TXT   -> texto
                 DOC/DOCX   -> PENDENTE (Express não lê; converter em PDF)
                        |
                 [2] EXTRAÇÃO
                 CNPJ (com dígito verificador conferido)
                 Razão social | Competência | Valor
                 Vencimento | Código de receita
                        |
                 [3] CLASSIFICAÇÃO
                 Templates + tabela de códigos + desempate
                 -> DAS | PIS | COFINS | IR | CSLL
                 -> ou NECESSITA_VALIDACAO / DESCONHECIDO
                        |
                 [4] EMPRESA
                 CNPJ > razão social > nome fantasia > pasta de origem
                        |
                 [5] COMPETÊNCIA
                 campo explícito > período de apuração > inferida
                 (vencimento NUNCA vira competência)
                        |
                 [6] CONFIANÇA + TRAVAS
                        |
        +---------------+-----------------------+
        |                                       |
   sem trava e score alto                 qualquer trava
        |                                       |
 [7] NOME PADRONIZADO                    /PENDENTES_VALIDACAO
 [8] ARQUIVAMENTO no servidor              /<MOTIVO>/arquivo
     (cópia, nunca sobrescreve)            + arquivo.laudo.json
        |                                    (o que faltou, candidatos,
 [9] (Fase 3) cópia para a pasta              sugestões de empresa)
     monitorada do Express                        |
        |                                    pessoa resolve
 [10] REGISTRO em registro.csv  <----------------+
```

## Diagrama

```mermaid
flowchart TD
    A[/ENTRADA_DOCUMENTOS/] --> B[Leitura: PDF/OCR/XLSX/TXT]
    B -->|sem texto| P[PENDENTES: SEM_TEXTO]
    B --> C[Extração de campos]
    C --> D[Classificação por templates + códigos]
    D -->|ambíguo ou desconhecido| P
    D --> E[Identificação da empresa]
    E -->|não identificada| P
    E --> F[Competência]
    F -->|ausente ou só inferida| P
    F --> G{Score e travas}
    G -->|trava ativa| P
    G -->|score < 65| P
    G -->|65 a 84| H[Arquiva e marca para conferência]
    G -->|>= 85| I[Arquiva automaticamente]
    H --> J[Pasta da empresa no servidor]
    I --> J
    J --> K[(Fase 3) Pasta monitorada do Express]
    K --> L[Express vincula à tarefa]
    J --> M[registro.csv + detalhado.jsonl]
    P --> M
    P --> N[Fiscal resolve a pendência e reprocessa]
    N --> A
```

## Onde o Express entra

O Express é acionado **depois** de a automação ter padronizado o arquivo — nunca
antes. Motivo: o Express trabalha melhor com um arquivo já nomeado e íntegro, e o
escritório precisa da cópia organizada no servidor **mesmo que** o Express não
encontre a tarefa. Os dois caminhos são independentes de propósito: se a
integração com o Express falhar ou mudar, o arquivamento continua funcionando.
