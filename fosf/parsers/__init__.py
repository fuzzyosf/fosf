#!/usr/bin/env python3
"""
The :mod:`fosf.parsers` package provides high-level functions for parsing textual
representations of directed graphs, sort taxonomies, OSF terms, OSF clauses, and OSF theories.

Each function calls the corresponding parser class and returns an objcet from
:mod:`fosf.syntax`.
"""

import networkx as nx

from fosf.parsers.base import BaseOSFParser
from fosf.parsers.clause import OsfConstraintParser, NormalizationParser
from fosf.parsers.graph import GraphParser
from fosf.parsers.taxonomy import TaxonomyParser
from fosf.parsers.term import OsfTermParser, UnificationParser
from fosf.parsers.theory import OsfTheoryParser
from fosf.syntax.base import Tag
from fosf.syntax.constraints import Clause
from fosf.syntax.taxonomy import SortTaxonomy
from fosf.syntax.terms import Term
from fosf.syntax.theory import OsfTheory


def parse_graph(string: str) -> nx.DiGraph:
    """
    Parse a textual representation of a (weighted) DAG.

    Parameters
    ----------
    string: str
        The string representation of the (weighted) DAG.

    Returns
    -------
    :class:`networkx.DiGraph`
        The parsed weighted DAG.

    Note
    ----
    The accepted syntax is defined in :ref:`graph-grammar`.
    """
    return GraphParser().parse(string)


def parse_taxonomy(string: str) -> SortTaxonomy:
    """
    Parse a textual representation of a (fuzzy) sort taxonomy.

    Parameters
    ----------
    string: str
        The string representation of the (fuzzy) sort taxonomy.


    Returns
    -------
    SortTaxonomy
        The parsed sort taxonomy

    Note
    ----
    The accepted syntax is defined in :ref:`taxonomy-grammar`.
    """
    return TaxonomyParser().parse(string)


# TODO add overloads
def parse_term(string: str, default_tag: str = "X", create_using: type = None) -> Term:
    """
    Parse a textual representation of an OSF term.

    Parameters
    ----------
    string : str
        The string representation of the OSF term.
    default_tag : str, default="X"
        The default base identifier for a tag, used when an explicit tag is missing.
        Defaults to ``"X"``.
    create_using : type, optional
        Term class to construct the output. Should be one of
        :class:`~fosf.syntax.terms.Term` or :class:`~fosf.syntax.terms.NormalTerm`. If
        None, defaults to :class:`~fosf.syntax.terms.Term`

    Returns
    -------
    Term
        The parsed OSF term.

    Note
    ----
    The accepted OSF term syntax is defined in :ref:`term-grammar`.
    """
    return OsfTermParser().parse(string, default_tag, create_using)


def parse_clause(string: str, create_using: bool = None, root: Tag = None) -> Clause:
    """
    Parse a textual representation of an OSF clause.

    Parameters
    ----------
    string : str
        The string representation of the OSF clause.
    create_using : type, optional
        Clause class to construct the output. Should be one of
        :class:`~fosf.syntax.constraints.Clause`,
        :class:`~fosf.syntax.constraints.RootedClause`,
        :class:`~fosf.syntax.constraints.SolvedClause`, or
        :class:`~fosf.syntax.constraints.RootedSolvedClause`.
        If None, defaults to :class:`~fosf.syntax.constraints.Clause`
    root : Tag, optional
        Root tag. Required if ``create_using`` is
        :class:`~fosf.syntax.constraints.RootedClause` or
        :class:`~fosf.syntax.constraints.RootedSolvedClause`.

    Returns
    -------
    Clause
        The parsed OSF clause.

    Note
    ----
    The accepted OSF clause syntax is defined in :ref:`clause-grammar`.
    """
    return OsfConstraintParser().parse(string, create_using, root)


def parse_theory(string: str, ensure_closed=False) -> OsfTheory:
    """
    Parse a textual representation of an OSF theory.

    Parameters
    ----------
    string : str
        The string representation of the OSF theory.
    ensure_closed : bool, default=False
        If True, close the theory to ensure its order-consistency.

    Returns
    -------
    OsfTheory
        The parsed OSF theory.

    Note
    ----
    The accepted OSF theory syntax is defined in :ref:`theory-grammar`.
    """
    return OsfTheoryParser().parse(string, ensure_closed)
