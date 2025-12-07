#!/usr/bin/env python3

from __future__ import annotations
import sys
import os
from typing import Any
import jpype


jpype.startJVM(classpath=os.getenv("TLA_SANY_LSP_CLASSPATH"))

ToolIO = jpype.JClass("util.ToolIO")
SpecObj = jpype.JClass("tla2sany.modanalyzer.SpecObj")
OutErrSanyOutput = jpype.JClass("tla2sany.output.OutErrSanyOutput")
LogLevel = jpype.JClass("tla2sany.output.LogLevel")
SANY = jpype.JClass("tla2sany.drivers.SANY")
SemanticNode = jpype.JClass("tla2sany.semantic.SemanticNode")
OpDefNode = jpype.JClass("tla2sany.semantic.OpDefNode")
ModuleNode = jpype.JClass("tla2sany.semantic.ModuleNode")
Location = jpype.JClass("tla2sany.st.Location")
SimpleFilenameToStream = jpype.JClass("util.SimpleFilenameToStream")
UniqueString = jpype.JClass("util.UniqueString")


class ParserException(Exception):
    def __init__(self, spec: SpecObj, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.spec = spec
        self.errors = []
        for error in self.spec.getParseErrors().getErrorDetails():
            self.errors.append(error)
        for error in self.spec.getSemanticErrors().getErrorDetails():
            self.errors.append(error)


class Parser:
    @classmethod
    def create_parser(
        cls, file: str, out: OutErrSanyOutput | None = None
    ) -> Parser | None:
        if out is None:
            out = OutErrSanyOutput(
                ToolIO.err, ToolIO.err, LogLevel.INFO, LogLevel.ERROR
            )
        spec = SpecObj(file)
        try:
            assert SANY.frontEndMain(spec, file, out) == 0
            assert spec.getSemanticErrors().isSuccess()
            return cls(spec)
        except AssertionError as ex:
            raise ParserException(spec) from ex

    def __init__(self, spec: SpecObj) -> None:
        self.spec = spec
        self.mt = self.spec.getExternalModuleTable()
        self.root = self.mt.getRootModule()

        self.locator = SimpleFilenameToStream()

        self.files: dict[str, list[str]] = {}
        self.locations: dict[str, list[tuple[Location, int, SemanticNode]]] = {}
        self.visit(self.root)

    def get_path_from_name(self, name: str) -> str:
        return os.path.abspath(str(self.locator.resolve(name, True)))

    def get_file(self, file: str) -> Any:
        if file not in self.files:
            with open(file, "r") as fp:
                self.files[file] = fp.readlines()
        return self.files[file]

    def print_loc(self, loc: Location, prefix: str = "") -> str:
        file = self.get_file(self.get_path_from_name(loc.source()))
        line0, col0, line1, col1 = (x - 1 for x in loc.getCoordinates())
        if line0 == line1:
            return prefix + file[line0][col0 : col1 + 1]
        buf = [file[line0][col0:]]
        for line in range(line0 + 1, line1):
            buf.append(file[line])
        buf += [file[line1][: col1 + 1]]
        return "".join(prefix + line for line in buf)

    def visit(self, node: SemanticNode, depth: int = 1) -> None:
        assert isinstance(node, SemanticNode), type(node)

        loc = node.getLocation()
        path = self.get_path_from_name(loc.source())
        if path not in self.locations:
            self.locations[path] = []
        self.locations[path].append((loc, depth, node))

        print(depth * "|", repr(node), loc, file=sys.stderr)
        print(self.print_loc(loc, prefix=depth * "|" + " "), file=sys.stderr)

        for child in node.getListOfChildren():
            self.visit(child, depth + 1)

        print((depth - 1) * "|", "`", sep="", file=sys.stderr)

    def lookup_cursor(self, file: str, line: int, col: int) -> SemanticNode | None:
        file = os.path.abspath(file)
        max_depth = 0
        target: SemanticNode | None = None
        for loc, depth, node in self.locations[file]:
            line0, col0, line1, col1 = (x - 1 for x in loc.getCoordinates())
            if line0 <= line <= line1:
                if col0 <= col <= col1:
                    if depth > max_depth:
                        target = node
                        max_depth = depth
        return target

    def resolve_symbol(self, name: str | UniqueString) -> SemanticNode | None:
        if isinstance(name, str):
            name = UniqueString.of(name)
        ctx = self.root.getContext()
        symbol = ctx.getSymbol(name)
        if symbol is None:
            return None
        if isinstance(symbol, OpDefNode):
            if (reloc_symbol := symbol.getSource()) is not None:
                return reloc_symbol
        return symbol


if __name__ == "__main__":
    parser = Parser.create_parser(sys.argv[1])
    node = parser.lookup_cursor("main.tla", 6, 16)
    data = UniqueString.of(parser.print_loc(node.getLocation()))
    print(parser.resolve_symbol(data))
