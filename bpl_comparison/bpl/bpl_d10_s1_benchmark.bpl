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

isa(s0, top0) with 1.0.
isa(s1, top0) with 1.0.
isa(s10, s4) with 0.268.
isa(s10, s5) with 0.411.
isa(s11, s4) with 0.183.
isa(s12, s6) with 0.457.
isa(s13, s7) with 0.585.
isa(s14, s8) with 0.477.
isa(s14, s9) with 0.717.
isa(s15, s9) with 0.284.
isa(s16, s11) with 0.125.
isa(s17, s10) with 0.89.
isa(s18, s12) with 0.703.
isa(s19, s13) with 0.476.
isa(s2, top0) with 1.0.
isa(s20, s15) with 0.226.
isa(s21, s14) with 0.603.
isa(s22, s16) with 0.278.
isa(s22, s17) with 0.821.
isa(s23, s17) with 0.971.
isa(s24, s18) with 0.382.
isa(s25, s19) with 0.723.
isa(s26, s20) with 0.889.
isa(s26, s21) with 0.177.
isa(s27, s20) with 0.905.
isa(s28, s22) with 0.135.
isa(s29, s23) with 0.89.
isa(s3, top0) with 1.0.
isa(s30, s23) with 0.189.
isa(s31, s22) with 0.253.
isa(s32, s24) with 0.479.
isa(s33, s25) with 0.962.
isa(s34, s27) with 0.723.
isa(s35, s26) with 0.58.
isa(s35, s27) with 0.384.
isa(s36, s29) with 0.851.
isa(s37, s28) with 0.718.
isa(s38, s30) with 0.116.
isa(s38, s31) with 0.99.
isa(s39, s31) with 0.775.
isa(s4, top0) with 1.0.
isa(s40, s32) with 0.773.
isa(s41, s33) with 0.352.
isa(s42, s35) with 0.193.
isa(s43, s34) with 0.81.
isa(s43, s35) with 0.503.
isa(s44, s36) with 0.918.
isa(s44, s37) with 0.364.
isa(s45, s37) with 0.359.
isa(s46, s39) with 0.117.
isa(s47, s38) with 0.217.
isa(s48, s41) with 0.29.
isa(s49, s40) with 0.711.
isa(s5, top0) with 1.0.
isa(s50, s43) with 0.542.
isa(s51, s42) with 0.339.
isa(s51, s43) with 0.148.
isa(s52, s44) with 0.617.
isa(s53, s44) with 0.232.
isa(s53, s45) with 0.63.
isa(s54, s46) with 0.73.
isa(s54, s47) with 0.473.
isa(s55, s46) with 0.192.
isa(s56, s48) with 0.725.
isa(s57, s48) with 0.473.
isa(s57, s49) with 0.145.
isa(s58, s50) with 0.582.
isa(s59, s51) with 0.697.
isa(s6, s0) with 0.748.
isa(s6, s1) with 0.1.
isa(s60, s52) with 0.95.
isa(s60, s53) with 0.628.
isa(s61, s52) with 0.563.
isa(s61, s53) with 0.913.
isa(s62, s54) with 0.224.
isa(s62, s55) with 0.827.
isa(s63, s55) with 0.225.
isa(s64, s56) with 0.458.
isa(s64, s57) with 0.935.
isa(s65, s56) with 0.249.
isa(s66, s59) with 0.776.
isa(s67, s58) with 0.413.
isa(s67, s59) with 0.753.
isa(s68, s61) with 0.661.
isa(s69, s60) with 0.895.
isa(s7, s0) with 0.475.
isa(s70, s63) with 0.414.
isa(s71, s62) with 0.776.
isa(s8, s2) with 0.372.
isa(s9, s3) with 0.232.


direct_instance_of(s64_instance, s64) with 0.343.
direct_instance_of(s65_instance, s65) with 0.906.
direct_instance_of(s66_instance, s66) with 0.485.
direct_instance_of(s67_instance, s67) with 0.968.
direct_instance_of(s68_instance, s68) with 0.697.
direct_instance_of(s69_instance, s69) with 0.66.
direct_instance_of(s70_instance, s70) with 0.203.
direct_instance_of(s71_instance, s71) with 0.955.

test_pair(s65_instance, s0).
test_pair(s69_instance, s4).
test_pair(s70_instance, s5).
test_pair(s64_instance, s1).
test_pair(s66_instance, s3).
test_pair(s70_instance, s4).
test_pair(s68_instance, s4).
test_pair(s68_instance, s5).
test_pair(s66_instance, s2).
test_pair(s67_instance, s2).
