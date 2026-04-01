#!/usr/bin/env python3

import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import UnificationParser, OsfTermParser, parse_term
from fosf.reasoning import unify_terms, TermUnifier
from fosf.syntax.terms import NormalTerm

@parameterized_class([
    {"test_file": "1.fosf", "alpha": 0.2},
    {"test_file": "2.fosf", "alpha": 0.8},
    {"test_file": "3.fosf", "alpha": 0.4},
    {"test_file": "4.fosf", "alpha": 0.6},
    {"test_file": "5.fosf", "alpha": 0.5},
])
class TestClauseNormalizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = UnificationParser()
        cls.term_parer = OsfTermParser()
        cls.term_unifier = TermUnifier()

    def test_term_unifier_taxonomy(self):
        sol_alpha = self.alpha
        program_file = os.path.join(TEST_DIR, "programs/term", self.test_file)
        solution_file = os.path.join(TEST_DIR, "solutions/term", self.test_file+".sol")
        with open(program_file, "r") as f:
            tax, term1, term2 = self.parser.parse(f.read().strip())

        with open(solution_file, "r") as f:
            sol_unifier = parse_term(f.read().strip(), create_using=NormalTerm)

        unifier = unify_terms([term1, term2], tax, rename_terms=True)
        unifier2, alpha = self.term_unifier.unify([term1, term2], tax, rename_terms=True,
                                           return_degree=True)
        self.assertEqual(alpha, sol_alpha)
        self.assertTrue(sol_unifier.equivalent_to(unifier))
        self.assertTrue(sol_unifier.equivalent_to(unifier2))
        self.assertTrue(unifier.equivalent_to(sol_unifier))
        self.assertTrue(unifier2.equivalent_to(sol_unifier))
        self.assertTrue(unifier.equivalent_to(unifier2))
        self.assertTrue(unifier2.equivalent_to(unifier))

        unifier = unify_terms([term2, term1], tax, rename_terms=True)
        unifier2, alpha = self.term_unifier.unify([term2, term1], tax, rename_terms=True,
                                           return_degree=True)
        self.assertEqual(alpha, sol_alpha)
        self.assertTrue(sol_unifier.equivalent_to(unifier))
        self.assertTrue(sol_unifier.equivalent_to(unifier2))
        self.assertTrue(unifier.equivalent_to(sol_unifier))
        self.assertTrue(unifier2.equivalent_to(sol_unifier))
        self.assertTrue(unifier.equivalent_to(unifier2))
        self.assertTrue(unifier2.equivalent_to(unifier))


if __name__ == "__main__":
    unittest.main()
