#!/usr/bin/env python3

import itertools
import os
import unittest

import networkx as nx
from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import TaxonomyParser
from fosf.utils.graph import maximal_lower_bounds


@parameterized_class([
    {"test_file": "1.txt"},
    {"test_file": "2.txt"},
    {"test_file": "random_20.txt"},
    {"test_file": "random_50.txt"},
    # {"test_file": "random_100.txt"},
    # {"test_file": "random_200.txt"},
    # {"test_file": "random_500.txt"},
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
            for supersort in nx.descendants(self.taxonomy.graph, sort):
                self.assertTrue(self.taxonomy.is_subsort(sort, supersort))

    def test_supersort(self):
        for sort in self.taxonomy.graph:
            for subsort in nx.ancestors(self.taxonomy.graph, sort):
                self.assertTrue(self.taxonomy.is_subsort(subsort, sort))

    def test_not_subsort(self):
        for sort in self.taxonomy.graph:
            descendants =  nx.descendants(self.taxonomy.graph, sort)
            incomparables = (self.nodes - descendants) - {sort}
            for incomparable in incomparables:
                self.assertFalse(self.taxonomy.is_subsort(sort, incomparable))

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
