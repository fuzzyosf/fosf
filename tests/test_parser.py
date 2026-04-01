#!/usr/bin/env python3

import glob
import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import NormalizationParser
from fosf.syntax import Sort, Tag, Feature
from fosf.syntax.constraints import (SortConstraint, FeatureConstraint, EqualityConstraint,
                                     Clause, Constraint)
from fosf.syntax.taxonomy import SortTaxonomy

test_files = glob.glob(os.path.join(TEST_DIR, "programs/clause", "*"))
test_files = [ {"test_file" : f} for f in test_files]


@parameterized_class(test_files)
class TestParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = NormalizationParser()

    def test_clause_parser(self):
        with open(self.test_file, "r") as f:
            _, clause = self.parser.parse(f.read().strip())
            self.assertIsInstance(clause, Clause)
            for c in clause:
                self.assertIsInstance(c, Constraint)
                if isinstance(c, SortConstraint):
                    self.assertIsInstance(c.X, Tag)
                    self.assertIsInstance(c.s, Sort)
                elif isinstance(c, FeatureConstraint):
                    self.assertIsInstance(c.X, Tag)
                    self.assertIsInstance(c.Y, Tag)
                    self.assertIsInstance(c.f, Feature)
                elif isinstance(c, EqualityConstraint):
                    self.assertIsInstance(c.X, Tag)
                    self.assertIsInstance(c.Y, Tag)
                else:
                    self.assertFalse(True)


    def test_taxonomy_parser(self):
        with open(self.test_file, "r") as f:
            tax, _ = self.parser.parse(f.read().strip())
            self.assertIsInstance(tax, SortTaxonomy)
            for u, v in tax.graph.edges():
                self.assertIsInstance(u, Sort)
                self.assertIsInstance(v, Sort)
