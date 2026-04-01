#!/usr/bin/env python3

from collections import defaultdict
from typing import overload

from fosf.syntax.base import Feature, Tag
from fosf.syntax.constraints import (Constraint, Clause, FeatureConstraint,
                                     EqualityConstraint, SortConstraint,
                                     RootedClause, RootedSolvedClause, SolvedClause)

from fosf.syntax.taxonomy import SortTaxonomy


@overload
def normalize_clause(clause: RootedClause,
                     taxonomy: SortTaxonomy) -> RootedSolvedClause: ...


@overload
def normalize_clause(clause: Clause, taxonomy: SortTaxonomy) -> SolvedClause: ...


def normalize_clause(clause: Clause, taxonomy: SortTaxonomy) -> SolvedClause:
    """
    Normalize a clause according to a sort taxonomy.

    Parameters
    ----------
    clause : Clause
    taxonomy : SortTaxonomy

    Returns
    -------
    SolvedClause
    """
    return ClauseNormalizer().normalize(clause, taxonomy)


class ClauseNormalizer:
    """
    Class implementing the OSF constraint normalization rules of :cite:`AitKaci1993b`.
    """

    def __init__(self):
        """
        Attributes
        ----------
        taxonomy : SortTaxonomy
            The taxonomy used for greatest lower bound computation on sorts.
        self.rep_to_code: dict[Tag, int]
            A mapping from tags to an integer bitcode
        self.rep_to_feats: dict[Tag, dict[Feature, Tag]]
            A mapping from tags to feature->tag maps.
        """
        self.taxonomy: SortTaxonomy
        # X : s -> self.rep_to_code[X] = code(s)
        self.rep_to_code: dict[Tag, int]
        # X.f = Y -> self.rep_to_feats[X][f] = Y
        self.rep_to_feats: dict[Tag, dict[Feature, Tag]]

        # For union-find
        self._parents: dict
        self._indices: dict
        self._cost: dict

    def _init_structures(self, clause, taxonomy):
        self.taxonomy = taxonomy
        self.rep_to_code = defaultdict(lambda: self.taxonomy.top_code)
        self.rep_to_feats = defaultdict(lambda: dict())

        # For union-find
        self._parents = {}
        self._indices = {}
        for X in clause.tags:
            self._add_tag(X)
        self._cost = defaultdict(lambda: 0)

    # Union-find methods
    def _add_tag(self, X: Tag):
        if X in self._indices:
            return
        self._parents[X] = X
        self._indices[X] = len(self._indices)

    def deref_tag(self, X: Tag) -> Tag:
        if X not in self._indices:
            raise KeyError(X)
        parents = self._parents
        while self._indices[X] != self._indices[parents[X]]:
            parents[X] = parents[parents[X]]
            X = parents[X]
        return X

    def _merge_tags(self, X: Tag, Y: Tag) -> tuple[bool, Tag, Tag]:
        X, Y = self.deref_tag(X), self.deref_tag(Y)
        if self._indices[X] == self._indices[Y]:
            return False, X, Y
        # Merge Y into X or X into Y depending on cost
        if (self._cost[X], self._indices[Y]) < (self._cost[Y], self._indices[X]):
            X, Y = Y, X
        self._parents[Y] = X
        return True, X, Y

    def _connected(self, X: Tag, Y: Tag) -> bool:
        return self._indices[self.deref_tag(X)] == self._indices[self.deref_tag(Y)]

    # Clause normalization methods
    def __call__(self, clause, taxonomy):
        return self.normalize(clause, taxonomy)

    @overload
    def normalize(self, clause: RootedClause,
                  taxonomy: SortTaxonomy) -> RootedSolvedClause: ...

    @overload
    def normalize(self, clause: Clause,
                  taxonomy: SortTaxonomy) -> SolvedClause: ...

    def normalize(self, clause: Clause, taxonomy: SortTaxonomy) -> SolvedClause:
        """
        Normalize a clause according to a sort taxonomy.

        Parameters
        ----------
        clause : Clause
        taxonomy : SortTaxonomy

        Returns
        -------
        SolvedClause
        """
        self._init_structures(clause, taxonomy)

        for c in clause.constraints:
            consistent = self._process_constraint(c)
            if not consistent:
                FAIL_TAG = Tag("_FAIL")
                bot = self.taxonomy.bot
                s = SortConstraint(FAIL_TAG, bot)
                return RootedSolvedClause(FAIL_TAG, s)

        # Build the normalized clause
        if isinstance(clause, RootedClause):
            return self._build_output(clause.root)
        return self._build_output()

    def _process_constraint(self, c: Constraint):
        if isinstance(c, SortConstraint):
            return self._process_sort_constraint(c.X, c.s)
        if isinstance(c, FeatureConstraint):
            return self._process_feature_constraint(c.X, c.f, c.Y)
        if isinstance(c, EqualityConstraint):
            return self._process_equality_constraint(c.X, c.Y)

    def _process_sort_constraint(self, X, s):
        rep = self.deref_tag(X)
        self.rep_to_code[rep] &= self.taxonomy.code(s)
        return self._consistency_check(rep)

    def _process_feature_constraint(self, X, f, Y):
        X, Y = self.deref_tag(X), self.deref_tag(Y)
        if f not in self.rep_to_feats[X]:
            self.rep_to_feats[X][f] = Y
            self._cost[X] += 1
            return True
        Z = self.deref_tag(self.rep_to_feats[X][f])
        if Y != Z:
            return self._process_equality_constraint(Y, Z)
        return True

    def _process_equality_constraint(self, X, Y):
        stack = [(X, Y)]

        while stack:
            X, Y = stack.pop()

            merged, X, Y = self._merge_tags(X, Y)
            if not merged:
                # Tags are already merged
                continue

            # Merge sorts
            self.rep_to_code[X] &= self.rep_to_code[Y]
            if not self._consistency_check(X):
                return False

            # Merge features
            for f, Z in self.rep_to_feats[Y].items():
                Z = self.deref_tag(Z)
                if f not in self.rep_to_feats[X]:
                    self.rep_to_feats[X][f] = Z
                    self._cost[X] += 1
                else:
                    stack.append((self.rep_to_feats[X][f], Z))
        return True

    def _consistency_check(self, tag):
        return self.rep_to_code[tag] != self.taxonomy.bot_code

    @overload
    def _build_output(self) -> SolvedClause: ...

    @overload
    def _build_output(self, root: Tag) -> RootedSolvedClause: ...

    def _build_output(self, root=None) -> SolvedClause:
        if root is None:
            clause = SolvedClause()
        else:
            clause = RootedSolvedClause(root)
        seen = set()
        for tag in self._indices:
            if (rep := self.deref_tag(tag)) in seen:
                continue
            seen.add(rep)
            for feat, val in self.rep_to_feats[rep].items():
                clause.add(FeatureConstraint(rep, feat, self.deref_tag(val)))
            sort = self.taxonomy._decode(self.rep_to_code[rep])
            clause.add(SortConstraint(rep, sort))
        return clause
