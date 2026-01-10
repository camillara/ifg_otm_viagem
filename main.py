from pulp import (
    PULP_CBC_CMD, LpStatus
)

from otm_model import build_trip_milp_pulp
from import_export_json import (build_front_json_from_solution, parse_db_to_model_inputs)

import json

JSON_PATH = "database.json"

if __name__ == "__main__":

    # ----------- USO -----------
    V, F, DEP, DUR, C, C_hotel, C_food, C_transfer = parse_db_to_model_inputs(JSON_PATH)

    origin = "GYN"  # exemplo
    dest = "ATL"  # exemplo

    # limites de dias (exemplo simples)
    D_total = 7.0
    d_min = {i: 0.0 for i in V}
    d_max = {i: D_total for i in V}
    d_max['GYN'] = 2
    d_min['ATL'] = 2
    d_max['ATL'] = 2


    # restrição: tempo total em voo <= TMAX (horas)
    TMAX = 20.0

    model = build_trip_milp_pulp(
        V=V, origin=origin, dest=dest,
        F=F, DEP=DEP, DUR=DUR, C=C,
        tau=24.0,
        D_total=D_total,
        TMAX=TMAX,      # <= D_max (in hours of flight)
        d_min=d_min, d_max=d_max,
        C_hotel=C_hotel, C_food=C_food, nA=1, nC=0, alpha=1.0,
        C_transfer=C_transfer,
    )

    status = model.solve(PULP_CBC_CMD(msg=True))
    print("Status:", LpStatus[status])
    print("Obj (cost):", model.objective.value())

    # Print chosen flights
    for v in model.variables():
        if v.name.startswith("x_") and v.value() > 0.5:
            print(v.name, "=", v.value())

    # Print days
    for i in V:
        print(i, "y=", model.variablesDict()[f"y_{i}"].value(),
              "d=", model.variablesDict()[f"d_{i}"].value(),
              "t=", model.variablesDict()[f"t_{i}"].value())

    with open("database.json","r",encoding="utf-8") as f:
        db = json.load(f)

    #Export json as otm result
    front_json = build_front_json_from_solution(model, db, origin="GYN", dest="RIO")
    with open("front_payload.json","w",encoding="utf-8") as f:
        json.dump(front_json, f, ensure_ascii=False, indent=2)