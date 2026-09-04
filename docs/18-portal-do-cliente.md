# 18 — Portal do Cliente: configuração completa

> **O que este documento é e o que não é.** Não tenho acesso à documentação da
> Domínio a partir do meu ambiente (o portal de suporte é bloqueado pela política
> de rede), então **não há nomes de menu e botão aqui**. O que há é a parte que
> não depende da tela e onde mora a maior parte do trabalho: as **decisões**, a
> ordem de ativação, os testes e os riscos. Marquei com `[TELA]` tudo que você
> confirma no sistema.
>
> Se colar os artigos do Portal do Cliente em `docs/fontes/`, eu transformo os
> `[TELA]` em passo a passo literal.

---

## O erro que define este projeto

No arquivamento interno, errar significa documento na pasta errada — chato, e
você conserta antes de alguém ver.

No Portal do Cliente, **errar é externo**: o cliente vê. E existe um erro que
não tem conserto — **cliente A enxergar documento do cliente B**. Isso é
incidente de LGPD, é obrigação de comunicar, e é o tipo de coisa que faz um
escritório novo perder um contrato no primeiro mês.

Por isso a regra estrutural aqui é diferente da do arquivamento:

> **Silêncio é não publicar.** Tipo de documento sem decisão registrada não vai
> para o portal. Nada é publicado "por padrão".

É assim que a `config/portal/matriz-publicacao.csv` está montada: linha com
`PUBLICA` em branco não publica.

---

## PARTE 1 — Decisões, antes de tocar no sistema

### 1.1 Perfis de acesso

Defina os perfis **antes** de cadastrar o primeiro cliente. Mudar perfil depois
significa revisar cliente por cliente.

| Perfil | Vê | Exemplo típico |
|---|---|---|
| **SÓCIO** | Tudo da empresa dele | dono, administrador |
| **FINANCEIRO** | Guias, boletos, obrigações a pagar | quem paga as contas |
| **RH** | Folha, holerites, rescisões | quem cuida de pessoal |
| **CONTADOR (interno)** | Tudo, de todos | equipe do escritório |

Duas regras que evitam o incidente grave:

1. **Holerite e rescisão não vão para o perfil FINANCEIRO.** São dados pessoais
   de terceiros; quem paga contas não precisa ver salário individual.
2. **Um usuário, uma empresa** — salvo grupo econômico com autorização escrita.
   Contador de duas empresas do mesmo dono é o caso em que o vazamento acontece
   por configuração, não por falha do sistema.

`[TELA]` Confirmar quais perfis o Portal oferece e se dá para criar perfil
próprio. Se não der, adapte a matriz aos perfis existentes — **não** libere
tudo para todos por falta de perfil.

### 1.2 Matriz de publicação

Preencha `config/portal/matriz-publicacao.csv`. É a peça central: por tipo de
documento, decide se publica, quem vê, quando, com quanto de antecedência e se
dispara aviso.

Três colunas merecem atenção:

- **`QUANDO`** — `APOS_CONFERENCIA` deve ser o padrão nos primeiros 90 dias.
  `IMEDIATO` só para documento que não passa por conferência (contrato social,
  recibo de entrega).
- **`PRAZO_DIAS`** — para guias, é o compromisso que você assume com o cliente.
  5 dias antes do vencimento é razoável; menos que 3 gera atraso de pagamento
  e a culpa cai no escritório.
- **`QUEM_VE`** — na dúvida, o perfil mais restrito. Ampliar depois é fácil;
  explicar por que alguém viu o que não devia, não.

### 1.3 Quem responde

Portal sem dono vira caixa de entrada abandonada. Defina, por escrito:

- quem publica;
- quem confere antes de publicar;
- **quem responde quando o cliente escreve pelo portal**, e em quanto tempo;
- quem revoga acesso quando alguém sai da empresa do cliente.

O terceiro é o mais esquecido: cliente que manda mensagem pelo portal e não é
respondido volta para o WhatsApp — e aí o portal morreu.

### 1.4 Identidade e comunicação

`[TELA]` Logo, cores, nome de exibição, endereço de e-mail remetente.

**Item crítico e frequentemente esquecido: entregabilidade.** Se os avisos do
portal caem em spam, tudo "funciona" e ninguém recebe. Teste obrigatório antes
do go-live: dispare um aviso para um Gmail, um Outlook/Hotmail e um e-mail
corporativo, e confirme que chegou **na caixa de entrada**. Se cair em spam,
resolva a autenticação do domínio (SPF/DKIM) com quem cuida do e-mail da
Lucrattiva antes de ativar qualquer rotina.

---

## PARTE 2 — Configuração, na ordem

### Etapa 1 — Cliente-teste (faça isto primeiro, sempre)

Crie **uma empresa de teste** no portal, com e-mail do próprio escritório como
usuário. Pode ser a própria Lucrattiva.

Tudo — publicação, perfil, rotina, aviso — passa por ela antes de encostar em
cliente real. É o que permite ir rápido sem risco: você erra na empresa de
teste, à vontade, e ninguém vê.

**Não pule esta etapa por pressa.** Ela é o que torna a pressa segura.

### Etapa 2 — Cadastro base

`[TELA]` Para cada empresa: razão social, CNPJ, regime, código no Domínio,
responsáveis e e-mails, perfis.

Use a exportação do Onvio para não digitar duas vezes — e confira contra o
cadastro da automação:

```bat
python -m docauto onvio-conferir --empresas data\onvio\empresas.csv
```

CNPJ divergente entre portal e Processos é a origem de "publiquei e o cliente
não vê".

### Etapa 3 — Publicação manual, 1 cliente-piloto

Antes de qualquer automação: publique **à mão** um documento real para **um**
cliente piloto (idealmente o mais próximo, que avisa se algo estiver errado sem
virar problema comercial).

Confirme, entrando com o usuário do cliente:

- [ ] ele vê o documento certo;
- [ ] ele **não** vê nada de outra empresa;
- [ ] o perfil restringe o que deveria restringir;
- [ ] o aviso chegou na caixa de entrada, não no spam;
- [ ] ele consegue baixar o arquivo;
- [ ] ele consegue responder/enviar documento de volta, se isso estiver no escopo.

O terceiro e o quarto item são os que reprovam com mais frequência.

### Etapa 4 — Onboarding do cliente

Portal configurado e vazio é o desfecho mais comum desse tipo de projeto.
Defina o roteiro de ativação:

1. Convite enviado (rotina R09);
2. Ligação ou áudio de 2 minutos explicando **o que ele ganha** — não como se
   usa: "suas guias vão estar aqui, sempre no mesmo lugar, 5 dias antes do
   vencimento";
3. Acompanhamento: quem não acessou em 7 dias recebe um empurrão humano.

**Meta mensurável:** 80% dos clientes com primeiro acesso em 30 dias. Sem meta,
ninguém acompanha, e em três meses o portal é uma tela que só o escritório abre.

### Etapa 5 — Go-live por ondas

| Onda | Quem | Quando avançar |
|---|---|---|
| 0 | Empresa de teste | Tudo passou |
| 1 | 1 cliente piloto | 1 semana sem incidente |
| 2 | 3 a 5 clientes | 1 semana sem incidente |
| 3 | Carteira toda | — |

---

## PARTE 3 — Checklist de go-live

Nenhum item pode ficar em branco.

**Segurança e LGPD**
- [ ] Cada usuário vê **apenas** a empresa dele (testado entrando como cliente)
- [ ] Holerite/rescisão restritos ao perfil correto
- [ ] Processo definido para revogar acesso de quem sai da empresa do cliente
- [ ] Registro de quem publicou o quê, e quando
- [ ] Definido o que fazer se um documento for publicado errado (despublicar, avisar, registrar)

**Operação**
- [ ] Matriz de publicação preenchida, sem linha ambígua
- [ ] Responsável por publicar, conferir e responder definidos por escrito
- [ ] Prazo de resposta ao cliente acordado (ex.: 1 dia útil)
- [ ] Rotina de conferência antes de publicar

**Comunicação**
- [ ] Aviso chega na caixa de entrada em Gmail, Outlook e corporativo
- [ ] Remetente e assinatura conferidos
- [ ] Texto dos avisos revisado (é a voz do escritório com o cliente)

**Adoção**
- [ ] Roteiro de onboarding pronto
- [ ] Meta de primeiro acesso definida e com dono

---

## PARTE 4 — O que NÃO fazer

1. **Não ligue rotina automática antes do portal estar redondo no manual.**
   Automatizar um processo errado só faz o erro chegar mais rápido a mais gente.
2. **Não publique documento sem conferência** nos primeiros 90 dias.
3. **Não libere a carteira toda de uma vez** — nem que a pressa peça.
4. **Não use cliente real como teste**, nem "o cliente camarada". Use a empresa
   de teste.
5. **Não deixe o portal sem meta de adoção.**
