#!/usr/bin/env python3

from __future__ import annotations

from abc import ABC
from collections import defaultdict
from itertools import count
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fosf.syntax.terms import NormalTerm

from fosf.syntax.base import Tag, Feature, Sort, DisjunctiveSort
from fosf.syntax.taxonomy import SortTaxonomy


class Constraint(ABC):
    """
    Abstract base class for an OSF constraint.

    Attributes
    ----------
    tags : set[Tag]
        The set of tags appearing in the constraint.
    """
    tags: set[Tag] = set()


class SortConstraint(Constraint):
    """
    Represent a sort constraint  ``X : s``.
    """

    def __init__(self, X: Tag, s: Sort):
        """
        Parameters
        ----------
        s : Sort
        X : Tag

        Attributes
        ----------
        tags : set[Tag]
            The set of tags appearing in the constraint.
        """
        self.X = X
        self.s = s
        self.tags: set[Tag] = {self.X}

    def __repr__(self):
        return f"SortConstraint({repr(self.X)}, {repr(self.s)})"

    def __str__(self):
        return f"{self.X} : {self.s}"

    def __hash__(self):
        if isinstance(self.s, DisjunctiveSort):
            # Ensure sort is hashable
            self.s = self.s.freeze()
        return hash((self.X, self.s))

    def __eq__(self, other):
        if not isinstance(other, SortConstraint):
            return False
        return self.X == other.X and self.s == other.s


class FeatureConstraint(Constraint):
    """
    Represent a feature constraint ``X.f = Y``.
    """

    def __init__(self, X: Tag, f: Feature, Y: Tag):
        """
        Parameters
        ----------
        X : Tag
        f : Feature
        Y : Tag

        Attributes
        ----------
        tags : set[Tag]
            The set of tags appearing in the constraint.
        """
        self.X: Tag = X
        self.f: Feature = f
        self.Y: Tag = Y
        self.tags: set[Tag] = {self.X, self.Y}

    def __repr__(self):
        return f"FeatureConstraint({repr(self.X)}, {repr(self.f)}, {repr(self.Y)})"

    def __str__(self):
        return f"{self.X}.{self.f} = {self.Y}"

    def __hash__(self):
        return hash((self.X, self.f, self.Y))

    def __eq__(self, other):
        if not isinstance(other, FeatureConstraint):
            return False
        return self.X == other.X and self.f == other.f and self.Y == other.Y


class EqualityConstraint(Constraint):
    """
    Represent an equality constraint ``X = Y``.
    """

    def __init__(self, X: Tag, Y: Tag):
        """
        Parameters
        ----------
        X : Tag
        Y : Tag

        Attributes
        ----------
        tags : set[Tag]
            The set of tags appearing in the constraint.
        """
        self.X: Tag = X
        self.Y: Tag = Y
        self.tags: set[Tag] = {self.X, self.Y}

    def __repr__(self):
        return f"EqualityConstraint({repr(self.X)}, {repr(self.Y)})"

    def __str__(self):
        return f"{self.X} = {self.Y}"

    def __hash__(self):
        return hash((self.X, self.Y))

    def __eq__(self, other):
        if not isinstance(other, EqualityConstraint):
            return False
        return self.tags == other.tags


class Clause:
    """
    Represent an OSF clause, a conjunctive set of OSF constraints.
    """

    def __init__(self, *constraints: Constraint):
        """
        Parameters
        ----------
        *constraints : Constraint
            The initial constraints of the clause.

        Attributes
        ----------
        constraints : set[Constraint]
            The constraints of the clause.
        tags : set[Tag]
            The set of tags appearing in the constraint.
        tag_to_feats : dict[Tag, dict[Feature, set[Tag]]]
            A mapping from tags to a feature->tags map.
        """
        self.constraints: set[Constraint] = set()
        self.tags: set[Tag] = set()
        self.tag_to_feats: dict[Tag, dict[Feature, set[Tag]]] = \
                defaultdict(lambda: defaultdict(set))
        self.add(*constraints)

    def add(self, *constraints: Constraint):
        """
        Add constraints to the clause.
        """
        for c in constraints:
            if c in self.constraints:
                continue
            self.constraints.add(c)
            self.tags.update(c.tags)
            if isinstance(c, FeatureConstraint):
                self.tag_to_feats[c.X][c.f].add(c.Y)

    def sorts(self) -> set[Sort]:
        """
        Return the sorts appearing in the clause.
        """
        out = set()
        for c in self.constraints:
            if isinstance(c, SortConstraint):
                out.add(c.s)
        return out

    def subclause(self, root: Tag) -> RootedClause:
        "Return the subclause rooted at `root`."
        def visit(tag):
            reached.add(tag)
            for _, tags in self.tag_to_feats[tag].items():
                for t in tags:
                    if t not in reached:
                        visit(t)
        reached = set()
        visit(root)
        constraints = (c for c in self.constraints if c.tags.issubset(reached))
        return RootedClause(root, *constraints, ensure_rooted=False)

    def normalize(self, taxonomy: SortTaxonomy) -> SolvedClause:
        """
        Compute the normal (or solved) form of the clause.
        """
        from fosf.reasoning import ClauseNormalizer
        return ClauseNormalizer().normalize(self, taxonomy)

    def rename(self, base_tag: str = "X", start: int = 0) -> Clause:
        """
        Rename the tags of the clause.

        Parameters
        ----------
        base_tag : str, default="X"
            The base name of the tags used for the renaming.
        start : int, default = 0
            The base index for the tags used for the renaming. E.g., if base_tag is "X",
            the tags will be X0, X1, X2, ...
        """
        tag_counter = count(start)
        def new_tag(): return Tag(f"{base_tag}{next(tag_counter)}")
        renaming = defaultdict(new_tag)
        clause = type(self)()
        for c in self.constraints:
            if isinstance(c, SortConstraint):
                clause.add(SortConstraint(renaming[c.X], c.s))
            elif isinstance(c, FeatureConstraint):
                clause.add(FeatureConstraint(
                    renaming[c.X], c.f, renaming[c.Y]))
            elif isinstance(c, EqualityConstraint):
                clause.add(EqualityConstraint(renaming[c.X], renaming[c.Y]))
        return clause

    def __eq__(self, other):
        if not isinstance(other, Clause):
            return False
        return self.constraints == other.constraints

    def __contains__(self, constraint: Constraint):
        return constraint in self.constraints

    def __repr__(self):
        constraints = sorted([repr(c) for c in self.constraints])
        return f"{self.__class__.__name__}({', '.join(constraints)})"

    def __str__(self):
        constraints = sorted([str(c) for c in self.constraints])
        return "  &  ".join(constraints) + "."

    def __iter__(self):
        return iter(self.constraints)

    def __and__(self, other):
        if isinstance(other, Clause):
            return Clause(*self.constraints, *other.constraints)
        if isinstance(other, Constraint):
            return Clause(*self.constraints, other)
        raise TypeError(f"{other} should be a Constraint or a Clause")

    def __add__(self, other):
        return self & other


class RootedClause(Clause):
    """
    Represent a rooted OSF clause, a clause with a distinguished root tag.
    """

    def __init__(self, root: Tag, *constraints: Constraint,
                 ensure_rooted: bool = False):
        """
        Parameters
        ----------
        root : Tag
            The root of the clause.
        *constraints : Constraint
            The initial constraints of the clause.
        ensure_rooted: bool, default=False
            If True, ensure that the added constraints are indeed rooted.

        Attributes
        ----------
        root : Tag
            The root Tag of the clause.
        constraints : set[Constraint]
            The constraints of the clause.
        tags : set[Tag]
            The set of tags appearing in the constraint.
        tag_to_feats : dict[Tag, dict[Feature, set[Tag]]]
            A mapping from tags to a feature->tags map.
        """
        self.root: Tag = root
        self.constraints: set[Constraint] = set()
        self.tags: set[Tag] = set()
        self.tag_to_feats: dict[Tag, dict[Feature, set[Tag]]] = \
                defaultdict(lambda: defaultdict(set))
        if ensure_rooted:
            # Note: we cannot immediately use self.add, because the order
            # in which the constraints are processed is not guaranteed
            subclause = Clause(*constraints).subclause(self.root)
            self.constraints = subclause.constraints
            self.tags = subclause.tags
            self.tag_to_feats = subclause.tag_to_feats
        else:
            self.add(*constraints, ensure_rooted=ensure_rooted)

    def add(self, *constraints: Constraint, ensure_rooted: bool = False):
        """
        Add constraints to the clause.

        Parameters
        ----------
        *constraints : Constraint
            The constraints to be added
        ensure_rooted : bool, default=False
            If True, ensure that the constraints keep the clause rooted.

        Raise
        -----
        RuntimeError
            If ensure_rooted is True, and the added constraints do not maintain the clause
            rooted.
        """
        for c in constraints:
            if c in self.constraints:
                continue
            if ensure_rooted:
                if isinstance(c, FeatureConstraint):
                    if c.X not in self.tags:
                        raise RuntimeError(
                            f"Cannot add {c!s} to rooted clause {self!s}")
                if not c.tags.issubset(self.tags):
                    raise RuntimeError(
                        f"Cannot add {c!s} to RootedClause {self!s}")
            self.constraints.add(c)
            self.tags.update(c.tags)
            if isinstance(c, FeatureConstraint):
                self.tag_to_feats[c.X][c.f].add(c.Y)

    def subclause(self, root) -> RootedClause:
        "Return the subclause rooted at `root`."
        if root == self.root:
            return self
        return super().subclause(root)

    def normalize(self, taxonomy: SortTaxonomy) -> RootedSolvedClause:
        from fosf.reasoning import ClauseNormalizer
        return ClauseNormalizer().normalize(self, taxonomy)

    def rename(self, base_tag: str = "X", start: int = 0) -> RootedClause:
        tag_counter = count(start)
        def new_tag(): return Tag(f"{base_tag}{next(tag_counter)}")
        renaming = defaultdict(new_tag)
        new_root = new_tag()
        renaming[self.root] = new_root
        clause = RootedClause(new_root)
        for c in self.constraints:
            if isinstance(c, SortConstraint):
                clause.add(SortConstraint(renaming[c.X], c.s))
            elif isinstance(c, FeatureConstraint):
                clause.add(FeatureConstraint(
                    renaming[c.X], c.f, renaming[c.Y]))
            elif isinstance(c, EqualityConstraint):
                clause.add(EqualityConstraint(renaming[c.X], renaming[c.Y]))
        return clause

    def __repr__(self):
        constraints = sorted([repr(c) for c in self.constraints])
        return f"{self.__class__.__name__}({self.root!r}, {', '.join(constraints)})"


class SolvedClause(Clause):
    """
    Represent an OSF clause in solved form.
    """

    def __init__(self, *constraints: Constraint):
        """
        Parameters
        ----------
        *constraints : Constraint
            The initial constraints of the clause.

        Attributes
        ----------
        constraints : set[Constraint]
            The constraints of the clause.
        tags : set[Tag]
            The set of tags appearing in the constraint.
        tag_to_feats : dict[Tag, dict[Feature, Tag]]
            A mapping from tags to a feature->tag map.
        tag_to_sort : dict[Tag, Sort]
            A mapping from each tag to its unique sort.
        """
        self.constraints: set[Constraint] = set()
        self.tags: set[Tag] = set()
        self.tag_to_feats: dict[Tag, dict[Feature, Tag]] = defaultdict(dict)
        self.tag_to_sort: dict[Tag, Sort] = dict()
        self.add(*constraints)
        # TODO: ensure every tag is sorted?

    def add(self, *constraints: Constraint):
        """
        Add constraints to the clause.

        Parameters
        ----------
        *constraints : Constraint
            The constraints to be added

        Raise
        -----
        RuntimeError
            If the added constraints do not maintain the clause solved.
        """
        for c in constraints:
            if c in self.constraints:
                continue
            if isinstance(c, EqualityConstraint):
                raise RuntimeError(
                    f"Cannot add {c!s} to SolvedClause {self!s}")
            if isinstance(c, SortConstraint):
                if c.X in self.tag_to_sort:
                    raise RuntimeError(
                        f"Cannot add {c!s} to SolvedClause {self!s}")
                self.tag_to_sort[c.X] = c.s
            if isinstance(c, FeatureConstraint):
                if c.f in self.tag_to_feats[c.X]:
                    raise RuntimeError(
                        f"Cannot add {c!s} to SolvedClause {self!s}")
                self.tag_to_feats[c.X][c.f] = c.Y
            self.constraints.add(c)
            self.tags.update(c.tags)

    def subclause(self, root) -> RootedSolvedClause:
        "Return the subclause rooted at `root`."
        stack = [root]
        clause = RootedSolvedClause(root)
        seen = set()
        while stack:
            tag = stack.pop()
            if tag in seen:
                continue
            seen.add(tag)
            if tag in self.tag_to_sort:
                sort = self.tag_to_sort[tag]
                clause.add(SortConstraint(tag, sort))
                for feature, other in self.tag_to_feats[tag].items():
                    clause.add(FeatureConstraint(tag, feature, other))
                    stack.append(other)
        return clause

    def normalize(self, _: SortTaxonomy) -> SolvedClause:
        return self


class RootedSolvedClause(SolvedClause, RootedClause):
    """
    Represent a solved OSF clause with a distinguished Tag as its root.
    """

    def __init__(self, root: Tag,  *constraints: Constraint):
        """
        Parameters
        ----------
        root : Tag
            The root of the clause.
        *constraints : Constraint
            The initial constraints of the clause.

        Attributes
        ----------
        constraints : set[Constraint]
            The constraints of the clause.
        tags : set[Tag]
            The set of tags appearing in the constraint.
        tag_to_feats : dict[Tag, dict[Feature, Tag]]
            A mapping from tags to a feature->tag map.
        tag_to_sort : dict[Tag, Sort]
            A mapping from each tag to its unique sort.
        """
        self.root = root
        super().__init__(*constraints)

    def subclause(self, root) -> RootedSolvedClause:
        "Return the subclause rooted at `root`."
        if root == self.root:
            return self
        return super().subclause(root)

    def to_term(self) -> NormalTerm:
        """
        Return an equivalent :class:`NormalTerm`.
        """
        from fosf.syntax.terms import NormalTerm

        def visit(tag):
            if tag in seen:
                return NormalTerm(tag)
            seen.add(tag)
            sort = self.tag_to_sort[tag]
            subterms = {f: visit(other)
                        for f, other in self.tag_to_feats[tag].items()}
            return NormalTerm(tag, sort, subterms)
        seen = set()
        return visit(self.root)

    def equivalent_to(self, other: RootedSolvedClause) -> bool:
        """
        Return whether this clause is equivalent to another rooted solved clause.
        """
        if not isinstance(other, RootedSolvedClause):
            return False

        def equal_sorts(tag, other_tag):
            "Check if the tags are sorted by the same sort or both undefined"
            this_sort = self.tag_to_sort.get(tag, 0)
            other_sort = other.tag_to_sort.get(other_tag, 0)
            return this_sort == other_sort

        # Compare root sorts
        if not equal_sorts(self.root, other.root):
            return False

        stack = [(self.root, other.root)]
        checked = set()
        while stack:
            tag, other_tag = stack.pop()
            if (tag, other_tag) in checked:
                continue
            checked.add((tag, other_tag))
            # Compare features
            this_feats = self.tag_to_feats[tag]
            other_feats = other.tag_to_feats[other_tag]
            if this_feats.keys() != other_feats.keys():
                return False
            for feature, value in this_feats.items():
                other_value = other_feats[feature]
                # Compare sorts
                if not equal_sorts(value, other_value):
                    return False
                # Add to stack
                stack.append((value, other_value))
        return True

    def rename(self, base_tag="X", start=0) -> RootedSolvedClause:
        tag_counter = count(start)
        def new_tag(): return Tag(f"{base_tag}{next(tag_counter)}")
        renaming = defaultdict(new_tag)

        new_root = new_tag()
        renaming[self.root] = new_root
        clause = RootedSolvedClause(new_root)
        stack = [self.root]
        visited = set()
        while stack:
            tag = stack.pop()
            if tag in visited:
                continue
            visited.add(tag)
            clause.add(SortConstraint(renaming[tag], self.tag_to_sort[tag]))
            for f, other in sorted(self.tag_to_feats[tag].items()):
                clause.add(FeatureConstraint(
                    renaming[tag], f, renaming[other]))
                stack.append(other)
        return clause
