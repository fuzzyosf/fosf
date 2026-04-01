#!/usr/bin/env python3

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fosf.syntax.constraints import RootedClause, RootedSolvedClause

from fosf.syntax import Sort, Tag, Feature, DisjunctiveSort


class Term:
    """
    Represent an OSF term X:s(f1 -> t1, ..., fn -> tn).
    """

    def __init__(self, X: Tag, s: Sort | None = None,
                 subterms: dict[Feature, list[Term]] | None = None):
        """
        Parameters
        ----------
        X : Tag
            The root tag of the term.
        s : Sort  | None
            The root sort of the term. If None, when the OSF term is processes, it is assumed to be
            the top sort in a given Sort taxonomy.
        subterms: dict[Feature, list[Term]] | None
            The subterms of the OSF term. In a non-normal OSF term, the same feature may
            point to different subterms.

        Attributes
        ----------
        X : Tag
            The root tag of the term.
        s : Sort
            The root sort of the term.
        subterms : dict[Feature, list[Term]]
            Possibly empty dict mapping each feature to a list of subterms.
        """
        self.X = X
        self.s = s
        self.subterms = defaultdict(list) if subterms is None else subterms

    def dfs(self):
        """
        Generate subterms depth-first.
        """
        stack = [self]
        while stack:
            yield (term := stack.pop())
            for _, subterm in term.iter_subterms():
                stack.append(subterm)

    def bfs(self):
        """
        Generate subterms breadth-first.
        """
        queue = deque([self])
        while queue:
            yield (term := queue.popleft())
            for _, subterm in term.iter_subterms():
                queue.append(subterm)

    def to_clause(self) -> RootedClause:
        """
        Transform the OSF term into an equivalent rooted clause.

        Returns
        -------
        RootedClause
            The rooted clause corresponding to the OSF term.
        """
        from fosf.syntax.constraints import RootedClause
        clause = RootedClause(self.X)
        for c in self.generate_constraints():
            clause.add(c)
        return clause

    def generate_constraints(self):
        """
        Generate the OSF constraints expressed by the OSF term.
        """
        from fosf.syntax.constraints import SortConstraint, FeatureConstraint
        if self.s is not None:
            yield SortConstraint(self.X, self.s)
        for term in self.dfs():
            for f, subterm in term.iter_subterms():
                yield FeatureConstraint(term.X, f, subterm.X)
                if subterm.s is not None:
                    yield SortConstraint(subterm.X, subterm.s)

    def tags(self) -> set[Tag]:
        """
        Return the set of :class:`Tag`'s appearing in the OSF term.
        """
        out = set()
        for term in self.dfs():
            out.add(term.X)
        return out

    def sorts(self) -> set[Sort]:
        """
        Return the set of :class:`Sort`'s appearing in the OSF term.
        """
        out = set()
        for term in self.dfs():
            if term.s is not None:
                if isinstance(term.s, DisjunctiveSort):
                    out.add(term.s.freeze())
                else:
                    out.add(term.s)
        return out

    def pretty_print(self, spaces=0, feature=""):
        "Pretty-print the OSF Term."
        out = " " * spaces
        if feature:
            out += f"{feature} -> "
        out += f"{self.X}"
        if self.s is not None:
            out += f" : {self.s}"
        if self.subterms:
            out += "("
        print(out)
        for feature, term in self.iter_subterms():
            term.pretty_print(spaces+4, feature)
        if self.subterms:
            print(" " * spaces + ")")

    def __repr__(self):
        out = f"{self.__class__.__name__}(X={self.X!r}"
        if self.s is not None:
            out += f", s={self.s!r}"
        if self.subterms:
            out += f", subterms={dict(self.subterms)!r}"
        out += ")"
        return out

    def __str__(self):
        out = f"{self.X}"
        if self.s is not None:
            out += f" : {self.s}"
        if self.subterms:
            pairs = [f"{f} -> {str(subterm)}"
                     for f, subterm in self.iter_subterms()]
            out += f"({', '.join(pairs)})"
        return out

    def __getitem__(self, key: Feature):
        return self.subterms.get(key, None)

    def __eq__(self, other: Term):
        return (self.X == other.X and self.s == other.s and
                self.subterms == other.subterms)

    def iter_subterms(self):
        """
        Generate (feature, subterm) pairs.
        """
        for feature, subterms in self.subterms.items():
            for subterm in subterms:
                yield (feature, subterm)

    def tag_to_sort(self) -> dict[Tag, set[Sort]]:
        """
        Return a mapping from each :class:`Tag` to its set of :class:`Sort`'s.
        """
        out = defaultdict(set)
        for term in self.dfs():
            if term.s:
                out[term.X].add(term.s)
        return out


class NormalTerm(Term):
    """
    Represent an OSF term in normal form.
    """

    def __init__(self, X: Tag, s: Sort | None = None, subterms: dict[Feature, NormalTerm]
                 | None= None):
        """
        Parameters
        ----------
        X : Tag
            The root tag.
        s : Sort  | None
            The root sort. If None, when the OSF term is processes, it is assumed to be
            the top sort in a given Sort taxonomy.
        subterms: dict[Feature, NormalTerm] | None
            The subterms of the OSF term. In a normal OSF term, each feature may point to
            at most one (normal) subterm.

        Attributes
        ----------
        X : Tag
            The root tag of the term.
        s : Sort
            The root sort of the term.
        subterms : dict[Feature, Term]
            Possibly empty dict mapping each feature to a unique subterm.
        """
        self.X = X
        self.s = s
        self.subterms = {} if subterms is None else subterms

    def to_clause(self) -> RootedSolvedClause:
        """
        Transform the OSF term into an equivalent rooted solved clause.

        Returns
        -------
        RootedSolvedClause
            The rooted solved clause corresponding to the OSF term.
        """
        from fosf.syntax.constraints import (RootedSolvedClause, SortConstraint,
                                             FeatureConstraint)
        clause = RootedSolvedClause(self.X)
        for term in self.dfs():
            if term.s is not None:
                clause.add(SortConstraint(term.X, term.s))
            for f, subterm in term.subterms.items():
                clause.add(FeatureConstraint(term.X, f, subterm.X))
        return clause

    def equivalent_to(self, other: NormalTerm) -> bool:
        """
        Return whether this Term is equivalent to another normal term.
        """
        this_clause = self.to_clause()
        other_clause = other.to_clause()
        return this_clause.equivalent_to(other_clause)

    def iter_subterms(self):
        """
        Generate (feature, subterm) pairs.
        """
        yield from self.subterms.items()

    def tag_to_sort(self) -> dict[Tag, Sort]:
        """
        Return a mapping from each :class:`Tag` to its :class:`Sort`.
        """
        out = dict()
        for term in self.dfs():
            if term.s:
                out[term.X] = term.s
        return out
