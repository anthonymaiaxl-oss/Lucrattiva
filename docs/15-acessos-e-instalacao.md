# 15 — O que dá para automatizar, o que só você pode fazer

## Resposta direta sobre acesso

**Não dá para eu configurar o Express dentro do Domínio/Onvio por você**, e não
é uma questão de permissão que se resolva me dando uma senha:

1. **Onde eu rodo.** Esta sessão vive num contêiner temporário na nuvem, sem
   rota até a rede do escritório. Não existe caminho de rede daqui para o seu
   `\\SERVIDOR` nem para o computador onde o Express está instalado — dar
   acesso não cria esse caminho. E o contêiner é descartado ao fim da sessão:
   nada que eu "deixasse rodando" sobreviveria.
2. **Credenciais do Domínio.** Não peça nem me passe usuário e senha do Onvio.
   É a conta que dá acesso aos dados fiscais dos seus clientes, e o acesso
   ficaria registrado como se fosse você. Isso não se corrige depois.
3. **Configuração do Express.** É clique em tela autenticada do produto da
   Thomson Reuters. Mesmo com acesso, seria eu operando a conta de um sistema de
   terceiro em nome do escritório — e o suporte deles não dá cobertura a isso.

**A boa notícia:** a parte trabalhosa não é o clique no Express, é preparar o
ambiente para que aquele clique funcione. E essa parte está automatizada.

---

## O que já está automatizado (você roda, um comando cada)

| Comando | O que faz |
|---|---|
| `scripts\instalar.bat` | Python, ambiente virtual, dependências, config, cadastro e pastas — tudo de uma vez |
| `python -m docauto doutor` | **Diz o que falta para funcionar neste computador**: pastas que não existem, pasta sem permissão de escrita, leitor de PDF ausente, destino de Dropbox com caminho errado, caminho estourando o limite do Windows, envio sem pasta configurada |
| `python -m docauto validar` | Confere o cadastro (CNPJ inválido, duplicado, razão vazia) |
| `python -m docauto diagnosticar` | Calibra os templates com as suas guias (docs/13) |
| `scripts\agendar.bat` | Cria as duas tarefas agendadas do Windows |

O `doutor` é o mais próximo do que você pediu: em vez de eu olhar o seu
servidor, ele olha — e devolve a lista do que corrigir, com o motivo. Ele
**reprova** o ambiente (código de saída 1) enquanto houver erro, então dá para
rodar antes de cada etapa sem depender de ninguém lembrar de conferir.

```
[OK  ] cadastro de empresas   3 empresa(s), 3 ativa(s), 0 erro(s)
[!   ] tabela de códigos      NAO_CONFERIDA
         -> conferir contra a tabela oficial da RFB antes de produção (docs/03)
[ERRO] leitor de PDF          nenhum instalado
         -> pip install pypdf — sem ele nenhum PDF é lido
[ERRO] entrada                D:/NAO_EXISTE
         -> pasta não existe
[!   ] destino DROPBOX        Z:/Dropbox/CONTABIL/CLIENTES
         -> nem a pasta que o contém existe — criar aqui produziria uma pasta
            local que não sincroniza
[OK  ] limite de caminho      pior caso 202 de 240 (38 de folga)
```

Aquele aviso do Dropbox merece destaque: se o caminho estiver errado, a
automação criaria uma pasta local comum, os arquivos empilhariam ali e **nunca
sincronizariam** — parecendo, o tempo todo, que estava tudo certo. O `doutor`
se recusa a criar a pasta nesse caso.

---

## O que só você pode fazer (4 itens, ~40 minutos)

**1. Configurar o Express no Domínio/Onvio.** Entrar com a conta do escritório,
localizar o Express dentro do Processos e verificar se existe a opção de baixar
a **pasta local** de envio automático (o artigo oficial 9146 descreve esse
recurso). Anote o caminho que ela criar.

**2. Colar esse caminho no config:**

```yaml
envio:
  habilitado: true
  modo: "pasta_monitorada"
  pasta_monitorada: "C:/Users/SEU_USUARIO/<pasta criada pelo Express>"
  empresas_piloto: ["0001"]
```

E rodar `python -m docauto doutor` — ele confirma se a pasta existe e é gravável.

**3. Instalar o Dropbox** (ou Drive) na máquina e apontar o `destinos`.
`doutor` valida o caminho.

**4. Escolher a conta das tarefas agendadas** e rodar os `.bat` na mão com ela
antes de agendar. O erro mais comum de implantação não é de configuração: é a
conta do agendador não ter acesso ao `\\SERVIDOR`.

---

## A sequência completa no servidor

```bat
scripts\instalar.bat
REM editar config\config.yaml (caminhos, destinos)
REM preencher data\empresas.csv

python -m docauto doutor              REM repita até zerar os erros
python -m docauto validar
python -m docauto diagnosticar --entrada C:\amostras --texto C:\amostras\_texto
python -m docauto processar --dry-run
python -m docauto processar
python -m docauto enviar
scripts\agendar.bat                   REM como administrador
```

## Se quiser mesmo que alguém configure por dentro

Duas saídas legítimas, nesta ordem:

1. **Suporte da Thomson Reuters**, com acesso remoto agendado: eles configuram o
   Express na sua conta, com cobertura contratual. É o caminho certo para o que
   é do produto deles.
2. **Chamada de tela comigo**: você compartilha a tela, opera os cliques e eu
   digo o que clicar e por quê. Você mantém o controle da conta e eu não toco em
   credencial nenhuma.

O que **não** vale a pena: me passar senha, ou abrir acesso remoto ao servidor
para uma sessão que é descartada em algumas horas. O ganho seria zero e o risco,
permanente.
