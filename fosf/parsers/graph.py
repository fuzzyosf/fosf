#!/usr/bin/env python3

from lark import Lark
import networkx as nx

from fosf.parsers.base import BaseOSFParser, _BaseOSFTransformer


GRAPH_GRAMMAR = "grammars/graph.lark"


class _GraphTransformer(_BaseOSFTransformer):

    def __init__(self):
        super().__init__()
        self.decs = []
        self.fuzzy = False

    def sorts(self, tree):
        return [t.value for t in tree]

    def fuzzysort(self, tree):
        "Handle a sort with an approximation degree."
        if len(tree) > 1:
            weight = float(tree[1].value)
            if weight < 1:
                self.fuzzy = True
            return (tree[0].value, weight)
        return (tree[0].value, 1.0)

    def fuzzysorts(self, tree):
        "Handle a list of sorts associated with an approximation degree."
        return tree

    def declaration(self, tree):
        self.decs.extend([(subsort, supersort[0], supersort[1])
                          for subsort in tree[0]
                          for supersort in tree[1]])

    def declarations(self, _) -> nx.DiGraph:
        g = nx.DiGraph()
        for u, v, w in self.decs:
            g.add_edge(u, v, weight=w)
        return g

    def transform(self, parse_tree):
        self.decs = []
        return super().transform(parse_tree)


class GraphParser(BaseOSFParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers",
                                             GRAPH_GRAMMAR, parser="lalr")
        self.transformer = _GraphTransformer()

    def parse(self, expression: str) -> nx.DiGraph:
        parse_tree = self.parser.parse(expression)
        return self.transformer.transform(parse_tree)
