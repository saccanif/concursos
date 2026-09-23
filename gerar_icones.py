# -*- coding: utf-8 -*-
"""
Gera os ícones do app em docs/.

A marca é um edital sobre fundo azul, com uma linha em rosa — as cores da
bandeira do Espírito Santo. Desenho geométrico, sem fonte externa, para
continuar legível no tamanho que o iOS usa na tela de início (~60 px).

Uso:  python gerar_icones.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parent / "docs"

AZUL = (21, 48, 79)
PAPEL = (255, 255, 255)
ROSA = (201, 69, 92)
CINZA = (169, 185, 200)

TAMANHOS = (180, 192, 512)  # 180 = apple-touch-icon; 192/512 = manifest


def desenhar(lado: int) -> Image.Image:
    # Desenha em 4x e reduz no fim: bordas limpas sem antialias manual.
    escala = 4
    s = lado * escala
    imagem = Image.new("RGB", (s, s), AZUL)
    pincel = ImageDraw.Draw(imagem)

    def caixa(x0, y0, x1, y1, cor, raio):
        pincel.rounded_rectangle([s * x0, s * y0, s * x1, s * y1],
                                 radius=int(s * raio), fill=cor)

    caixa(.22, .17, .78, .83, PAPEL, .05)          # a folha do edital
    caixa(.30, .28, .62, .335, AZUL, .028)         # linhas de texto
    caixa(.30, .41, .70, .465, ROSA, .028)         # a linha em destaque
    caixa(.30, .54, .58, .595, CINZA, .028)
    caixa(.30, .655, .66, .71, CINZA, .028)

    return imagem.resize((lado, lado), Image.LANCZOS)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for lado in TAMANHOS:
        caminho = DESTINO / f"icone-{lado}.png"
        desenhar(lado).save(caminho, "PNG", optimize=True)
        print(f"{caminho.name}  {caminho.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
