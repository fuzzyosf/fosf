#!/usr/bin/env python3

from collections import defaultdict
from typing import overload

from lark import Lark

from fosf.parsers.base import _BaseOSFTransformer, BaseOSFParser
from fosf.parsers.taxonomy import _TaxonomyTransformer
from fosf.syntax.base import Tag, Feature
from fosf.syntax.taxonomy import SortTaxonomy
from fosf.syntax.terms import Term, NormalTerm


TERM_GRAMMAR = "grammars/osf_term.lark"
TERM_UNIFICATION_GRAMMAR = "grammars/term_unification.lark"


class _OsfTermTransformer(_BaseOSFTransformer):

    def __init__(self):
        super().__init__()
        self.tags = set()

    def subterm(self, tree):
        "Process a subterm: FEATURE -> term."
        feat = Feature(tree[0].value)
        term = tree[1]
        return (feat, term)

    def subterms(self, tree):
        "Process subterms: '(' subterm (',' subterm)* ')'."
        d = defaultdict(list)
        for k, v in tree:
            d[k].append(v)
        return d

    def untagged_term(self, tree):
        """Process an untagged term: sort (subterms)?."""
        sort = tree[0]
        if len(tree) > 1:
            return {"tag": None, "sort": sort, "subterms": tree[1]}
        return {"tag": None, "sort": sort, "subterms": None}

    def unsorted_term(self, tree):
        """Process an unsorted term: TAG (subterms)?."""
        tag = Tag(tree[0].value)
        self.tags.add(tag)
        if len(tree) > 1:
            return {"tag": tag, "sort": None, "subterms": tree[1]}
        return {"tag": tag, "sort": None, "subterms": None}

    def term(self, tree):
        """Process a tagged term: TAG (":" untagged_term)."""
        tag = Tag(tree[0].value)
        sort = tree[1]
        self.tags.add(tag)
        if len(tree) > 2:
            return {"tag": tag, "sort": sort, "subterms": tree[2]}
        return {"tag": tag, "sort": sort, "subterms": None}

    def transform(self, parse_tree):
        self.tags = set()
        return super().transform(parse_tree)


class OsfTermParser(BaseOSFParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers",
                                             TERM_GRAMMAR, parser="lalr")
        self.transformer = _OsfTermTransformer()
        self.term_constructor = Term
        self.tags = set()
        self.tag_counter = 0

    def _dict_to_term(self, term_dict, default_tag):
        def visit(term):
            sort = term["sort"]
            tag = self.__find_tag(default_tag) \
                if term["tag"] is None else term["tag"]
            if self.term_constructor == NormalTerm:
                if term['subterms'] is None:
                    subterms = {}
                else:
                    subterms = {k: visit(v[0])
                                for k, v in term['subterms'].items()}
            else:
                if term['subterms'] is None:
                    subterms = defaultdict(list)
                else:
                    subterms = defaultdict(list)
                    for feature, values in term["subterms"].items():
                        for value in values:
                            subterms[feature].append(visit(value))
            return self.term_constructor(tag, sort, subterms)
        return visit(term_dict)

    def __find_tag(self, default_tag):
        while (tag := Tag(f"{default_tag}{self.tag_counter}")) in self.tags:
            self.tag_counter += 1
        self.tags.add(tag)
        return tag

    @overload
    def parse(self, expression: str, default_tag="X",
              create_using=NormalTerm) -> NormalTerm: ...

    @overload
    def parse(self, expression: str, default_tag="X",
              create_using=Term) -> Term: ...

    def parse(self, expression: str, default_tag="X", create_using=None) -> Term:
        parse_tree = self.parser.parse(expression)
        if create_using is None:
            self.term_constructor = Term
        else:
            self.term_constructor = create_using
        term_dict = self.transformer.transform(parse_tree)
        self.tags = self.transformer.tags
        self.tag_counter = 0
        return self._dict_to_term(term_dict, default_tag)


class _UnificationTransformer(_TaxonomyTransformer, _OsfTermTransformer):

    def program(self, tree):
        return tree[0], tree[1], tree[2]


class UnificationParser(OsfTermParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers", TERM_UNIFICATION_GRAMMAR)
        self.transformer = _UnificationTransformer()
        self.tag_counter = 0
        self.term_constructor = Term
        self.tags = set()

    @overload
    def parse(self, expression: str, default_tag="X",
              term_constructor=NormalTerm) -> tuple[SortTaxonomy, NormalTerm, NormalTerm]: ...

    @overload
    def parse(self, expression: str, default_tag="X",
              term_constructor=Term) -> tuple[SortTaxonomy, Term, Term]: ...

    def parse(self, expression: str, default_tag="X", term_constructor=Term) -> tuple[SortTaxonomy, Term, Term]:
        parse_tree = self.parser.parse(expression)
        taxonomy, dict1, dict2 = self.transformer.transform(parse_tree)
        self.tags = self.transformer.tags
        self.tag_counter = 0
        self.term_constructor = term_constructor
        term1 = self._dict_to_term(dict1, default_tag)
        term2 = self._dict_to_term(dict2, default_tag)
        return taxonomy, term1, term2
