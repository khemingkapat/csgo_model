import pandas as pd
from typing import List, Dict
import warnings
import streamlit as st
import re

image_dim = 1024


def convert_to_snake_case(df, prefix):
    # Function to convert a string to snake_case
    def to_snake_case(text, prefix):
        # Convert to lowercase first
        s = text.lower()
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^\w_]", "", s)
        return f"{prefix}{s}"

    new_df = df.copy()
    new_df.index = [to_snake_case(idx, prefix) for idx in df.index]

    return new_df


def transform_coord(map_data, player_loc, x_col="x", y_col="y"):
    result = player_loc.copy()

    pos_x = map_data["pos_x"]
    pos_y = map_data["pos_y"]
    scale = map_data["scale"]

    result[x_col] = (result[x_col] - pos_x) / scale
    result[y_col] = image_dim - (pos_y - result[y_col]) / scale

    return result


def transform_coords(map_data, player_loc, status):
    tf = player_loc.copy()
    for st in status:
        tf = transform_coord(map_data, tf, x_col=f"{st}_x", y_col=f"{st}_y")
    return tf


def transform_actions(
    actions: pd.DataFrame,
    status: List[str],
    status_extra_cols: Dict[str, List[str]] = {},
    status_code: Dict[str, str] = {},
    common_extra_cols: List[str] = [],
    rename_col: Dict[str, str] = {},
    check_dup_without_cols: List[str] = [],
    keep: str = "first",
    assign_dup: dict = {},
    drop_na_cols: List[str] = [],
) -> pd.DataFrame:
    """Transforms action data.

    This function processes action data, potentially enriching it with status
    information, handling duplicates, and adding common extra columns.

    Args:
        actions (pd.DataFrame): The action data to transform.
        status (List[str]): Status information to merge with the action data.
        status_extra_cols (Dict[str, List[str]], optional): Extra columns from the
            status data to include in the transformed output. Defaults to {}.
        status_code (Dict[str, str], optional): A mapping to use when
            processing status codes. Defaults to {}.
        common_extra_cols (List[str], optional): A list of extra columns to add
            to the output. Defaults to [].
        check_dup_cols (List[str], optional): Columns to check for duplicates.
            Defaults to [].
        keep (str, optional): How to handle duplicates. See the pandas
            'DataFrame.drop_duplicates' keep parameter. Defaults to "first".
        assign_dup (dict, optional): How to assign values to duplicates.
            Defaults to {}.

    Returns:
        pd.DataFrame: The transformed action data.
    """
    keep_opts = {"first": "last", "last": "first"}
    result = pd.DataFrame()
    for st in status:
        st_cols = []
        extra_cols = status_extra_cols.get(st, [])
        for col in actions.columns:
            if col.startswith(st):
                st_cols.append(col)

            if col in extra_cols:
                st_cols.append(col)

            if col in common_extra_cols:
                st_cols.append(col)
        st_df = actions.loc[:, st_cols]

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)
            code = status_code.get(st, None)
            st_df.loc[:, "status"] = code if code is not None else st

        new_cols = []
        for col in st_df.columns:
            if col == f"{st}_side":
                new_cols.append(col)
                continue
            replaced_col = col.replace(f"{st}_", "")
            new_cols.append(rename_col.get(replaced_col, replaced_col))
        st_df.columns = new_cols
        # st_df.columns = [col.replace(f"{st}_","") if col != f"{st}_side" else col
        #                 for col in st_df.columns]

        result = pd.concat([result.drop_duplicates(), st_df.drop_duplicates()])

    side = result[f"{status[0]}_side"]
    for st in status[1:]:
        side = side.fillna(result[f"{st}_side"])
    result["side"] = side
    if check_dup_without_cols is not None and check_dup_without_cols:
        check_dup_cols = [
            col for col in result.columns if col not in check_dup_without_cols
        ]
        dup_idx = result.duplicated(subset=check_dup_cols, keep=keep_opts[keep])
        keep_idx = result.duplicated(subset=check_dup_cols, keep=keep)
        for key, value in assign_dup.items():
            result.loc[dup_idx, key] = value

        result = result.loc[~keep_idx, :]

    return result


@st.cache_data
def transform_all_data(clean_dfs, all_map_data):
    """Transform all data at once instead of per round"""
    selected_map = clean_dfs["matches"]["map_name"].iloc[0]
    map_data = all_map_data[selected_map]

    all_player_frames = clean_dfs["player_frames"].iloc[::2]  # Reduce density
    transformed_all_locations = transform_coord(map_data, all_player_frames)

    transformed_all_flashes = None
    flash_lines = None
    if not clean_dfs["flashes"].empty:
        tf_all_flashes = transform_coords(
            map_data, clean_dfs["flashes"], ["attacker", "player"]
        )
        transformed_all_flashes = transform_actions(
            tf_all_flashes,
            ["attacker", "player"],
            {
                "player": [
                    "flash_duration",
                ]
            },
            {"attacker": "flasher", "player": "flashee"},
            check_dup_without_cols=[
                "status",
                "flash_duration",
                "attacker_side",
                "player_side",
            ],
            assign_dup={"status": "both"},
            common_extra_cols=["tick"],
        )

        flash_lines = tf_all_flashes

    transformed_all_kills = None
    kill_lines = None
    if not clean_dfs["kills"].empty:
        tf_all_kills = transform_coords(
            map_data, clean_dfs["kills"], ["attacker", "victim"]
        )
        transformed_all_kills = transform_actions(
            tf_all_kills,
            ["attacker", "victim"],
            check_dup_without_cols=["attacker_side", "victim_side"],
            assign_dup={"status": "suicide"},
            common_extra_cols=["tick"],
        )
        kill_lines = tf_all_kills

    transformed_all_grenades = None
    grenade_lines = None
    if not clean_dfs["grenades"].empty:
        tf_all_grenades = transform_coords(
            map_data, clean_dfs["grenades"], ["thrower", "grenade"]
        )
        transformed_all_grenades = transform_actions(
            tf_all_grenades, ["thrower", "grenade"], common_extra_cols=["throw_tick"]
        )
        grenade_lines = tf_all_grenades

    rounds_sum_df = clean_dfs["rounds"][
        [
            "n_ticks",
            "bomb_plant_tick",
            "winning_side",
            "round_end_reason",
            "ct_freeze_time_end_eq_val",
            "t_freeze_time_end_eq_val",
        ]
    ].copy()

    def check_nan(val, default=0, show=False):
        result = val if not pd.isna(val) else default
        if show and pd.isna(val):
            print(f"{val} => {result}")
        return result

    def is_empty_series(series_or_value):
        """Safely check if a value is an empty series or a boolean/scalar"""
        if isinstance(series_or_value, pd.Series):
            return series_or_value.empty
        return False

    def safe_sum(series_or_value):
        """Safely sum a series or return 0 if it's not a series"""
        if isinstance(series_or_value, pd.Series):
            return int(series_or_value.sum())
        elif isinstance(series_or_value, bool):
            return 1 if series_or_value else 0
        return 0

    def safe_any(series_or_value):
        """Safely check if any value in a series is True"""
        if isinstance(series_or_value, pd.Series):
            return series_or_value.any()
        return bool(series_or_value)

    for idx, _ in list(rounds_sum_df.iterrows()):
        # Initialize default values for all columns that might be set in this loop
        # This ensures all rows have all expected columns even if data is missing
        default_columns = [
            "ct_flash_opp",
            "t_flash_opp",
            "ct_flashed",
            "t_flashed",
            "ct_avg_flash_duration",
            "t_avg_flash_duration",
            "ct_kills",
            "t_kills",
            "ct_first_kill",
            "t_first_kill",
            "ct_hs_prob",
            "t_hs_prob",
            "ct_trade_prob",
            "t_trade_prob",
            "ct_flash_kill_prob",
            "t_flash_kill_prob",
            "ct_assist_prob",
            "t_assist_prob",
            "ct_kast_prob",
            "t_kast_prob",
            "ct_damage_done",
            "t_damage_done",
            "ct_shot_fires",
            "t_shot_fires",
            "ct_shot_connected_prob",
            "t_shot_connected_prob",
            "ct_grenades_thrown",
            "t_grenades_thrown",
            "ct_grenade_connected_prob",
            "t_grenade_connected_prob",
        ]
        for col in default_columns:
            if col not in rounds_sum_df.columns:
                rounds_sum_df[col] = 0

        if idx in clean_dfs["flashes"].index:
            sel_f_df = clean_dfs["flashes"].loc[idx]

            # Handle both Series and DataFrame cases
            if isinstance(sel_f_df, pd.DataFrame):
                ct_flasher_idx = sel_f_df["attacker_side"] == "CT"
                t_flasher_idx = sel_f_df["attacker_side"] == "T"
                ct_flashed_idx = sel_f_df["player_side"] == "CT"
                t_flashed_idx = sel_f_df["player_side"] == "T"
            else:
                # Handle single row case
                ct_flasher_idx = sel_f_df["attacker_side"] == "CT"
                t_flasher_idx = sel_f_df["attacker_side"] == "T"
                ct_flashed_idx = sel_f_df["player_side"] == "CT"
                t_flashed_idx = sel_f_df["player_side"] == "T"

            # Use safer approach for summing series or scalar values
            rounds_sum_df.loc[idx, "ct_flash_opp"] = safe_sum(ct_flasher_idx)
            rounds_sum_df.loc[idx, "t_flash_opp"] = safe_sum(t_flasher_idx)
            rounds_sum_df.loc[idx, "ct_flashed"] = safe_sum(ct_flashed_idx)
            rounds_sum_df.loc[idx, "t_flashed"] = safe_sum(t_flashed_idx)

            # Safe calculation of means
            if isinstance(sel_f_df, pd.DataFrame):
                ct_flash_duration = (
                    sel_f_df.loc[ct_flashed_idx, "flash_duration"].mean()
                    if safe_any(ct_flashed_idx)
                    else 0
                )
                t_flash_duration = (
                    sel_f_df.loc[t_flashed_idx, "flash_duration"].mean()
                    if safe_any(t_flashed_idx)
                    else 0
                )
            else:
                # Single row case
                ct_flash_duration = sel_f_df["flash_duration"] if ct_flashed_idx else 0
                t_flash_duration = sel_f_df["flash_duration"] if t_flashed_idx else 0

            rounds_sum_df.loc[idx, "ct_avg_flash_duration"] = check_nan(
                ct_flash_duration, 0
            )
            rounds_sum_df.loc[idx, "t_avg_flash_duration"] = check_nan(
                t_flash_duration, 0
            )
        else:
            flash_columns = [
                "ct_flash_opp",
                "t_flash_opp",
                "ct_flashed",
                "t_flashed",
                "ct_avg_flash_duration",
                "t_avg_flash_duration",
            ]
            for col in flash_columns:
                rounds_sum_df.loc[idx, col] = 0

        if idx in clean_dfs["kills"].index:
            sel_k_df = clean_dfs["kills"].loc[idx]

            # Handle both DataFrame and Series cases
            if isinstance(sel_k_df, pd.DataFrame):
                ct_atk_idx = sel_k_df["attacker_side"] == "CT"
                t_atk_idx = sel_k_df["attacker_side"] == "T"
                ct_vic_idx = sel_k_df["victim_side"] == "CT"
                t_vic_idx = sel_k_df["victim_side"] == "T"

                # Using safer approaches for calculations
                ct_n_k = (
                    sel_k_df.loc[ct_atk_idx].attacker_steam_id.nunique()
                    if safe_any(ct_atk_idx)
                    else 0
                )
                t_n_k = (
                    sel_k_df.loc[t_atk_idx].attacker_steam_id.nunique()
                    if safe_any(t_atk_idx)
                    else 0
                )

                ct_n_a = (
                    sel_k_df.loc[ct_atk_idx].assister_steam_id.nunique(dropna=True)
                    if safe_any(ct_atk_idx)
                    else 0
                )
                t_n_a = (
                    sel_k_df.loc[t_atk_idx].assister_steam_id.nunique(dropna=True)
                    if safe_any(t_atk_idx)
                    else 0
                )

                ct_n_s = 5 - safe_sum(ct_vic_idx)
                t_n_s = 5 - safe_sum(t_vic_idx)

                ct_n_t = (
                    sel_k_df.loc[ct_atk_idx].player_traded_steam_id.nunique(dropna=True)
                    if safe_any(ct_atk_idx)
                    else 0
                )
                t_n_t = (
                    sel_k_df.loc[t_atk_idx].player_traded_steam_id.nunique(dropna=True)
                    if safe_any(t_atk_idx)
                    else 0
                )

                rounds_sum_df.loc[idx, "ct_kills"] = safe_sum(ct_atk_idx)
                rounds_sum_df.loc[idx, "t_kills"] = safe_sum(t_atk_idx)

                rounds_sum_df.loc[idx, "ct_first_kill"] = int(
                    sel_k_df.loc[ct_atk_idx]["is_first_kill"].any()
                    if safe_any(ct_atk_idx)
                    else 0
                )
                rounds_sum_df.loc[idx, "t_first_kill"] = int(
                    sel_k_df.loc[t_atk_idx]["is_first_kill"].any()
                    if safe_any(t_atk_idx)
                    else 0
                )

                rounds_sum_df.loc[idx, "ct_hs_prob"] = check_nan(
                    (
                        sel_k_df.loc[ct_atk_idx]["is_headshot"].mean()
                        if safe_any(ct_atk_idx)
                        else 0
                    ),
                    0,
                )
                rounds_sum_df.loc[idx, "t_hs_prob"] = check_nan(
                    (
                        sel_k_df.loc[t_atk_idx]["is_headshot"].mean()
                        if safe_any(t_atk_idx)
                        else 0
                    ),
                    0,
                )

                rounds_sum_df.loc[idx, "ct_trade_prob"] = check_nan(
                    (
                        sel_k_df.loc[ct_atk_idx]["is_trade"].mean()
                        if safe_any(ct_atk_idx)
                        else 0
                    ),
                    0,
                )
                rounds_sum_df.loc[idx, "t_trade_prob"] = check_nan(
                    (
                        sel_k_df.loc[t_atk_idx]["is_trade"].mean()
                        if safe_any(t_atk_idx)
                        else 0
                    ),
                    0,
                )

                rounds_sum_df.loc[idx, "ct_flash_kill_prob"] = check_nan(
                    (
                        sel_k_df.loc[ct_atk_idx]["victim_blinded"].mean()
                        if safe_any(ct_atk_idx)
                        else 0
                    ),
                    0,
                )
                rounds_sum_df.loc[idx, "t_flash_kill_prob"] = check_nan(
                    (
                        sel_k_df.loc[t_atk_idx]["victim_blinded"].mean()
                        if safe_any(t_atk_idx)
                        else 0
                    ),
                    0,
                )

                rounds_sum_df.loc[idx, "ct_assist_prob"] = check_nan(
                    (
                        sel_k_df.loc[ct_atk_idx]["assister_steam_id"].notnull().mean()
                        if safe_any(ct_atk_idx)
                        else 0
                    ),
                    0,
                )
                rounds_sum_df.loc[idx, "t_assist_prob"] = check_nan(
                    (
                        sel_k_df.loc[t_atk_idx]["assister_steam_id"].notnull().mean()
                        if safe_any(t_atk_idx)
                        else 0
                    ),
                    0,
                )

                ct_kast = max(ct_n_k, ct_n_a, ct_n_s, ct_n_t)
                t_kast = max(t_n_k, t_n_a, t_n_s, t_n_t)

                rounds_sum_df.loc[idx, "ct_kast_prob"] = ct_kast / 5
                rounds_sum_df.loc[idx, "t_kast_prob"] = t_kast / 5

            else:
                # Handle single row case
                ct_atk = sel_k_df["attacker_side"] == "CT"
                t_atk = sel_k_df["attacker_side"] == "T"
                ct_vic = sel_k_df["victim_side"] == "CT"
                t_vic = sel_k_df["victim_side"] == "T"

                # Fill in single row values
                rounds_sum_df.loc[idx, "ct_kills"] = 1 if ct_atk else 0
                rounds_sum_df.loc[idx, "t_kills"] = 1 if t_atk else 0
                rounds_sum_df.loc[idx, "ct_deaths"] = 1 if ct_vic else 0
                rounds_sum_df.loc[idx, "t_deaths"] = 1 if t_vic else 0

                rounds_sum_df.loc[idx, "ct_first_kill"] = (
                    1 if ct_atk and sel_k_df["is_first_kill"] else 0
                )
                rounds_sum_df.loc[idx, "t_first_kill"] = (
                    1 if t_atk and sel_k_df["is_first_kill"] else 0
                )

                # Probability values for single row are either 0 or 1
                rounds_sum_df.loc[idx, "ct_hs_prob"] = (
                    1 if ct_atk and sel_k_df["is_headshot"] else 0
                )
                rounds_sum_df.loc[idx, "t_hs_prob"] = (
                    1 if t_atk and sel_k_df["is_headshot"] else 0
                )

                rounds_sum_df.loc[idx, "ct_trade_prob"] = (
                    1 if ct_atk and sel_k_df["is_trade"] else 0
                )
                rounds_sum_df.loc[idx, "t_trade_prob"] = (
                    1 if t_atk and sel_k_df["is_trade"] else 0
                )

                rounds_sum_df.loc[idx, "ct_flash_kill_prob"] = (
                    1 if ct_atk and sel_k_df["victim_blinded"] else 0
                )
                rounds_sum_df.loc[idx, "t_flash_kill_prob"] = (
                    1 if t_atk and sel_k_df["victim_blinded"] else 0
                )

                rounds_sum_df.loc[idx, "ct_assist_prob"] = (
                    1 if ct_atk and pd.notna(sel_k_df["assister_steam_id"]) else 0
                )
                rounds_sum_df.loc[idx, "t_assist_prob"] = (
                    1 if t_atk and pd.notna(sel_k_df["assister_steam_id"]) else 0
                )

                # For KAST in single row case, simple assignment of 0.2 (1/5) if applicable
                ct_kast = 0.2 if ct_atk else 0
                t_kast = 0.2 if t_atk else 0

                rounds_sum_df.loc[idx, "ct_kast_prob"] = ct_kast
                rounds_sum_df.loc[idx, "t_kast_prob"] = t_kast

        if idx in clean_dfs["damages"].index:
            sel_d_df = clean_dfs["damages"].loc[idx]

            if isinstance(sel_d_df, pd.DataFrame):
                ct_atk_idx = sel_d_df["attacker_side"] == "CT"
                t_atk_idx = sel_d_df["attacker_side"] == "T"
                ct_vic_idx = sel_d_df["victim_side"] == "CT"
                t_vic_idx = sel_d_df["victim_side"] == "T"

                rounds_sum_df.loc[idx, "ct_damage_done"] = int(
                    sel_d_df.loc[ct_atk_idx, "total_damage"].sum()
                    if safe_any(ct_atk_idx)
                    else 0
                )
                rounds_sum_df.loc[idx, "t_damage_done"] = int(
                    sel_d_df.loc[t_atk_idx, "total_damage"].sum()
                    if safe_any(t_atk_idx)
                    else 0
                )

            else:
                # Handle single row case
                ct_atk = sel_d_df["attacker_side"] == "CT"
                t_atk = sel_d_df["attacker_side"] == "T"
                ct_vic = sel_d_df["victim_side"] == "CT"
                t_vic = sel_d_df["victim_side"] == "T"

                rounds_sum_df.loc[idx, "ct_damage_done"] = (
                    int(sel_d_df["total_damage"]) if ct_atk else 0
                )
                rounds_sum_df.loc[idx, "t_damage_done"] = (
                    int(sel_d_df["total_damage"]) if t_atk else 0
                )

        if idx in clean_dfs["weapon_fires"].index:
            sel_wf_df = clean_dfs["weapon_fires"].loc[idx]

            if isinstance(sel_wf_df, pd.DataFrame):
                ct_ply_idx = sel_wf_df["player_side"] == "CT"
                t_ply_idx = sel_wf_df["player_side"] == "T"

                rounds_sum_df.loc[idx, "ct_shot_fires"] = safe_sum(ct_ply_idx)
                rounds_sum_df.loc[idx, "t_shot_fires"] = safe_sum(t_ply_idx)

                rounds_sum_df.loc[idx, "ct_shot_connected_prob"] = (
                    sel_wf_df.loc[ct_ply_idx]["shot_connected"].mean()
                    if safe_any(ct_ply_idx)
                    else 0
                )

                rounds_sum_df.loc[idx, "t_shot_connected_prob"] = (
                    sel_wf_df.loc[t_ply_idx]["shot_connected"].mean()
                    if safe_any(t_ply_idx)
                    else 0
                )
            else:
                # Handle single row case
                ct_ply = sel_wf_df["player_side"] == "CT"
                t_ply = sel_wf_df["player_side"] == "T"

                rounds_sum_df.loc[idx, "ct_shot_fires"] = 1 if ct_ply else 0
                rounds_sum_df.loc[idx, "t_shot_fires"] = 1 if t_ply else 0

                rounds_sum_df.loc[idx, "ct_shot_connected_prob"] = (
                    sel_wf_df["shot_connected"] if ct_ply else 0
                )
                rounds_sum_df.loc[idx, "t_shot_connected_prob"] = (
                    sel_wf_df["shot_connected"] if t_ply else 0
                )

        if idx in clean_dfs["grenades"].index:
            sel_g_df = clean_dfs["grenades"].loc[idx]

            if isinstance(sel_g_df, pd.DataFrame):
                ct_g_idx = sel_g_df["thrower_side"] == "CT"
                t_g_idx = sel_g_df["thrower_side"] == "T"

                # Fixed approach for counting
                ct_grenades_count = safe_sum(ct_g_idx)
                t_grenades_count = safe_sum(t_g_idx)

                rounds_sum_df.loc[idx, "ct_grenades_thrown"] = ct_grenades_count
                rounds_sum_df.loc[idx, "t_grenades_thrown"] = t_grenades_count

                # For the grenade type counts, ensure we're working with non-empty data
                if safe_any(ct_g_idx):
                    ct_g_type_counts = convert_to_snake_case(
                        sel_g_df.loc[ct_g_idx].value_counts("grenade_type"), "ct_"
                    ).fillna(0)
                    for col in ct_g_type_counts.index:
                        rounds_sum_df.loc[idx, col] = ct_g_type_counts[col]

                if safe_any(t_g_idx):
                    t_g_type_counts = convert_to_snake_case(
                        sel_g_df.loc[t_g_idx].value_counts("grenade_type"), "t_"
                    ).fillna(0)
                    for col in t_g_type_counts.index:
                        rounds_sum_df.loc[idx, col] = t_g_type_counts[col]

                # For grenade connected probability, ensure we're not calculating on empty series
                ct_connected_prob = (
                    sel_g_df[ct_g_idx].grenade_connected.mean()
                    if safe_any(ct_g_idx)
                    else 0
                )
                t_connected_prob = (
                    sel_g_df[t_g_idx].grenade_connected.mean()
                    if safe_any(t_g_idx)
                    else 0
                )

                rounds_sum_df.loc[idx, "ct_grenade_connected_prob"] = check_nan(
                    ct_connected_prob, 0
                )
                rounds_sum_df.loc[idx, "t_grenade_connected_prob"] = check_nan(
                    t_connected_prob, 0
                )
            else:
                # Handle single row case
                ct_g = sel_g_df["thrower_side"] == "CT"
                t_g = sel_g_df["thrower_side"] == "T"

                rounds_sum_df.loc[idx, "ct_grenades_thrown"] = 1 if ct_g else 0
                rounds_sum_df.loc[idx, "t_grenades_thrown"] = 1 if t_g else 0

                # Handle grenade type counts for a single row
                if ct_g:
                    grenade_type_col = f"ct_{sel_g_df['grenade_type'].lower()}"
                    if grenade_type_col not in rounds_sum_df.columns:
                        rounds_sum_df[grenade_type_col] = 0
                    rounds_sum_df.loc[idx, grenade_type_col] = 1

                if t_g:
                    grenade_type_col = f"t_{sel_g_df['grenade_type'].lower()}"
                    if grenade_type_col not in rounds_sum_df.columns:
                        rounds_sum_df[grenade_type_col] = 0
                    rounds_sum_df.loc[idx, grenade_type_col] = 1

                rounds_sum_df.loc[idx, "ct_grenade_connected_prob"] = (
                    sel_g_df["grenade_connected"] if ct_g else 0
                )
                rounds_sum_df.loc[idx, "t_grenade_connected_prob"] = (
                    sel_g_df["grenade_connected"] if t_g else 0
                )
    rounds_sum_df["bomb_plant_tick"] = (
        rounds_sum_df["bomb_plant_tick"].fillna(-1).astype(int)
    )

    rounds_sum_df["ct_fire_grenade"] = (
        rounds_sum_df["ct_incendiary_grenade"] + rounds_sum_df["ct_molotov"]
    )
    rounds_sum_df["t_fire_grenade"] = (
        rounds_sum_df["t_incendiary_grenade"] + rounds_sum_df["t_molotov"]
    )

    rounds_sum_df.drop(
        ["ct_incendiary_grenade", "t_incendiary_grenade", "ct_molotov", "t_molotov"],
        axis=1,
        inplace=True,
    )

    count_columns = [
        # Kills, deaths, flash counts, etc.
        "ct_flash_opp",
        "t_flash_opp",
        "ct_flashed",
        "t_flashed",
        "ct_kills",
        "t_kills",
        "ct_first_kill",
        "t_first_kill",
        "ct_shot_fires",
        "t_shot_fires",
        "ct_grenades_thrown",
        "t_grenades_thrown",
        "ct_he_grenade",
        "t_he_grenade",
        "ct_smoke_grenade",
        "t_smoke_grenade",
        "ct_flashbang",
        "t_flashbang",
        "ct_decoy_grenade",
        "t_decoy_grenade",
        "ct_fire_grenade",
        "t_fire_grenade",
        # Add any other count columns here
    ]

    # Convert damage columns which should be integers
    damage_columns = [
        "ct_damage_done",
        "t_damage_done",
    ]

    # Convert all count columns to int
    for col in count_columns + damage_columns:
        if col in rounds_sum_df.columns:
            # Replace any remaining NaN with 0 before converting to int
            rounds_sum_df[col] = rounds_sum_df[col].fillna(0).astype(int)

    # Convert bomb_plant_tick to int (already has -1 for NaN)
    rounds_sum_df["bomb_plant_tick"] = rounds_sum_df["bomb_plant_tick"].astype(int)
    rounds_sum_df[["ct_grenade_connected_prob", "t_grenade_connected_prob"]] = (
        rounds_sum_df[["ct_grenade_connected_prob", "t_grenade_connected_prob"]].fillna(
            0
        )
    )
    rounds_sum_df = pd.concat(
        [
            rounds_sum_df.drop("round_end_reason", axis=1),
            pd.get_dummies(
                rounds_sum_df["round_end_reason"],
                prefix="round_end_reason",
                columns=[
                    "BombDefused",
                    "CTWin",
                    "TargetBombed",
                    "TargetSaved",
                    "TerroristsWin",
                ],
            ).astype(int),
        ],
        axis=1,
    )
    rounds_sum_df["winning_side"] = (
        rounds_sum_df["winning_side"].str.lower() == "ct"
    ).astype(int)

    all_players = (
        clean_dfs["player_frames"][
            [
                "steam_id",
                "name",
                "team",
            ]
        ]
        .drop_duplicates()
        .set_index(["name"])
    )
    max_round = clean_dfs["rounds"].index.max()

    sel_k = clean_dfs["kills"]
    sel_d = clean_dfs["damages"]

    for name in all_players.index:
        sel_player_kill_mask = sel_k.attacker_name == name
        sel_player_death_mask = sel_k.victim_name == name
        sel_player_assist_mask = sel_k.assister_name == name
        sel_player_flash_assist_mask = sel_k.flash_thrower_name == name
        sel_player_traded_mask = sel_k.player_traded_name == name

        k = sel_player_kill_mask.groupby("round_num").any()
        a = (
            sel_player_assist_mask.groupby("round_num").any()
            | sel_player_flash_assist_mask.groupby("round_num").any()
        )
        s = ~(sel_player_death_mask.groupby("round_num").any())
        t = sel_player_traded_mask.groupby("round_num").any()

        sel_player_kill = sel_k[sel_player_kill_mask]
        sel_player_death = sel_k[sel_player_death_mask]
        sel_player_assist = sel_k[sel_player_assist_mask]
        sel_player_flash_assist = sel_k[sel_player_flash_assist_mask]

        # display(sel_player_death)

        all_players.loc[name, "kills"] = len(sel_player_kill)
        all_players.loc[name, "deaths"] = len(sel_player_death)
        all_players.loc[name, "assist"] = len(sel_player_assist)
        all_players.loc[name, "flash_assist"] = len(sel_player_flash_assist)
        all_players.loc[name, "first_kill"] = sel_player_kill.is_first_kill.sum()
        all_players.loc[name, "first_death"] = sel_player_death.is_first_kill.sum()
        all_players.loc[name, "kast"] = (k | a | s | t).sum() / max_round

        sel_player_damage = sel_d[sel_d.attacker_name == name]
        sel_player_dmg_round = sel_player_damage.groupby("round_num").agg(
            rtd=("total_damage", "sum")
        )
        all_players.loc[name, "ADR"] = sel_player_dmg_round.rtd.sum() / max_round

    result_df = rounds_sum_df[["winning_side"]]
    result_df.columns = ["ct_win"]
    result_df["t_win"] = (~result_df["ct_win"].astype(bool)).astype(int)
    result_df[["ct_kills", "t_kills"]] = rounds_sum_df[["ct_kills", "t_kills"]]
    result_df["round_end_reason"] = clean_dfs["rounds"]["round_end_reason"]
    result_df.reset_index(inplace=True)

    return {
        "map": selected_map,
        "player_locations": transformed_all_locations,
        "flashes": transformed_all_flashes,
        "flash_lines": flash_lines,
        "kills": transformed_all_kills,
        "kill_lines": kill_lines,
        "grenades": transformed_all_grenades,
        "grenade_lines": grenade_lines,
        "rounds_sum": rounds_sum_df,
        "player_stats": all_players,
        "round_results": result_df,
    }
