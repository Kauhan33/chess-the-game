"""Gera os PDFs de entrega em entrega/: o documento unificado e os recortes E1, E2 e E3.

Uso: python tools/gerar_pdf.py
Converte os capítulos de docs/ de Markdown para HTML (conversor próprio, sem dependências) e imprime
em PDF A4 com o Chrome ou o Edge sem janela. A capa vem de entrega/dados_capa.json, que fica fora do
git. Sem esse arquivo, sai uma capa genérica, sem nomes.

O sumário precisa do número da página de cada título, e só o navegador sabe a paginação. Por isso a
impressão roda duas vezes: a primeira serve para ler, no próprio PDF, onde cada título caiu.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
DELIVERY_DIR = ROOT / "entrega"
COVER_DATA_FILE = DELIVERY_DIR / "dados_capa.json"
BUILD_DIR = ROOT / "build" / "pdf"
BROWSER_PROFILE = BUILD_DIR / "perfil-navegador"
COVER_IMAGE = DOCS_DIR / "img" / "tela_partida.png"
WINDOWS_BROWSERS = (r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe")
WINDOWS_PROGRAM_FOLDERS = ("ProgramFiles", "ProgramFiles(x86)")
MAC_BROWSER = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BROWSER_COMMANDS = ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge")
PRINT_TIMEOUT_SECONDS = 180
MAX_LAYOUT_PASSES = 4
# Figura mais larga que isto, e com esta proporção, fica ilegível em retrato: vai para página deitada.
LANDSCAPE_MIN_WIDTH = 1700
LANDSCAPE_MIN_RATIO = 1.3
DIAGRAM_FOLDER = "uml/"
DIAGRAM_DPI = 150
_PNG_SIZE_OFFSET = 16

ALL_CHAPTERS = (
    "01-visao-e-requisitos.md",
    "02-prototipos-ui-ux.md",
    "03-casos-de-uso.md",
    "04-modelagem-uml.md",
    "05-arquitetura.md",
    "06-computacao-grafica.md",
    "07-plano-de-testes.md",
    "08-matriz-rastreabilidade.md",
    "09-kanban.md",
)
EXCERPT_NOTE = "Recorte da documentação unificada. Referências a outros capítulos apontam para ela."
# Escrito por extenso: no papel, um link embutido no texto não leva a lugar nenhum.
CODE_NOTE = ("Código-fonte em Python, com o README de instruções: https://github.com/Kauhan33/chess-the-game. "
             "O mesmo código acompanha esta documentação no arquivo chess-the-game-codigo.zip.")


@dataclass(frozen=True)
class Document:
    file_name: str
    title: str
    chapters: tuple[str, ...]
    note: str = ""


DOCUMENTS = (
    Document("A3_Documentacao_Unificada.pdf", "Documentação Unificada", ALL_CHAPTERS, CODE_NOTE),
    Document("A3_E1_Requisitos_e_Telas.pdf", "E1: Especificação de Requisitos e Telas", ALL_CHAPTERS[:2], EXCERPT_NOTE),
    Document("A3_E2_Casos_de_Uso.pdf", "E2: Modelagem de Casos de Uso", ALL_CHAPTERS[2:3], EXCERPT_NOTE),
    Document("A3_E3_Classes_e_Sequencia.pdf", "E3: Modelagem Estrutural e Dinâmica", ALL_CHAPTERS[3:4], EXCERPT_NOTE),
)

_IMAGE_LINE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LIST_ITEM = re.compile(r"^(\d+\.|-) ")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
_BLOCK_START = re.compile(r"^(#|\||>|```|<!--|(\d+\.|-) )")
_LANDSCAPE_LEADING = re.compile(r"^<(p|h2|h3)\b")
_MAX_LANDSCAPE_LEADING = 3


def _inline(text: str) -> str:
    """Converte a marcação de linha: `código`, **negrito**, *itálico* e [link](destino)."""
    protected: list[str] = []

    def protect(content: str) -> str:
        protected.append(content)
        return f"\x00{len(protected) - 1}\x00"

    def code(match: re.Match) -> str:
        content = match.group(1)
        swatch = f'<span class="amostra" style="background:{content}"></span>' if _HEX_COLOR.fullmatch(content) else ""
        return protect(f"<code>{swatch}{html.escape(content)}</code>")

    text = re.sub(r"`([^`]+)`", code, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<strong>\1</strong>", text)
    return re.sub(r"\x00(\d+)\x00", lambda match: protected[int(match.group(1))], text)


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        image.seek(_PNG_SIZE_OFFSET)
        return struct.unpack(">II", image.read(8))


def _diagram_size_style(path: Path, source: str) -> str:
    """Diagrama no tamanho em que foi gerado, nunca ampliado: a fonte fica igual entre os diagramas."""
    if not source.startswith(DIAGRAM_FOLDER):
        return ""
    return f' style="max-width:min(100%,{_png_size(path)[0] / DIAGRAM_DPI:.2f}in)"'


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


@dataclass
class HtmlBuilder:
    """Converte os capítulos, numerando títulos e figuras ao longo do documento inteiro."""

    headings: list[tuple[int, str, str]] = field(default_factory=list)
    figure_count: int = 0
    _blocks: list[str] = field(default_factory=list)

    def _figure(self, alt: str, source: str) -> str:
        path = (DOCS_DIR / source).resolve()
        if not path.exists():
            sys.exit(f"Imagem não encontrada: {source}")
        self.figure_count += 1
        caption = f"Figura {self.figure_count}: {html.escape(alt)}"
        size = _diagram_size_style(path, source)
        return f'<figure><img src="{path.as_uri()}" alt="{html.escape(alt)}"{size}><figcaption>{caption}</figcaption></figure>'

    def _block_figure(self, alt: str, source: str) -> str:
        width, height = _png_size((DOCS_DIR / source).resolve())
        figure = self._figure(alt, source)
        is_wide = width >= LANDSCAPE_MIN_WIDTH and width / height >= LANDSCAPE_MIN_RATIO
        return self._landscape_section(figure) if is_wide else figure

    def _landscape_section(self, figure: str) -> str:
        """A página deitada leva junto o título e o texto da figura, que senão ficariam isolados antes dela."""
        leading: list[str] = []
        while self._blocks and _LANDSCAPE_LEADING.match(self._blocks[-1]) and len(leading) < _MAX_LANDSCAPE_LEADING:
            leading.insert(0, self._blocks.pop())
        css = "deitada com-texto" if leading else "deitada"
        return f'<section class="{css}">{"".join(leading)}{figure}</section>'

    def _heading(self, line: str) -> str:
        level = len(line) - len(line.lstrip("#"))
        text = line[level:].strip()
        anchor = f"t{len(self.headings) + 1}"
        self.headings.append((level, text, anchor))
        return f'<h{level} id="{anchor}">{_inline(text)}</h{level}>'

    def _table(self, lines: list[str]) -> str:
        header = _table_cells(lines[0])
        rows = [_table_cells(line) for line in lines[2:]]
        has_images = any("![" in cell for row in rows for cell in row)
        cell = self._gallery_cell if has_images else _inline
        css = _table_class(header, has_images)
        head = "" if not any(header) else "<thead><tr>" + "".join(f"<th>{_inline(item)}</th>" for item in header) + "</tr></thead>"
        body = "".join("<tr>" + "".join(f"<td>{cell(item)}</td>" for item in row) + "</tr>" for row in rows)
        return f'<table class="{css}">{head}<tbody>{body}</tbody></table>'

    def _gallery_cell(self, content: str) -> str:
        match = _IMAGE_LINE.fullmatch(content)
        return self._figure(match.group(1), match.group(2)) if match else _inline(content)

    def convert(self, markdown: str) -> str:
        lines = markdown.splitlines()
        self._blocks = []
        index = 0
        while index < len(lines):
            block, index = self._next_block(lines, index)
            if block:
                self._blocks.append(block)
        return "\n".join(self._blocks)

    def _next_block(self, lines: list[str], index: int) -> tuple[str, int]:
        line = lines[index]
        if not line.strip() or line.startswith("<!--"):
            return "", index + 1
        if line.startswith("```"):
            return _code_block(lines, index)
        if line.startswith("#"):
            return self._heading(line), index + 1
        if line.startswith("|"):
            end = _end_of_run(lines, index, "|")
            return self._table(lines[index:end]), end
        if line.startswith(">"):
            end = _end_of_run(lines, index, ">")
            return "<blockquote>" + _inline(" ".join(item[1:].strip() for item in lines[index:end])) + "</blockquote>", end
        if _LIST_ITEM.match(line):
            return _list_block(lines, index)
        image = _IMAGE_LINE.fullmatch(line.strip())
        if image:
            return self._block_figure(image.group(1), image.group(2)), index + 1
        return _paragraph(lines, index)


def _table_class(header: list[str], has_images: bool) -> str:
    if has_images:
        return "galeria"
    if not any(header):
        return "ficha"
    return {"Caso": "casos", "Requisito": "rnf", "ID": "requisitos", "RF": "matriz", "Coluna": "kanban"}.get(header[0], "comum")


def _end_of_run(lines: list[str], index: int, prefix: str) -> int:
    end = index
    while end < len(lines) and lines[end].startswith(prefix):
        end += 1
    return end


def _code_block(lines: list[str], index: int) -> tuple[str, int]:
    end = index + 1
    while end < len(lines) and not lines[end].startswith("```"):
        end += 1
    return f"<pre><code>{html.escape(chr(10).join(lines[index + 1:end]))}</code></pre>", end + 1


def _list_block(lines: list[str], index: int) -> tuple[str, int]:
    tag = "ol" if lines[index][0].isdigit() else "ul"
    items: list[str] = []
    while index < len(lines) and lines[index].strip() and not lines[index].startswith("<!--"):
        line = lines[index]
        if _LIST_ITEM.match(line):
            items.append(_LIST_ITEM.sub("", line))
        else:
            items[-1] += " " + line.strip()
        index += 1
    return f"<{tag}>" + "".join(f"<li>{_inline(item)}</li>" for item in items) + f"</{tag}>", index


def _paragraph(lines: list[str], index: int) -> tuple[str, int]:
    parts: list[str] = []
    while index < len(lines) and lines[index].strip() and not _BLOCK_START.match(lines[index]):
        parts.append(lines[index].strip())
        index += 1
    return f"<p>{_inline(' '.join(parts))}</p>", index


CSS = """
@page { size: A4; margin: 17mm 16mm 18mm 16mm;
        @bottom-right { content: counter(page); font: 9pt 'Segoe UI', sans-serif; color: #6b5a44; }
        @bottom-left { content: "Chess - The Game"; font: 9pt 'Segoe UI', sans-serif; color: #8a7a64; } }
@page deitada { size: A4 landscape; margin: 11mm 14mm 14mm 14mm;
        @bottom-right { content: counter(page); font: 9pt 'Segoe UI', sans-serif; color: #6b5a44; }
        @bottom-left { content: "Chess - The Game"; font: 9pt 'Segoe UI', sans-serif; color: #8a7a64; } }
@page capa { margin: 0; @bottom-right { content: none; } @bottom-left { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', 'Noto Sans', 'DejaVu Sans', Arial, sans-serif; font-size: 10.2pt; line-height: 1.45;
       color: #24170e; margin: 0; }
.capa { page: capa; height: 297mm; padding: 24mm 22mm 20mm; display: flex; flex-direction: column; color: #f0e4c8;
        background: linear-gradient(180deg, #17100b 0%, #2a1b12 60%, #422c1c 100%); break-after: page; }
.capa .instituicao { font-size: 13pt; color: #ebcb8b; font-weight: 600; }
.capa .uc { font-size: 11pt; color: #c9b89a; margin-top: 1.5mm; line-height: 1.5; }
.capa h1 { font-family: 'Palatino Linotype', Palatino, Georgia, serif; font-size: 40pt; line-height: 1.1; color: #ebcb8b;
           margin: 22mm 0 3mm; border: 0; padding: 0; break-before: auto; }
.capa .documento { font-size: 15pt; margin-bottom: 9mm; }
.capa img { width: 100%; border: 1px solid #8f6d33; display: block; }
.capa .dados { margin-top: auto; border-top: 1px solid #8f6d33; padding-top: 5mm; font-size: 11pt; line-height: 1.6; }
.capa .dados b { color: #ebcb8b; font-weight: 600; }
.capa .integrantes { margin: 1mm 0 0; padding: 0; list-style: none; }
.sumario { break-after: page; }
.sumario h2 { break-before: auto; }
.sumario .nota { color: #543a1e; font-size: 9.5pt; }
.sumario a { display: flex; align-items: baseline; color: inherit; text-decoration: none; padding: .55mm 0; }
.sumario a span:first-child { flex: 0 1 auto; }
.sumario a i { flex: 1; border-bottom: 1px dotted #a08c6c; margin: 0 2mm; }
.sumario .n1 { font-weight: 600; margin-top: 2.2mm; }
.sumario .n2 { padding-left: 5mm; font-size: 9.6pt; }
h1 { font-family: 'Palatino Linotype', Palatino, Georgia, serif; font-size: 22pt; color: #422c1c; margin: 0 0 5mm;
     padding-bottom: 2mm; border-bottom: 2px solid #c8a15a; break-before: page; break-after: avoid; }
main > h1:first-child { break-before: auto; }
h2 { font-family: 'Palatino Linotype', Palatino, Georgia, serif; font-size: 15pt; color: #6c4e2e; margin: 7mm 0 2.5mm;
     break-after: avoid; }
h3 { font-size: 11.5pt; color: #6c4e2e; margin: 5mm 0 1.5mm; break-after: avoid; }
p { margin: 0 0 2.6mm; }
p:has(+ pre), p:has(+ table), p:has(+ ol), p:has(+ ul) { break-after: avoid; }
ol, ul { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: .8mm; }
code { font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: .88em; background: #f4eddd; padding: 0 .6mm;
       border-radius: .6mm; overflow-wrap: break-word; }
.amostra { display: inline-block; width: 3mm; height: 3mm; margin-right: 1mm; border: .2mm solid #6c4e2e; vertical-align: -.4mm; }
pre { background: #f7f1e3; border-left: 1mm solid #c8a15a; padding: 2.5mm 3.5mm; margin: 0 0 3.5mm; font-size: 8.6pt;
      line-height: 1.38; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; overflow-wrap: normal; }
table { width: 100%; border-collapse: collapse; margin: 1.5mm 0 4mm; font-size: 8.9pt; line-height: 1.34; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
table.comum, table.ficha { break-inside: avoid; }
th { background: #422c1c; color: #f0e4c8; text-align: left; font-weight: 600; padding: 1.3mm 1.8mm; }
th code { background: none; color: inherit; }
td { border-bottom: .25mm solid #dccdb0; padding: 1.2mm 1.8mm; vertical-align: top; overflow-wrap: break-word; }
tbody tr:nth-child(even) td { background: #fbf7ee; }
table.ficha { font-size: 9.4pt; }
table.ficha td:first-child { width: 26mm; }
table.casos { font-size: 7.7pt; line-height: 1.28; table-layout: fixed; }
table.casos th, table.casos td { padding: .95mm 1.2mm; }
table.casos th:nth-child(1) { width: 17.5%; } table.casos th:nth-child(2) { width: 22%; }
table.casos th:nth-child(3) { width: 19%; } table.casos th:nth-child(4) { width: 26%; }
table.casos th:nth-child(5) { width: 15.5%; }
table.requisitos { font-size: 8.3pt; table-layout: fixed; }
table.requisitos th:nth-child(1) { width: 8%; } table.requisitos th:nth-child(2) { width: 28%; }
table.requisitos th:nth-child(3) { width: 45%; } table.requisitos th:nth-child(4) { width: 19%; }
table.rnf { font-size: 8.3pt; table-layout: fixed; }
table.rnf th:nth-child(1) { width: 19%; } table.rnf th:nth-child(2) { width: 22%; }
table.rnf th:nth-child(3) { width: 45%; } table.rnf th:nth-child(4) { width: 14%; }
table.matriz { font-size: 8.3pt; table-layout: fixed; }
table.matriz th:nth-child(1) { width: 7%; } table.matriz th:nth-child(2) { width: 37%; }
table.matriz th:nth-child(3) { width: 12%; } table.matriz th:nth-child(4) { width: 34%; }
table.matriz th:nth-child(5) { width: 10%; }
table.kanban { font-size: 8.5pt; table-layout: fixed; }
table.kanban th:nth-child(1) { width: 17%; } table.kanban th:nth-child(2) { width: 6%; }
table.kanban th:nth-child(3) { width: 50%; } table.kanban th:nth-child(4) { width: 6%; }
table.kanban th:nth-child(5) { width: 21%; }
table.galeria { table-layout: fixed; margin-top: 0; }
table.galeria td { background: none !important; border: 0; padding: .8mm; width: 50%; }
table.galeria th { text-align: center; }
table.galeria img { width: 100%; max-height: none; border: .25mm solid #b9a988; }
table.galeria figure { margin: 0; }
table.galeria figcaption { font-size: 7.8pt; margin-top: .6mm; }
figure { margin: 1mm 0 4mm; break-inside: avoid; text-align: center; }
figure img { display: inline-block; max-width: 100%; max-height: 222mm; width: auto; height: auto; }
figcaption { font-size: 8.8pt; color: #543a1e; margin-top: 1mm; }
p:has(+ figure) { break-after: avoid; break-inside: avoid; }
h2 + p + figure img, h3 + p + figure img { max-height: 200mm; }
h2 + h3 + p + figure img { max-height: 192mm; }
section.deitada { page: deitada; }
section.deitada > :first-child { margin-top: 0; }
section.deitada figure { margin: 0; }
section.deitada img { max-height: 170mm; }
section.com-texto img { max-height: 136mm; }
blockquote { margin: 2mm 0 4mm; padding: 2.5mm 4mm; background: #fbf1e3; border-left: 1mm solid #8f6d33; }
"""


def load_cover_data() -> dict:
    """Só este script lê os dados pessoais, e só para o PDF que fica em entrega/."""
    try:
        return json.loads(COVER_DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[aviso] {COVER_DATA_FILE.name} não existe: a capa sai sem nomes.")
    except json.JSONDecodeError as error:
        print(f"[aviso] {COVER_DATA_FILE.name} está inválido ({error}): a capa sai sem nomes.")
    return {}


def _cover_details(data: dict) -> str:
    rows = []
    if data.get("grupo"):
        rows.append(f"<div><b>{html.escape(data['grupo'])}</b></div>")
    members = [member for member in data.get("integrantes", []) if member.get("nome", "").strip()]
    if members:
        items = "".join(
            f"<li>{html.escape(member['nome'])}" + (f", RA {html.escape(member['ra'])}" if member.get("ra") else "") + "</li>"
            for member in members
        )
        rows.append(f'<div><b>Integrantes:</b><ul class="integrantes">{items}</ul></div>')
    professors = [name for name in data.get("professores", []) if name.strip()]
    if professors:
        rows.append(f"<div><b>Professores:</b> {html.escape(', '.join(professors))}</div>")
    if data.get("cidade_ano"):
        rows.append(f"<div>{html.escape(data['cidade_ano'])}</div>")
    return "".join(rows)


def render_cover(document: Document, data: dict) -> str:
    institution = html.escape(data.get("instituicao", ""))
    course_lines = [data.get("unidade_curricular", "Computação Gráfica e Realidade Virtual"), data.get("curso", ""), data.get("periodo", "")]
    course = "<br>".join(html.escape(line) for line in course_lines if line)
    return f"""
<section class="capa">
  <div class="instituicao">{institution}</div>
  <div class="uc">{course}</div>
  <h1>Chess - The Game</h1>
  <div class="documento">{html.escape(document.title)}</div>
  <img src="{COVER_IMAGE.resolve().as_uri()}" alt="Partida em andamento">
  <div class="dados">{_cover_details(data)}</div>
</section>"""


def render_contents(document: Document, headings: list, pages: dict[str, int]) -> str:
    entries = []
    for level, text, anchor in headings:
        if level > 2:
            continue
        page = pages.get(anchor, "")
        entries.append(f'<a class="n{level}" href="#{anchor}"><span>{_inline(text)}</span><i></i><span>{page}</span></a>')
    note = f'<p class="nota">{html.escape(document.note)}</p>' if document.note else ""
    return f'<section class="sumario"><h2>Sumário</h2>{note}{"".join(entries)}</section>'


def build_html(document: Document, cover_data: dict, pages: dict[str, int]) -> tuple[str, list]:
    builder = HtmlBuilder()
    body = "\n".join(builder.convert((DOCS_DIR / chapter).read_text(encoding="utf-8")) for chapter in document.chapters)
    page = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Chess - The Game: {html.escape(document.title)}</title>
<style>{CSS}</style></head><body>{render_cover(document, cover_data)}
{render_contents(document, builder.headings, pages)}
<main>{body}</main></body></html>"""
    return page, builder.headings


def _browser_paths() -> list[str]:
    folders = [os.environ[name] for name in WINDOWS_PROGRAM_FOLDERS if name in os.environ]
    return [os.path.join(folder, browser) for folder in folders for browser in WINDOWS_BROWSERS] + [MAC_BROWSER]


def find_browser() -> str:
    for path in _browser_paths():
        if os.path.exists(path):
            return path
    for name in BROWSER_COMMANDS:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Chrome ou Edge não encontrado. É preciso um deles para gerar o PDF.")


def print_to_pdf(browser: str, html_file: Path, pdf_file: Path) -> None:
    pdf_file.unlink(missing_ok=True)
    command = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
               "--allow-file-access-from-files", f"--user-data-dir={BROWSER_PROFILE}", "--virtual-time-budget=20000",
               f"--print-to-pdf={pdf_file}", html_file.as_uri()]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=PRINT_TIMEOUT_SECONDS)
    if not pdf_file.exists():
        sys.exit(f"O navegador não gerou {pdf_file.name}:\n{completed.stderr}")


def _pdf_objects(data: bytes) -> dict[int, bytes]:
    return {int(number): body for number, body in re.findall(rb"(?m)^(\d+) 0 obj\s*(.*?)\s*endobj", data, re.DOTALL)}


def _ordered_pages(objects: dict[int, bytes]) -> list[int]:
    """Percorre a árvore de páginas do PDF na ordem de leitura."""
    root = next(body for body in objects.values() if re.search(rb"/Type\s*/Catalog", body))
    pages_root = int(re.search(rb"/Pages\s+(\d+) 0 R", root).group(1))

    def walk(number: int) -> list[int]:
        body = objects[number]
        if re.search(rb"/Type\s*/Pages\b", body):
            kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.DOTALL).group(1)
            return [page for kid in re.findall(rb"(\d+) 0 R", kids) for page in walk(int(kid))]
        return [number]

    return walk(pages_root)


def read_heading_pages(pdf_file: Path) -> dict[str, int]:
    """Lê os destinos nomeados que o navegador cria para os links do sumário: âncora -> página."""
    objects = _pdf_objects(pdf_file.read_bytes())
    page_numbers = {number: index + 1 for index, number in enumerate(_ordered_pages(objects))}
    destinations = {}
    for body in objects.values():
        for anchor, page in re.findall(rb"/(t\d+)\s*\[\s*(\d+) 0 R\s*/XYZ", body):
            destinations[anchor.decode()] = page_numbers[int(page)]
    if not destinations:
        sys.exit(f"Não foi possível ler os destinos de {pdf_file.name}: o formato do PDF mudou.")
    return destinations


def generate(document: Document, browser: str, cover_data: dict) -> int:
    """Imprime até o sumário parar de mudar. Devolve o número de páginas."""
    html_file = BUILD_DIR / f"{Path(document.file_name).stem}.html"
    pdf_file = DELIVERY_DIR / document.file_name
    pages: dict[str, int] = {}
    for _ in range(MAX_LAYOUT_PASSES):
        page, headings = build_html(document, cover_data, pages)
        html_file.write_text(page, encoding="utf-8")
        print_to_pdf(browser, html_file, pdf_file)
        found = read_heading_pages(pdf_file)
        missing = [text for level, text, anchor in headings if level <= 2 and anchor not in found]
        if missing:
            sys.exit(f"Título sem destino em {document.file_name}: {missing[0]}")
        if found == pages:
            return len(_ordered_pages(_pdf_objects(pdf_file.read_bytes())))
        pages = found
    sys.exit(f"O sumário de {document.file_name} não estabilizou em {MAX_LAYOUT_PASSES} impressões.")


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DELIVERY_DIR.mkdir(exist_ok=True)
    browser = find_browser()
    cover_data = load_cover_data()
    for document in DOCUMENTS:
        page_count = generate(document, browser, cover_data)
        print(f"{document.file_name}: {page_count} páginas")


if __name__ == "__main__":
    main()
