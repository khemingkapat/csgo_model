import pandas as pd
import re


def get_top_level(data):
    for key, value in data.items():
        if not isinstance(value, (dict, list)) and value is not None:
            yield key, value


def camel_to_snake(name):
    """Converts a string from camelCase to snake_case, handling consecutive uppercase letters."""
    name = re.sub(r"((?<=[a-z0-9])[A-Z]|(?<!^)[A-Z](?=[a-z]))", r"_\1", name).lower()
    return name


def parse_json_to_dfs(data):

    parsed = {
        "matches": [],
        "rounds": [],
        "kills": [],
        "damages": [],
        "grenades": [],
        "bomb_events": [],
        "weapon_fires": [],
        "flashes": [],
        "frames": [],
        "players": [],
        "team_frames": [],
        "player_frames": [],
        "inventory": [],
        "bomb_location": [],
        "projectiles": [],
        "smokes": [],
        "fires": [],
    }

    # Extract match_id first since it's needed for all other tables
    match_data = dict(get_top_level(data))
    match_id = match_data["matchId"]
    match_data["match_id"] = match_id  # Add match_id to itself for consistency
    parsed["matches"].append(match_data)

    if "gameRounds" in data and data["gameRounds"]:
        for round in data["gameRounds"]:
            round_data = dict(get_top_level(round))
            round_num = round_data["roundNum"]
            round_data["match_id"] = match_id
            parsed["rounds"].append(round_data)

            # Process CT side players
            if (
                "ctSide" in round
                and round["ctSide"]
                and "players" in round["ctSide"]
                and round["ctSide"]["players"]
            ):
                for player in round["ctSide"]["players"]:
                    ct_player_data = dict(get_top_level(player))
                    ct_player_data["team_name"] = round["ctSide"]["teamName"]
                    # ct_player_data["match_id"] = match_id  # Add match_id
                    if ct_player_data not in parsed["players"]:
                        parsed["players"].append(ct_player_data)

            # Process T side players
            if (
                "tSide" in round
                and round["tSide"]
                and "players" in round["tSide"]
                and round["tSide"]["players"]
            ):
                for player in round["tSide"]["players"]:
                    t_player_data = dict(get_top_level(player))
                    t_player_data["team_name"] = round["tSide"]["teamName"]
                    # t_player_data["match_id"] = match_id  # Add match_id
                    if t_player_data not in parsed["players"]:
                        parsed["players"].append(t_player_data)

            # Process kills
            if "kills" in round and round["kills"]:
                for kill in round["kills"]:
                    kill_data = dict(get_top_level(kill))
                    kill_data["round_num"] = round_num
                    # kill_data["match_id"] = match_id
                    parsed["kills"].append(kill_data)

            # Process damages
            if "damages" in round and round["damages"]:
                for damage in round["damages"]:
                    damage_data = dict(get_top_level(damage))
                    damage_data["round_num"] = round_num
                    # damage_data["match_id"] = match_id
                    parsed["damages"].append(damage_data)

            # Process grenades
            if "grenades" in round and round["grenades"]:
                for grenade in round["grenades"]:
                    grenade_data = dict(get_top_level(grenade))
                    grenade_data["round_num"] = round_num
                    # grenade_data["match_id"] = match_id
                    parsed["grenades"].append(grenade_data)

            # Process bomb events
            if "bombEvents" in round and round["bombEvents"]:
                for bomb_event in round["bombEvents"]:
                    bomb_event_data = dict(get_top_level(bomb_event))
                    bomb_event_data["round_num"] = round_num
                    # bomb_event_data["match_id"] = match_id
                    parsed["bomb_events"].append(bomb_event_data)

            # Process weapon fires
            if "weaponFires" in round and round["weaponFires"]:
                for weapon_fire in round["weaponFires"]:
                    weapon_fire_data = dict(get_top_level(weapon_fire))
                    weapon_fire_data["round_num"] = round_num
                    # weapon_fire_data["match_id"] = match_id
                    parsed["weapon_fires"].append(weapon_fire_data)

            # Process flashes
            if "flashes" in round and round["flashes"]:
                for flash in round["flashes"]:
                    flash_data = dict(get_top_level(flash))
                    flash_data["round_num"] = round_num
                    # flash_data["match_id"] = match_id
                    parsed["flashes"].append(flash_data)

            # Process frames
            if "frames" in round and round["frames"]:
                for frame in round["frames"]:
                    frame_data = dict(get_top_level(frame))
                    frame_data["round_num"] = round_num
                    # frame_data["match_id"] = match_id
                    parsed["frames"].append(frame_data)

                    # Process bomb location
                    if "bomb" in frame and frame["bomb"]:
                        bomb_location_data = dict(get_top_level(frame["bomb"]))
                        # bomb_location_data["match_id"] = match_id
                        bomb_location_data["round_num"] = round_num
                        bomb_location_data["tick"] = frame["tick"]
                        parsed["bomb_location"].append(bomb_location_data)

                    # Process projectiles
                    if "projectiles" in frame and frame["projectiles"]:
                        for projectile in frame["projectiles"]:
                            projectile_data = dict(get_top_level(projectile))
                            # projectile_data["match_id"] = match_id
                            projectile_data["round_num"] = round_num
                            projectile_data["tick"] = frame["tick"]
                            parsed["projectiles"].append(projectile_data)

                    # Process smokes
                    if "smokes" in frame and frame["smokes"]:
                        for smoke in frame["smokes"]:
                            smoke_data = dict(get_top_level(smoke))
                            # smoke_data["match_id"] = match_id
                            smoke_data["round_num"] = round_num
                            smoke_data["tick"] = frame["tick"]
                            parsed["smokes"].append(smoke_data)

                    # Process fires
                    if "fires" in frame and frame["fires"]:
                        for fire in frame["fires"]:
                            fire_data = dict(get_top_level(fire))
                            # fire_data["match_id"] = match_id
                            fire_data["round_num"] = round_num
                            fire_data["tick"] = frame["tick"]
                            parsed["fires"].append(fire_data)

                    # Process T side frames
                    if (
                        "t" in frame
                        and frame["t"]
                        and "players" in frame["t"]
                        and frame["t"]["players"]
                    ):
                        t_team_frame_data = dict(get_top_level(frame["t"]))
                        t_team_frame_data["round_num"] = round_num
                        # t_team_frame_data["match_id"] = match_id
                        t_team_frame_data["tick"] = frame["tick"]
                        parsed["team_frames"].append(t_team_frame_data)

                        for player in frame["t"]["players"]:
                            player_frame_data = dict(get_top_level(player))
                            t_player_data = {
                                "playerName": player["name"],
                                "steamID": player["steamID"],
                                "team_name": t_team_frame_data["teamName"],
                                "match_id": match_id,  # Add match_id
                            }
                            if t_player_data not in parsed["players"]:
                                parsed["players"].append(t_player_data)

                            # player_frame_data["match_id"] = match_id
                            player_frame_data["round_num"] = round_num
                            player_frame_data["tick"] = frame["tick"]
                            parsed["player_frames"].append(player_frame_data)

                            if "inventory" in player and player["inventory"]:
                                for inventory in player["inventory"]:
                                    inventory_data = dict(get_top_level(inventory))
                                    # inventory_data["match_id"] = match_id
                                    inventory_data["round_num"] = round_num
                                    inventory_data["player_id"] = player["steamID"]
                                    inventory_data["tick"] = frame["tick"]
                                    parsed["inventory"].append(inventory_data)

                    # Process CT side frames
                    if (
                        "ct" in frame
                        and frame["ct"]
                        and "players" in frame["ct"]
                        and frame["ct"]["players"]
                    ):
                        ct_team_frame_data = dict(get_top_level(frame["ct"]))
                        ct_team_frame_data["round_num"] = round_num
                        # ct_team_frame_data["match_id"] = match_id
                        ct_team_frame_data["tick"] = frame["tick"]
                        parsed["team_frames"].append(ct_team_frame_data)

                        for player in frame["ct"]["players"]:
                            player_frame_data = dict(get_top_level(player))
                            ct_player_data = {
                                "playerName": player["name"],
                                "steamID": player["steamID"],
                                "team_name": ct_team_frame_data["teamName"],
                                "match_id": match_id,  # Add match_id
                            }
                            if ct_player_data not in parsed["players"]:
                                parsed["players"].append(ct_player_data)

                            # player_frame_data["match_id"] = match_id
                            player_frame_data["round_num"] = round_num
                            player_frame_data["tick"] = frame["tick"]
                            parsed["player_frames"].append(player_frame_data)

                            if "inventory" in player and player["inventory"]:
                                for inventory in player["inventory"]:
                                    inventory_data = dict(get_top_level(inventory))
                                    # inventory_data["match_id"] = match_id
                                    inventory_data["round_num"] = round_num
                                    inventory_data["player_id"] = player["steamID"]
                                    inventory_data["tick"] = frame["tick"]
                                    parsed["inventory"].append(inventory_data)

    # Convert all parsed data to DataFrames with snake_case column names
    for key, value in parsed.items():
        if value:
            df = pd.DataFrame(value).drop_duplicates()
            df.columns = [camel_to_snake(col) for col in df.columns]
            yield key, df
