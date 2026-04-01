#!/usr/bin/env python3

from collections import defaultdict

import networkx as nx

from fosf.syntax.constraints import (SortConstraint, EqualityConstraint,
                                     Clause, SolvedClause, RootedClause)
from fosf.syntax.terms import Term


def osf_term_to_nx(term: Term):
    return osf_clause_to_nx(term.to_clause())


def osf_clause_to_nx(clause: Clause):
    if isinstance(clause, SolvedClause):
        return __solved_clause_to_nx(clause)

    def _tag_to_sort():
        tag_to_sort = defaultdict(set)
        for c in clause.constraints:
            if isinstance(c, SortConstraint):
                tag_to_sort[c.X].add(c.s)
        return tag_to_sort

    def _eq():
        eq = [(c.X, c.Y)
              for c in clause.constraints if isinstance(c, EqualityConstraint)]
        return eq

    tag_to_sort = _tag_to_sort()
    eq = _eq()
    g = nx.MultiDiGraph()

    for tag in clause.tags:
        sorts = tag_to_sort[tag]
        if sorts:
            g.add_node(
                tag, label=f'{tag} : {"+".join(str(sort) for sort in sorts)}')
        else:
            g.add_node(tag, label=f'{tag}')
    if isinstance(clause, RootedClause):
        sorts = tag_to_sort[clause.root]
        sort_label = "+".join(str(sort) for sort in sorts)
        if sorts:
            g.add_node(clause.root,
                       label=f'{clause.root} : {sort_label}',
                       peripheries=2)
        else:
            g.add_node(clause.root, label=f'{clause.root}', peripheries=2)
    for tag, features in clause.tag_to_feats.items():
        for feat, values in features.items():
            for val in values:
                g.add_edge(tag, val, label=feat)
    for x, y in eq:
        g.add_edge(x, y, label="=", style="dashed", dir="none")
    return g


def __solved_clause_to_nx(clause: SolvedClause):
    g = nx.MultiDiGraph()
    for tag, sort in clause.tag_to_sort.items():
        if sort:
            g.add_node(tag, label=f'{tag} : {sort}')
        else:
            g.add_node(tag, label=f'{tag}')
    if isinstance(clause, RootedClause):
        sort = clause.tag_to_sort[clause.root]
        if sort:
            g.add_node(clause.root, label=f'{clause.root} : {sort}',
                       peripheries=2)
        else:
            g.add_node(clause.root, label=f'{clause.root}', peripheries=2)
    for tag, features in clause.tag_to_feats.items():
        for feat, other in features.items():
            g.add_edge(tag, other, label=feat)
    return g
