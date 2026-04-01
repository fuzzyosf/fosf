# Fuzzy Order-Sorted Feature (OSF) Logic in Python

## Installation

Create a Python >=3.10 virtual environment, activate it, and run `pip install -e .`.

To run tests and check that everything works: `pip install -e .'[test]'` and then `pytest`.

To use the drawing functions, Graphviz (https://graphviz.org/) is also required.
E.g., on Ubuntu:
```
$ sudo apt update
$ sudo apt install graphviz graphviz-dev
$ pip install -e .'[drawing]'
```
**Note**: running the drawing functions in `fosf/utils/draw.py` (in particular
`graphviz_to_png` and `notebook_display` will create a `.fosf` folder in your
system's home directory to store the drawings of OSF structures.

To run the example notebooks with Jupyter:
```
$ pip install ipykernel
$ python -m ipykernel install --user --name=fosf
```
Now you can run the Jupyter notebooks locally after selecting the `fosf` kernel.

## Examples

The `examples` folder contains the following example notebooks for using the
`fosf` library.

- `Fuzzy OSF Logic.ipynb` goes through the main features of (fuzzy) OSF logic
  and the `fosf` library.
- `IJCAR.ipynb` goes through the examples in the figures of the IJCAR 2026 short
  paper submission.

## Comparison with Bousi~Prolog

The folder `bpl_comparison` contains the scripts and files that are relevant
for the Bousi~Prolog comparison section of the IJCAR 2026 short paper
submission. More details can be found in `bpl_comparison/README.md`.

## Project structure

- `fosf/parsers`: code for parsing (fuzzy) sort taxonomies, OSF terms, clauses
  and theories from strings in order to build internal representations.
  `fosf/parsers/grammars` contains the related EBNF
  [Lark](https://lark-parser.readthedocs.io/en/stable/) grammars.
- `fosf/reasoning`: algorithms for OSF clause normalization, OSF term
  normalization, unification and theory unification.
- `fosf/syntax`: code defining Python classes that represent fuzzy OSF sort
  taxonomies, clauses, terms, and theories, and related methods to handle them.

The documentation for `fosf` is available at
[https://fosf.pages.dev/](https://fosf.pages.dev/).
