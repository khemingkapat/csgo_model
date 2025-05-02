import pandas as pd
from typing import List, Dict
import warnings

image_dim = 1024


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
