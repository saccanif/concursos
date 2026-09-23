# Edital Aberto

Monitor de concursos públicos abertos no Brasil, com o Espírito Santo em primeiro plano.

O app tem duas metades:

1. **O coletor** (`coletor.py`) roda aqui no computador, lê o PCI Concursos, normaliza
   os dados e guarda em SQLite.
2. **A página** (`web/app.html`) é publicada como artifact privado e aberta no iPhone
   ou no iPad, pelo Safari, de qualquer lugar.

Página publicada: https://claude.ai/artifact/L8QQkD86niWg5LvRzspDb9

---

## Atualizar os dados

```
python coletor.py
```

Isso baixa a lista, atualiza o banco, diz quantos concursos são novos e quantos
encerraram, e regera `web/app.html` com os dados embutidos.

Depois é preciso republicar a página para que o celular veja os dados novos. No
Claude Code, dentro desta pasta:

> atualiza o Edital Aberto

O artifact é republicado na **mesma URL** — o atalho salvo no iPhone continua valendo.

### Outros comandos

| Comando | O que faz |
| --- | --- |
| `python coletor.py` | coleta, atualiza o banco e regera a página |
| `python coletor.py --resumo` | mostra o que já está no banco, sem acessar a internet |
| `python coletor.py --resumo --uf ES` | idem, só Espírito Santo |
| `python coletor.py --sem-rede` | regera a página a partir do banco |

---

## Abrir no iPhone e no iPad

1. Abra a URL no Safari, já logado na mesma conta Claude.
2. Compartilhar → **Adicionar à Tela de Início**. Vira um ícone, abre em tela cheia.

A página carrega os dados embutidos no próprio arquivo, então depois de aberta ela
funciona mesmo sem sinal.

**Favoritos** (a estrela) ficam guardados no servidor do artifact, então o que você
marca no iPhone aparece no iPad e vice-versa. Se o armazenamento remoto não estiver
disponível, a página cai para o armazenamento do próprio aparelho sem quebrar.

---

## O que a página mostra

- Seletor **Espírito Santo · Nacional · Brasil** no topo, com a contagem de cada um.
- Busca por órgão, cargo ou estado (digitar `minas` filtra Minas Gerais).
- Filtros por escolaridade, salário mínimo e prazo de encerramento; ordem por prazo,
  salário, vagas ou nome.
- Tarja colorida à esquerda pelo prazo: vermelho até 3 dias, âmbar até 10, verde acima.
- Etiqueta `novo` nos concursos que apareceram desde a coleta anterior.
- Tocar na linha abre a página do concurso no PCI.

---

## Estrutura

```
coletor.py          coleta, normaliza, grava e gera a página
dados/concursos.db  SQLite — histórico de todas as coletas
dados/concursos.json export completo da última coleta
web/modelo.html     a página, com __DADOS__ no lugar do JSON
web/app.html        gerado pelo coletor: modelo + dados, pronto para publicar
```

`web/app.html` é gerado — editar a página significa editar `web/modelo.html` e rodar
`python coletor.py --sem-rede`.

### Banco

`concursos` guarda um registro por concurso, com `ativo = 0` quando ele sai da lista
do PCI, e `coleta_inicial` marcando em qual coleta apareceu pela primeira vez — é daí
que sai a etiqueta `novo`. `coletas` guarda uma linha por execução. Nada é apagado,
então dá para consultar o histórico direto:

```sql
SELECT orgao, salario, inscricoes_ate FROM concursos
WHERE uf = 'ES' AND ativo = 0 ORDER BY inscricoes_ate DESC;
```

---

## Dependências

`requests` e `lxml`, ambos já instalados. Se precisar em outra máquina:

```
pip install requests lxml
```

---

## Se o coletor parar de achar concursos

Ele avisa explicitamente quando o seletor `div.na` não casa mais — significa que o
PCI mudou o HTML. A estrutura esperada hoje é:

- `div.ua` — cabeçalho de estado, com a sigla no atributo `id`
- `div.na` — um concurso, irmão do cabeçalho (não aninhado); dentro dele
  `div.ca > a` (órgão e link), `div.cd` (vagas, salário, cargos, escolaridade)
  e `div.ce` (prazo de inscrição)

Os seletores estão em `extrair()` e `ler_item()`.
