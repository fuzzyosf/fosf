#!/usr/bin/env python3

from collections import defaultdict

from lark import Lark

from fosf.parsers.base import BaseOSFParser
from fosf.parsers.graph import _GraphTransformer
from fosf.syntax.base import Sort
from fosf.syntax.taxonomy import SortTaxonomy, FuzzySortTaxonomy


TAXONOMY_GRAMMAR = "grammars/taxonomy.lark"


class _TaxonomyTransformer(_GraphTransformer):

    def __init__(self):
        super().__init__()
        self._instances = defaultdict(dict)

    def baseinstance(self, tree):
        return tree[0].value, 1.0

    def fuzzyinstance(self, tree):
        degree = float(tree[0].value)
        instance = tree[1].value
        return instance, degree

    def instance(self, tree):
        return tree[0]

    def instances(self, tree):
        return tree

    def instance_dec(self, tree):
        instances = tree[0]
        sorts = tree[1]
        for instance, degree in instances:
            for sort in sorts:
                self._instances[instance][Sort(sort)] = degree

    def declarations(self, _) -> SortTaxonomy:
        if self.fuzzy:
            return FuzzySortTaxonomy(self.decs, instances=self._instances)
        return SortTaxonomy(self.decs, instances=self._instances)

    def transform(self, parse_tree):
        self.decs = []
        self.fuzzy = False
        return super().transform(parse_tree)


class TaxonomyParser(BaseOSFParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers",
                                             TAXONOMY_GRAMMAR, parser="lalr")
        self.transformer = _TaxonomyTransformer()

    def parse(self, expression: str) -> SortTaxonomy:
        parse_tree = self.parser.parse(expression)
        return self.transformer.transform(parse_tree)
