import geopandas as gpd
import os

DATA_PATH = "data"

# load stops with stufen and population
bus_stop_path = os.path.join(DATA_PATH, "interim/bus_stops_enhanced.json")
bus_stops = gpd.read_file(bus_stop_path)

budget = 1500000

actions = {
    "tree": {
        "costs": 5000,
        "heat_red": 12,
    },
    "green_pergola": {
        "costs": 1000,
        "heat_red": 5,
    },
    "thermal_foil": {
        "costs": 700,
        "heat_red": 5,
    },
}


def calculate_actions_in_budget(budget):
    # TODO: variable factors based on input data
    factor_0_5 = 2
    factor_60_74 = 1
    factor_75_ = 2
    # population_factor
    bus_stops["population_factor"] = (
        factor_0_5 * bus_stops["prozent_0_5"]
        + factor_60_74 * bus_stops["prozent_60_74"]
        + factor_75_ * bus_stops["prozent_75_"]
    )
    bus_stops_sorted = bus_stops.sort_values(
        by=["stufe", "population_factor"], ascending=False
    )

    # divide budget
    bus_stops_after_actions = bus_stops_sorted[
        ["stufe", "population_factor", "shelter", "name", "geometry"]
    ]
    bus_stops_after_actions.reset_index(drop=True, inplace=True)
    bus_stops_after_actions = bus_stops_after_actions.copy()
    bus_stops_after_actions["stufe_post_action"] = bus_stops_after_actions["stufe"]
    bus_stops_after_actions["action"] = None
    current_budget = budget
    # first apply simple actions
    for i, stop in bus_stops_after_actions.iterrows():
        # consider only levels above 1
        if stop["stufe"] in [3, 2]:
            # choose applicable action
            action = "thermal_foil" if stop["shelter"] == "yes" else "green_pergola"
            # apply action if budget available
            if actions[action]["costs"] <= current_budget:
                bus_stops_after_actions.loc[i, "action"] = action
                bus_stops_after_actions.loc[i, "stufe_post_action"] = (
                    stop["stufe_post_action"] - 1
                )
                current_budget -= actions[action]["costs"]
            else:
                break

    # apply more expensive actions if budget available
    for i, stop in bus_stops_after_actions.iterrows():
        # consider only levels above 1
        if stop["stufe"] in [3, 2]:
            # choose applicable action
            action = "tree"
            # apply action if budget available
            current_action_costs = (
                0
                if bus_stops_after_actions.iloc[i]["action"] == None
                else actions[bus_stops_after_actions.iloc[i]["action"]]["costs"]
            )
            if (actions[action]["costs"] - current_action_costs) <= current_budget:
                bus_stops_after_actions.loc[i, "action"] = action
                bus_stops_after_actions.loc[i, "stufe_post_action"] = (
                    stop["stufe_post_action"] - 1
                )
                current_budget -= actions[action]["costs"] - current_action_costs
            else:
                break

    return bus_stops_after_actions


bus_stops_after_actions = calculate_actions_in_budget(budget=budget)

print(bus_stops_after_actions.head(20))
