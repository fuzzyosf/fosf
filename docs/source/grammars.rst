EBNF grammars for parsing OSF structures
========================================

.. _base-grammar:

Base OSF Grammar
----------------

Defines rules for sorts, disjunctive sorts (sets of sorts), and features.
It is extended by all the other grammars.

In short:

- A sort is a sequence of characters starting with a lowercase letter, or a
  quoted string. E.g.: ``person``, ``student``, ``movie``, ...
- A feature is also a sequence of characters starting with a lowercase letter.
  E:g.: ``spouse``, ``directed_by``, ...
- Disjunctive sorts are sets ``{s1, ..., sn}`` of sorts.
- A tag is a sequence of characters starting with an uppercase letter. E.g.:
  ``X``, ``Y``, ``X0``, ...

.. literalinclude:: ../../fosf/parsers/grammars/base_osf.lark
   :language: perl
   :caption: fosf/parsers/grammars/base_osf.lark


.. _graph-grammar:

Graph Grammar
-------------

The graph grammar used by :func:`fosf.parsers.parse_graph`.

- Subsort declarations have shape ``s0 < s1``,
  meaning that ``s0`` is subsumed by ``s1``.
- Fuzzy subsort declarations have shape ``s0 < s1 (0.5)``,
  meaning that ``s0`` is subsumed by ``s1`` with degree 0.5
- Multiple sorts can appear to the left and right of ``<``. E.g.,
  ``s0, s1 < s3 (0.2), s4`` means that
  ``s0`` and ``s1`` are subsumed by ``s3`` (both with degree 0.2), and also by
  ``s4`` (implicitly with degree 1).

.. literalinclude:: ../../fosf/parsers/grammars/graph.lark
   :language: perl
   :caption: fosf/parsers/grammars/graph.lark


.. _taxonomy-grammar:

Taxonomy Grammar
----------------

The taxonomy grammar used by :func:`fosf.parsers.parse_taxonomy`.
It extends :ref:`graph-grammar` by adding rules to parse (fuzzy) instance
declarations, which must follow the (fuzzy) subsort declarations. (Fuzzy)
instance declarations have this shape:

- ``{ a, 0.5/b, c } < s0, s1``, meaning that ``a``, ``b`` and ``c`` all belong
  to the sorts ``s0`` and ``s1``. The membership degree of ``b`` with respect to
  ``s0`` and also ``s1`` is 0.5.


.. literalinclude:: ../../fosf/parsers/grammars/taxonomy.lark
   :language: perl
   :caption: fosf/parsers/grammars/taxonomy.lark


.. _term-grammar:

OSF Term Grammar
----------------

The OSF term grammar used by :func:`fosf.parsers.parse_term`. The following are
all examples of valid expressions for OSF terms.

- ``X:s``, a tagged term without subterms.
- ``s(g -> X)``, an untagged term with a single unsorted subterm.
- ``X:s(f -> Y:s1, g -> Z)``, a tagged term with two subterms.
- ``X0:person(spouse -> X1:director(last_name -> N:string, spouse -> X0), last_name -> N)``


.. literalinclude:: ../../fosf/parsers/grammars/osf_term.lark
   :language: perl
   :caption: fosf/parsers/grammars/osf_term.lark


.. _clause-grammar:

OSF Clause Grammar
------------------

The OSF clause grammar used by :func:`fosf.parsers.parse_clause`. An OSF clause
is a conjunction of constraints of shape

- ``X:s``, a sort constraint, expressing that the object denoted by ``X`` must
  be of sort (type) ``s``.
- ``X.f = Y``, a feature constraint, expressing that applying the feature ``f``
  to the object denoted by ``X`` results in the object denoted by ``Y``.
- ``X = Y``, expressing that ``X`` and ``Y`` represent the same entity.

An example of a valid expression for an OSF clause is: ::

   X0:person   & X0.spouse = X1 & X0.last_name = N &
   X1:director & X1.spouse = X0 & X1.last_name = N & N:string .

.. literalinclude:: ../../fosf/parsers/grammars/osf_constraints.lark
   :language: perl
   :caption: fosf/parsers/grammars/osf_constraints.lark


.. _theory-grammar:

OSF Theory Grammar
------------------

The OSF theory grammar used by :func:`fosf.parsers.parse_theory`.
It extends :ref:`taxonomy-grammar` by adding rules to parse sort definitions.
A sort definitions associates a sort with an OSF term such that

- the OSF term is in normal form,
- untagged terms are not allowed,
- the set of tags in two different sort definitions must be disjoint.

An example of a valid sort definition is: ::

   person := Yp:person(spouse -> Y1:person(spouse -> Yp)).


.. literalinclude:: ../../fosf/parsers/grammars/osf_theory.lark
   :language: perl
   :caption: fosf/parsers/grammars/osf_theory.lark
