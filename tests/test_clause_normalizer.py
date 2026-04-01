#!/usr/bin/env python3

import json
import os
import unittest

from parameterized import parameterized_class

from fosf.config import TEST_DIR
from fosf.parsers import NormalizationParser
from fosf.reasoning import ClauseNormalizer
from fosf.syntax import Sort, FrozenDisjunctiveSort, Tag, Feature
from fosf.utils.graph import free_lattice_taxonomy


@parameterized_class([
    {"test_file": "1.osf"},
    {"test_file": "2.osf"},
    {"test_file": "3.osf"},
    {"test_file": "4.osf"},
    {"test_file": "5.osf"},
    {"test_file": "5.osf"},
    {"test_file": "6.osf"},
    {"test_file": "7.osf"},
    {"test_file": "8.osf"},
    {"test_file": "9.osf"},
])
class TestClauseNormalizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cn = ClauseNormalizer()
        cls.parser = NormalizationParser()

    @classmethod
    def shared_stuff(cls, solution_dict):
        sol_features_ = solution_dict["features"]
        sol_features = dict()
        for tag, vs in sol_features_.items():
            sol_features[Tag(tag)] = dict()
            for f, other in vs.items():
                sol_features[Tag(tag)][Feature(f)] = Tag(other)
        sol_rep_ = solution_dict["rep"]
        sol_rep = dict()
        for k, v in sol_rep_.items():
            sol_rep[Tag(k)] = Tag(v)
        sol_subsets_ = solution_dict["subsets"]
        sol_subsets = dict()
        for k, v in sol_subsets_.items():
            sol_subsets[Tag(k)] = [Tag(x) for x in v]
        return sol_features, sol_rep, sol_subsets


    def test_clause_normalizer(self):
        program_file = os.path.join(TEST_DIR, "programs/clause", self.test_file)
        solution_file = os.path.join(TEST_DIR, "solutions/clause",
                                     self.test_file+".sol.json")
        with open(program_file, "r") as f:
            _, clause = self.parser.parse(f.read().strip())

        with open(solution_file, "r") as f:
            solution_dict = json.load(f)

        cn = self.cn
        tax = free_lattice_taxonomy(clause.sorts().union({Sort("bot")}))
        _ = cn.normalize(clause, tax)

        sol_sorts_ = solution_dict["sorts"]
        sol_sorts = dict()
        for c, v in sol_sorts_.items():
            sol_sorts[Tag(c)] = {Sort("+".join(sorted(str(s) for s in v)))}
        sol_features, sol_rep, sol_subsets = self.shared_stuff(solution_dict)

        for tag in cn._indices:
            # Check Equivalence classes
            uf_subset = {other for other in cn._indices if cn._connected(tag, other)}
            self.assertFalse(uf_subset.difference(sol_subsets[tag]))

            # Check sorts assignment
            cn_sorts = cn.taxonomy._decode(cn.rep_to_code[cn.deref_tag(tag)])
            if isinstance(cn_sorts, FrozenDisjunctiveSort):
                cn_sorts = set(sort for sort in cn_sorts.value)
            else:
                cn_sorts = set({cn_sorts})
            tag_sol_sorts = sol_sorts.get(sol_rep[tag], {tax.top})
            self.assertFalse(cn_sorts.difference(tag_sol_sorts))

            # Check feature assignments
            for f, v in cn.rep_to_feats[cn.deref_tag(tag)].items():
                v = cn.deref_tag(v)
                self.assertEqual(sol_rep[sol_features[sol_rep[tag]][f]], sol_rep[v])

            for f, v in sol_features[sol_rep[tag]].items():
                v = sol_rep[v]
                self.assertEqual(cn.deref_tag(cn.rep_to_feats[cn.deref_tag(tag)][f]), cn.deref_tag(v))

    def test_clause_normalizer_taxonomy(self):
        program_file = os.path.join(TEST_DIR, "programs/clause", self.test_file)
        solution_file = os.path.join(TEST_DIR, "solutions/clause",
                                     self.test_file+".sol_tax.json")
        with open(program_file, "r") as f:
            program = str(f.read().strip())
            tax, clause = self.parser.parse(program)

        with open(solution_file, "r") as f:
            solution_dict = json.load(f)

        cn = self.cn
        _ = cn.normalize(clause, tax)

        sol_sorts_ = solution_dict["sorts"]
        sol_sorts = dict()
        for c, v in sol_sorts_.items():
            if len(v) == 1:
                sol_sorts[Tag(c)] = {Sort(v[0])}
            else:
                sol_sorts[Tag(c)] = FrozenDisjunctiveSort(*v)
        sol_features, sol_rep, sol_subsets = self.shared_stuff(solution_dict)

        for tag in cn._indices:
            # Check Equivalence classes
            uf_subset = {other for other in cn._indices if cn._connected(tag, other)}
            self.assertFalse(uf_subset.difference(sol_subsets[tag]))

            # Check sorts assignment
            cn_sorts = cn.taxonomy._decode(cn.rep_to_code[cn.deref_tag(tag)])
            if isinstance(cn_sorts, FrozenDisjunctiveSort):
                cn_sorts = cn_sorts.value
            else:
                cn_sorts = {cn_sorts}
            tag_sol_sorts = sol_sorts.get(sol_rep[tag], {tax.top})
            self.assertFalse(cn_sorts.difference(tag_sol_sorts))

            # Check feature assignments
            for f, v in cn.rep_to_feats[cn.deref_tag(tag)].items():
                v = cn.deref_tag(v)
                self.assertEqual(sol_rep[sol_features[sol_rep[tag]][f]], sol_rep[v])

            for f, v in sol_features[sol_rep[tag]].items():
                v = sol_rep[v]
                self.assertEqual(cn.deref_tag(cn.rep_to_feats[cn.deref_tag(tag)][f]), cn.deref_tag(v))


if __name__ == "__main__":
    unittest.main()
