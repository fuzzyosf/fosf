#!/usr/bin/env python3

from __future__ import annotations

from typing import ClassVar


class Tag(str):
    """
    Represent a tag symbol in an OSF term or OSF clause.

    :class:`Tag` is a string subclass used to distinguish tags from regular strings. It is
    hashable and comparable. Equality is based on both the type and the string value.
    """

    def __repr__(self):
        return f"Tag({super().__repr__()})"

    def __hash__(self) -> int:
        return hash(("Tag", super().__hash__()))

    def __eq__(self, other: Tag) -> bool:
        return isinstance(other, Tag) and super().__eq__(other)


class Feature(str):
    """
    Represent a feature symbol in an OSF term or OSF clause.

    :class:`Feature` is a string subclass used to distinguish features from regular
    strings. It is hashable and comparable. Equality is based on both the type and the
    string value.
    """

    def __repr__(self):
        return f"Feature({super().__repr__()})"

    def __hash__(self) -> int:
        return hash(("Feature", super().__hash__()))

    def __eq__(self, other: Feature) -> bool:
        return isinstance(other, Feature) and super().__eq__(other)


class Sort:
    """
    Represent a single sort, a named element of a sort taxonomy.

    :class:`Sort` objects are hashable and comparable. Equality is based on both the type
    and the string value.
    """

    def __init__(self, value: str | Sort):
        """
        Parameters
        ----------
        value : str or Sort
            The name of the sort, or an existing :class:`Sort` instance. If initialized from
            another `Sort`, the `.value` attribute is used. Disjunctive sorts (e.g.,
            :class:`DisjunctiveSort`, :class:`FrozenDisjunctiveSort`) are not allowed.

        Attributes
        ----------
        value : str
            The name of the sort.

        Raises
        ------
        TypeError
            If `value` is not a string or a `Sort` instance.
        """
        if isinstance(value, Sort) and not isinstance(value, (DisjunctiveSort, FrozenDisjunctiveSort)):
            value = value.value
        elif not isinstance(value, str):
            raise TypeError(
                f"Sort must be initialized with a str or Sort, got {type(value).__name__}")
        self.value: str = value

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"Sort({self.value!r})"

    def __hash__(self):
        return hash(("Sort", self.value))

    def __eq__(self, other):
        return isinstance(other, Sort) and self.value == other.value

    def __lt__(self, other):
        return self.value < other.value


class DisjunctiveSort(Sort):
    """
    Represent a mutable disjunctive sort.

    A :class:`DisjunctiveSort` is set of individual :class:`Sort` objects and represents
    their union. It is mutable: sorts can be added after construction. A frozen variant
    can be obtained via the :meth:`freeze` method.
    """

    __hash__: ClassVar[None] = None

    def __init__(self, *sorts: str | Sort):
        """
        Parameters
        ----------
        *sorts : str or Sort
            One or more sorts to initialize the disjunction.

        Attributes
        ----------
        value : set[Sort]
        """
        self.value: set[Sort] = set()
        self.add(*sorts)

    def add(self, *sorts: str | Sort):
        "Add one or more sorts to the disjunction"
        for sort in sorts:
            if isinstance(sort, Sort):
                self.value.add(sort)
            else:
                # TODO: check other types, e.g. str
                self.value.add(Sort(sort))

    def freeze(self) -> FrozenDisjunctiveSort:
        "Return an immutable :class:`FrozenDisjunctiveSort` containing the same sorts."
        return FrozenDisjunctiveSort(*self.value)

    def __str__(self):
        return f'{{ {", ".join(sorted(str(s) for s in self.value))} }}'

    def __repr__(self):
        return f"DisjunctiveSort({', '.join(sorted(repr(s) for s in self.value))})"

    def __eq__(self, other):
        return isinstance(other, DisjunctiveSort) and self.value == other.value

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)


class FrozenDisjunctiveSort(Sort):
    """
    Represent an immutable disjunctive sort.

    A :class:`FrozenDisjunctiveSort` contains a fixed set of `Sort` objects representing
    their union. Unlike `DisjunctiveSort`, this class is immutable and hashable. The
    mutable variant can be obtained via the :meth:`thaw` method.
    """

    def __init__(self, *sorts: str | Sort):
        """
        Parameters
        ----------
        *sorts : str or Sort
            One or more sorts to initialize the frozen disjunction.

        Attributes
        ----------
        value : frozenset[Sort]
        """
        self.value: frozenset[Sort] = frozenset(Sort(sort) for sort in sorts)
        self._hash: int | None = None

    def thaw(self) -> DisjunctiveSort:
        "Return a mutable :class:`DisjunctiveSort` containing the same sorts."
        return DisjunctiveSort(*self.value)

    def __str__(self):
        return f'{{ {", ".join(sorted(str(s) for s in self.value))} }}'

    def __repr__(self):
        return f"FrozenDisjunctiveSort({', '.join(sorted(repr(s) for s in self.value))})"

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(("DisjunctiveSort", self.value))
        return self._hash

    def __eq__(self, other):
        return isinstance(other, FrozenDisjunctiveSort) and self.value == other.value

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)
