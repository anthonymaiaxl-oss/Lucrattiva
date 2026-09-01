# 07 — Sistema de confiança

## O que mudou em relação ao modelo do rascunho

O modelo original (CNPJ +40, tributo +25, competência +20, código +15, faixas
90/70) tem três furos que aparecem na primeira semana de uso real:

| Furo | Consequência | Correção adotada |
|---|---|---|
| Score único decide tudo | Um documento com 92 pontos e **empresa errada** é arquivado. Score alto compra o direito de errar. | **Duas camadas independentes:** score (prioriza) e **travas** (bloqueiam). Qualquer trava manda para validação mesmo com 100 pontos. |
| "CNPJ encontrado" vale igual em qualquer situação | CNPJ lido no documento mas ausente do cadastro pontuava como se estivesse tudo certo. | Pontuação por **nível de identificação**: cadastrado 35 · razão forte 25 · razão fraca 12 · fantasia 15 · pasta 8 · CNPJ não cadastrado 5. |
| Não considera a qualidade da leitura | OCR ruim gera texto ruim e score idêntico ao de um PDF nativo perfeito. | **Multiplicadores:** OCR ×0,85; texto com menos de 200 caracteres ×0,70. |

Um quarto ajuste, descoberto testando: o score do tipo é medido **em relação ao
máximo que aquele template consegue atingir**. O DAS não tem código de receita
para somar, então um DAS perfeito chega a 60 de 60 (=100%), não a 60 de 100. Sem
isso, todo DAS ficaria eternamente em "revisão recomendada" e o fiscal aprenderia
a clicar em tudo sem olhar — que é o pior resultado possível.

## Tabela de pontos (`config.yaml`, ajustável)

| Evidência | Pontos |
|---|---|
| Empresa por **CNPJ** válido e cadastrado | **+35** |
| Empresa por razão social ≥ 90% | +25 |
| Empresa por nome fantasia | +15 |
| Empresa por razão social 82–90% | +12 |
| Empresa por pasta de origem | +8 |
| CNPJ válido porém fora do cadastro | +5 |
| **Tipo do documento** (proporcional ao score do template) | **até +30** |
| Competência de **campo explícito** | +20 |
| Competência de **período de apuração** | +16 |
| Competência inferida | +8 |
| Valor total localizado | +6 |
| Vencimento localizado | +4 |
| _Multiplicador:_ texto por OCR | ×0,85 |
| _Multiplicador:_ texto com menos de 200 caracteres | ×0,70 |

## Faixas

| Score | Decisão | O que acontece |
|---|---|---|
| **≥ 85** | `AUTOMATICO` | Arquiva. Entra na conferência por amostragem. |
| **65–84** | `ARQUIVADO_COM_REVISAO` | Arquiva **e** entra na lista de conferência da semana. Documento fica no lugar certo; a conferência é sobre o acerto, não sobre o arquivamento. |
| **< 65** | `PENDENTE_VALIDACAO` | Não arquiva na empresa. Vai para a fila. |

## Travas — passam por cima do score

| Trava | Motivo |
|---|---|
| `EMPRESA_NAO_IDENTIFICADA` | Sem empresa não existe destino. |
| `EMPRESA_POR_SEMELHANCA_FRACA` | 82–90% de similaridade é palpite, não identificação. |
| `EMPRESA_APENAS_PELA_PASTA` | Pasta é pista, não prova. |
| `CLASSIFICACAO_AMBIGUA` | Dois tributos a menos de 15 pontos. |
| `DOCUMENTO_DESCONHECIDO` | Nenhum template atingiu o mínimo. |
| `RETENCAO_CONJUNTA` | Guia cobre mais de um tributo (código 5952). |
| `COMPETENCIA_NAO_IDENTIFICADA` | Sem competência não existe pasta de destino. |
| `COMPETENCIA_INFERIDA` | Nenhum rótulo explícito no documento. |
| `COMPETENCIA_FORA_DA_JANELA` | Mais de 60 meses atrás ou mais de 2 à frente. |
| `CAMPOS_OBRIGATORIOS_AUSENTES` | Falta campo exigido pelo template. |
| `SEM_TEXTO` | PDF é imagem e o OCR está desligado. |
| `FORMATO_NAO_ACEITO_PELO_EXPRESS` | `.doc`/`.docx` — converter para PDF. |
| `CAMINHO_MUITO_LONGO` | Estouraria o limite do Windows. |

## Como calibrar (não adivinhe os pesos)

1. Separe **50 documentos reais já conferidos** — o gabarito.
2. `python -m docauto processar --entrada <pasta> --dry-run`.
3. Meça duas coisas, em ordem de importância:
   - **Falso positivo** (arquivou errado): meta **zero**. Um único caso já é
     motivo para subir limiar, apertar trava ou corrigir template — sempre.
   - **Falso negativo** (mandou para pendência algo que estava certo): tolerável.
     É trabalho manual, não é erro.
4. Ajuste `config.yaml` e repita. **Nunca** relaxe uma trava para reduzir a fila;
   corrija o template ou o cadastro, que é onde está a causa real.
5. Repita mensalmente nos primeiros três meses e a cada novo tipo de documento.

**A ordem certa é: primeiro zero erro, depois menos fila.** Um fluxo que manda
30% para pendência e nunca erra já economiza 70% do trabalho e mantém a
confiança da equipe. Um fluxo que automatiza 100% e erra 2% destrói a confiança
na primeira semana — e aí ninguém mais usa.
