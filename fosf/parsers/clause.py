#!/usr/bin/env python3

from lark import Lark

from fosf.parsers.base import _BaseOSFTransformer, BaseOSFParser
from fosf.parsers.taxonomy import _TaxonomyTransformer
from fosf.syntax.base import Tag, Feature
from fosf.syntax.constraints import (Clause, RootedClause, SolvedClause,
                                     RootedSolvedClause, EqualityConstraint,
                                     SortConstraint, FeatureConstraint)


CONSTRAINT_GRAMMAR = "grammars/osf_constraints.lark"
CLAUSE_NORMALIZATION_GRAMMAR = "grammars/clause_normalization.lark"


class _OsfConstraintTransformer(_BaseOSFTransformer):

    def __init__(self):
        super().__init__()
        self.osf_clause = Clause()
        self.root = None

    def clause(self, _):
        return self.osf_clause

    def sort_constraint(self, tree):
        X = Tag(tree[0].value)
        s = tree[1]
        return self.osf_clause.add(SortConstraint(X, s))

    def feature_constraint(self, tree):
        X = Tag(tree[0].value)
        f = Feature(tree[1].value)
        Y = Tag(tree[2].value)
        return self.osf_clause.add(FeatureConstraint(X, f, Y))

    def equality_constraint(self, tree):
        X = Tag(tree[0].value)
        Y = Tag(tree[1].value)
        return self.osf_clause.add(EqualityConstraint(X, Y))

    def transform(self, parse_tree, create_using=None, root=None):
        if create_using is None:
            if root is None:
                self.osf_clause = Clause()
            else:
                self.osf_clause = RootedClause(root)
        elif root is None:
            if create_using in {RootedClause, RootedSolvedClause}:
                msg = ("A root must be specified for a clause"
                       f" of type {create_using}")
                raise TypeError(msg)
            self.osf_clause = create_using()
        else:
            if create_using in {Clause, SolvedClause}:
                msg = f"Clauses of type {create_using} do not require a root"
                raise TypeError(msg)
            if isinstance(root, str):
                root = Tag(root)
            self.osf_clause = create_using(root)
        return super().transform(parse_tree)


class OsfConstraintParser(BaseOSFParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers", CONSTRAINT_GRAMMAR,
                                             parser="lalr")
        self.transformer = _OsfConstraintTransformer()

    def parse(self, expression: str, create_using=None, root=None) -> Clause:
        parse_tree = self.parser.parse(expression)
        return self.transformer.transform(parse_tree, create_using, root)


class _NormalizationTransformer(_TaxonomyTransformer, _OsfConstraintTransformer):

    def program(self, tree):
        taxonomy = tree[0]
        clause = tree[1]
        return taxonomy, clause


class NormalizationParser(BaseOSFParser):

    def __init__(self):
        self.parser = Lark.open_from_package("fosf.parsers",
                                             CLAUSE_NORMALIZATION_GRAMMAR,
                                             parser="lalr")
        self.transformer = _NormalizationTransformer()
