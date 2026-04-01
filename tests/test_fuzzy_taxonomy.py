#!/usr/bin/env python3

from collections import defaultdict
import itertools
import os
import unittest

import networkx as nx
from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import TaxonomyParser
from fosf.syntax import FrozenDisjunctiveSort
from fosf.utils.graph import maximal_lower_bounds


def nx_path_degree(graph, u, v):
    max_weight = 0
    for path in nx.all_simple_paths(graph, u, v):
        path_weight = 1
        for u, v in zip(path, path[1:]):
            weight = graph[u][v]['weight']
            path_weight = min(weight, path_weight)
        max_weight = max(path_weight, max_weight)
    return max_weight


@parameterized_class([
    {"test_file": "fuzzy_random_10.txt"},
    {"test_file": "fuzzy_random_20.txt"},
    {"test_file": "fuzzy_random_50.txt"},
    # {"test_file": "fuzzy_random_100.txt"},
    # {"test_file": "fuzzy_random_200.txt"},
    # {"test_file": "fuzzy_random_500.txt"},
])
class TestTaxonomy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        parser = TaxonomyParser()
        taxonomy_file = os.path.join(TEST_DIR, "taxonomies", cls.test_file)
        with open(taxonomy_file, "r") as f:
            cls.taxonomy = parser.parse(f.read())
        cls.nodes = cls.taxonomy.graph.nodes()

    def test_subsort(self):
        for sort in self.taxonomy.graph:
            self.assertTrue(self.taxonomy.is_subsort(sort, sort))
            self.assertEqual(self.taxonomy.degree(sort, sort), 1)
            for supersort in nx.descendants(self.taxonomy.graph, sort):
                self.assertTrue(self.taxonomy.is_subsort(sort, supersort))
                tax_degree = self.taxonomy.degree(sort, supersort)
                nx_degree = nx_path_degree(self.taxonomy.graph, sort, supersort)
                self.assertEqual(tax_degree, nx_degree)

    def test_supersort(self):
        for sort in self.taxonomy.graph:
            for subsort in nx.ancestors(self.taxonomy.graph, sort):
                self.assertTrue(self.taxonomy.is_subsort(subsort, sort))
                tax_degree = self.taxonomy.degree(subsort, sort)
                nx_degree = nx_path_degree(self.taxonomy.graph, subsort, sort)
                self.assertEqual(tax_degree, nx_degree)

    def test_not_subsort(self):
        for sort in self.taxonomy.graph:
            descendants =  nx.descendants(self.taxonomy.graph, sort)
            incomparables = (self.nodes - descendants) - {sort}
            for incomparable in incomparables:
                self.assertFalse(self.taxonomy.is_subsort(sort, incomparable))
                tax_degree = self.taxonomy.degree(sort, incomparable)
                self.assertEqual(tax_degree, 0)

    def test_multi_degree(self):
        sources = list(self.taxonomy.graph[self.taxonomy.bot])
        sinks = list(self.taxonomy.graph.pred[self.taxonomy.top])
        degrees = self.taxonomy.degree(sources, sinks)
        nx_degrees = defaultdict(dict)

        iter_source_iter_targets_degrees = self.taxonomy.degree(sources, sinks)
        for source in sources:
            iter_targets_degrees = self.taxonomy.degree(source, sinks)
            for sink in sinks:
                iter_sources_degrees = self.taxonomy.degree(sources, sink)
                iter_source_iter_targets_degree = iter_source_iter_targets_degrees[source][sink]
                iter_targets_degree = iter_targets_degrees[sink]
                degree = degrees[source][sink]
                nx_degree = nx_path_degree(self.taxonomy.graph, source, sink)
                nx_degrees[source][sink] = nx_degree
                self.assertEqual(degree, nx_degree)
                self.assertEqual(iter_source_iter_targets_degree, nx_degree)
                self.assertEqual(iter_targets_degree, nx_degree)

        for sink in sinks:
            iter_sources_degrees = self.taxonomy.degree(sources, sink)
            for source in sources:
                nx_degree = nx_degrees[source][sink]
                iter_sources_degree = iter_sources_degrees[source][sink]
                self.assertEqual(iter_sources_degree, nx_degree)

        sources_sort = FrozenDisjunctiveSort(*sources)
        sinks_sort = FrozenDisjunctiveSort(*sinks)

        disj_degree = self.taxonomy.degree(sources_sort, sinks_sort)
        disj_nx_degree = min(max(nx_degrees[source][sink] for sink in sinks)
                             for source in sources)
        nx_degrees[sources_sort][sinks_sort] = disj_nx_degree
        self.assertEqual(disj_degree, disj_nx_degree)

        for source in sources:
            disj_target_degree = self.taxonomy.degree(source, sinks_sort)
            nx_disj_target_degree = max(nx_degrees[source][sink] for sink in sinks)
            nx_degrees[source][sinks_sort] = nx_disj_target_degree
            self.assertEqual(disj_target_degree, nx_disj_target_degree)

        for sink in sinks:
            disj_source_degree = self.taxonomy.degree(sources_sort, sink)
            nx_disj_source_degree = min(nx_degrees[source][sink] for source in sources)
            nx_degrees[sources_sort][sink] = nx_disj_source_degree
            self.assertEqual(disj_source_degree, nx_disj_source_degree)

        mixed_sources = [sources_sort, *sources]
        iterable_source_disj_target_degrees = self.taxonomy.degree(mixed_sources, sinks_sort)
        for source in mixed_sources:
            tax_degree = iterable_source_disj_target_degrees[source][sinks_sort]
            nx_degree = nx_degrees[source][sinks_sort]
            self.assertEqual(tax_degree, nx_degree)

        for sink in sinks:
            iterable_source_single_target_degrees = self.taxonomy.degree(mixed_sources, sink)
            for source in sources:
                tax_degree = iterable_source_single_target_degrees[source][sink]
                nx_degree = nx_degrees[source][sink]
                self.assertEqual(tax_degree, nx_degree)

        mixed_targets = [sinks_sort, *sinks]
        disj_source_iterable_target_degrees = self.taxonomy.degree(sources_sort, mixed_targets)
        for target in mixed_targets:
            tax_degree = disj_source_iterable_target_degrees[target]
            nx_degree = nx_degrees[sources_sort][target]
            self.assertEqual(tax_degree, nx_degree)

        iterables_degrees = self.taxonomy.degree(mixed_sources, mixed_targets)
        for s in mixed_sources:
            for t in mixed_targets:
                tax_degree = iterables_degrees[s][t]
                nx_degree = nx_degrees[s][t]
                self.assertEqual(tax_degree, nx_degree)

    def test_glb(self):
        # this test assumes that the function maximal_lower_bounds works correctly
        # We cannot use Networkx's lowest_common_ancestor, since it returns a
        # representative LCA, and not the set of all maximal lower bounds
        for s, t in itertools.combinations(self.nodes, 2):
            tax_glbs = self.taxonomy.glb(s, t)
            mlbs = maximal_lower_bounds(self.taxonomy.graph, s, t)
            if len(mlbs) == 1:
                self.assertEqual(tax_glbs, mlbs.pop())
            else:
                self.assertEqual(tax_glbs.value, mlbs)


if __name__ == '__main__':
    unittest.main()
