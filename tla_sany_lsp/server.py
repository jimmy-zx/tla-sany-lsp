#!/usr/bin/env python3

from urllib.parse import urlparse, unquote
from pygls.lsp.server import LanguageServer
from lsprotocol import types
from tla_sany_lsp.parser import Parser, ParserException


def uri_to_path(uri: str) -> str:
    return unquote(urlparse(uri).path)


class TLALanguageServer(LanguageServer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parsers: dict[str, Parser] = {}

    def init_parser(self, uri: str) -> list[types.Diagnostic]:
        try:
            self.parsers[uri] = Parser.create_parser(uri_to_path(uri))
            return []
        except ParserException as ex:
            diags: list[types.Diagnostic] = []
            for error in ex.errors:
                line0, col0, line1, col1 = (
                    max(x - 1, 0) for x in error.getLocation().getCoordinates()
                )
                diags.append(
                    types.Diagnostic(
                        message=str(error),
                        severity=types.DiagnosticSeverity.Error,
                        range=types.Range(
                            start=types.Position(line=line0, character=col0),
                            end=types.Position(line=line1, character=col1),
                        ),
                    )
                )
            return diags

    def get_parser(self, uri: str) -> Parser:
        if uri not in self.parsers:
            self.init_parser(uri)
        return self.parsers[uri]


server = TLALanguageServer("tla-sany-lsp", "v0.1")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    diags = ls.init_parser(params.text_document.uri)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=params.text_document.uri,
            diagnostics=diags,
        )
    )


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    diags = ls.init_parser(params.text_document.uri)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=params.text_document.uri,
            diagnostics=diags,
        )
    )


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
def goto_definition(ls: TLALanguageServer, params: types.DefinitionParams):
    document_uri = params.text_document.uri
    pos = params.position
    parser = ls.get_parser(document_uri)
    node = parser.lookup_cursor(uri_to_path(document_uri), pos.line, pos.character)
    symbol = parser.print_loc(node.getLocation())
    resolved = parser.resolve_symbol(symbol)

    if not resolved:
        return

    loc = resolved.getLocation()
    line0, col0, line1, col1 = (x - 1 for x in loc.getCoordinates())

    return types.Location(
        uri=f"file://{parser.get_path_from_name(loc.source())}",
        range=types.Range(
            start=types.Position(line=line0, character=col0),
            end=types.Position(line=line1, character=col1),
        ),
    )


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(ls: TLALanguageServer, params: types.HoverParams):
    pos = params.position
    document_uri = params.text_document.uri

    parser = ls.get_parser(document_uri)
    node = parser.lookup_cursor(uri_to_path(document_uri), pos.line, pos.character)

    hover_content = [] + [str(comment) for comment in node.getPreComments() or []]

    symbol = parser.print_loc(node.getLocation())
    resolved = parser.resolve_symbol(symbol)
    if resolved:
        hover_content += [str(comment) for comment in resolved.getPreComments()]

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value="\n\n".join(hover_content),
        ),
        range=types.Range(
            start=types.Position(line=pos.line, character=0),
            end=types.Position(line=pos.line + 1, character=0),
        ),
    )


def main():
    server.start_io()


if __name__ == "__main__":
    main()
