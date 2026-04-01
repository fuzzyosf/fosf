#!/usr/bin/env python3

import random

import networkx as nx
import numpy as np

from fosf.syntax.base import Tag, Sort, Feature
from fosf.syntax.taxonomy import SortTaxonomy, FuzzySortTaxonomy
from fosf.syntax.terms import Term


def random_taxonomy(size: int,
                    avg_out_degree: int | float = 3,
                    seed: int = 1):
    np.random.seed(seed)

    prob = (avg_out_degree * 2)/size
    g = nx.fast_gnp_random_graph(size, prob, seed=seed, directed=True)

    edges = [(f"s{u}", f"s{v}") for (u, v) in g.edges() if u < v]

    return SortTaxonomy(edges)


def random_fuzzy_taxonomy(size: int,
                          avg_out_degree: int | float = 3,
                          seed: int = 1):
    np.random.seed(seed)

    prob = (avg_out_degree * 2) / size
    g = nx.fast_gnp_random_graph(size, prob, seed=seed, directed=True)

    def weight(): return np.random.uniform(low=1e-2, high=1.0)
    edges = [(f"s{u}", f"s{v}", round(weight(), 2))
             for u, v in g.edges() if u < v]

    return FuzzySortTaxonomy(edges)


def random_osf_graph(num_nodes: int,
                     node_labels: list[Sort | str],
                     edge_labels: list[Feature | str],
                     extra_edge_prob: float = 0.3,
                     seed: int = 1) -> tuple[nx.DiGraph, Tag]:
    rng = random.Random(seed)
    G = nx.DiGraph()

    node_labels = [label if isinstance(label, Sort) else Sort(
        label) for label in node_labels]
    edge_labels = [label if isinstance(label, Feature) else Feature(
        label) for label in edge_labels]

    nodes = [Tag(f"X{i}") for i in range(num_nodes)]

    # Add nodes with random labels
    for node in nodes:
        label = rng.choice(node_labels)
        G.add_node(node, label=label)

    # Build a directed spanning tree rooted at X0
    root = Tag("X0")
    rng.shuffle(nodes)
    connected = {root}
    while len(connected) < len(nodes):
        # Ensure all nodes are added to the spanning tree
        for node in nodes:
            if node in connected:
                continue
            # Choose a random parent
            parent = rng.choice(sorted(connected))  # sorted is for determinism
            # Ensure unique edge label from parent to node
            used_labels = {data["label"] for _, data in G[parent].items()}
            available = [lbl for lbl in edge_labels if lbl not in used_labels]
            if not available:
                continue
            edge_label = rng.choice(available)
            G.add_edge(parent, node, label=edge_label)
            connected.add(node)

    # Add extra edges randomly (can create cycles, but root remains unique source)
    for u in nodes:
        used_labels = {data["label"] for _, data in G[u].items()}
        available_labels = [
            lbl for lbl in edge_labels if lbl not in used_labels]
        for v in nodes:
            if not available_labels:
                break
            if u != v and not G.has_edge(u, v) and rng.random() < extra_edge_prob:
                edge_label = rng.choice(available_labels)
                G.add_edge(u, v, label=edge_label)
                available_labels.remove(edge_label)

    return G, root


def random_osf_term(num_nodes: int,
                    sorts: list[Sort | str],
                    features: list[Feature | str],
                    extra_feature_prob: float = 0.3,
                    seed: int = 1) -> Term:

    def visit(node):
        if node in seen:
            return Term(X=node)
        seen.add(node)
        sort = G.nodes[node]["label"]
        subterms = {v['label']: [visit(k)] for k, v in G[node].items()}
        return Term(node, sort, subterms)

    seen = set()
    G, root = random_osf_graph(
        num_nodes, sorts, features, extra_feature_prob, seed)
    return visit(root)
