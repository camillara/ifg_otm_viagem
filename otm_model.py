from pulp import (
    LpProblem, LpVariable, LpMinimize, lpSum,
    LpBinary, LpContinuous, LpInteger
)


def build_trip_milp_pulp(
    V,                       # list of cities
    origin, dest,            # fixed origin/destination (must be in V)
    F,                       # dict: (i,j) -> list of flight ids f
    DEP, DUR, C,             # dicts keyed by (i,j,f) -> value (hours / cost)
    tau=24.0,                # hours per day
    D_total=7.0,             # total days (continuous)
    TMAX=15.0,               # max total flight time (hours)  <= D_max (your constraint)
    d_min=None, d_max=None,  # dicts keyed by i -> min/max days (continuous), optional
    C_hotel=None,            # dict i -> cost per day
    C_food=None,             # dict i -> cost per day (per person-day)
    nA=1, nC=0, alpha=1.0,   # people parameters for food
    C_transfer=None,         # dict i -> transfer fixed cost if visit
    bigM=None                # Big-M; if None, compute a safe-ish value
):
    assert origin in V and dest in V and origin != dest

    # Defaults
    if d_min is None: d_min = {i: 0.0 for i in V}
    if d_max is None: d_max = {i: D_total for i in V}
    if C_hotel is None: C_hotel = {i: 0.0 for i in V}
    if C_food  is None: C_food  = {i: 0.0 for i in V}
    if C_transfer is None: C_transfer = {i: 0.0 for i in V}

    # Build arc set from provided flight lists
    A = [(i, j) for (i, j) in F.keys() if i != j and len(F[(i, j)]) > 0]

    # Compute Big-M if not provided
    # Use horizon based on max(DEP + DUR) plus max stay time
    if bigM is None:
        if len(DEP) == 0:
            raise ValueError("DEP is empty; provide bigM explicitly or fill DEP.")
        max_time = max(DEP[k] + DUR[k] for k in DEP.keys())
        bigM = max_time + tau * D_total + 10.0  # small buffer

    model = LpProblem("Trip_Scheduling_Flights_Only", LpMinimize)

    # --- Decision variables ---
    # Flight choice
    x = {}
    for (i, j) in A:
        for f in F[(i, j)]:
            x[(i, j, f)] = LpVariable(f"x_{i}_{j}_{f}", cat=LpBinary)

    # Aggregated arc
    X = {(i, j): LpVariable(f"X_{i}_{j}", lowBound=0, upBound=1, cat=LpContinuous) for (i, j) in A}

    # Visit
    y = {i: LpVariable(f"y_{i}", cat=LpBinary) for i in V}

    # Arrival/start time at city
    t = {i: LpVariable(f"t_{i}", lowBound=0, cat=LpContinuous) for i in V}

    # Days at city (continuous)
    d = {i: LpVariable(f"d_{i}", lowBound=0, cat=LpContinuous) for i in V}

    # Integer days proxy if you still want it (>= d_i)
    dias = {i: LpVariable(f"dias_{i}", lowBound=0, cat=LpInteger) for i in V}

    # MTZ ordering
    u = {i: LpVariable(f"u_{i}", lowBound=0, cat=LpContinuous) for i in V}

    # --- Objective (min cost) ---
    food_factor = (nA + alpha * nC)

    model += (
        lpSum(C[(i, j, f)] * x[(i, j, f)] for (i, j) in A for f in F[(i, j)]) +
        lpSum(C_hotel[i] * dias[i] for i in V) +
        lpSum(C_food[i] * food_factor * dias[i] for i in V) +
        lpSum(C_transfer[i] * y[i] for i in V)
    ), "Total_Cost"

    # --- Constraints ---

    # Fix origin/destination as visited
    model += y[origin] == 1, "Visit_origin"
    model += y[dest] == 1, "Visit_dest"

    # Aggregation: X_ij = sum_f x_ijf
    for (i, j) in A:
        model += X[(i, j)] == lpSum(x[(i, j, f)] for f in F[(i, j)]), f"Agg_{i}_{j}"
        model += lpSum(x[(i, j, f)] for f in F[(i, j)]) <= 1, f"AtMostOneFlight_{i}_{j}"

    # Flow for open path with fixed origin/dest:
    # out - in = 1 at origin, = -1 at dest, = 0 otherwise (when visited)
    # We'll link visit y with degree constraints.
    for i in V:
        out_i = lpSum(X[(i, j)] for (ii, j) in A if ii == i)
        in_i  = lpSum(X[(j, i)] for (j, jj) in A if jj == i)

        if i == origin:
            model += out_i - in_i == 1, "Flow_origin"
        elif i == dest:
            model += out_i - in_i == -1, "Flow_dest"
        else:
            model += out_i - in_i == 0, f"Flow_{i}"

        # Degree/visit coupling:
        # If y_i=0 then no in/out; if y_i=1 then:
        # - for intermediate nodes: in=out=1
        # - origin: out=1, in=0
        # - dest: in=1, out=0
        if i == origin:
            model += out_i == 1, "Origin_out_degree"
            model += in_i == 0,  "Origin_in_degree"
        elif i == dest:
            model += in_i == 1,  "Dest_in_degree"
            model += out_i == 0, "Dest_out_degree"
        else:
            model += in_i == y[i],  f"InDegree_{i}"
            model += out_i == y[i], f"OutDegree_{i}"

    # MTZ subtour elimination on X (only meaningful for visited nodes)
    n = len(V)
    for i in V:
        model += u[i] <= n * y[i], f"MTZ_u_ub_{i}"
        model += u[i] >= 0,        f"MTZ_u_lb_{i}"

    for (i, j) in A:
        if i != j:
            model += u[i] - u[j] + n * X[(i, j)] <= n - 1, f"MTZ_{i}_{j}"

    # Fix start ordering at origin: set u[origin] = 0 (stronger than your inequality)
    model += u[origin] == 0, "MTZ_fix_origin"

    # Days constraints
    for i in V:
        model += d[i] <= d_max[i] * y[i], f"DaysMax_{i}"
        model += d[i] >= d_min[i] * y[i], f"DaysMin_{i}"
        model += dias[i] >= d[i],         f"Dias_ge_d_{i}"

    model += lpSum(d[i] for i in V) == D_total, "TotalDays"

    # Sequencing: t_i + tau*d_i <= DEP_ijf  if flight chosen; and t_j >= DEP + DUR
    for (i, j) in A:
        for f in F[(i, j)]:
            dep = DEP[(i, j, f)]
            dur = DUR[(i, j, f)]

            model += (
                t[i] + tau * d[i] <= dep + bigM * (1 - x[(i, j, f)]),
                f"Seq_depart_{i}_{j}_{f}"
            )
            model += (
                t[j] >= dep + dur - bigM * (1 - x[(i, j, f)]),
                f"Seq_arrive_{i}_{j}_{f}"
            )

    # Fix start time at origin
    model += t[origin] == 0, "StartTime_origin"

    # --- Flight time constraint: total DUR <= TMAX (this is your "tempo <= D_max") ---
    total_flight_time = lpSum(DUR[(i, j, f)] * x[(i, j, f)] for (i, j) in A for f in F[(i, j)])
    model += total_flight_time <= TMAX, "MaxTotalFlightTime"

    return model