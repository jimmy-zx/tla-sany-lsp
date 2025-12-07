# tla-sany-lsp

A TLA+ Language Server implemented in Python, using `tla2sany`.

## Features

- Diagnostics
- Goto definition
- Hover for comments

## Installation

Run the following in the project root.
```
pip install -e .
```

Download `tla2tools.jar` from [here](https://github.com/tlaplus/tlaplus/releases),
and set the following environment variable
```
TLA_SANY_LSP_CLASSPATH=[path to tla2tools.jar]
```

## Running

```
tla-sany-lsp
```

### Vim integeration

Using [yegappan/lsp](https://github.com/yegappan/lsp):
```
call LspAddServer([#{name: 'tla-lsp', filetype: 'tla', path: 'tla-sany-lsp'}])
```
