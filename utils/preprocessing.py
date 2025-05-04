def preprocess(dfs):
    import pandas as pd

    processed = {}

    # Step 1: Initial preprocessing
    for key, val in dfs.items():
        df = val.copy()

        # Standardize index
        if "round_num" in df.columns:
            df = df.set_index(["round_num"])

        if key == "damages":
            df["total_damage"] = df["hp_damage"] + df["armor_damage"]
            df["total_damage_taken"] = df["hp_damage_taken"] + df["armor_damage_taken"]

        processed[key] = df

    processed["matches"]["match_date"] = pd.to_datetime(
        processed["matches"]["match_date"]
    )

    processed["rounds"]["n_ticks"] = (
        processed["rounds"]["end_tick"] - processed["rounds"]["start_tick"]
    )

    # Step 2: Tick normalization
    idx_r_df = processed["rounds"]
    for key, df in processed.items():
        if key == "rounds":
            continue

        tick_cols = [col for col in df.columns if "tick" in col]
        if not tick_cols:
            continue

        common_idx = df.index.intersection(idx_r_df.index)

        for idx in common_idx:
            first_tick = idx_r_df.loc[idx, "start_tick"]
            df.loc[idx, tick_cols] = df.loc[idx, tick_cols] - first_tick

        processed[key] = df

    # Step 3: Add 'shot_connected' to weapon_fires
    wf_df = processed["weapon_fires"].copy()
    d_df = processed["damages"].copy()

    for idx in wf_df.index.unique():
        round_wf = wf_df.loc[idx].copy()
        round_d = d_df.loc[idx].copy()

        if isinstance(round_wf, pd.Series):
            round_wf = round_wf.to_frame().T
        if isinstance(round_d, pd.Series):
            round_d = round_d.to_frame().T

        round_wf["combo_key"] = (
            round_wf["tick"].astype(str)
            + "_"
            + round_wf["player_steam_id"].astype("float64").astype(str)
        )
        round_d["combo_key"] = (
            round_d["tick"].astype(str)
            + "_"
            + round_d["attacker_steam_id"].astype("float64").astype(str)
        )

        round_wf["shot_connected"] = round_wf["combo_key"].isin(
            round_d["combo_key"].values
        )
        round_wf.drop("combo_key", axis=1, inplace=True)

        if isinstance(wf_df.loc[idx], pd.Series):
            wf_df.loc[idx, "shot_connected"] = round_wf["shot_connected"].iloc[0]
        else:
            wf_df.loc[idx, "shot_connected"] = round_wf["shot_connected"].values

    processed["weapon_fires"] = wf_df

    # Step 4: Add 'grenade_connected' to grenades
    g_df = processed["grenades"].copy()
    g_df["grenade_side"] = g_df.thrower_side

    for idx in g_df.index.unique():
        round_g = g_df.loc[idx].copy()
        round_d = d_df.loc[idx].copy()

        if isinstance(round_g, pd.Series):
            round_g = round_g.to_frame().T
        if isinstance(round_d, pd.Series):
            round_d = round_d.to_frame().T

        round_d = round_d[round_d["weapon_class"] == "Grenade"]

        round_g["grenade_connected"] = round_g["thrower_steam_id"].isin(
            round_d["attacker_steam_id"].values
        )

        if isinstance(g_df.loc[idx], pd.Series):
            g_df.loc[idx, "grenade_connected"] = round_g["grenade_connected"].iloc[0]
        else:
            g_df.loc[idx, "grenade_connected"] = round_g["grenade_connected"].values

    processed["grenades"] = g_df

    return processed
