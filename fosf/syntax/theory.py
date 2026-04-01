#!/usr/bin/env python3

from collections import defaultdict
from itertools import count

import networkx as nx

from fosf.syntax.base import Tag, Sort, Feature
from fosf.syntax.taxonomy import TagTaxonomy, SortTaxonomy
from fosf.syntax.terms import NormalTerm


class TheoryTag:
    """
    Represent a Tag used in an OSF theory.
    """

    def __init__(self, tag: Tag,
                 sort: Sort,
                 features: dict[Feature, Tag] | None = None):
        """
        Parameters
        ----------
        tag : Tag
            The theory tag.
        sort : Sort
            The unique sort associated to this tag.
        features : dict[Feature, Tag] | None 
            The features defined for this tag in the OSF theory.

        Attributes
        ----------
        tag : Tag
        sort : Sort
        features : dict[Feature, Tag]
            A possibly empty dict mapping each feature defined in the theory for this
            TheoryTag to the corresponding Tag.
        """
        self.tag: Tag = tag
        self.sort: Sort = sort
        if features is None:
            self.features = dict()
        else:
            self.features = features

    def __hash__(self):
        return hash(self.tag)

    def __repr__(self):
        if self.features:
            return f"TheoryTag({self.tag}, {self.sort}, {self.features})"
        return f"TheoryTag({self.tag}, {self.sort})"


class OsfTheory:
    """
    Represent an OSF theory of sort definitition.

    A sort definition imposes structural constraints on OSF terms.
    """

    def __init__(self, taxonomy: SortTaxonomy,
                 definitions: dict[Sort, NormalTerm],
                 tags: dict[Tag, TheoryTag] | None = None,
                 ensure_closed: bool = False):
        """
        Parameters
        ----------
        taxonomy : SortTaxonomy
            The sort taxonomy for this theory
        definitions : dict[Sort, NormalTerm]
            A mapping from each :class:`Sort` to its definition as a :class:`NormalTerm`
        tags : dict[Tag, TheoryTag] | None, default=None
            A mapping from each :class:`Tag` to its :class:`TheoryTag` object. If None, it
            is computed.
        ensure_closed : bool, default=False
            If True, close the OSF theory to ensure its order-consistency.

        Attributes
        ----------
        taxonomy : SortTaxonomy
            The background sort subsumption taxonomy.
        definitions : dict[Sort, NormalTerm]
            A mapping from each :class:`Sort` to its definition as a :class:`NormalTerm`
        tags : dict[Tag, TheoryTag]
            A mapping from each :class:`Tag` to its :class:`TheoryTag` object.
        tag_taxonomy : TagTaxonomy
            The tag taxonomy representing the ordering on theory tags induced by the sort
            taxonomy and the theory.
        """

        self.taxonomy = taxonomy
        self.definitions: dict[Sort, NormalTerm] = definitions
        if ensure_closed:
            self._close()
            self._init_structures()
        elif tags is None:
            self._init_structures()
        else:
            self.tags = tags
        self.tag_taxonomy = self._tag_taxonomy(taxonomy)

    def sort(self, X: Tag) -> Sort:
        """
        Return the sort associated to a tag in the theory.
        """
        return self.tags[X].sort

    def features(self, X: Tag) -> dict[Feature, Tag]:
        """
        Return the features defined for a tag in the theory.
        """
        return self.tags[X].features

    def _check_or_init_def(self, sort):
        if sort not in self.definitions:
            tag_s = Tag(f"Y{sort}")
            self.definitions[sort] = NormalTerm(tag_s, sort)
            self.tags[tag_s] = TheoryTag(tag_s, sort)

    def _tag_taxonomy(self, taxonomy):

        tag_graph = nx.DiGraph()
        for sort in taxonomy.topo[1:-1]:
            tag = self.definitions[sort].X
            tag_graph.add_node(tag)

        stack = set()
        for s, t in taxonomy.graph.edges():
            self._check_or_init_def(s)
            self._check_or_init_def(t)
            tag_s = self.definitions[s].X
            tag_t = self.definitions[t].X
            stack.add((tag_s, tag_t))

        tag_graph = nx.DiGraph()
        for term in self.definitions.values():
            for tag in term.tags():
                tag_graph.add_node(tag)

        top_tag = self.definitions[self.taxonomy.top].X
        bot_tag = self.definitions[self.taxonomy.bot].X

        while stack:
            x, y = stack.pop()
            if (x, y) in tag_graph.edges:
                continue
            tag_graph.add_edge(x, y)

            if x == bot_tag:
                continue

            tx, ty = self.tags[x], self.tags[y]
            for f in ty.features:
                if f not in tx.features:
                    raise RuntimeError(f"Missing feature {f} from {ty} >= {tx}")
                fx, fy = self.features(x)[f], self.features(y)[f]
                stack.add((fx, fy))

        for node in tag_graph.nodes:
            if tag_graph.in_degree(node) == 0 and node != bot_tag:
                tag_graph.add_edge(bot_tag, node)
            if tag_graph.out_degree(node) == 0 and node != top_tag:
                tag_graph.add_edge(node, top_tag)

        return TagTaxonomy(tag_graph.edges)

    def _init_structures(self):
        self.tags = {}
        for sort, term in self.definitions.items():
            for subterm in term.dfs():
                Y = subterm.X
                sort = subterm.s
                if sort is not None:
                    features = {f: subsubterm.X
                                for f, subsubterm in subterm.subterms.items()}
                    self.tags[Y] = TheoryTag(Y, sort, features)

    def _close(self):
        from fosf.reasoning.terms import unify_terms
        inverse_topo = nx.topological_sort(self.taxonomy.graph.reverse())
        graph = self.taxonomy.graph
        top = next(inverse_topo)

        if top not in self.definitions:
            top_tag = Tag("Ytop")
            self.definitions[top] = NormalTerm(top_tag, top)
        else:
            top_tag = self.definitions[top].X

        tag_counter = count(0)
        def _new_tag(): return Tag(f"Y{next(tag_counter)}")

        def rename_term(term, renaming):
            X, s = term.X, term.s
            return NormalTerm(renaming[X], s,
                              {f: rename_term(subterm, renaming) for f, subterm in
                               term.subterms.items()})

        for sort in inverse_topo:
            # Take current definition, or create a basic one
            if sort in self.definitions:
                old_definition = self.definitions[sort]
                theory_tag = old_definition.X
            else:
                theory_tag = Tag(f"Y{sort}")
                old_definition = NormalTerm(theory_tag, sort)

            # Unify the sort's definition with the supersorts' definition
            parents = set(graph.succ[sort])-{self.taxonomy.top}
            if parents:
                terms_to_unify = [old_definition] + \
                    [self.definitions[parent] for parent in parents]
                unifier = unify_terms(terms_to_unify, self.taxonomy, rename_terms=True,
                                      return_degree=False)
            else:
                unifier = old_definition

            # Rename the new definition
            unifier_root = unifier.X
            renaming = defaultdict(_new_tag)
            renaming[unifier_root] = theory_tag
            new_definition = rename_term(unifier, renaming)
            self.definitions[sort] = new_definition

    def __getitem__(self, key: str | Sort):
        """
        Return the definition of a sort.
        """
        return self.definitions[Sort(key)]
