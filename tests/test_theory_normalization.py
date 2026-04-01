#!/usr/bin/env python3

import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import OsfTheoryParser, OsfTermParser, parse_term
from fosf.reasoning import TheoryTermNormalizer
from fosf.syntax.terms import NormalTerm

@parameterized_class([
    {"test_file": "1.osf",  "close": False},
    {"test_file": "2.osf",  "close": False},
    {"test_file": "3.osf",  "close": False},
    {"test_file": "4.osf",  "close": False},
    {"test_file": "5.osf",  "close": False},
    {"test_file": "6.osf",  "close": False},
    {"test_file": "7.osf",  "close": False},
    {"test_file": "8.osf",  "close": False},
    {"test_file": "9.osf",  "close": False},
    {"test_file": "10.osf", "close": False},
])
class TestClauseNormalizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parser = OsfTheoryParser()
        cls.term_parser = OsfTermParser()
        cls.term_unifier = TheoryTermNormalizer()

    def test_term_unifier_taxonomy(self):
        theory_file = os.path.join(TEST_DIR, "programs/theory", self.test_file)
        term_file = theory_file.replace(".osf", ".term.osf")
        solution_file = os.path.join(TEST_DIR, "solutions/theory", self.test_file+".sol")
        with open(theory_file, "r") as f:
            theory = self.parser.parse(f.read().strip(), ensure_closed=self.close)

        with open(term_file, "r") as f:
            term = self.term_parser.parse(f.read().strip())

        with open(solution_file, "r") as f:
            sol_unifier = parse_term(f.read().strip(), create_using=NormalTerm)

        unifier = self.term_unifier.normalize(term, theory)
        unifier2 = self.term_unifier.normalize(term, theory, normalize_first=False)

        self.assertTrue(sol_unifier.equivalent_to(unifier))
        self.assertTrue(unifier.equivalent_to(sol_unifier))
        self.assertTrue(sol_unifier.equivalent_to(unifier2))
        self.assertTrue(unifier2.equivalent_to(sol_unifier))

if __name__ == "__main__":
    unittest.main()
