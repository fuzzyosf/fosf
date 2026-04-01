:mod:`fosf` - Fuzzy OSF Logic in Python
=======================================

These pages contain the documentation for :mod:`fosf`, a Python implementation of the
main reasoning algorithms of (fuzzy) order-sorted feature (OSF) logic
:cite:`AitKaci1993b`
:cite:`Milanese2024`.
In particular, :mod:`fosf` supports the following operations.

- **(Fuzzy) OSF taxonomic reasoning**: computing greatest lower bounds (GLBs) of
  sorts, deciding sort subsumption, computing sort subsumption degrees, computing
  membership degrees of instances with respect to sorts.
- **OSF clause and term normalization**: simplifying a given OSF clause
  or term into a normal form.
- **(Fuzzy) OSF term unification**: unifying two (normal) OSF terms to compute
  their GLB in the (fuzzy) OSF term subsumption lattice, and computing the
  subsumption degree of the unifier with respect to the initial terms.
- **(Fuzzy) OSF term normalization with respect to an OSF theory**: Normalize
  an OSF term according to the structural constraints imposed by sort
  definitions :cite:`AitKaci1997`, and computing the satisfaction degree of a
  term with respect to the OSF theory.

Below you can find an example of how to use :mod:`fosf`, the API reference, and
the EBNF grammar reference for parsing OSF syntax.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Example - Fuzzy OSF Logic with fosf <notebooks/fuzzy_osf_logic.ipynb>
   api/index
   grammars


Indices
=======

* :ref:`genindex`
* :ref:`modindex`

References
----------

.. bibliography::
