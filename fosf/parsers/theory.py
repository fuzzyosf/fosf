#!/usr/bin/env python3

from lark import Lark

from fosf.parsers.taxonomy import TaxonomyParser, _TaxonomyTransformer
from fosf.syntax.base import Sort, Tag, Feature
from fosf.syntax.terms import Term, NormalTerm
from fosf.syntax.theory import TheoryTag, OsfTheory

THEORY_GRAMMAR = "grammars/osf_theory.lark"


class _OsfTheoryTransformer(_TaxonomyTransformer):

    def __init__(self):
        super().__init__()
        self.definitions: dict[Sort, Term] = {}
        self.tags: dict[Tag, TheoryTag] = {}

    def theory(self, tree):
        return tree[0], self.definitions, self.tags

    def definition(self, tree):
        sort = Sort(tree[0].value)
        term = tree[1]
        self.definitions[sort] = term

    def term(self, tree):
        tag = Tag(tree[0].value)
        sort = Sort(tree[1].value)
        if len(tree) <= 2:
            self.tags[tag] = TheoryTag(tag, sort)
            return NormalTerm(tag, sort)
        pairs = tree[2]
        features = {}
        subterms = {}
        for f, term in pairs:
            subterms[f] = term
            features[f] = term.X
        theory_tag = TheoryTag(tag, sort, features)
        self.tags[tag] = theory_tag
        return NormalTerm(tag, sort, subterms)

    def unsorted_term(self, tree):
        tag = Tag(tree[0].value)
        if len(tree) > 1:
            return NormalTerm(tag, s=None, subterms=tree[1])
        return NormalTerm(tag)

    def subterms(self, tree):
        return tree

    def subterm(self, tree):
        return Feature(tree[0]), tree[1]

    def transform(self, parse_tree):
        self.definitions = {}
        self.tags = {}
        return super().transform(parse_tree)


class OsfTheoryParser(TaxonomyParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers", THEORY_GRAMMAR)
        self.transformer = _OsfTheoryTransformer()

    def parse(self, expression: str, ensure_closed=False) -> OsfTheory:
        parse_tree = self.parser.parse(expression)
        return OsfTheory(*self.transformer.transform(parse_tree),
                         ensure_closed=ensure_closed)
