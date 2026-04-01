#!/usr/bin/env python3

from collections import defaultdict
from itertools import chain, combinations
from typing import Iterable

import networkx as nx
from tqdm import tqdm

from fosf.syntax.base import Sort, DisjunctiveSort
from fosf.syntax.taxonomy import SortTaxonomy


def graph_to_dag(graph: nx.DiGraph):
    "Construct a DAG on the strongly connected components of an input graph"
    # Make a copy of the graph
    graph.remove_edges_from(nx.selfloop_edges(graph))

    # Get maximal cycles
    cycles = nx.strongly_connected_components(graph)

    # Get component representatives
    rep = {}
    for cycle in cycles:
        u = cycle.pop()
        rep[u] = u
        for v in cycle:
            rep[v] = u
    for node in graph.nodes():
        if node not in rep:
            rep[node] = node

    # Construct graph on components
    g = nx.DiGraph()
    for u, v, data in graph.edges(data=True):
        w = data['weight']
        ru = rep[u]
        rv = rep[v]
        if (ru, rv) in g.edges():
            # Update weight
            rw = g[ru][rv]['weight']
            if w > rw:
                g[ru][rv]['weight'] = w
        elif ru != rv:
            g.add_edge(ru, rv, weight=w)

    g.remove_edges_from(nx.selfloop_edges(g))
    return g, rep


def free_lattice_taxonomy(nodes):
    def powerset(iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(1, len(s)+1))

    def to_node(subset):
        return "+".join(sorted(str(s) for s in subset))

    edges = []
    nodes = [Sort(node) for node in nodes]
    if len(nodes) == 0:
        return SortTaxonomy([("bot", "top")])

    if len(nodes) == 1:
        node = nodes[0]
        extremes = []
        for x in ["bot", "top"]:
            xc = 0
            while Sort(f"{x}{xc}") in nodes:
                xc += 1
            extremes.append(Sort(f"{x}{xc}"))
        bot, top = extremes[0], extremes[1]
        return SortTaxonomy([(bot, node), (node, top)])

    power = list(powerset(nodes))
    for subset in power:
        for other in power:
            if set(subset).issubset(set(other)):
                u = to_node(other)
                v = to_node(subset)
                if u == v:
                    continue
                edges.append((u, v, 1))
    return SortTaxonomy(edges)


def serialize_taxonomy(taxonomy, bot=True, top=True, destination=None):
    graph = taxonomy.graph
    supersorts_dict = defaultdict(set)
    if not bot or not top:
        graph = graph.copy()
        if not bot:
            graph.remove_node(taxonomy.bot)
        if not top:
            graph.remove_node(taxonomy.top)
    sorts = graph.nodes()
    for sort in sorted(sorts):
        supersorts = graph[sort]
        if supersorts:
            supersorts_iter = (f"{k} ({v['weight']})"
                               if 'weight' in v and v['weight'] < 1
                               else str(k)
                               for k, v in graph[sort].items())
            supersorts_string = ", ".join(supersorts_iter)
            supersorts_dict[supersorts_string].add(sort)
    lines = []
    for sorts, subsorts in supersorts_dict.items():
        subsorts_string = ", ".join(str(x) for x in subsorts)
        lines.append(f"{subsorts_string} < {sorts}.")
    if destination:
        with open(destination, "w") as f:
            f.write("\n".join(lines))
    else:
        return "\n".join(lines)


def all_pairs_glbs(taxonomy, disable_tqdm=False) -> dict:
    "Return a dict mapping pairs of nodes to their GLB."
    glbs_map = {}
    for u in tqdm(taxonomy.topo[1:], disable=disable_tqdm):
        nodes = list(taxonomy.graph.pred[taxonomy.top])
        seen = set()
        while nodes:
            v = nodes.pop()
            if taxonomy.rank[v] <= taxonomy.rank[u]:
                continue
            if v in seen:
                continue
            seen.add(v)
            glbs = taxonomy.glb(u, v)
            if isinstance(glbs, DisjunctiveSort):
                glbs_map[(u, v)] = glbs
                nodes.extend(list(taxonomy.graph.pred[v]))
            else:
                if glbs == taxonomy.bot:
                    continue
                glbs_map[(u, v)] = glbs
                nodes.extend(list(taxonomy.graph.pred[v]))
    return glbs_map


def minimal_ancestors(graph: nx.DiGraph, sources: Iterable, bot=None):
    nodes = set(sources)

    visited = set()
    out = set()
    while nodes:
        node = nodes.pop()
        if node in visited:
            continue
        visited.add(node)
        if bot is not None:
            if bot in graph.pred[node]:
                out.add(node)
        elif not graph.pred[node]:
            out.add(node)
        for child in graph.pred[node]:
            nodes.add(child)
    return out


def maximal_lower_bounds(dag: nx.DiGraph, node_s, node_t):
    lower_bounds_s = nx.ancestors(dag, node_s)
    if node_t in lower_bounds_s:
        return {node_t}
    lower_bounds_t = nx.ancestors(dag, node_t)
    if node_s in lower_bounds_t:
        return {node_s}
    common_lower_bounds = lower_bounds_s.intersection(lower_bounds_t)
    maximal_lower_bounds = set()
    for lower_bound in common_lower_bounds:
        is_mlb = True
        for adj in dag[lower_bound]:
            if adj in common_lower_bounds:
                is_mlb = False
                break
        if is_mlb:
            maximal_lower_bounds.add(lower_bound)
    return maximal_lower_bounds
