import pandas as pd

path = "../esta/parsed/"

files = [
    "matches",
    "rounds",
    "kills",
    "damages",
    "grenades",
    "bomb_events",
    "weapon_fires",
    "flashes",
    "frames",
    "players",
    "team_frames",
    "player_frames",
    "inventory",
    "bomb_location",
    "projectiles",
    "smokes",
    "fires",
]


def read_all_files(filenames, path=path):
    result = dict()
    for file in filenames:
        file_path = f"{path}{file}.parquet"
        try:
            df = pd.read_parquet(file_path)
            result[file] = df
        except FileNotFoundError:
            print(f"{file_path} not found")
            continue
    return result


def index_df(
    dfs_dict,
    include=None,
    index_by=None,
):

    if include is None:
        include = [
            "player_frames",
            "flashes",
            "smokes",
            "damages",
            "kills",
            "rounds",
            "frames",
            "grenades",
            "weapon_fires",
            "players",
            "team_frames",
            "inventory",
            "bomb_location",
            "projectiles",
            "fires",
        ]
    if index_by is None:
        index_by = ["match_id", "round_num"]

    indexed_dfs = {}

    for df_name, df in dfs_dict.items():
        if df_name in include:
            indexed_dfs[df_name] = df.set_index(index_by)
            print(f"Indexed DataFrame '{df_name}' by {index_by}.")
        else:
            indexed_dfs[df_name] = df.copy()

    return indexed_dfs


def preprocess_context_data(dfs_dict):
    processed_dfs = {name: df.copy() for name, df in dfs_dict.items()}

    if "damages" in processed_dfs:
        damages_df = processed_dfs["damages"]

        damages_df.loc[:, "total_damage"] = (
            damages_df["hp_damage"] + damages_df["armor_damage"]
        )

        damages_df.loc[:, "total_damage_taken"] = (
            damages_df["hp_damage_taken"] + damages_df["armor_damage_taken"]
        )

        damages_df.loc[:, "attacker_steam_id"] = damages_df["attacker_steam_id"].astype(
            "Int64"
        )
        damages_df.loc[:, "victim_steam_id"] = damages_df["victim_steam_id"].astype(
            "Int64"
        )

        processed_dfs["damages"] = damages_df

    else:
        print(
            "Warning: 'damages' DataFrame not found in dfs_dict. Skipping damage preprocessing."
        )

    if "grenades" in processed_dfs:
        grenades_df = processed_dfs["grenades"]

        grenades_df.loc[:, "grenade_side"] = grenades_df["thrower_side"]

        grenades_df = grenades_df[
            grenades_df["throw_tick"] < grenades_df["destroy_tick"]
        ]
        processed_dfs["grenades"] = grenades_df

    else:
        print(
            "Warning: 'grenades' DataFrame not found in dfs_dict. Skipping grenade preprocessing."
        )

    return processed_dfs


def normalize_tick(dfs_dict, include=None):

    if include is None:
        include = [
            "player_frames",
            "flashes",
            "smokes",
            "damages",
            "kills",
            "frames",
            "grenades",
            "weapon_fires",
        ]

    processed_dfs = {name: df.copy() for name, df in dfs_dict.items()}

    for df_name in include:
        df = processed_dfs[df_name]
        tick_cols = [col for col in df if "tick" in col]
        start_tick = dfs_dict["rounds"]["start_tick"].reindex(df.index)

        df.loc[:, tick_cols] = df.loc[:, tick_cols].sub(start_tick, axis=0)
        processed_dfs[df_name] = df

    return processed_dfs
