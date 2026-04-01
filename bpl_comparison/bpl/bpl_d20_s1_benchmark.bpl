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
isa(s100, s93) with 0.874.
isa(s101, s92) with 0.322.
isa(s102, s94) with 0.585.
isa(s103, s95) with 0.598.
isa(s104, s97) with 0.212.
isa(s105, s96) with 0.858.
isa(s106, s98) with 0.351.
isa(s107, s98) with 0.627.
isa(s107, s99) with 0.973.
isa(s108, s101) with 0.117.
isa(s109, s100) with 0.605.
isa(s109, s101) with 0.821.
isa(s11, s4) with 0.183.
isa(s110, s102) with 0.31.
isa(s110, s103) with 0.826.
isa(s111, s103) with 0.449.
isa(s112, s103) with 0.877.
isa(s113, s103) with 0.772.
isa(s114, s104) with 0.601.
isa(s115, s104) with 0.223.
isa(s115, s105) with 0.154.
isa(s116, s107) with 0.303.
isa(s117, s106) with 0.209.
isa(s118, s106) with 0.14.
isa(s119, s106) with 0.197.
isa(s12, s6) with 0.457.
isa(s120, s108) with 0.742.
isa(s121, s109) with 0.604.
isa(s122, s110) with 0.111.
isa(s122, s111) with 0.971.
isa(s123, s110) with 0.165.
isa(s124, s112) with 0.611.
isa(s125, s112) with 0.283.
isa(s125, s113) with 0.327.
isa(s126, s114) with 0.769.
isa(s127, s114) with 0.276.
isa(s127, s115) with 0.623.
isa(s128, s116) with 0.973.
isa(s129, s116) with 0.862.
isa(s129, s117) with 0.316.
isa(s13, s7) with 0.585.
isa(s130, s118) with 0.544.
isa(s130, s119) with 0.846.
isa(s131, s118) with 0.658.
isa(s132, s121) with 0.117.
isa(s133, s120) with 0.241.
isa(s133, s121) with 0.163.
isa(s134, s122) with 0.538.
isa(s135, s123) with 0.646.
isa(s136, s125) with 0.386.
isa(s137, s124) with 0.612.
isa(s138, s127) with 0.622.
isa(s139, s126) with 0.99.
isa(s139, s127) with 0.442.
isa(s14, s8) with 0.477.
isa(s14, s9) with 0.717.
isa(s140, s129) with 0.771.
isa(s141, s128) with 0.596.
isa(s141, s129) with 0.702.
isa(s142, s131) with 0.16.
isa(s143, s130) with 0.338.
isa(s143, s131) with 0.433.
isa(s144, s133) with 0.289.
isa(s145, s132) with 0.667.
isa(s146, s135) with 0.16.
isa(s147, s134) with 0.777.
isa(s148, s137) with 0.824.
isa(s149, s136) with 0.334.
isa(s149, s137) with 0.274.
isa(s15, s9) with 0.284.
isa(s150, s138) with 0.676.
isa(s151, s139) with 0.572.
isa(s152, s141) with 0.337.
isa(s153, s140) with 0.932.
isa(s154, s143) with 0.762.
isa(s155, s142) with 0.159.
isa(s155, s143) with 0.795.
isa(s156, s144) with 0.917.
isa(s157, s145) with 0.939.
isa(s158, s147) with 0.311.
isa(s159, s146) with 0.113.
isa(s159, s147) with 0.655.
isa(s16, s11) with 0.125.
isa(s160, s148) with 0.954.
isa(s160, s149) with 0.955.
isa(s161, s149) with 0.601.
isa(s162, s151) with 0.677.
isa(s163, s150) with 0.924.
isa(s163, s151) with 0.451.
isa(s164, s152) with 0.537.
isa(s164, s153) with 0.644.
isa(s165, s153) with 0.595.
isa(s166, s155) with 0.927.
isa(s167, s154) with 0.934.
isa(s167, s155) with 0.455.
isa(s168, s156) with 0.967.
isa(s169, s157) with 0.257.
isa(s17, s10) with 0.89.
isa(s170, s159) with 0.222.
isa(s171, s158) with 0.214.
isa(s172, s161) with 0.953.
isa(s173, s160) with 0.555.
isa(s173, s161) with 0.844.
isa(s174, s160) with 0.119.
isa(s175, s161) with 0.114.
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
isa(s72, s65) with 0.906.
isa(s73, s64) with 0.343.
isa(s73, s65) with 0.485.
isa(s74, s66) with 0.968.
isa(s74, s67) with 0.66.
isa(s75, s67) with 0.697.
isa(s76, s68) with 0.203.
isa(s76, s69) with 0.505.
isa(s77, s68) with 0.955.
isa(s78, s70) with 0.621.
isa(s78, s71) with 0.313.
isa(s79, s70) with 0.467.
isa(s8, s2) with 0.372.
isa(s80, s72) with 0.913.
isa(s81, s72) with 0.616.
isa(s81, s73) with 0.103.
isa(s82, s75) with 0.394.
isa(s83, s74) with 0.655.
isa(s83, s75) with 0.574.
isa(s84, s77) with 0.422.
isa(s85, s76) with 0.897.
isa(s86, s79) with 0.661.
isa(s87, s78) with 0.918.
isa(s87, s79) with 0.114.
isa(s88, s81) with 0.722.
isa(s89, s80) with 0.936.
isa(s9, s3) with 0.232.
isa(s90, s83) with 0.255.
isa(s91, s82) with 0.998.
isa(s92, s84) with 0.223.
isa(s92, s85) with 0.727.
isa(s93, s84) with 0.939.
isa(s94, s86) with 0.159.
isa(s94, s87) with 0.778.
isa(s95, s86) with 0.78.
isa(s96, s88) with 0.931.
isa(s96, s89) with 0.212.
isa(s97, s88) with 0.74.
isa(s98, s91) with 0.124.
isa(s99, s90) with 0.118.
isa(s99, s91) with 0.125.


direct_instance_of(s162_instance, s162) with 0.259.
direct_instance_of(s163_instance, s163) with 0.399.
direct_instance_of(s164_instance, s164) with 0.218.
direct_instance_of(s165_instance, s165) with 0.829.
direct_instance_of(s166_instance, s166) with 0.41.
direct_instance_of(s167_instance, s167) with 0.946.
direct_instance_of(s168_instance, s168) with 0.624.
direct_instance_of(s169_instance, s169) with 0.891.
direct_instance_of(s170_instance, s170) with 0.86.
direct_instance_of(s171_instance, s171) with 0.915.
direct_instance_of(s172_instance, s172) with 0.514.
direct_instance_of(s173_instance, s173) with 0.592.
direct_instance_of(s174_instance, s174) with 0.819.
direct_instance_of(s175_instance, s175) with 0.357.

test_pair(s164_instance, s2).
test_pair(s171_instance, s4).
test_pair(s174_instance, s5).
test_pair(s174_instance, s4).
test_pair(s163_instance, s0).
test_pair(s166_instance, s2).
test_pair(s163_instance, s1).
test_pair(s169_instance, s5).
test_pair(s169_instance, s4).
test_pair(s172_instance, s4).
