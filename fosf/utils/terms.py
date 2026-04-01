#!/usr/bin/env python3

from collections import defaultdict
from itertools import count
from typing import Iterator, overload

from fosf.syntax import Tag, Term, NormalTerm


@overload
def rename_apart(*terms: NormalTerm, base_tag="X") -> Iterator[NormalTerm]: ...


@overload
def rename_apart(*terms: Term, base_tag="X") -> Iterator[Term]: ...


def rename_apart(*terms: Term, base_tag="X") -> Iterator[Term]:
    tag_counter = count(0)
    def _new_tag(): return Tag(f"{base_tag}{next(tag_counter)}")

    @overload
    def visit(term: NormalTerm) -> NormalTerm: ...

    @overload
    def visit(term: Term) -> Term: ...

    def visit(term):
        X = renaming[term.X]
        if isinstance(term, NormalTerm):
            return NormalTerm(X, term.s,
                              {f: visit(t) for f, t in term.iter_subterms()})
        return Term(X, term.s, {f: [visit(t) for t in term.subterms[f]]
                                for f in term.subterms})

    for term in terms:
        renaming = defaultdict(_new_tag)
        yield visit(term)
