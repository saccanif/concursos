# Edital Aberto

App para acompanhar concursos públicos abertos no Brasil, com o Espírito Santo em
primeiro plano. Feito para viver no celular: abre pelo ícone na tela de início,
atualiza sozinho e funciona sem sinal.

Nada roda no seu computador. A coleta acontece na nuvem do GitHub, de hora em hora.

```
GitHub Actions (de hora em hora)        Seu iPhone / iPad
  coletor.py                              abre o app
  └─ lê o PCI Concursos                   └─ busca docs/dados.json
  └─ grava docs/dados.json                └─ mostra a lista
  └─ commita no repositório               └─ guarda p/ funcionar offline
           │                                       ▲
           └────────── GitHub Pages ───────────────┘
```

---

## Colocar no ar (uma vez só)

### 1. Criar o repositório

No github.com, crie um repositório novo chamado `concursos`. Deixe **público** — o
GitHub Pages só é gratuito em repositório público, e aqui não há nada sigiloso: são
dados abertos do PCI, e seus favoritos ficam guardados no próprio aparelho, nunca no
repositório.

Não marque nenhuma opção de inicialização (README, .gitignore, licença).

### 2. Subir o código

Nesta pasta, com o endereço do repositório recém-criado:

```bash
git remote add origin https://github.com/SEU_USUARIO/concursos.git
git branch -M main
git push -u origin main
```

### 3. Ligar o GitHub Pages

No repositório: **Settings → Pages → Build and deployment**

- Source: `Deploy from a branch`
- Branch: `main`, pasta `/docs`
- Save

Em um ou dois minutos o app estará em:

```
https://SEU_USUARIO.github.io/concursos/
```

### 4. Ligar a coleta automática

Na aba **Actions**, aceite habilitar os workflows. Abra *Coletar concursos* e clique
em **Run workflow** para fazer a primeira rodada na hora, sem esperar a virada da hora.

### 5. Instalar no celular

Abra o endereço no Safari → botão Compartilhar → **Adicionar à Tela de Início**.

Vira um ícone igual a qualquer outro app: abre em tela cheia, sem barra de navegador.

---

## Como o app se mantém atualizado

Três caminhos, e você não precisa fazer nada em nenhum deles:

| Quando | O que acontece |
| --- | --- |
| A cada hora | O GitHub Actions roda o coletor e commita os dados novos |
| Ao abrir o app | Busca `dados.json` na rede; pinta a lista guardada na hora e troca quando o novo chega |
| Ao voltar pro app | Se a última coleta tem mais de 10 minutos, busca de novo sozinho |

O botão **⟳** no canto superior força a busca a qualquer momento. Ao lado dele fica
escrito há quanto tempo os dados foram coletados.

Sem conexão o app continua abrindo, com a última coleta guardada, e avisa na tela
que os dados podem estar velhos.

---

## O que a tela mostra

- Seletor **Espírito Santo · Nacional · Brasil**, com a contagem de cada um.
- Busca por órgão, cargo ou estado — digitar `minas` filtra Minas Gerais.
- Filtros de situação, escolaridade, salário mínimo e prazo; ordem por prazo,
  salário, vagas ou nome do órgão.
- **Concursos com inscrição aberta e os que ainda vão abrir**, no mesmo lugar.
  Os que vão abrir levam etiqueta `a abrir`, tarja índigo e o prazo escrito como
  "abre 25/09 · em 1 dia". Na ordem por prazo, os abertos vêm primeiro, porque
  são os que dá para resolver hoje; depois os futuros, na ordem em que abrem.
  O filtro *Situação* separa os dois quando você quiser olhar um de cada vez.
- Tarja colorida à esquerda pelo prazo: vermelho até 3 dias, âmbar até 10, verde
  acima, índigo para quem ainda não abriu.
- Etiqueta `novo` em quem apareceu nas últimas 36 horas.
- Estrela para favoritar. Os favoritos ficam no aparelho — marcar no iPhone não
  aparece no iPad, porque o app é estático e não tem servidor guardando isso.
- Tocar na linha abre a matéria do concurso no PCI.

---

## Estrutura

```
coletor.py                     coleta, normaliza e grava docs/dados.json
gerar_icones.py                gera os ícones do app
requirements.txt               requests + lxml
.github/workflows/coletar.yml  a automação de hora em hora
docs/                          isto é o que o GitHub Pages publica
  index.html                   o app inteiro, num arquivo só
  sw.js                        service worker: offline e abertura instantânea
  manifest.webmanifest         faz o navegador tratar como app instalável
  dados.json                   a última coleta (reescrito pela automação)
  icone-*.png                  ícones da tela de início
```

### Não há banco de dados

O histórico é o histórico do git: cada coleta vira um commit de `docs/dados.json`.
Para saber o que é novidade, o coletor compara a coleta atual com o JSON que já está
no repositório e carrega adiante o `visto_em` de cada concurso.

Para olhar o passado:

```bash
git log --oneline -- docs/dados.json
git show <commit>:docs/dados.json | python -m json.tool | less
```

---

## Mexer no app

### Rodar o coletor à mão

```bash
pip install -r requirements.txt
python coletor.py              # coleta e regrava docs/dados.json
python coletor.py --resumo --uf ES   # só mostra o que já está no JSON
```

### Testar a página localmente

```bash
cd docs && python -m http.server 8777
```

e abra `http://localhost:8777`. Precisa ser por servidor, não abrindo o arquivo
direto — o service worker não funciona em `file://`.

### Mudar a frequência da coleta

Em `.github/workflows/coletar.yml`, o campo `cron` (em UTC). Hoje está `"23 * * * *"`,
de hora em hora. O mínimo prático do GitHub é de 5 em 5 minutos, mas agendamento é
por ordem de chegada e atrasa quando a fila está cheia — de hora em hora é o ponto
em que ele é confiável.

---

## Se parar de funcionar

**O app mostra dados antigos e não atualiza.** Veja a aba Actions. O GitHub desativa
workflows agendados depois de 60 dias sem atividade no repositório; se for isso,
aparece um aviso com um botão para reativar.

**A coleta falhou.** O coletor avisa explicitamente quando o seletor `div.na` não casa
mais, o que significa que o PCI mudou o HTML. A estrutura esperada hoje:

- `div.ua` — cabeçalho de estado, com a sigla no atributo `id`
- `div.na` — um concurso, irmão do cabeçalho (não aninhado); dentro dele
  `div.ca > a` (órgão e link), `div.cd` (vagas, salário, cargos, escolaridade)
  e `div.ce` (prazo de inscrição)

Os seletores estão em `extrair()` e `ler_item()`, em `coletor.py`.

O coletor tenta três vezes antes de desistir, porque o PCI fica atrás do Cloudflare
e às vezes recusa a primeira requisição vinda de um datacenter.

**O app não atualiza mesmo com dados novos no repositório.** O service worker guarda
a casca do app. Ao mudar `index.html` ou `sw.js`, suba o número em `var VERSAO` no
`sw.js` — é isso que faz o celular descartar a versão antiga.

---

Os dados vêm do [PCI Concursos](https://www.pciconcursos.com.br/concursos/). Confirme
prazos e requisitos sempre no edital oficial do órgão.
