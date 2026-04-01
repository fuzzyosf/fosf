#!/usr/bin/env python3

from lark import Lark, Transformer

from fosf.syntax import Sort, FrozenDisjunctiveSort

BASE_GRAMMAR = "grammars/base_osf.lark"


class _BaseOSFTransformer(Transformer):

    def sort(self, tree):
        if isinstance(tree[0], (FrozenDisjunctiveSort)):
            return tree[0]
        return Sort(tree[0].value)

    def disjunctive_sort(self, tree):
        return FrozenDisjunctiveSort(*(t.value for t in tree))


class BaseOSFParser:

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers", BASE_GRAMMAR,
                                             parser="lalr", start="sort")
        self.transformer = _BaseOSFTransformer()

    def parse(self, expression: str, **kwargs) -> Sort:
        parse_tree = self.parser.parse(expression)
        return self.transformer.transform(parse_tree, **kwargs)
