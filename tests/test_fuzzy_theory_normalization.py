#!/usr/bin/env python3

import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import OsfTheoryParser, OsfTermParser, parse_term
from fosf.reasoning import TheoryTermNormalizer
from fosf.syntax.terms import NormalTerm

@parameterized_class([
    {"test_file": "1.fosf", "close": True, "alpha": 0.2},
    {"test_file": "2.fosf", "close": True, "alpha": 0.2},
])
class TestClauseNormalizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = OsfTheoryParser()
        cls.term_parser = OsfTermParser()
        cls.term_unifier = TheoryTermNormalizer()

    def test_term_unifier_taxonomy(self):
        theory_file = os.path.join(TEST_DIR, "programs/theory", self.test_file)
        term_file = theory_file.replace(".fosf", ".term.fosf")
        solution_file = os.path.join(TEST_DIR, "solutions/theory", self.test_file+".sol")
        with open(theory_file, "r") as f:
            theory = self.parser.parse(f.read().strip(), ensure_closed=self.close)

        with open(term_file, "r") as f:
            term = self.term_parser.parse(f.read().strip())

        with open(solution_file, "r") as f:
            sol_unifier = parse_term(f.read().strip(), create_using=NormalTerm)

        unifier, alpha = self.term_unifier.normalize(term, theory, normalize_first=True,
                                                     return_degree=True)

        self.assertTrue(sol_unifier.equivalent_to(unifier))
        self.assertTrue(unifier.equivalent_to(sol_unifier))
        self.assertEqual(alpha, self.alpha)

if __name__ == "__main__":
    unittest.main()
