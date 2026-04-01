#!/usr/bin/env python3

from collections import defaultdict, deque
from typing import overload

from fosf.reasoning import TermUnifier
from fosf.syntax.base import Tag, Sort, Feature
from fosf.syntax.constraints import Constraint, FeatureConstraint, SortConstraint
from fosf.syntax.taxonomy import SortTaxonomy, FuzzySortTaxonomy
from fosf.syntax.terms import Term, NormalTerm
from fosf.syntax.theory import OsfTheory


class _Frame:

    def __init__(self, tag: Tag):
        self.tag = tag
        self.local_tags = defaultdict(set)  # Map global X to local Ys
        self.global_tag = dict()           # Map local Y to global X
        self.main_sort: Sort

    def pairs(self):
        for x, ys in self.local_tags.items():
            for y in ys:
                yield (x, y)

    def __str__(self):
        _locals = ", ".join([f"{Y}/{X}" for Y, X in self.pairs()])
        return f"{self.tag}:{self.main_sort} [{_locals}]"

    def __repr__(self):
        _locals = ", ".join([f"{Y}/{X}" for Y, X in self.pairs()])
        return f"{self.tag}:{self.main_sort} [{_locals}]"


class TheoryTermNormalizer:
    """
    Class implementing OSF theory normalization according to the constraint normalization
    rules of :cite:`AitKaci1997`. Additionally, it implements the computation of the
    satisfaction degree of an OSF term with respect to the constraints of the OSF theory.

    Note
    ----
    A *global tag* is a tag appearing in an OSF term. A *local tag* is a theory tag.
    """

    def __init__(self):
        """
        Attributes
        ----------
        taxonomy : SortTaxonomy
            A backgrond (fuzzy) sort subsumption taxonomy.
        theory : OsfTheory
            The OSF theory used for normalization.
        rep_to_feats : dict[Tag, dict[Feature, Tag]]
            A dict mapping each tag to a feature-tag map. Represents the features
            materialized for each tag, and their corresponding value.
        frames : dict[Tag, _Frame]
            A dict maping each global tag to its principal frame.
        global_to_frames : dict[Tag, set[Tag]]
            A dict mapping each global tag ``X`` to the frames where ``X`` appears.
        eq_queue : deque[tuple[Tag, Tag]]
            High-priority queue, holding equality constraints to be processed.
        queue : deque[Constraint]
            Queue, holding the rest of the constraints to be processed.
        rule_9_stack : dict[Tag, Feature]
            Low-priority stack, delaying the rule-9 applications which can cause the
            normalization to diverge.
        """
        self.taxonomy: SortTaxonomy
        # X.f = Y -> self.rep_to_feats[X][f] = Y
        self.rep_to_feats: dict[Tag, dict[Feature, Tag]]

        # For union-find
        self._parents: dict
        self._indices: dict
        self._cost: dict

        # Theory for normalization
        self.theory: OsfTheory
        # Map a tag to the frames where it appears
        self.global_to_frames: dict[Tag, set[Tag]]
        # Map a tag to their main frame
        self.frames: dict[Tag, _Frame]

        self.eq_queue: deque[tuple[Tag, Tag]]
        self.queue: deque[Constraint]
        self.rule_9_stack: dict[Tag, Feature]

    @overload
    def normalize(self, term: Term, theory: OsfTheory, normalize_first: bool,
                  return_degree=False) -> NormalTerm: ...

    @overload
    def normalize(self, term: Term, theory: OsfTheory, normalize_first: bool,
                  return_degree=True) -> tuple[NormalTerm, float]: ...

    # Main method
    def normalize(self, term: Term,
                  theory: OsfTheory,
                  normalize_first: bool = True,
                  return_degree: bool = False) -> NormalTerm | tuple[NormalTerm, float]:
        """
        Normalize an input (normal) OSF term with respect to an OSF theory.

        OSF theory normalization ensures that an input (normal) OSF term satisfies the
        constraints of an OSF theory.

        Parameters
        ----------
        term : Term
        theory : OsfTheory
        normalize_first : bool, default=True
            If True, make sure that the input term is in Normal form.
        return_degree: bool, default=False
            If True, return the satisfaction degree of the normalized OSF term with
            respect to the OSF theory.
        """

        cn = None
        if normalize_first:
            cn = TermUnifier()
            term = cn.normalize(term, theory.taxonomy)
        self._init_structures(term, theory, cn)

        root = term.X

        for c in term.generate_constraints():
            self.queue.append(c)

        while self.eq_queue or self.queue or self.rule_9_stack:
            if self.eq_queue:
                X, Y = self.eq_queue.popleft()
                consistent = self._process_equality_constraint(X, Y)
            elif self.queue:
                consistent = self._process_constraint(self.queue.popleft())
            else:
                X, f = self.rule_9_stack.popitem()
                Z = self._new_tag()
                consistent = self._process_feature_constraint(X, f, Z)
            if not consistent:
                FAIL_TAG = Tag("_FAIL")
                return NormalTerm(FAIL_TAG, self.taxonomy.bot)

        output = self._build_output(root)
        if return_degree:
            if isinstance(self.taxonomy, FuzzySortTaxonomy):
                return output, self._subsumption_degree()
            return output, 1.0
        return output

    def _init_structures(self, clause, theory, cn=None):
        self.taxonomy = theory.taxonomy
        self.rep_to_feats = defaultdict(lambda: dict())

        # For union-find
        if cn:
            self._parents = cn._parents.copy()  # TODO keep copy?
            self._indices = cn._indices.copy()
        else:
            self._parents = {}
            self._indices = {}
            for X in clause.tags():
                self._add_tag(X)
        self._cost = defaultdict(lambda: 0)

        self.theory = theory
        self.global_to_frames = defaultdict(set)
        self.frames = dict()

        self.tag_counter = 0
        self.eq_queue = deque()  # High priority constraints
        self.queue = deque()
        self.rule_9_stack = dict()

    # Union-find methods
    def _add_tag(self, X: Tag):
        if X in self._indices:
            return
        self._parents[X] = X
        self._indices[X] = len(self._indices)

    def deref_tag(self, X: Tag) -> Tag:
        if X not in self._indices:
            raise KeyError(X)
        parents = self._parents
        while self._indices[X] != self._indices[parents[X]]:
            parents[X] = parents[parents[X]]
            X = parents[X]
        return X

    def _merge_tags(self, X: Tag, Y: Tag) -> tuple[bool, Tag, Tag]:
        X, Y = self.deref_tag(X), self.deref_tag(Y)
        if self._indices[X] == self._indices[Y]:
            return False, X, Y
        # Merge Y into X or X into Y depending on cost
        fX = X in self.frames
        fY = Y in self.frames
        if (fX, self._cost[X], self._indices[Y]) < (fY, self._cost[Y], self._indices[X]):
            X, Y = Y, X
        self._parents[Y] = X
        return True, X, Y

    def _connected(self, X: Tag, Y: Tag) -> bool:
        return self._indices[self.deref_tag(X)] == self._indices[self.deref_tag(Y)]

    # Methods for processing constraints
    def _process_constraint(self, c: Constraint):
        consistent = True
        if isinstance(c, SortConstraint):
            consistent = self._process_sort_constraint(c.X, c.s)
        if isinstance(c, FeatureConstraint):
            consistent = self._process_feature_constraint(c.X, c.f, c.Y)
        return consistent

    def _process_sort_constraint(self, X, s):
        X = self.deref_tag(X)
        if X in self.frames:
            # Refine frame
            current_s = self.frames[X].main_sort
            if self.taxonomy.is_subsort(current_s, s):
                return True
            glb = self.taxonomy.glb(s, current_s)
            if glb == self.taxonomy.bot:
                return False
            self.frames[X].main_sort = glb
            Y_glb = self.theory.definitions[glb].X
            self._update_frame_locals(X, X, Y_glb)
            self._check_features(X, Y_glb)
            return True
        # Otherwise, initialize frame
        Y = self.theory.definitions[s].X
        self.frames[X] = _Frame(X)
        self.frames[X].main_sort = s
        self.frames[X].local_tags[X].add(Y)
        self.frames[X].global_tag[Y] = X
        self.global_to_frames[X].add(X)
        self._cost[X] += 1
        self._check_features(X, Y)  # TODO Necessary here?
        self._check_rule_9(X, Y, X)
        return True

    def _process_feature_constraint(self, X1, f, X2):
        X1, X2 = self.deref_tag(X1), self.deref_tag(X2)
        if f in self.rep_to_feats[X1]:
            X3 = self.deref_tag(self.rep_to_feats[X1][f])
            if X3 != X2:
                self.eq_queue.append((X2, X3))
            return True
        self.rep_to_feats[X1][f] = X2
        self._cost[X1] += 1
        # Apply rule 5
        for X in self.global_to_frames[X1]:
            updates = set()
            for Y1 in self.frames[X].local_tags[X1]:
                if f in self.theory.features(Y1):
                    Y2 = self.theory.features(Y1)[f]
                    sort = self.theory.sort(Y2)
                    if sort is not None:
                        self.queue.append(SortConstraint(X2, sort))
                    if X1 == X2:
                        # self._update_frame_locals(X, X2, Y2) would
                        # modify self.frames[X].local_tags[X1]
                        # resulting in a RuntimeError
                        # We delay calling the method in this case
                        updates.add((X, X2, Y2))
                    else:
                        self._update_frame_locals(X, X2, Y2)
            for args in updates:
                self._update_frame_locals(*args)
        return True

    def _process_equality_constraint(self, X1, X2):
        merged, X1, X2 = self._merge_tags(X1, X2)
        if not merged:
            return True
        # Merge features
        for f, Z in self.rep_to_feats[X2].items():
            Z = self.deref_tag(Z)
            if f in self.rep_to_feats[X1]:
                Z1 = self.deref_tag(self.rep_to_feats[X1][f])
                if Z1 != Z:
                    self.eq_queue.append((Z1, Z))
            else:
                self.rep_to_feats[X1][f] = Z
        # Merge frames (either both exist, or only X1's exists, or neither)
        if X1 in self.frames and X2 in self.frames:
            frame1 = self.frames[X1]
            frame2 = self.frames[X2]
            ss1 = frame1.main_sort
            ss2 = frame2.main_sort
            s_glb = self.theory.taxonomy.glb(ss1, ss2)
            frame1.main_sort = s_glb
            if s_glb == self.taxonomy.bot:
                return False
            Yglb = self.theory.definitions[s_glb].X
            for X, Y in frame2.pairs():
                if X == X2 or Y == X2:
                    continue
                self.global_to_frames[X].discard(X2)
                self._update_frame_locals(X1, X, Y)
            self._update_frame_locals(X1, X1, Yglb)
            self._check_features(X1, Yglb)

        for X in self.global_to_frames[X2]-{X1, X2}:
            frame = self.frames[X]
            Y1s = frame.local_tags[X2]
            for Y1 in Y1s:
                self._update_frame_locals(X, X1, Y1)
            frame.local_tags.pop(X2)

        return True

    # Utilities and data structure maintenance
    def _new_tag(self):
        while (tag := Tag(f"Z{self.tag_counter}")) in self._indices:
            self.tag_counter += 1
        self._add_tag(tag)
        return tag

    def _check_common_features(self, X: Tag, Y1: Tag, Y2: Tag):
        Y1_features = self.theory.features(Y1)
        Y2_features = self.theory.features(Y2)
        for f in Y1_features.keys() & Y2_features.keys():
            self.rule_9_stack[X] = f

    def _check_features(self, X: Tag, Y: Tag):
        # TODO: check efficiency: is it always necessary to recurse?
        frame_X = X
        stack = {(X, Y)}
        seen = set()
        while stack:
            X, Y = stack.pop()
            if (X, Y) in seen:
                continue
            seen.add((X, Y))
            for f, X1 in self.rep_to_feats[X].items():
                X1 = self.deref_tag(X1)
                if f in self.theory.features(Y):
                    Y1 = self.theory.features(Y)[f]
                    self._update_frame_locals(frame_X, X1, Y1)
                    stack.add((X1, Y1))
                    s1 = self.theory.sort(Y1)
                    if s1 is not None:
                        c = SortConstraint(X1, s1)
                        self.queue.append(c)

    def _update_frame_locals(self, X, X1, Y1):
        # Check local tags associatd with X1 in X's frame
        frame = self.frames[X]
        if X1 not in frame.local_tags:
            frame.local_tags[X1].add(Y1)
        else:
            current_Y1s = frame.local_tags[X1]
            if Y1 in current_Y1s:
                return
            add = False
            to_remove = set()
            for current_Y1 in current_Y1s:
                if self.theory.tag_taxonomy.is_subsort(current_Y1, Y1):
                    # We already have a more specific version of Y1 in this frame
                    # No need to check anything else
                    add = False
                    break
                add = True
                if self.theory.tag_taxonomy.is_subsort(Y1, current_Y1):
                    to_remove.add(current_Y1)
                else:
                    # rule 9
                    self._check_common_features(X1, current_Y1, Y1)
            frame.local_tags[X1].difference_update(to_remove)
            if add:
                frame.local_tags[X1].add(Y1)
                self._check_rule_9(X1, Y1, tag_to_exclude=X)

        # Check the global tag for Y1 in X
        if Y1 not in frame.global_tag:
            frame.global_tag[Y1] = X1
        else:
            current_X1 = self.deref_tag(frame.global_tag[Y1])
            if X1 != current_X1:
                self.eq_queue.append((X1, current_X1))
        self.global_to_frames[X1].add(X)

    def _check_rule_9(self, X: Tag, Y: Tag, tag_to_exclude=None):
        done = set()
        for tag in self.global_to_frames[X]-{tag_to_exclude}:
            current_locals = self.frames[tag].local_tags[X]
            if Y in current_locals:
                return
            for Yp in current_locals:
                if Yp in done:
                    continue
                done.add(Yp)
                if self.theory.tag_taxonomy.is_subsort(Yp, Y):
                    # We already have a more specific version of Y in this frame
                    # No need to check anything else
                    break
                if self.theory.tag_taxonomy.is_subsort(Y, Yp):
                    # Our tag is more specific that Yp, but might have more features
                    # We continue checking the others
                    continue
                self._check_common_features(X, Y, Yp)

    def _build_output(self, root: Tag) -> NormalTerm:
        def visit(tag):
            rep = self.deref_tag(tag)
            if rep in seen:
                return NormalTerm(rep)
            seen.add(rep)
            if rep in self.frames:
                sort = self.frames[rep].main_sort
            else:
                sort = self.taxonomy.top
            subterms = {f: visit(other)
                        for f, other in self.rep_to_feats[rep].items()}
            return NormalTerm(rep, sort, subterms)
        seen = set()
        return visit(root)

    def _subsumption_pairs(self):
        derefed_tags = {self.deref_tag(tag) for tag in self._indices}
        sub_pairs = defaultdict(set)
        for tag in derefed_tags:
            frame = self.frames[tag]
            for X, Y in frame.pairs():
                X = self.deref_tag(X)
                if X not in self.frames:
                    continue
                s = self.frames[X].main_sort
                t = self.theory.sort(Y)
                if s != t:
                    sub_pairs[s].add(t)
        return sub_pairs

    def _subsumption_degree(self) -> float:
        sub_pairs = self._subsumption_pairs()
        if not sub_pairs:
            # if sub_pairs is empty, s and t in _subsumption_pairs were always equal
            return 1.0
        sources = sub_pairs.keys()
        targets = {val for values in sub_pairs.values() for val in values}
        degrees = self.theory.taxonomy.degree(sources, targets)
        alpha = min(degrees[s][t] for s, ts in sub_pairs.items() for t in ts)
        return alpha
