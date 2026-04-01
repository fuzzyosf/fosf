#!/usr/bin/env python3


import networkx as nx
import numpy as np
import random

from fosf.syntax import FuzzySortTaxonomy


BASE_BPL_PROGRAM = """
transitive_isa(X, Y) :- isa(X, Y).
transitive_isa(X, Y) :- isa(X, Z),
                        transitive_isa(Z, Y).

instance_of(Instance, Sort) :- direct_instance_of(Instance, Sort).
instance_of(Instance, Sort) :- direct_instance_of(Instance, Subsort),
                               transitive_isa(Subsort, Sort).

time_pair(Instance, Sort, N, AvgTime) :-
    once(instance_of(Instance, Sort)), % warmup
    statistics(cputime, T0),
    forall(between(1, N, _), once(instance_of(Instance, Sort))),
    statistics(cputime, T1),
    TotalTime is T1 - T0,
    AvgTime is TotalTime / N.

all_times(AvgTimes, N) :-
    findall(AvgTime,
        ( test_pair(I, S),
          time_pair(I, S, N, AvgTime)
        ),
        AvgTimes).

average(List, Avg) :-
    sum_list(List, Sum),
    length(List, N),
    N > 0,
    Avg is Sum / N.

benchmark_average(Avg, N) :-
    all_times(Times, N),
    average(Times, Avg).

time_truth_degree_once(Instance, Sort, Time, MaxDegree) :-
    % For very slow graphs
    once(truth_degree(instance_of(Instance, Sort), _)), % warmup
    statistics(cputime, T0), % start measuring
    findall(D, truth_degree(instance_of(Instance, Sort), D), Degrees),
    max_list(Degrees, MaxDegree),
    statistics(cputime, T1),
    Time is T1 - T0.

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

all_truth_times(TimesMax, N) :-
    findall((Time, MaxDegree),
        ( test_pair(I, S),
          time_truth_degree(I, S, N, Time, MaxDegree)
        ),
        TimesMax).

average_times(TimesMax, AvgTime) :-
    findall(Time, member((Time,_), TimesMax), Times),
    sum_list(Times, Sum),
    length(Times, N),
    N > 0,
    AvgTime is Sum / N.

benchmark_truth(AvgTime, TimesMax, N) :-
    all_truth_times(TimesMax, N),
    average_times(TimesMax, AvgTime).
""".strip()

BPL_TIMING_WRAPPER = "statistics(cputime, T0), {command}, statistics(cputime, T1), Time is T1 - T0."
BPL_FUZZY_RULE = "isa({subsort}, {supersort}) with {degree}."
BPL_FUZZY_INSTANCE = "direct_instance_of({instance}, {sort}) with {degree}."
BPL_SUBSUMPTION_DEGREE = "findall(D, truth_degree(instance_of({instance}, {sink}), D), Degrees), max_list(Degrees, Maxdegree)"


def generate_random_dag(n_ranks: int, initial_branches: int=3, base_nodes_per_branch: int=2,
                        split_probability: float = 0.05, intra_branch_p: float = 0.1,
                        seed: int = 1) -> nx.DiGraph:
    """
    Generate a random layered DAG with stochastic branch splitting.

    - n_ranks : number of ranks (layers).
    - initial_branches : number of branches at rank 0. May increase according to split_probability
    - base_nodes_per_branch : nodes per branch at rank 0.
    - split_probability : chance that a branch splits at a given rank.
    - intra_branch_p : edge probability within a branch.
    - seed : rNG seed.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    G = nx.DiGraph()
    ranks: list[list[int]] = []
    next_node = 0

    # branches represented as dicts
    branches = [
        {"id": i}
        for i in range(initial_branches)
    ]
    next_branch_id = initial_branches

    for r in range(n_ranks):
        rank_nodes: list[int] = []
        new_branches = []
        # branch splitting
        for br in branches:
            # Each branch might split
            splits = 1 + (rng.random() < split_probability)
            for _ in range(splits):
                new_branches.append({
                    "id": next_branch_id,
                    "parent": br["id"],
                })
                next_branch_id += 1
        # create nodes for this rank
        branch_nodes: dict[int, list[int]] = {}
        for br in new_branches:
            nodes = list(range(next_node, next_node + base_nodes_per_branch))
            next_node += base_nodes_per_branch
            branch_nodes[br["id"]] = nodes
            rank_nodes.extend(nodes)
            for v in nodes:
                G.add_node(v, rank=r, branch=br["id"])
        # connect to previous rank
        if r > 0:
            prev_rank = ranks[-1]
            prev_by_branch: dict[int, list[int]] = {}
            for u in prev_rank:
                prev_by_branch.setdefault(G.nodes[u]["branch"], []).append(u)
            for br in new_branches:
                parent = br["parent"]
                src = prev_by_branch[parent]
                dst = branch_nodes[br["id"]]
                # ensure coverage
                for v in dst:
                    G.add_edge(rng.choice(src), v)
                for u in src:
                    if G.out_degree(u) == 0:
                        G.add_edge(u, rng.choice(dst))
                # add extra intra-branch edges
                for u in src:
                    for v in dst:
                        if rng.random() < intra_branch_p:
                            G.add_edge(u, v)
        branches = new_branches
        ranks.append(rank_nodes)
    return G

def random_bousi_fuzzy_taxonomy(n_ranks: int, initial_branches=3, base_nodes_per_branch=2,
                                split_probability=0.05, intra_branch_p=0.1, seed: int = 1,
                                osftest=False):
    rng = random.Random(seed)
    np.random.seed(seed)

    # Generate random DAG
    G = generate_random_dag(n_ranks, initial_branches, base_nodes_per_branch,
                            split_probability, intra_branch_p, seed)

    # Add random weights
    random_degree = lambda: round(np.random.uniform(0.1, 1), 3)
    fuzzy_edges = [(f"s{v}", f"s{u}", random_degree()) for u, v in G.edges()]

    # Encode the DAG in fosf
    tax = FuzzySortTaxonomy(fuzzy_edges)
    graph = tax.graph

    # Print some information
    n_nodes = graph.number_of_nodes()
    print(f"{n_nodes = }")
    mean_indegree = np.mean([graph.in_degree(node) for node in graph.nodes()])
    print(f"{mean_indegree = :f}")

    leaves = list(sorted(graph[tax.bot]))
    sinks = list(sorted(graph.pred[tax.top]))

    # Start encoding the DAG in Bousi~Prolog
    out = BASE_BPL_PROGRAM+"\n\n"

    # Encode fuzzy subsumption
    for u, v, w in sorted(graph.edges(data=True)):
        if u == tax.bot:
            continue
        w = w['weight']
        out += BPL_FUZZY_RULE.format(subsort=u, supersort=v, degree=w)+"\n"
    out += "\n"

    # Add a fuzzy instance for every leave
    for s in leaves:
        instance = f"{s}_instance"
        w = random_degree()
        tax.add_instance(instance, s, degree=w)
        out += "\n"+BPL_FUZZY_INSTANCE.format(sort=s, instance=instance, degree=w)
    out += "\n"

    # Define candidate pairs to test
    test_pairs = []
    for leave in leaves:
        for sink in sinks:
            if not tax.is_subsort(leave, sink):
                continue
            instance = f"{leave}_instance"
            test_pairs.append((instance, sink))
    # Sample 10 pairs to test
    test_sample = rng.sample(test_pairs, 10)

    # Encode the test pairs with the predicate `test_pair`
    # Generate BPL commands to test the pairs
    test_pair_commands = []
    for instance, sink in test_sample:
        out += "\n"+f"test_pair({instance}, {sink})."
        test_pair_commands.append(f"time_truth_degree_once({instance}, {sink}, Time, Degree).")

    # Define the filename for the BPL encoding of the DAG
    base_outfile = f"bpl_d{n_ranks}_s{seed}_benchmark.bpl"

    # Define additional BPL test commands
    instance, sink = test_sample[0]
    load_command = f"ld osf/{base_outfile}"
    command = BPL_TIMING_WRAPPER.format(command=f"once(instance_of({instance}, {sink}))")
    fuzzy_command = BPL_TIMING_WRAPPER.format(command=BPL_SUBSUMPTION_DEGREE.format(sink=sink, instance=instance))

    commands = "\n".join([load_command, # Command for loading the taxonomy in Bousi~Prolog
                          command, fuzzy_command, # For manual testing
                          "\nbenchmark_average(Avg, 1000)", # Benchmark command for instance checking
                          "\nbenchmark_truth(AvgTime, TimesMax, 100).", # Benchmark command for membership degree
                          ] + test_pair_commands # Manual fuzzy test pairs for when BPL goes out of global stack
                         )

    if not osftest:
        return out, base_outfile, commands

    # Additionally run the FOSF benchmark
    times = []
    degrees = []
    fuzzy_times = []

    REPEAT = 1000
    FUZZY_REPEAT = 1000
    # These can be adjusted according to how long the tests take, similar to the BPL
    # predicates. If the time required is very short, we can do 10000 repetitions to get a
    # more accurate timing
    for instance, sink in test_sample:
        # Time OSF instance check
        # Same timing structure as BPL: warmup + iterations + average
        # The output of is_instance is *not* cached in fosf
        _ = tax.is_instance(instance, sink) # warmup
        s = time.process_time()
        for _ in range(REPEAT):
            _ = tax.is_instance(instance, sink)
        t = time.process_time()
        times.append((t-s)/REPEAT)

        # Time OSF subsumption degree
        # Same timing structure as BPL: warmup + iterations + average
        # The subsumption degree is *not* cached in fosf
        degree = tax.membership_degree(instance, sink) # warmup
        s = time.process_time()
        for _ in range(FUZZY_REPEAT):
            _ = tax.membership_degree(instance, sink)
        t = time.process_time()
        fuzzy_times.append((t-s)/FUZZY_REPEAT)
        degrees.append(degree)

    # Print the average timing over the sample
    print(f"Average instance check times: {np.mean(times):f}")
    print(f"Average fuzzy membership times: {np.mean(fuzzy_times):f}")
    # Print the timings for each sample
    print(f"{times = }")
    print(f"{fuzzy_times = }")
    # Print the subsumption degrees
    # So we can compare that fosf and BPL get the same numbers
    print(degrees)
    return out, base_outfile, commands


if __name__ == "__main__":
    import os
    import time

    from argparse import ArgumentParser

    BPL_DIR = os.path.join("./bpl")
    os.makedirs(BPL_DIR, exist_ok=True)

    parser = ArgumentParser()
    parser.add_argument('-d', '--depth', type=int, default=10)
    parser.add_argument('-s', '--seed', type=int, default=1)
    parser.add_argument('-o', '--outdir', type=str, default=BPL_DIR)
    parser.add_argument('-w', '--overwrite', action="store_true", default=False)
    parser.add_argument('-t', '--osftest', action="store_true", default=False)
    args = parser.parse_args()

    n_ranks, seed = args.depth, args.seed

    program, base_outfile, commands = random_bousi_fuzzy_taxonomy(n_ranks=n_ranks,
                                                            osftest=args.osftest,
                                                            seed=seed)
    commands_basefile = base_outfile+".commands"
    program_outfile = os.path.join(BPL_DIR, base_outfile)
    commands_outfile = os.path.join(BPL_DIR, commands_basefile)

    if not os.path.exists(program_outfile) or args.overwrite:
        with open(program_outfile, "w") as f:
            f.write(program)
            print(f"Program file saved at {program_outfile}")
    else:
        print(f"Already exists: {program_outfile}")

    if not os.path.exists(commands_outfile) or args.overwrite:
        with open(commands_outfile, "w") as f:
            f.write(commands)
            print(f"Program file saved at {commands_outfile}")
    else:
        print(f"Already exists: {commands_outfile}")
