#!/usr/bin/env python3

import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import OsfTheoryParser


@parameterized_class([
    {"test_file": "1.osf"},
    {"test_file": "2.osf"},
])
class TestClauseNormalizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = OsfTheoryParser()

    def test_term_unifier_taxonomy(self):
        base_file = os.path.join(TEST_DIR, "programs/theory", self.test_file)
        closed_file = base_file.replace(".osf", "_closed.osf")
        closure_file = base_file.replace(".osf", "_to_close.osf")
        with open(closed_file, "r") as f:
            closed_theory = self.parser.parse(f.read().strip())

        with open(closure_file, "r") as f:
            theory_to_close = self.parser.parse(f.read().strip(), ensure_closed=True)

        for s, def_ in closed_theory.definitions.items():
            self.assertIn(s, theory_to_close.definitions)
            c_def_ = theory_to_close.definitions[s]
            self.assertTrue(def_.equivalent_to(c_def_))


if __name__ == "__main__":
    unittest.main()
