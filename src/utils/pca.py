import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import copy
from sklearn.cluster import AgglomerativeClustering


def angle_between_vectors(v1, v2, degree=True):
    """
    Calculate angle between two vectors.

    Args:
        v1, v2 (np.array): Input vectors
        degree (bool): If True, return angle in degrees; if False, return in radians

    Returns:
        float: Angle in degrees (default) or radians
    """
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    angle_rad = np.arccos(np.clip(cos_angle, -1.0, 1.0))

    if degree:
        return np.degrees(angle_rad)
    return angle_rad


def create_sliding_windows(df_length, window_size=15, overlap=5):
    """
    Create sliding windows for temporal analysis.

    Args:
        df_length (int): Length of the dataframe
        window_size (int): Size of each window
        overlap (int): Overlap between consecutive windows

    Returns:
        list: List of slice objects representing windows
    """
    windows = []
    window_start = 0

    # Create sliding windows
    while window_start + window_size <= df_length:
        window_end = window_start + window_size
        windows.append(slice(window_start, window_end))
        window_start += window_size - overlap

    # Handle remaining data
    if len(windows) > 0:
        last_end = windows[-1].stop
        if last_end < df_length:
            remaining = df_length - last_end
            min_window_size = max(window_size // 2, 1)

            if remaining >= min_window_size:
                new_start = max(last_end - overlap, 0)
                windows.append(slice(new_start, df_length))
            else:
                windows[-1] = slice(windows[-1].start, df_length)

    # Ensure at least one window exists
    if not windows:
        windows.append(slice(0, df_length))

    return windows


def perform_pca_on_window(X, max_cmps=5):
    """
    Perform PCA analysis on a single window of data.

    Args:
        X (pd.DataFrame): Window data

    Returns:
        dict: Dictionary containing PCA results
    """
    n_components = min(max_cmps, len(X) - 1, X.shape[1])

    scaler = StandardScaler()
    pca = PCA(n_components=n_components)

    X_scaled = scaler.fit_transform(X.values)
    pca_result = pca.fit_transform(X_scaled)

    components = pd.DataFrame(
        pca.components_,
        columns=X.columns,
        index=[f"PC{i+1}" for i in range(pca_result.shape[1])],
    )

    return {
        "pca": pca,
        "scaler": scaler,
        "pca_result": pd.DataFrame(
            pca_result, columns=[f"PC{i}" for i in range(1, n_components + 1)]
        ),
        "components": components,
        "explained_variance_ratio": pca.explained_variance_ratio_,
    }


def calculate_start_position(X):
    """
    Calculate the starting position from position columns.

    Args:
        X (pd.DataFrame): Window data

    Returns:
        tuple: (x, y) starting position, or None if no position columns found
    """
    x_cols = [col for col in X.columns if col.endswith("x") and col.startswith("p")]
    y_cols = [col for col in X.columns if col.endswith("y") and col.startswith("p")]

    if x_cols and y_cols:
        return (X.iloc[0][x_cols].mean(), X.iloc[0][y_cols].mean())
    return None


def calculate_pc_vectors(components, start_pos, scale_factor=128):
    """
    Calculate PC vectors from components and starting position.

    Args:
        components (pd.DataFrame): PCA components
        start_pos (tuple): Starting position (x, y)
        scale_factor (float): Scaling factor for vectors

    Returns:
        list: List of vector dictionaries with start_pos and end_pos
    """
    if start_pos is None:
        return dict()

    x_cols = [
        col for col in components.columns if col.endswith("x") and col.startswith("p")
    ]
    y_cols = [
        col for col in components.columns if col.endswith("y") and col.startswith("p")
    ]

    vectors = dict()
    for pc, row in components.iterrows():
        dx = row[x_cols].sum()
        dy = row[y_cols].sum()

        end_pos = (start_pos[0] + dx * scale_factor, start_pos[1] + dy * scale_factor)
        vectors[pc] = {"start_pos": start_pos, "end_pos": end_pos}

    return vectors


def filter_pc_by_group(pc_vectors, pc_groups, components):
    filtered_vecs = copy.deepcopy(pc_vectors)
    filtered_groups = copy.deepcopy(pc_groups)
    filtered_cmps = components.copy()
    for pc, group in pc_groups.items():
        if not group:
            del filtered_groups[pc]
            del filtered_vecs[pc]
            filtered_cmps.drop([pc], inplace=True)

    return (filtered_vecs, filtered_groups, filtered_cmps)


def filter_pc_by_similarity(pc_vectors, pc_groups, components):
    filtered_vecs = copy.deepcopy(pc_vectors)
    filtered_groups = copy.deepcopy(pc_groups)
    filtered_cmps = components.copy()

    vecs_df = pd.DataFrame()
    for pc, vec in pc_vectors.items():
        vecs_df.loc[pc, ["x", "y"]] = np.array(vec["end_pos"]) - np.array(
            vec["start_pos"]
        )

    clustering = AgglomerativeClustering(
        n_clusters=None, distance_threshold=0.3, metric="cosine", linkage="average"
    ).fit(vecs_df.values)
    vecs_df["label"] = clustering.labels_
    for label in np.unique(clustering.labels_):
        all_vecs = vecs_df[vecs_df.label == label].index
        n_vec = all_vecs.size
        new_pc = "PC" + "".join([pc[-1] for pc in all_vecs])
        new_cmps = components.loc[all_vecs].mean()
        filtered_cmps.drop(all_vecs, inplace=True)
        filtered_cmps.loc[new_pc] = new_cmps

        new_sx, new_sy, new_ex, new_ey = 0, 0, 0, 0
        new_pc_group = []
        for vec in all_vecs:
            new_sx += pc_vectors[vec]["start_pos"][0] / n_vec
            new_sy += pc_vectors[vec]["start_pos"][1] / n_vec

            new_ex += pc_vectors[vec]["end_pos"][0] / n_vec
            new_ey += pc_vectors[vec]["end_pos"][1] / n_vec
            del filtered_vecs[vec]

            new_pc_group += pc_groups[vec]

            del filtered_groups[vec]

        filtered_vecs[new_pc] = {
            "start_pos": (new_sx, new_sy),
            "end_pos": (new_ex, new_ey),
        }

        filtered_groups[new_pc] = new_pc_group

    return (filtered_vecs, filtered_groups, filtered_cmps)


def group_points_by_pc(components):
    """
    Group points by their alignment with principal components.

    Args:
        components (pd.DataFrame): PCA components

    Returns:
        dict: Dictionary grouping points by PC1 and PC2
    """
    x_cols = [
        col for col in components.columns if col.endswith("x") and col.startswith("p")
    ]
    y_cols = [
        col for col in components.columns if col.endswith("y") and col.startswith("p")
    ]

    pc_groups = {pc: [] for pc in components.index}

    if not x_cols or not y_cols:
        return pc_groups

    for p_idx in range(1, (components.columns.size // 2) + 1):
        best_vec = None
        min_angle = float("inf")

        for pc, row in components.iterrows():
            p_vec = components.loc[pc, [f"p{p_idx}x", f"p{p_idx}y"]].values
            c_vec = np.array([row[x_cols].sum(), row[y_cols].sum()])

            angle = angle_between_vectors(p_vec, c_vec)

            if angle < min_angle:
                best_vec = pc
                min_angle = angle
        pc_groups[best_vec].append(f"p{p_idx}")

    return pc_groups


def process_single_window(X, win_key, scale_factor=128):
    """
    Process a single window with complete PCA analysis.

    Args:
        X (pd.DataFrame): Window data
        win_key (str): Window identifier
        scale_factor (float): Scaling factor for vectors

    Returns:
        dict: Complete analysis results for the window
    """
    # Perform PCA
    pca_results = perform_pca_on_window(X)

    # Calculate positions and vectors
    start_pos = calculate_start_position(X)
    pc_vectors = calculate_pc_vectors(
        pca_results["components"], start_pos, scale_factor
    )
    # pc_vectors = calculate_dynamic_pc_vectors(pca_results["components"],pca_results["explained_variance_ratio"], start_pos, scale_factor)
    pc_groups = group_points_by_pc(pca_results["components"])
    # print(f"{'-'*25} before filter {'-'*25}")
    # print(pc_vectors)
    # print(pc_groups)
    # print(pca_results["components"])

    pc_vectors, pc_groups, cmps = filter_pc_by_group(
        pc_vectors, pc_groups, pca_results["components"]
    )
    # print(f"{'-'*25} group filtered {'-'*25}")
    # print(pc_vectors)
    # print(pc_groups)
    # print(cmps)
    pc_vectors, pc_groups, cmps = filter_pc_by_similarity(pc_vectors, pc_groups, cmps)
    # print(f"{'-'*25} similarity filtered {'-'*25}")
    # print(pc_vectors)
    # print(pc_groups)
    # print(cmps)

    pca_results["components"] = cmps
    # Combine all results
    result = {
        "start": X.index[0] if "tick" not in X.columns else X["tick"].min(),
        "end": X.index[-1] if "tick" not in X.columns else X["tick"].max(),
        **pca_results,
        "pc_vectors": pc_vectors,
        "pc_groups": pc_groups,
    }

    for pc in result["pc_vectors"].keys():
        result["pc_vectors"][pc]["tick"] = (result["end"] + result["start"]) // 2
    # Add start_pos only if position columns exist
    if start_pos is not None:
        result["start_pos"] = start_pos

    return result


def temporal_pca(df, window_size=15, overlap=5, scale_factor=128):
    """
    Perform temporal PCA analysis on sliding windows of data.

    Args:
        df (pd.DataFrame): Input dataframe
        window_size (int): Size of each sliding window
        overlap (int): Overlap between consecutive windows
        scale_factor (float): Scaling factor for PC vectors

    Returns:
        dict: Results for each window
    """
    windows = create_sliding_windows(len(df), window_size, overlap)
    result = {}

    for n_win, slc in enumerate(windows, start=1):
        win_key = f"window_{n_win}"
        X = df.iloc[slc]
        result[win_key] = process_single_window(X, win_key, scale_factor)

    return result


def inverse_pc_groups(pc_groups):
    """
    Inversing from list of player into dict of player and their PC

    Args:
        pc_groups (dict(List[])): pc_groups result from temporal_pca

    Returns:
        dict: Player and their PC
    """

    result = dict()
    for pc, players in pc_groups.items():
        for player in players:
            result[player] = pc
    return result


def group_similarity(group1, group2):
    group1 = set(group1)
    group2 = set(group2)

    return len(group1.intersection(group2)) / len(group1.union(group2))


def eu_dist(x1, y1, x2, y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def chain_pc_vectors(tpca_result):
    list_results = [copy.deepcopy(window_data) for window_data in tpca_result.values()]
    chained_vecs = []
    for pc, vec in list_results[0]["pc_vectors"].items():
        new_vec = copy.deepcopy(vec)
        new_vec["name"] = pc
        chained_vecs.append(new_vec)

    for index in range(1, len(list_results)):
        print(index)
        for cpc, cg in list_results[index]["pc_groups"].items():
            if not cg:
                continue
            print(f"\t{cpc=} with {cg=}")
            max_sim = 0
            max_group = None
            max_pc = None
            min_dist = float("inf")
            for ppc, pg in list_results[index - 1]["pc_groups"].items():
                group_sim = group_similarity(cg, pg)
                start = list_results[index]["pc_vectors"][cpc]["start_pos"]
                end = list_results[index - 1]["pc_vectors"][ppc]["end_pos"]
                dist = eu_dist(*start, *end)
                print(
                    f"\t\tchecking with {ppc=} have {pg=} with {group_sim=} also {dist=} that {start=},{end=}",
                    end="",
                )
                if (group_sim > max_sim) or (
                    (group_sim == max_sim) and (dist < min_dist)
                ):
                    max_sim = group_sim
                    max_pc = ppc
                    min_dist = dist
                    max_group = pg
                    print("✅")
                else:
                    print("")

            print(f"\tbest match with {max_pc} have {max_group} with {max_sim=}")
            print()

            current_vector = list_results[index]["pc_vectors"][cpc]
            dx = current_vector["end_pos"][0] - current_vector["start_pos"][0]
            dy = current_vector["end_pos"][1] - current_vector["start_pos"][1]
            start_pos = list_results[index - 1]["pc_vectors"][max_pc]["end_pos"]
            end_pos = (start_pos[0] + dx, start_pos[1] + dy)
            new_vec = {
                "start_pos": start_pos,
                "end_pos": end_pos,
                "tick": list_results[index]["pc_vectors"][cpc]["tick"],
                "name": cpc,
            }
            chained_vecs.append(new_vec)

            list_results[index]["pc_vectors"][cpc] = new_vec
    return chained_vecs
