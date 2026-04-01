#!/usr/bin/env python3

from collections import defaultdict
from collections.abc import Iterable, Callable
from functools import cache, reduce
import operator
from typing import Generic, TypeGuard, TypeVar, overload

from bitarray import bitarray
import networkx as nx
import numpy as np

from fosf.exceptions import NotADag
from fosf.syntax.base import Tag, Sort, DisjunctiveSort, FrozenDisjunctiveSort


T = TypeVar("T")
R = TypeVar("R")


# TODO Check use of specific types where there should be general ones
class BaseTaxonomy(Generic[T, R]):
    """Generic taxonomy over directed acyclic graphs with bitvector encoding.

    :class:`BaseTaxonomy` represents a partially ordered set of nodes using a directed
    acyclic graph (DAG) structure. Each node is encoded as a bitvector for efficient
    computation of greatest lower bounds (GLBs) and subsort relationships. Optional
    weights can be associated with edges. Special top and bottom elements are
    automatically added if missing from the input edges.

    This class is generic in the node type `T` and the return type `R` for GLB
    computations when multiple maximal lower bounds exist.
    """

    _NODE_TYPE: type[T] | Callable = lambda x: x
    _BOT_PREFIX: str = "bot"
    _TOP_PREFIX: str = "top"
    _DISJUNCTIVE_TYPE: type = set

    def __init__(self, edges: Iterable[tuple[str | T, str | T] |
                                       tuple[str | T, str | T, float]]):
        """
        Parameters
        ----------
        edges : Iterable[tuple[str | T, str | T] | tuple[str | T, str | T, float]]
            An iterable of edges defining the DAG. Each edge can optionally include a
            weight (float). Nodes can be strings or instances of `T`.

        Attributes
        ----------
        graph : nx.DiGraph
            The DAG representation of the taxonomy.
        bot : T
            The bottom node in the taxonomy.
        top : T
            The top node in the taxonomy.
        topo : list[T]
            The list of nodes in topological order.
        rank : dict[T, int]
            A mapping from nodes to their rank in the topological order.
        node_to_code : dict[T, int]
            A mapping from nodes to their bitcode.
        code_to_node : dict[int, T]
            A mapping from bitcodes to nodes.

        Raises
        ------
        :class:`fosf.exceptions.NotADag`
            If the input edges form a cycle.
        """

        self.graph, self.bot, self.top = self._init_graph(edges)
        self.instances = None

        try:
            topo_gen = nx.topological_sort(self.graph)  # if cyclic: error
            self.topo: list[T] = list(topo_gen)
        except nx.NetworkXUnfeasible:
            raise NotADag("The input graph is not a DAG")

        self.rank: dict[T, int] = {node: i for i, node in enumerate(self.topo)}
        self.code_to_node: dict[int, T] = {}
        self.node_to_code: dict[T, int] = {}
        self._preprocess()

    @property
    def top_code(self) -> int:
        "The bit code of the top element"
        return self.node_to_code[self.top]

    @property
    def bot_code(self) -> int:
        "The bit code of the bottom element"
        return self.node_to_code[self.bot]

    def glb(self, *nodes: T | str) -> T | R:
        """
        Return the greatest lower bound of the input nodes:
        """
        if not nodes:
            return self.top
        code = reduce(operator.and_, [self.code(n) for n in nodes])
        glb = self._decode(code)
        return glb

    def code(self, node: T | str | Iterable[T]) -> int:
        """
        Return the code associated to a node or set of nodes.

        Parameters
        ----------
        node : T | str | Iterable[T]
            The node or nodes for which to return a code. If an iterable of nodes is
            passed, the code is the bitwise OR of the codes of each node in the iterable.
        """
        if isinstance(node, str):
            return self.node_to_code[self._NODE_TYPE(node)]
        if isinstance(node, Iterable):
            return reduce(operator.or_, (self.code(n) for n in node))
        return self.node_to_code[node]

    def is_subsort(self, s: T | str, t: T | str) -> bool:
        """
        Check if a node is subsumed by another sort.
        """
        s_code = self.code(s)
        return (s_code & self.code(t)) == s_code

    def _init_graph(self,
                    edges: Iterable[tuple[str | T, str | T] |
                                    tuple[str | T, str | T, float]]):
        g = nx.DiGraph()
        for edge in edges:
            u, v = edge[0], edge[1]
            w = 1.0
            if len(edge) > 2:
                if isinstance(edge[2], (float, int)):
                    w = edge[2]
                elif isinstance(edge[2], dict):
                    w = edge[2]["weight"]
                else:
                    msg = f"Invalid weight argument type for {edge[2]}: {type(edge[2]).__name__}"
                    raise TypeError(msg)
            g.add_edge(self._NODE_TYPE(u), self._NODE_TYPE(v), weight=w)
        bot, top = self._add_or_find_bot_and_top(g)
        return g, bot, top

    def _add_or_find_bot_and_top(self, graph: nx.DiGraph):
        sources = set()
        sinks = set()
        for node in graph.nodes():
            if graph.in_degree(node) == 0:
                sources.add(node)
            if graph.out_degree(node) == 0:
                sinks.add(node)
        if not sources or not sinks:
            raise NotADag("The input edges must not form a cycle.")

        # Add dummy bot if needed
        if len(sources) > 1:
            i = 0
            while (bot := self._NODE_TYPE(f"{self._BOT_PREFIX}{i}")) in graph:
                i += 1
            graph.add_weighted_edges_from((bot, src, 1.0) for src in sources)
        else:
            bot = sources.pop()

        # Add dummy top if needed
        if len(sinks) > 1:
            i = 0
            while (top := self._NODE_TYPE(f"{self._TOP_PREFIX}{i}")) in graph:
                i += 1
            graph.add_weighted_edges_from((sink, top, 1.0) for sink in sinks)
        else:
            top = sinks.pop()
        return bot, top

    def _preprocess(self):
        code = 0
        self.node_to_code[self.bot] = code
        self.code_to_node[code] = self.bot
        for i, node in enumerate(self.topo[1:]):
            code = (1 << i)
            for child in self.graph.pred[node]:
                code = code | self.node_to_code[child]
            self.node_to_code[node] = code
            self.code_to_node[code] = node

    def _decode(self, code: int) -> T | R:
        lca = self.code_to_node.get(code)
        if lca is None:
            return self._code_to_mlbs(code)
        return lca

    def _lower_bounds(self, code: int) -> set[T]:
        bitcode = bitarray(f"{code:0{len(self.topo)-1}b}")
        mask = np.frombuffer(bitcode.unpack(), dtype=bool)[::-1]
        lower_bounds: set[T] = {node for bit,
                                node in zip(mask, self.topo[1:]) if bit}
        return lower_bounds

    def lower_bounds(self, s: str | T) -> set[T]:
        "Return the set of lower bounds of a node."
        return self._lower_bounds(self.code(s))

    @cache
    def _code_to_mlbs(self, code: int) -> R:
        lower_bounds = self._lower_bounds(code)

        # Maximal elements
        maximal_lower_bounds = self._DISJUNCTIVE_TYPE()

        for lb in lower_bounds:
            if not any(parent in lower_bounds for parent in self.graph[lb]):
                maximal_lower_bounds.add(lb)

        n_mlbs = len(maximal_lower_bounds)
        if n_mlbs == 1:
            return maximal_lower_bounds.value.pop()
        if n_mlbs == 0:
            return self.bot

        if hasattr(maximal_lower_bounds, "freeze"):
            return maximal_lower_bounds.freeze()
        else:
            return maximal_lower_bounds

    # Traversal
    def _iter_parents_code(self, s, code):
        # Iterate over the parents of s
        # yield only the ones that are 'subsumed' by the code
        for parent in self.graph[s]:
            parent_code = self.node_to_code[parent]
            if parent_code & code == parent_code:
                yield parent

    def _topological(self, s, t):
        # Yield sorts in topological order from s to t
        s_index = self.rank[s]
        t_index = self.rank[t]
        for v in self.topo[s_index:(t_index+1)]:
            yield v


class TagTaxonomy(BaseTaxonomy[Tag, set[Tag]]):
    """
    Taxonomy of tag symbols.

    Used in :class:`fosf.syntax.theory.OsfTheory` to store the ordering of Tags induced by
    an OSF theory.
    """

    _NODE_TYPE = Tag
    _BOT_PREFIX = "X_bot"
    _TOP_PREFIX = "X_top"
    _DISJUNCTIVE_TYPE = set

    def __init__(self, edges: Iterable[tuple[str | Tag, str | Tag] |
                                       tuple[str | Tag, str | Tag, float]]):
        """
        Parameters
        ----------
        edges : Iterable[tuple[str | Tag, str | Tag]]
            An iterable of edges defining the DAG. Nodes can be strings or :class:`Tag`'s.

        Attributes
        ----------
        graph : nx.DiGraph
            The DAG representation of the Tag taxonomy.
        bot : Tag
            The bottom Tag in the taxonomy.
        top : Tag
            The top Tag in the taxonomy.
        topo : list[Tag]
            The list of tags in topological order.
        rank : dict[Tag, int]
            A mapping from tags to their rank in the topological order.
        node_to_code : dict[Tag, int]
            A mapping from tags to their bitcode.
        code_to_node : dict[int, Tag]
            A mapping from bitcodes to tags.
        """
        super().__init__(edges)

class SortTaxonomy(BaseTaxonomy[Sort, DisjunctiveSort]):
    """
    Taxonomy of sort symbols.
    """

    _NODE_TYPE = Sort
    _BOT_PREFIX = "bot"
    _TOP_PREFIX = "top"
    _DISJUNCTIVE_TYPE = DisjunctiveSort

    def __init__(self,
                 edges: Iterable[tuple[str | Sort, str | Sort] | tuple[str | Sort, str | Sort, float]],
                 # TODO: add class SingletonSort or Instance for instances
                 instances: dict[str, dict[Sort, float]] | None = None):
        """
        Parameters
        ----------
        edges : Iterable[tuple[str | Sort, str | Sort] | tuple[str | Sort, str | Sort, float]]
            An iterable of edges defining the DAG. Each edge can optionally include a
            weight (float). Nodes can be strings or instances of :class:`Sort`.
        instances : dict[str, dict[Sort, float]] | None
            Optional dict mapping instances to the sorts they are direct members of,
            together with their membership degree

        Attributes
        ----------
        graph : nx.DiGraph
            The DAG representation of the sort taxonomy.
        bot : Sort
            The bottom sort in the taxonomy.
        top : Sort
            The top sort in the taxonomy.
        topo : list[Sort]
            The list of sorts in topological order.
        rank : dict[Sort, int]
            A mapping from sorts to their rank in the topological order.
        node_to_code : dict[Sort, int]
            A mapping from sorts to their bitcode.
        code_to_node : dict[int, Sort]
            A mapping from bitcodes to sorts.

        Raises
        ------
        :class:`fosf.exceptions.NotADag`
            If the input edges form a cycle.
        """

        super().__init__(edges)
        self.instances = instances

    def is_subsort(self, s: Sort | str, t: Sort | str,
                   any_subsort: bool = True) -> bool:
        """
        Check if a sort is subsumed by another sort.

        Parameters
        ----------
        s : Sort | str
            A :class:`Sort` (possibly a :class:`DisjunctiveSort`)
        t : Sort | str
            A :class:`Sort` (possibly a :class:`DisjunctiveSort`)
        any_subsort : bool, default=True
            If True, if ``s`` is a :class:`DisjunctiveSort`, the method checks whether any
            sort in ``s`` is a subsort of ``t``
        """
        if isinstance(s, DisjunctiveSort) and len(s) > 1 and any_subsort:
            t_code = self.code(t)
            return any((self.code(si) & t_code) == self.code(si) for si in s)
        return super().is_subsort(s, t)

    def add_instance(self, instance: str, sort: str | Sort):
        """
        Add an instance to a sort.
        """
        sort = Sort(sort)
        if self.instances is None:
            self.instances = defaultdict(dict)
        if isinstance(self.instances, defaultdict):
            self.instances[instance][sort] = 1.0
            return
        if instance not in self.instances:
            self.instances[instance] = {}
        self.instances[instance][sort] = 1.0

    def is_instance(self, instance: str, sort: Sort):
        """
        Check whether an instance is a member of a sort.
        """
        assert self.instances is not None
        return any(self.is_subsort(parent, sort) for parent in self.instances[instance])

    def glb(self, *nodes: Sort | str) -> Sort | DisjunctiveSort:
        """
        Return the greatest lower bound of the input sorts:
        """
        if not nodes:
            return self.top
        try:
            code = reduce(operator.and_, [self.code(n) for n in nodes])
        except KeyError as e:
            node = e.args[0].value
            if self.instances and node in self.instances:
                return self._glb_with_instances(nodes)
            else:
                raise e from None
        glb = self._decode(code)
        return glb

    def _glb_with_instances(self, nodes):
        assert self.instances is not None
        instances = set()
        sorts = list()
        for node in nodes:
            if isinstance(node, Sort):
                sorts.append(node)
            elif node in self.instances:
                instances.add(node)
            else:
                # node may be a string: if it is invalid, an error will be raised later
                # TODO: raise error already?
                sorts.append(node)
        if len(instances) > 1:
            # The GLB of two instances is always the bottom element
            # Assuming unique names
            return self.bot
        instance = instances.pop()
        if all(self.is_instance(instance, sort) for sort in sorts):
            return instance
        return self.bot


class FuzzySortTaxonomy(SortTaxonomy):

    def add_instance(self, instance: str, sort: str | Sort,
                     degree: float = 1.0, check: bool = True):
        """
        Add an instance to a sort with a membership degree.

        Parameters
        ----------
        instance: str
        sort: str | Sort
        degree: float, default=1.0
            The membership degree.
        check: bool, default=True
            If true, check that the membership degree respects the semantics of fuzzy OSF
            logic.
        """

        if degree == 1.0 and not check:
            super().add_instance(instance, sort)
            return

        sort = Sort(sort)

        # Initialize self.instances if it does not exit yet
        if self.instances is None:
            self.instances = defaultdict(dict)

        if instance not in self.instances:
            self.instances[instance] = {sort: degree}
            # No need to check for other membership degrees
            return

        if not check:
            current_degree = self.instances[instance].get(sort, 0)
            self.instances[instance][sort] = max(current_degree, degree)
            return

        # Check other membership degrees
        for other, other_degree in self.instances[instance].items():
            if other == sort:
                continue
            if self.is_subsort(other, sort):
                sub_degree = self.degree(other, sort)
                if not (degree >= min(other_degree, sub_degree)):
                    message = f"{other} < {sort} = {sub_degree}. "
                    message += f"{other}({instance}) = {other_degree}. "
                    message += f" -> `degree` should be >= min({sub_degree}, {other_degree})"
                    raise ValueError(message)
            if self.is_subsort(sort, other):
                sub_degree = self.degree(sort, other)
                if not (other_degree >= min(degree, sub_degree)):
                    message = f"{sort} < {other} = {sub_degree}. "
                    message += f"{other}({instance}) = {other_degree}. "
                    message += f" -> `degree` should be <= min({sub_degree}, {other_degree})"
                    raise ValueError(message)

        # Set degree
        self.instances[instance][sort] = degree

    def membership_degree(self, instance: str, sort: str | Sort | Iterable) -> float:
        """
        Compute the degree of membership of an instance to a sort or sorts.
        """
        assert self.instances is not None
        if instance not in self.instances:
            return 0
        parents = self.instances[instance]
        if isinstance(sort, DisjunctiveSort):
            sort = sort.freeze()
        if isinstance(sort, str):
            sort = Sort(sort)
        degrees = self.degree(parents, sort)
        if isinstance(sort, Sort):
            return max(
                min(self.instances[instance][parent], degrees[parent][sort])
                for parent in degrees)
        if isinstance(sort, Iterable):
            # E.g., list of sorts, considered as a conjunction
            # # Approach 1
            # degrees = [self.membership_degree(instance, s) for s in sort]
            # return min(degrees)
            # Approach 2
            parents = self.instances[instance]
            degrees = self.degree(parents, sort)
            degrees = {parent:
                       {target: min(parents[parent], degrees[parent][target])
                        for target in targets} for parent, targets in degrees.items()}
            return min(
                max(degrees[parent][Sort(target)] for parent in parents)
                for target in sort)
        msg = f"Invalid argument type for {sort}: {type(sort).__name__}"
        raise TypeError(msg)

    # TODO: rename degree to subsumption_degree?
    @overload
    def degree(self, s: Sort | str, t: Sort | str) -> float: ...
    # Returns the subsumption degree of s wrt t

    @overload
    def degree(self, s: Sort | str,
               t: Iterable[Sort | str]) -> dict[Sort, float]: ...
    # For each t, returns the subsumption degree of s wrt t

    @overload
    def degree(self, s: Iterable[Sort | str],
               t: Sort | str | Iterable[Sort | str]) \
        -> dict[Sort, dict[Sort, float]]: ...
    # For each s, for each t, returns the subsumption degree of s wrt t

    def degree(self,
               s: Sort | str | Iterable[Sort | str],
               t: Sort | str | Iterable[Sort | str]):
        """
        Compute the subsumption degree of one or more sorts with repect to one or more
        sorts.
        """

        def is_simple_sort(x) -> TypeGuard[Sort]:
            if isinstance(x, (DisjunctiveSort, FrozenDisjunctiveSort)):
                return False
            return isinstance(x, Sort)

        def is_disjunctive_sort(x) \
                -> TypeGuard[DisjunctiveSort | FrozenDisjunctiveSort]:
            return isinstance(x, (DisjunctiveSort, FrozenDisjunctiveSort))

        if isinstance(s, str):
            s = Sort(s)
        if isinstance(t, str):
            t = Sort(t)

        if is_simple_sort(s):
            if is_simple_sort(t):
                return self._degree_single_source_multi_target(s, {t})[t]
            if is_disjunctive_sort(t):
                out = self._degree_single_source_multi_target(s, t)
                return max(out.get(tt, 0) for tt in t)
            if isinstance(t, Iterable):
                return self._degree_iterable_source_iterable_target([s], t)[s]
            msg = f"Invalid argument type for {t}: {type(t).__name__}"
            raise TypeError(msg)
        if is_disjunctive_sort(s):
            if is_simple_sort(t):
                out = self._degree_multi_source_multi_target(
                    s, {t}, self.code(t))
                return min(out[t].get(ss, 0) for ss in s)
            if is_disjunctive_sort(t):
                out = self._degree_multi_source_multi_target(
                    s, t, self.code(t))
                return min(max(out[tt].get(ss, 0) for tt in t) for ss in s)
            if isinstance(t, Iterable):
                return self._degree_iterable_source_iterable_target([s], t)[s]
            msg = f"Invalid argument type for {t}: {type(t).__name__}"
            raise TypeError(msg)
        if isinstance(s, Iterable):
            if isinstance(t, Sort):
                return self._degree_iterable_source_iterable_target(s, [t])
            if isinstance(t, Iterable):
                return self._degree_iterable_source_iterable_target(s, t)
            msg = f"Invalid argument type for {t}: {type(t).__name__}"
            raise TypeError(msg)
        msg = f"Invalid argument type for {s}: {type(s).__name__}"
        raise TypeError(msg)

    def _degree_single_source_multi_target(self,
                                           s: Sort,
                                           ts: Iterable[Sort],
                                           code: int | None = None) -> dict[Sort, float]:
        """
        Shortest-path-like algorithm from a source to a set of targets to compute
        the subsumption degree of s with respect to each target.
        The value of a path from a source to a target is the minimum weight on the path.
        The best path is the path with maximum value (fuzzy max-min composition/transitivity)
        """
        if code is None:
            code = self.code(ts)

        s_code = self.node_to_code[s]
        if s_code & code != s_code:
            # s is not a subsort of any target
            return {t: 0 for t in ts}

        visited = set()
        dist_to = {}
        dist_to[s] = 1.0

        t = max(ts, key=lambda t: self.rank[t])
        for v in self._topological(s, t):
            if not dist_to.get(v):
                continue
            for w in self._iter_parents_code(v, code):
                weight = self.graph[v][w]['weight']
                if w not in visited or dist_to[w] < min(dist_to[v], weight):
                    dist_to[w] = min(dist_to[v], weight)
                    visited.add(w)
        return dist_to

    def _degree_multi_source_multi_target(self,
                                          sources: Iterable[Sort],
                                          targets: Iterable[Sort],
                                          code: int | None = None):
        if code is None:
            code = self.code(targets)

        topo_s = min(sources, key=lambda x: self.rank[x])
        topo_t = max(targets, key=lambda x: self.rank[x])

        bottleneck = defaultdict(dict)
        for s in sources:
            bottleneck[s][s] = 1.0

        for u in self._topological(topo_s, topo_t):
            if u not in bottleneck:
                continue
            for v in self._iter_parents_code(u, code):
                weight = self.graph[u][v]['weight']
                for s, cost in bottleneck[u].items():
                    new_bottleneck = min(cost, weight)
                    if s not in bottleneck[v] or bottleneck[v][s] < new_bottleneck:
                        bottleneck[v][s] = new_bottleneck
        return bottleneck

    def _degree_iterable_source_iterable_target(self, sources, targets):
        traversal_srcs, disj_srcs, simple_srcs = self.__flatten(sources)
        traversal_tgts, disj_tgts, simple_tgts = self.__flatten(targets)
        degrees = self._degree_multi_source_multi_target(
            traversal_srcs, traversal_tgts)

        out = defaultdict(dict)
        for src in simple_srcs:
            for tgt in simple_tgts:
                out[src][tgt] = degrees[tgt].get(src, 0)
            for disj_tgt in disj_tgts:
                out[src][disj_tgt] = max(degrees[tgt].get(src, 0)
                                         for tgt in disj_tgt)
        for d_src in disj_srcs:
            for tgt in simple_tgts:
                out[d_src][tgt] = min(degrees[tgt].get(ss, 0)
                                      for ss in d_src)
            for d_tgt in disj_tgts:
                out[d_src][d_tgt] = min(max(degrees[tt].get(ss, 0)
                                            for tt in d_tgt) for ss in d_src)
        return out

    def __flatten(self, nodes: Iterable[str | Sort]) \
            -> tuple[set[Sort], set[FrozenDisjunctiveSort], set[Sort]]:
        traversal_nodes = set()
        disjunctive_nodes = set()
        simple_nodes = set()
        for node in nodes:
            if isinstance(node, str):
                simple_nodes.add(Sort(node))
                traversal_nodes.add(Sort(node))
            elif isinstance(node, (DisjunctiveSort, FrozenDisjunctiveSort)):
                if isinstance(node, DisjunctiveSort):
                    node = node.freeze()
                disjunctive_nodes.add(node)
                for sort in node:
                    traversal_nodes.add(sort)
            elif isinstance(node, Sort):
                simple_nodes.add(node)
                traversal_nodes.add(node)
        return traversal_nodes, disjunctive_nodes, simple_nodes
