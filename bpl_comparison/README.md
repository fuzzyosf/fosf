# Reproducing the comparison between Bousi~Prolog and `fosf`

Below are the steps for reproducing the comparison between Bousi~Prolog and `fosf`.

## Bousi~Prolog installation

The installer for Bousi~Prolog 4.0 can be found
[here](https://dectau.uclm.es/bousi-prolog/2018/07/26/downloads/). Please follow
the official instructions for installation.

## Generation of a random weighted DAG and testing in `fosf`

The Python script `./bpl.py` is responsible for:

- generating a random weighted directed acyclic graph (DAG) of specified depth,
  representing a fuzzy sort taxonomy, and a sample of (instance, sort) pairs to
  test,
- generating the file with the Bousi~Prolog encoding of the DAG (saved to the
  `./bpl` subfolder by default),
- generating a file with the corresponding Bousi~Prolog test commands,
- optionally, testing `fosf` on the same random DAG.

E.g., running `./bpl.py -d 10` will:
- generate a random weighted DAG of depth 10,
- save its Bousi~Prolog encoding to `./bpl/bpl_d10_s1_benchmark.bpl`
- save the corresponding Bousi~Prolog testing commands to `./bpl/bpl_d10_s1_benchmark.bpl.commands`

Passing the additional argument `-t` will perform the instance checking and
subsumption degree computations tests with the `fosf` library. E.g., the output
of `./bpl.py -d 10 -t` is:
```
n_nodes = 74
mean_indegree = 1.324324
Average instance check times: 0.000005
Average fuzzy membership times: 0.000120
times = [...]
fuzzy_times = [...]
[0.249, 0.268, 0.117, 0.1, 0.193, 0.117, 0.268, 0.411, 0.177, 0.177]
```
The outputs for the `fosf` tests corresponding to the various DAG configurations
can be found in the `./osf_timings` folder.

By default, the RNG seed for random DAG generation and sampling is set to 1.
The notebook `./Generating Random Weighted DAGs.ipynb` provides an example of
the DAG generation.

The sampled (instance, sort) pairs are such that they all have positive
membership degree. Otherwise, "instance" would not be an instance of "sort", and
`fosf` would return 0 by default, without even traversing the graph, thanks to
the bit encoding of the DAG.

## Bousi~Prolog encoding of a fuzzy sort taxonomy.

A fuzzy subsumption declaration like `slasher < thriller (0.5).` can be encoded
in Bousi~Prolog as:
```prolog
isa(slasher, thriller) with 0.5.
```

A fuzzy instance declaration like `{0.7/p} < slasher.` can be encoded in
Bousi~Prolog as:
```prolog
direct_instance_of(p, slasher) with 0.7.
```

The following rules take care of subsumption and membership transitivity:
```prolog
transitive_isa(X, Y) :- isa(X, Y).
transitive_isa(X, Y) :- isa(X, Z), transitive_isa(Z, Y).

instance_of(Instance, Sort) :- direct_instance_of(Instance, Sort).
instance_of(Instance, Sort) :- direct_instance_of(Instance, Subsort),
                               transitive_isa(Subsort, Sort).
```
Bousi~Prolog's resolution engine takes care of aggregating the weights.

The sampled test pairs are encoded as `test_pair(Instance, Sort)`.

## Instance checking in Bousi~Prolog

Checking whether an instance `I` has a positive membership degree with respect
to a sort `S` can be done by running:
```prolog
once(instance_of(I, S)).
```
In the paper's experiments, the timing for each `(I, S)` test pair is the
average over many iterations (10000, given that this test can be performed very
quickly) after a warm-up run:
```prolog
time_pair(Instance, Sort, N, AvgTime) :-
    once(instance_of(Instance, Sort)), % warmup
    statistics(cputime, T0),
    forall(between(1, N, _), once(instance_of(Instance, Sort))),
    statistics(cputime, T1),
    TotalTime is T1 - T0,
    AvgTime is TotalTime / N.
```
The timings for all the test pairs are obtained by:
```prolog
all_times(AvgTimes, N) :-
    findall(AvgTime,
        ( test_pair(I, S),
          time_pair(I, S, N, AvgTime)
        ),
        AvgTimes).

```
which are averaged by:
```prolog
average(List, Avg) :-
    sum_list(List, Sum),
    length(List, N),
    N > 0, Avg is Sum / N.

benchmark_average(Avg, N) :-
    all_times(Times, N),
    average(Times, Avg).
```

## Membership degree computation in Bousi~Prolog

In Bousi~Prolog 4.0, the truth degree of a goal like
```prolog
instance_of(p, movie).
```
can be accessed with the higher order predicate `truth_degree`:
```
truth_degree(instance_of(p, movie), D)
```
This will list the degree of each solution of the goal.

Getting the actual subsumption degree requires computing the *maximum* of all
solution degrees (according to fuzzy set theory's max-min transitivity of fuzzy
partial orders), as follows:
```
findall(D, truth_degree(instance_of(p, movie), D), Degrees), max_list(Degrees, MaxDegree).
```
For each `(Instance, Sort)` pair, we can thus get the timing of the subsumption degree
computation via:
```prolog
time_truth_degree(Instance, Sort, N, AvgTime, MaxDegree) :-
    % warmup and compute MaxDegree once
    findall(D, truth_degree(instance_of(Instance, Sort), D), Degrees),
    max_list(Degrees, MaxDegree),

    statistics(cputime, T0),
    forall(between(1, N, _),
        ( findall(D, truth_degree(instance_of(Instance, Sort), D), Ds),
          max_list(Ds, _))),
    statistics(cputime, T1),
    TotalTime is T1 - T0,
    AvgTime is TotalTime / N.
```
This will perform the test `N` times and get the average time. Because this
computation can be very expensive, for larger DAGs we resorted to setting
`N` as 1. The timings for all sample pairs are then averaged, similarly as the
instance check task.

For the DAG with depth 80, some `(I, S)` pairs resulted in "out of global
stack" errors. In this case, we ignored such pairs, and computed the mean
timings over the other sample pairs. For the DAGs of depth 100 and 120, all test
pairs produced "out of global stack" errors.

## Reproducing the Bousi~Prolog tests

The folder `./bpl/` here includes:

- Files of shape `bpl_d[depth]_s[seed]_benchmark.bpl`: Bousi~Prolog encodings of
  the random weighted DAGs of depth `depth` (generated by `./bpl.py`). The seed
  is always 1.
- Files of shape `bpl_d[depth]_s[seed]_benchmark.bpl.commands`: the Bousi~Prolog
  commands for loading the corresponding DAGs and performing the tests inside
  the `.bousi` executable. Below each relevant command, we included a copy of
  the output we obtained in our system.

For running the Bousi~Prolog tests:

- In your Bousi~Prolog installation folder (containing the `bousi` executable),
  create a symbolic link named `osf` to the folder `bpl_comparison/bpl/` of this
  repository.
- Run Bousi~Prolog in your terminal via `.bousi`.
- Copy and paste the commands from the `*.commands` file, e.g., `ld
  osf/bpl_d10_s1_benchmark.bpl` to load the DAG with depth 10 in Bousi~Prolog,
  and subsequent commands for the tests.
