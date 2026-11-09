"""Verifica paginas e referencias locais do Kenzoflix, sem pacotes externos."""

from html.parser import HTMLParser
from pathlib import Path
from posixpath import dirname, join, normpath
import re
from urllib.parse import unquote, urlsplit


class Pagina(HTMLParser):
    def __init__(self):
        super().__init__()
        self.doctype = False
        self.html = False
        self.tem_titulo = False
        self.dentro_titulo = False
        self.titulo = []
        self.referencias = []

    def handle_decl(self, decl):
        if decl.lower() == "doctype html":
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "html":
            self.html = True
        if tag == "title":
            self.tem_titulo = True
            self.dentro_titulo = True
        for atributo in ("src", "href"):
            valor = atributos.get(atributo)
            if valor:
                self.referencias.append(valor)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self.dentro_titulo = False

    def handle_data(self, data):
        if self.dentro_titulo:
            self.titulo.append(data)


def verificar(conteudos, arquivos):
    """Recebe textos HTML/CSS e os caminhos existentes, com maiusculas exatas."""
    erros = []
    if "index.html" not in arquivos:
        erros.append("A pagina inicial index.html nao existe.")

    for nome, texto in sorted(conteudos.items()):
        referencias = []
        if not texto.strip():
            erros.append(f"{nome}: arquivo vazio.")
        if nome.endswith(".html"):
            pagina = Pagina()
            pagina.feed(texto)
            if not pagina.doctype:
                erros.append(f"{nome}: falta <!DOCTYPE html>.")
            if not pagina.html:
                erros.append(f"{nome}: falta a tag <html>.")
            if not pagina.tem_titulo or not "".join(pagina.titulo).strip():
                erros.append(f"{nome}: falta um <title> preenchido.")
            referencias.extend(pagina.referencias)
        else:
            referencias.extend(
                valor.strip().strip("\"'")
                for valor in re.findall(r"url\(\s*([^)]*?)\s*\)", texto, re.I)
            )

        for referencia in referencias:
            url = urlsplit(referencia)
            if url.scheme or url.netloc or not url.path:
                continue
            caminho = unquote(url.path)
            if caminho.startswith("/"):
                erros.append(
                    f"{nome}: caminho absoluto {referencia!r}; "
                    "use um caminho relativo para o Pages deste repositorio."
                )
                continue
            destino = normpath(join(dirname(nome), caminho))
            if destino not in arquivos and join(destino, "index.html") not in arquivos:
                erros.append(f"{nome}: referencia local inexistente: {referencia}")

    return erros


def main():
    raiz = Path(__file__).resolve().parents[1]
    arquivos = {
        arquivo.relative_to(raiz).as_posix()
        for arquivo in raiz.rglob("*")
        if arquivo.is_file() and ".git" not in arquivo.relative_to(raiz).parts
    }
    fontes = sorted(list(raiz.glob("*.html")) + list(raiz.glob("*.css")))
    conteudos = {
        arquivo.relative_to(raiz).as_posix(): arquivo.read_text(encoding="utf-8-sig")
        for arquivo in fontes
    }
    erros = verificar(conteudos, arquivos)
    if erros:
        for erro in erros:
            print(f"ERRO: {erro}")
        raise SystemExit(1)
    paginas = sum(nome.endswith(".html") for nome in conteudos)
    print(f"OK: {paginas} paginas HTML e suas referencias locais verificadas.")


if __name__ == "__main__":
    main()
