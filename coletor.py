# -*- coding: utf-8 -*-
"""
Coletor de concursos públicos abertos no Brasil.

Roda dentro do GitHub Actions: lê a lista geral do PCI Concursos, normaliza os
campos (vagas, salário, escolaridade, prazo de inscrição) e grava
`docs/dados.json`, que é o arquivo que o app busca ao abrir.

Não há banco de dados. O histórico é o próprio histórico do git: cada coleta
vira um commit de `docs/dados.json`. Para saber o que é novidade, o coletor
compara a coleta atual com o JSON que já está no repositório e carrega adiante
a data em que cada concurso foi visto pela primeira vez.

Uso:
    python coletor.py              coleta e regrava docs/dados.json
    python coletor.py --resumo     mostra o que já está no JSON, sem rede
    python coletor.py --uf ES      limita o resumo impresso a um estado
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from lxml import html as LH

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "docs" / "dados.json"

FONTE = "https://www.pciconcursos.com.br/concursos/"
CABECALHOS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
HORAS_COMO_NOVIDADE = 36
TENTATIVAS = 3


# --------------------------------------------------------------------------- #
# Coleta
# --------------------------------------------------------------------------- #

def baixar(url: str = FONTE) -> str:
    """Busca a página, com algumas tentativas — o runner do Actions às vezes
    esbarra no Cloudflare do PCI na primeira ida."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(url, headers=CABECALHOS, timeout=45)
            resposta.raise_for_status()
            return resposta.content.decode("utf-8", errors="replace")
        except requests.RequestException as erro:
            ultimo_erro = erro
            if tentativa < TENTATIVAS:
                espera = 5 * tentativa
                print(f"  tentativa {tentativa} falhou ({erro}); repetindo em {espera}s")
                time.sleep(espera)
    raise RuntimeError(f"não foi possível baixar {url}: {ultimo_erro}")


def extrair(html: str) -> list[dict]:
    """Percorre a lista em ordem de documento.

    O PCI intercala cabeçalhos de estado (div.ua, com a sigla no id) e os
    concursos daquele estado (div.na). Não há aninhamento: o estado vale até
    aparecer o próximo cabeçalho.
    """
    doc = LH.fromstring(html)
    blocos = doc.xpath('//div[@class="na"]')
    if not blocos:
        raise RuntimeError(
            "Nenhum concurso encontrado na página. O layout do PCI Concursos "
            "provavelmente mudou e o seletor div.na precisa ser revisto."
        )

    uf = uf_nome = ""
    itens: list[dict] = []
    for elemento in blocos[0].getparent().iterchildren("div"):
        classe = elemento.get("class")
        if classe == "ua":
            uf = (elemento.get("id") or "").strip()
            uf_nome = titulo_estado(elemento.xpath('string(div[@class="uf"])'))
        elif classe == "na":
            item = ler_item(elemento, uf, uf_nome)
            if item:
                itens.append(item)
    return itens


def ler_item(elemento, uf: str, uf_nome: str) -> dict | None:
    ancoras = elemento.xpath('div[@class="ca"]/a')
    if not ancoras:
        return None
    ancora = ancoras[0]
    url = (ancora.get("href") or "").strip()
    orgao = limpar(ancora.text_content())
    if not url or not orgao:
        return None

    resumo = limpar(elemento.xpath('string(div[@class="ca"]/div[@class="cd"]/text()[1])'))
    spans = [limpar(s.text_content())
             for s in elemento.xpath('div[@class="ca"]/div[@class="cd"]//span')]
    escolaridade = spans[-1] if spans else ""

    return {
        "id": hashlib.sha1(url.encode("utf-8")).hexdigest()[:16],
        "orgao": orgao,
        "titulo": limpar(ancora.get("title") or ""),
        "url": url,
        "uf": uf,
        "uf_nome": uf_nome,
        "vagas": contar_vagas(resumo),
        "cadastro_reserva": bool(RE_CR.search(resumo)),
        "salario": extrair_salario(resumo),
        "salario_por_hora": bool(RE_HORA.search(resumo)),
        "cargos": extrair_cargos(spans),
        "escolaridade": escolaridade,
        "niveis": extrair_niveis(escolaridade),
        "inscricoes_ate": converter_data(elemento.xpath('string(div[@class="ca"]/div[@class="ce"])')),
    }


# --------------------------------------------------------------------------- #
# Normalização
# --------------------------------------------------------------------------- #

RE_VAGAS = re.compile(r"(\d+)\s*vagas?\b", re.I)
RE_CR = re.compile(r"cadastro\s+(?:de\s+)?reserva|\bCR\b", re.I)
RE_SALARIO = re.compile(r"R\$\s*([\d.]+,\d{2})")
RE_HORA = re.compile(r"por\s+hora", re.I)
RE_ESPACOS = re.compile(r"\s+")

NIVEIS = (("fundamental", "Fundamental"), ("medio", "Médio"),
          ("tecnico", "Técnico"), ("superior", "Superior"))

PALAVRAS_MIUDAS = {"de", "do", "da", "dos", "das", "e"}


def limpar(texto: str) -> str:
    return RE_ESPACOS.sub(" ", (texto or "").replace("\xa0", " ")).strip()


def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def titulo_estado(texto: str) -> str:
    """O nome do estado vem em caixa alta na fonte; devolve em caixa de título."""
    limpo = limpar(texto)
    if not limpo or limpo != limpo.upper():
        return limpo
    return " ".join(p.lower() if p.lower() in PALAVRAS_MIUDAS else p.capitalize()
                    for p in limpo.split(" "))


def contar_vagas(resumo: str) -> int | None:
    achado = RE_VAGAS.search(resumo)
    return int(achado.group(1)) if achado else None


def extrair_salario(resumo: str) -> float | None:
    achado = RE_SALARIO.search(resumo)
    if not achado:
        return None
    return float(achado.group(1).replace(".", "").replace(",", "."))


def extrair_cargos(spans: list[str]) -> str:
    """O span dos cargos engloba o da escolaridade, então vem concatenado."""
    if not spans:
        return ""
    cargos = spans[0]
    if len(spans) > 1 and spans[-1] and cargos.endswith(spans[-1]):
        cargos = cargos[: -len(spans[-1])]
    return cargos.strip(" ,;-")


def extrair_niveis(escolaridade: str) -> list[str]:
    texto = sem_acento(escolaridade)
    return [rotulo for chave, rotulo in NIVEIS if chave in texto]


def converter_data(texto: str) -> str | None:
    achado = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto or "")
    if not achado:
        return None
    dia, mes, ano = achado.groups()
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Persistência (o JSON anterior é a única memória)
# --------------------------------------------------------------------------- #

def ler_anterior() -> dict:
    if not SAIDA.exists():
        return {}
    try:
        return json.loads(SAIDA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def montar_pacote(itens: list[dict], anterior: dict) -> dict:
    agora = datetime.now(timezone.utc)
    antigos = {c["id"]: c for c in anterior.get("concursos", [])}
    primeira_coleta = not antigos
    corte = (agora - timedelta(hours=HORAS_COMO_NOVIDADE)).isoformat()

    for item in itens:
        visto = antigos.get(item["id"], {}).get("visto_em")
        item["visto_em"] = visto or agora.isoformat(timespec="seconds")
        item["novo"] = bool(not primeira_coleta and item["visto_em"] > corte)

    encerrados = [c for c in antigos.values() if c["id"] not in {i["id"] for i in itens}]

    return {
        "gerado_em": agora.isoformat(timespec="seconds"),
        "fonte": FONTE,
        "total": len(itens),
        "novos": sum(1 for i in itens if i["novo"]),
        "encerrados": len(encerrados),
        "concursos": itens,
    }


def gravar(pacote: dict) -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")


# --------------------------------------------------------------------------- #
# Saída no terminal
# --------------------------------------------------------------------------- #

def imprimir_resumo(pacote: dict, uf: str | None = None) -> None:
    concursos = pacote.get("concursos", [])
    if uf:
        alvo = uf.upper()
        concursos = [c for c in concursos if (c.get("uf") or "").upper() == alvo]

    hoje = date.today()
    onde = f" em {uf.upper()}" if uf else ""
    quando = pacote.get("gerado_em", "")[:16].replace("T", " ")
    print(f"\n{len(concursos)} concursos abertos{onde}  ·  coleta de {quando} UTC\n")

    for c in sorted(concursos, key=lambda c: c.get("inscricoes_ate") or "9999")[:40]:
        prazo = ""
        if c.get("inscricoes_ate"):
            limite = date.fromisoformat(c["inscricoes_ate"])
            prazo = f"{limite.strftime('%d/%m')} ({(limite - hoje).days}d)"
        salario = f"R$ {c['salario']:,.0f}".replace(",", ".") if c.get("salario") else "-"
        marca = "*" if c.get("novo") else " "
        print(f" {marca} [{c.get('uf') or '--':<3}] {c['orgao'][:52]:<52} {salario:>11}  {prazo}")

    if len(concursos) > 40:
        print(f"\n   ... e mais {len(concursos) - 40}.")


# --------------------------------------------------------------------------- #

def main() -> int:
    analisador = argparse.ArgumentParser(description="Coletor de concursos públicos")
    analisador.add_argument("--resumo", action="store_true",
                            help="mostra o que já está no JSON, sem acessar a rede")
    analisador.add_argument("--uf", help="limita o resumo impresso a um estado (ex.: ES)")
    argumentos = analisador.parse_args()

    if argumentos.resumo:
        pacote = ler_anterior()
        if not pacote:
            print(f"{SAIDA} ainda não existe. Rode sem --resumo para coletar.", file=sys.stderr)
            return 1
    else:
        print(f"Baixando {FONTE} ...")
        anterior = ler_anterior()
        try:
            itens = extrair(baixar())
        except RuntimeError as erro:
            print(f"Falha na coleta: {erro}", file=sys.stderr)
            return 1
        pacote = montar_pacote(itens, anterior)
        gravar(pacote)
        if anterior:
            print(f"{pacote['total']} concursos abertos · {pacote['novos']} novos · "
                  f"{pacote['encerrados']} sairam da lista.")
        else:
            print(f"Primeira coleta: {pacote['total']} concursos registrados.")

    imprimir_resumo(pacote, argumentos.uf)
    print(f"\nArquivo: {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
