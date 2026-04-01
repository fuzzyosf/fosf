#!/usr/bin/env python3
"""
The :mod:`fosf.syntax` module handles the internal representation of fuzzy OSF logic
objects, including tags, features, sorts, constraints, clauses, terms, theories and fuzzy
taxonomies.
"""

from fosf.syntax.base import (Tag, Feature, Sort,
                              DisjunctiveSort, FrozenDisjunctiveSort)
from fosf.syntax.constraints import (Constraint, SortConstraint, FeatureConstraint,
                                     EqualityConstraint, Clause, RootedClause,
                                     SolvedClause, RootedSolvedClause)
from fosf.syntax.taxonomy import TagTaxonomy, SortTaxonomy, FuzzySortTaxonomy
from fosf.syntax.terms import Term, NormalTerm
