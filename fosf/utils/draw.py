#!/usr/bin/env python3

from collections import defaultdict
import os

import networkx as nx
import pygraphviz as pgv

from fosf.config import PICS_DIR
from fosf.reasoning import TermUnifier, ClauseNormalizer
from fosf.syntax.constraints import Clause
from fosf.syntax.taxonomy import (BaseTaxonomy, TagTaxonomy,
                                  SortTaxonomy, FuzzySortTaxonomy)
from fosf.syntax.terms import Term


NODE_COLOR = "w"
FONTCOLOR = "#0f3861"
FONTSIZE = 20
WEIGHT_FONTSIZE = 14
COLORS = ["black", "red", "blue", "forestgreen", "pink", "violet",
          "orange", "purple", "cyan", "magenta", "yellow", "brown", "gray"]
HEX_COLORS = [
    "#FF389C", "#FF5733", "#FF8D1A", "#FFC300", "#C0FF00", "#75FF33", "#33FF57",
    "#33FFA8", "#33FFF3", "#33C4FF", "#3385FF", "#335BFF", "#6B33FF", "#A833FF",
    "#E633FF", "#FF33C4", "#FF336A", "#FF3333", "#FF6E5F", "#FF9DA4"]


def fig_setup(figsize=(7, 6)):
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111)
    return fig, ax


def no_border(ax):
    import matplotlib.pyplot as plt
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    plt.tight_layout()


def draw_graph(digraph, pos=None, font_color=FONTCOLOR, font_size=FONTSIZE,
               node_labels=None, node_color=NODE_COLOR, node_size=1000,
               edge_color="black", edge_width=2, return_pos=False):
    if pos is None:
        pos = nx.nx_agraph.graphviz_layout(digraph, 'dot')
    #
    nx.draw_networkx_nodes(digraph, pos, node_size=node_size,
                           node_color=node_color)
    nx.draw_networkx_edges(digraph, pos, width=edge_width,
                           edge_color=edge_color, arrows=True)
    nx.draw_networkx_labels(digraph, pos, font_size=font_size,
                            labels=node_labels, font_family="sans-serif",
                            font_color=font_color)
    if return_pos:
        return pos


def draw_weighted_graph(digraph, pos=None, font_color=FONTCOLOR, font_size=FONTSIZE,
                        node_labels=None, node_color=NODE_COLOR, node_size=1000,
                        edge_color="black", edge_width=2, label_pos=0.4, return_pos=False,
                        fuzzy_edge_color="red", fuzzy_edge_style="--"):
    if pos is None:
        pos = nx.nx_agraph.graphviz_layout(digraph, 'dot')
    #
    crisp_edges = [(a, b) for (a, b, w) in digraph.edges(
        data=True) if w['weight'] == 1]
    fuzzy_edges = [(a, b)
                   for (a, b, w) in digraph.edges(data=True) if w['weight'] < 1]
    nx.draw_networkx_nodes(digraph, pos, node_size=node_size,
                           node_color=node_color)
    nx.draw_networkx_edges(digraph, pos, width=edge_width, edgelist=crisp_edges,
                           edge_color=edge_color, arrows=True)
    nx.draw_networkx_edges(digraph, pos, width=edge_width, edgelist=fuzzy_edges,
                           edge_color=fuzzy_edge_color, style=fuzzy_edge_style, arrows=True)
    nx.draw_networkx_labels(digraph, pos, font_size=font_size,
                            labels=node_labels, font_family="sans-serif",
                            font_color=font_color)
    labels = nx.get_edge_attributes(digraph, 'weight')
    labels = {(u, v): round(labels[(u, v)], 2)
              for (u, v, d)
              in digraph.edges(data=True) if d["weight"] < 1}
    nx.draw_networkx_edge_labels(digraph, pos, font_color=fuzzy_edge_color, edge_labels=labels,
                                 label_pos=label_pos, font_size=WEIGHT_FONTSIZE)
    if return_pos:
        return pos


def draw_taxonomy(taxonomy: SortTaxonomy, pos=None, draw_bot=False, draw_top=False, **kwargs):
    digraph = taxonomy.graph.copy().reverse()
    if not draw_bot:
        digraph.remove_node(taxonomy.bot)
    if not draw_top:
        digraph.remove_node(taxonomy.top)
    draw_graph(digraph, pos=pos, **kwargs)


def draw_fuzzy_taxonomy(fuzzy_taxonomy: FuzzySortTaxonomy, pos=None, draw_bot=False,
                        draw_top=False, **kwargs):
    digraph = fuzzy_taxonomy.graph.copy().reverse()
    if not draw_bot:
        digraph.remove_node(fuzzy_taxonomy.bot)
    if not draw_top:
        digraph.remove_node(fuzzy_taxonomy.top)
    draw_weighted_graph(
        digraph, pos, fuzzy_edge_color='green', fuzzy_edge_style="-", **kwargs)


def _taxonomy_to_graphviz(taxonomy: BaseTaxonomy, drop=None, instances=False) -> nx.DiGraph:
    arrowstyle = "vee"
    style = 'solid'
    graph = nx.DiGraph()
    dummies_to_sorts = defaultdict(set)
    for u, v, w in taxonomy.graph.edges(data=True):
        w = w.get('weight', 1.0)
        w = w if w < 1 else ""
        graph.add_edge(v, u, label=w, style=style, dir="back",
                       fontcolor='red', arrowtail=arrowstyle)
    if drop == "top":
        graph.remove_node(taxonomy.top)
    elif drop == "bot":
        graph.remove_node(taxonomy.bot)
    elif drop == "both":
        graph.remove_node(taxonomy.top)
        graph.remove_node(taxonomy.bot)
    for node in graph.nodes():
        graph.nodes[node]['fontcolor'] = "#0F389C"
    if taxonomy.instances and instances:
        for instance, sorts in taxonomy.instances.items():
            graph.add_node(instance, fontcolor="black",
                           style="dotted", rank="max")
            for sort, degree in sorts.items():
                degree = degree if degree < 1 else ""
                graph.add_edge(sort, instance, style='dotted',
                               dir="none", label=degree)
    for dummy, sorts in dummies_to_sorts.items():
        edge_col = HEX_COLORS[dummy.value % len(HEX_COLORS)]
        sort1 = sorts.pop()
        while sorts:
            sort2 = sorts.pop()
            graph.add_edge(sort1, sort2, style='dashed',
                           dir="none", constraint=False, color=edge_col)
            sort1 = sort2
    return graph


def taxonomy_to_graphviz(taxonomy: BaseTaxonomy, drop=None, instances=False) -> pgv.AGraph:
    graph = _taxonomy_to_graphviz(taxonomy, drop, instances)
    A = nx.nx_agraph.to_agraph(graph)
    rank_max = []
    for n, data in graph.nodes(data=True):
        r = data.get("rank")
        if r is None:
            continue
        if r == "max":
            rank_max.append(n)
    if rank_max:
        sg = A.add_subgraph(rank="max")
        for node in rank_max:
            sg.add_node(node)
    return A


def osf_clause_to_graphviz(clause: Clause) -> pgv.AGraph:
    from fosf.utils.nx import osf_clause_to_nx
    graph = osf_clause_to_nx(clause)
    a = nx.nx_agraph.to_agraph(graph)
    return a


def osf_term_to_graphviz(term: Term) -> pgv.AGraph:
    return osf_clause_to_graphviz(term.to_clause())


def normalization_to_agraph(clause: Clause, taxonomy: SortTaxonomy,
                            clause_normalizer: ClauseNormalizer,
                            display_taxonomy=False) -> pgv.AGraph:
    from fosf.utils.nx import osf_clause_to_nx
    solved = clause_normalizer.normalize(clause, taxonomy)
    clauses = [solved, clause]
    graphs = [osf_clause_to_nx(clause) for clause in clauses]
    for graph, color in zip(graphs, COLORS):
        nx.set_node_attributes(graph, color, "color")
        nx.set_node_attributes(graph, color, "fontcolor")
        nx.set_edge_attributes(graph, color, "color")
        nx.set_edge_attributes(graph, color, "fontcolor")
    renaming = ("unif-", "clause-")
    g = nx.union_all(graphs, rename=renaming)
    color = COLORS[1]
    for tag in clause.tags:
        g.add_edge(f"clause-{tag}",
                   f"unif-{clause_normalizer.deref_tag(tag)}",
                   style="dotted", color=color)
    if display_taxonomy:
        if isinstance(taxonomy, FuzzySortTaxonomy):
            g.add_edges_from(_taxonomy_to_graphviz(
                taxonomy).edges(data=True))
        else:
            g.add_edges_from(_taxonomy_to_graphviz(taxonomy).edges(data=True))
    A = nx.nx_agraph.to_agraph(g)
    return A


def unification_to_agraph(terms: list[Term], taxonomy: SortTaxonomy,
                          display_taxonomy=False, rename_terms=True) -> pgv.AGraph:
    from fosf.utils.nx import osf_term_to_nx
    term_unifier = TermUnifier()
    unif = term_unifier.unify(terms, taxonomy, rename_terms=rename_terms)
    terms = [unif, *terms]
    graphs = [osf_term_to_nx(term) for term in terms]
    for graph, color in zip(graphs, COLORS):
        nx.set_node_attributes(graph, color, "color")
        nx.set_node_attributes(graph, color, "fontcolor")
        nx.set_edge_attributes(graph, color, "color")
        nx.set_edge_attributes(graph, color, "fontcolor")
    renaming = ("unif-", *[f"{i}-" for i, _ in enumerate(terms[1:])])
    g = nx.union_all(graphs, rename=renaming)
    if unif.s == taxonomy.bot:
        X = unif.X
        for term, prefix, color in zip(terms[1:], renaming[1:], COLORS[1:]):
            for tag in term.tags():
                g.add_edge(f"{prefix}{tag}", f"unif-{X}",
                           style="dotted", color=color)
    else:
        mappings = term_unifier.mappings
        for term, map_, prefix, color in zip(terms[1:], mappings, renaming[1:], COLORS[1:]):
            if isinstance(taxonomy, FuzzySortTaxonomy):
                g = __add_fuzzy_hom_edges(
                    g, term, map_, prefix, color, taxonomy, term_unifier)
            else:
                g = __add_hom_edges(g, term, map_, prefix, color, term_unifier)
    if display_taxonomy:
        if isinstance(taxonomy, FuzzySortTaxonomy):
            fuzzy_edges = _taxonomy_to_graphviz(
                taxonomy).edges(data=True)
            g.add_edges_from(fuzzy_edges)
        else:
            g.add_edges_from(_taxonomy_to_graphviz(taxonomy).edges(data=True))
    A = nx.nx_agraph.to_agraph(g)
    return A


def __add_hom_edges(g, term, map_, prefix, color, term_unifier):
    def rename(x): return x
    if map_:
        def rename(x): return map_[x]
    for tag in term.tags():
        solved_tag = term_unifier.deref_tag(rename(tag))
        g.add_edge(f"{prefix}{tag}", f"unif-{solved_tag}",
                   style="dotted", color=color)
    return g


def __add_fuzzy_hom_edges(g, term, map_, prefix, color, taxonomy, term_unifier):
    def rename(x): return x
    if map_:
        def rename(x): return map_[x]
    d = defaultdict(set)
    for subterm in term.dfs():
        tag = subterm.X
        solved_tag = term_unifier.deref_tag(rename(tag))
        solved_sort = term_unifier.taxonomy._decode(term_unifier.rep_to_code[solved_tag])
        sort = subterm.s
        if subterm.s is None:
            sort = taxonomy.top
        d[(tag, solved_tag, solved_sort)].add(sort)
    for (tag, solved_tag, solved_sort), sorts in d.items():
        degree = min(taxonomy.degree(solved_sort, sorts).values())
        if degree < 1:
            g.add_edge(f"{prefix}{tag}", f"unif-{solved_tag}", style="dotted",
                       color=color, label=degree, fontcolor=color)
        else:
            g.add_edge(f"{prefix}{tag}", f"unif-{solved_tag}", style="dotted",
                       color=color)
    return g


def graphviz_to_png(agraph: pgv.AGraph, filename=None, folder=None):
    if filename is None:
        filename = "temp_osfimage.png"
    if folder is None:
        os.makedirs(PICS_DIR, exist_ok=True)
        folder = PICS_DIR
    filename = os.path.join(folder, filename)
    agraph.draw(filename, prog="dot")
    return filename


def notebook_display(thing, filename=None, folder=None, **kwargs):
    from IPython.display import display as ipdisplay, Image
    if isinstance(thing, (SortTaxonomy, TagTaxonomy)):
        A = taxonomy_to_graphviz(thing, **kwargs)
    elif isinstance(thing, Clause):
        A = osf_clause_to_graphviz(thing)
    elif isinstance(thing, Term):
        A = osf_term_to_graphviz(thing)
    elif isinstance(thing, pgv.AGraph):
        A = thing
    elif isinstance(thing, nx.DiGraph):
        A = nx.nx_agraph.to_agraph(thing)
    else:
        raise TypeError(f"{type(thing)} not valid in notebook_display")
    filename = graphviz_to_png(A, filename, folder)
    ipdisplay(Image(filename))
