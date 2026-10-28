#!/usr/bin/env python3
# Lê um .docx sem dependências e imprime o texto na ordem do documento.
# Tabela vira uma linha por linha da tabela, com as células separadas por " | ".
#
# Rótulos não colam:
#   - quebra de linha (<w:br>, <w:cr>) dentro do parágrafo vira quebra de linha no texto;
#   - tabulação (<w:tab>) vira espaço;
#   - dois trechos de estilo diferente (negrito, cor, tamanho, fonte) vizinhos, sem
#     espaço entre eles, ganham um espaço ("RESPONSÁVEL" + "Fulano" vira "RESPONSÁVEL Fulano"),
#     exceto minúscula com minúscula, que é palavra partida pelo editor ("ferrament" + "a");
#   - parágrafos dentro de uma célula ficam separados por espaço.
#
#   python3 -I docx-para-texto.py <arquivo.docx>
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# pontuação que gruda no que veio antes / no que vem depois, sem espaço
GRUDA_ANTES = set(':;,.!?)]}%»”’+')
GRUDA_DEPOIS = set('([{«“‘')


def estilo(run):
    """Impressão digital do estilo de um trecho: dois trechos com a mesma são o mesmo estilo."""
    rpr = run.find(W + 'rPr')
    if rpr is None:
        return ()
    partes = []
    for filho in rpr:
        nome = filho.tag.replace(W, '')
        if nome in ('rtl', 'lang', 'noProof', 'szCs', 'bCs', 'iCs'):
            continue
        partes.append((nome, tuple(sorted((k.replace(W, ''), v) for k, v in filho.attrib.items()))))
    return tuple(sorted(partes))


def paragrafo(p):
    """Texto de um parágrafo, com '\n' onde o documento quebra a linha."""
    saida = []
    ultimo_estilo = None
    for run in p.iter(W + 'r'):
        est = estilo(run)
        for filho in run:
            tag = filho.tag
            if tag == W + 't':
                texto = filho.text or ''
                if not texto:
                    continue
                atual = ''.join(saida)
                if (
                    atual
                    and ultimo_estilo is not None
                    and est != ultimo_estilo
                    and not atual[-1].isspace()
                    and atual[-1] not in GRUDA_DEPOIS
                    and not texto[0].isspace()
                    and texto[0] not in GRUDA_ANTES
                    # minúscula colada em minúscula é a mesma palavra partida pelo editor
                    and not (atual[-1].islower() and texto[0].islower())
                ):
                    saida.append(' ')
                saida.append(texto)
                ultimo_estilo = est
            elif tag == W + 'tab':
                saida.append(' ')
            elif tag in (W + 'br', W + 'cr'):
                saida.append('\n')
                ultimo_estilo = None
    return ''.join(saida)


def linhas(p):
    return [l.strip() for l in paragrafo(p).split('\n') if l.strip()]


def celula(tc):
    partes = []
    for p in tc.findall(W + 'p'):
        partes.extend(linhas(p))
    return ' '.join(partes)


raiz = ET.fromstring(zipfile.ZipFile(sys.argv[1]).read('word/document.xml'))
for filho in raiz.find(W + 'body'):
    if filho.tag == W + 'p':
        for l in linhas(filho):
            print(l)
    elif filho.tag == W + 'tbl':
        for linha in filho.iter(W + 'tr'):
            print(' | '.join(celula(c) for c in linha.findall(W + 'tc')))
