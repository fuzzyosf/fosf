#!/usr/bin/env python3

from collections import defaultdict
from itertools import count
from typing import overload, Generator

from fosf.reasoning.clauses import ClauseNormalizer
from fosf.syntax.base import Tag
from fosf.syntax.constraints import SortConstraint, FeatureConstraint
from fosf.syntax.taxonomy import SortTaxonomy, FuzzySortTaxonomy
from fosf.syntax.terms import Term, NormalTerm
from fosf.syntax.theory import OsfTheory


@overload
def unify_terms(terms: list[Term], taxonomy: SortTaxonomy,
                theory: OsfTheory | None = None, rename_terms: bool = True,
                return_degree=False) -> NormalTerm: ...


@overload
def unify_terms(terms: list[Term], taxonomy: SortTaxonomy,
                theory: OsfTheory | None = None, rename_terms: bool = True,
                return_degree=True) -> tuple[NormalTerm, float]: ...


def unify_terms(terms: list[Term],
                taxonomy: SortTaxonomy,
                theory: OsfTheory | None = None,
                rename_terms: bool = True,
                return_degree: bool = False) -> NormalTerm | tuple[NormalTerm, float]:
    """
    Unify the OSF terms according to a sort taxonomy and optionally an OSF theory.

    Parameters
    ----------
    terms : list[Term]
        The OSF terms to unify.
    taxonomy : SortTaxonomy
        The background sort taxonomy for unification.
    theory : OsfTheory | None, default=None
        Optionally, an :class:`OsfTheory` to further normalize the unifier.
    rename_terms : bool, default=True
        If True, rename apart the terms to unify.
    return_degree : bool, default=False
        If True, return the subsumption degree of the unifier with respect to the input
        terms.

    Returns
    -------
    NormalTerm | tuple[NormalTerm, float]
        A NormalTerm if return_degree is False. Otherwise, a NormalTerm and and
        approximation degree.
    """
    tu = TermUnifier()
    return tu.unify(terms, taxonomy, theory, rename_terms, return_degree)


@overload
def normalize_term(term: Term, taxonomy: SortTaxonomy,
                   theory: OsfTheory | None = None,
                   return_degree: bool = False) -> NormalTerm: ...

@overload
def normalize_term(term: Term, taxonomy: SortTaxonomy,
                   theory: OsfTheory | None = None,
                   return_degree: bool = True) -> tuple[NormalTerm, float]: ...


def normalize_term(term: Term, taxonomy: SortTaxonomy,
                   theory: OsfTheory | None = None,
                   return_degree: bool = False) -> NormalTerm | tuple[NormalTerm, float]:
    """
    Normalize a single OSF term according to a sort taxonomy and optionally an OSF theory.

    Parameters
    ----------
    term : Term
    taxonomy : SortTaxonomy
    theory : OsfTheory | None, default=None
    return_degree : bool, default=False

    Returns
    -------
    NormalTerm | tuple[NormalTerm, float]
    """
    return unify_terms([term], taxonomy, theory=theory,
                       rename_terms=False, return_degree=return_degree)


class TermUnifier(ClauseNormalizer):
    """
    Class implementing OSF term unification :cite:`AitKaci1993b` and fuzzy OSF term
    unification :cite:`Milanese2024`.
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
        terms : list[Term]
            List of terms to unify.
        mappings : list[dict[Tag, Tag] | None] 
            List of tag renamings (or ``None``'s, if no renaming is applied), one for each
            term.
        """
        super().__init__()
        self.terms: list
        self.mappings: list

    def _init_structures(self, taxonomy, terms):
        self.mappings = []
        self.terms = terms

        # For clause normalization
        self.taxonomy = taxonomy
        self.rep_to_code = defaultdict(lambda: self.taxonomy.top_code)
        self.rep_to_feats = defaultdict(lambda: dict())

        # For union-find
        self._parents = {}
        self._indices = {}
        self._cost = defaultdict(lambda: 0)

    def normalize(self, term: Term,
                  taxonomy: SortTaxonomy,
                  theory: OsfTheory | None = None,
                  return_degree: bool = False) -> NormalTerm | tuple[NormalTerm, float]:
        """
        Normalize a single OSF term according to a sort taxonomy and optionally an OSF theory.

        Parameters
        ----------
        term : Term
        taxonomy : SortTaxonomy
        theory : OsfTheory | None, default=None
        return_degree : bool, default=False

        Returns
        -------
        NormalTerm | tuple[NormalTerm, float]
            A NormalTerm if return_degree is False. Otherwise, a NormalTerm and and
            approximation degree.
        """
        return self.unify([term], taxonomy, theory,
                          rename_terms=False,
                          return_degree=return_degree)

    @overload
    def unify(self, terms: list[Term], taxonomy: SortTaxonomy,
              theory: OsfTheory | None = None, rename_terms=True,
              return_degree=False) -> NormalTerm: ...

    @overload
    def unify(self, terms: list[Term], taxonomy: SortTaxonomy,
              theory: OsfTheory | None = None, rename_terms=True,
              return_degree=True) -> tuple[NormalTerm, float]: ...

    def unify(self, terms: list[Term],
              taxonomy: SortTaxonomy,
              theory: OsfTheory = None,
              rename_terms=True,
              return_degree=False) -> NormalTerm | tuple[NormalTerm, float]:
        """
        Compute the unification of a list of OSF Terms.

        This method attempts to unify the provided terms according to the given (fuzzy)
        taxonomy and, optionally, an OSF theory. Tags in the inpyt terms can be renamed
        to avoid clashes. Optionally, the fuzzy unification degree can also be returned.

        Parameters
        ----------
        terms : list[Term]
            The terms to unify.
        taxonomy : SortTaxonomy
            The (fuzzy) sort taxonomy used to compute greatest lower bounds of sorts
            during unification.
        theory : OsfTheory, optional
            An OSF theory used to normalize the resulting unifier according to its constraints.
        rename_terms : bool, default=True
            If True, rename tags in the input terms to avoid clashes.
        return_degree : bool, default=False
            If True, also return the fuzzy unification degree.

        Returns
        -------
        NormalTerm
            The normalized term resulting from unification.
        tuple[NormalTerm, float], optional
            If `return_degree` is True, a tuple of the normalized term and the fuzzy
            unification degree.
        """

        self._init_structures(taxonomy, terms)

        # If rename_terms=False, the rename function will be the identity
        def rename(x): return x
        # Otherwise, the following function will be used to generate new tags
        tag_counter = count(0)
        def _new_tag(): return Tag(f"X{next(tag_counter)}")

        consistent = True
        # This variable will store the root of the previous term in the iteration
        previous_root = None
        # Start by processing each term's constraints
        for term in terms:
            # Iterate over each term, possibly renaming them
            if rename_terms:
                # Initialize a new renaming dict for each term to avoid clashes
                # The tag counter is maintained, so each term has new tags
                tag_map = defaultdict(_new_tag)
                self.mappings.append(tag_map)
                def rename(x): return tag_map[x]
            else:
                self.mappings.append(None)

            this_root = rename(term.X)
            # Add the root tag to the UF
            self._add_tag(this_root)
            if previous_root:
                # Identify the current root and the one from the previous term
                consistent = self._process_equality_constraint(previous_root, this_root)
                if not consistent:
                    return self._return_inconsistent_term(return_degree=return_degree)
            # Store the root for the next term
            previous_root = this_root

            # Process the constraint directly generated by the terms
            for c in term.generate_constraints():
                if isinstance(c, SortConstraint):
                    # Possibly rename the tag and add it to the UF
                    X = rename(c.X)
                    self._add_tag(X)
                    # Process the constraint and check consistency
                    consistent = self._process_sort_constraint(X, c.s)
                elif isinstance(c, FeatureConstraint):
                    # Possibly rename the tags and add them to the UF
                    X, Y = rename(c.X), rename(c.Y)
                    self._add_tag(X)
                    self._add_tag(Y)
                    # Process the constraint
                    consistent = self._process_feature_constraint(X, c.f, Y)
                if not consistent:
                    return self._return_inconsistent_term(return_degree)

        # Get the root of the last term
        # "rename" here is the one used for the last term in the iteration
        root = rename(terms[-1].X)

        # Build normal term
        normal_term = self._build_output(root)
        degree = 1.0

        if return_degree and isinstance(self.taxonomy, FuzzySortTaxonomy):
            degree = self._subsumption_degree()

        if theory:
            from fosf.reasoning.theory import TheoryTermNormalizer
            ttn = TheoryTermNormalizer()
            normal_term = ttn.normalize(normal_term, theory, normalize_first=False)
            if return_degree:
                theory_degree = ttn._subsumption_degree()
                return normal_term, min(degree, theory_degree)
            return normal_term

        # Output
        if return_degree:
            return normal_term, degree
        return normal_term

    def _build_output(self, root: Tag) -> NormalTerm:
        def visit(tag):
            rep = self.deref_tag(tag)
            if rep in seen:
                return NormalTerm(rep)
            seen.add(rep)
            sort = self.taxonomy._decode(self.rep_to_code[rep])
            subterms = {f: visit(other)
                        for f, other in self.rep_to_feats[rep].items()}
            return NormalTerm(rep, sort, subterms)
        seen = set()
        return visit(root)

    def _return_inconsistent_term(self, return_degree=False):
        FAIL_TAG = Tag("_FAIL")
        if return_degree:
            return NormalTerm(FAIL_TAG, self.taxonomy.bot), 1
        return NormalTerm(FAIL_TAG, self.taxonomy.bot)

    def homomorphisms(self) -> Generator[dict[Tag, Tag], None, None]:
        """
        Generate mappings from the tags of each input term to the tags of their unifier.

        Each mapping witnesses the subsumption of the unifier with respect to the
        respective input OSF term.

        Note
        ----
        This method should be called *after* unifying a few OSF terms in order to obtain the
        tag mappings.
        """
        def rename(x): return x
        for term, mapping in zip(self.terms, self.mappings):
            if mapping:
                def rename(x): return mapping[x]
            homomorphism = {}
            for tag in term.tags():
                solved_tag = self.deref_tag(rename(tag))
                homomorphism[tag] = solved_tag
            yield homomorphism

    def _subsumption_pairs(self):
        def rename(x): return x
        for term, mapping in zip(self.terms, self.mappings):
            if mapping:
                def rename(x): return mapping[x]
            subsumption = defaultdict(set)
            for subterm in term.dfs():
                if subterm.s is None:
                    continue
                tag = subterm.X
                sort = subterm.s
                solved_tag = self.deref_tag(rename(tag))
                solved_sort = self.taxonomy._decode(self.rep_to_code[solved_tag])
                if sort == solved_sort:
                    continue
                subsumption[solved_sort].add(sort)
            yield subsumption

    def _subsumption_degree(self) -> float:
        alpha = 1.0
        for subsumption in self._subsumption_pairs():
            for solved_sort, sorts in subsumption.items():
                degree = self.taxonomy.degree(solved_sort, sorts)
                alpha = min(alpha, min(degree.values()))
        return alpha
