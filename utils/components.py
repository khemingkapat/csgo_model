import streamlit as st
import matplotlib.pyplot as plt
import os
from matplotlib.figure import Figure
import json
import pandas as pd
from .symbols import *
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np


def upload_and_parse_json(preview_limit=10):
    """
    Streamlit widget to upload a JSON file and return the parsed content.

    Args:
        preview_limit (int): Number of items to preview in the UI.
                             If 0, no preview is shown.

    Returns:
        dict or list or None: Parsed JSON data if uploaded successfully, else None.
    """
    uploaded_file = st.file_uploader("Upload your JSON file", type="json")

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.success("✅ JSON file loaded successfully!")

            # Show preview only if preview_limit > 0
            if preview_limit > 0:
                if isinstance(data, dict):
                    preview = {
                        k: data[k]
                        for i, k in enumerate(data.keys())
                        if i < preview_limit
                    }
                elif isinstance(data, list):
                    preview = data[:preview_limit]
                else:
                    preview = str(data)

                st.write(f"📄 Preview (first {preview_limit} items or keys):")
                st.json(preview)

            return data

        except Exception as e:
            st.error(f"❌ Error loading JSON: {e}")
            return None

    else:
        st.info("📂 Please upload a JSON file.")
        return None


def plot_map(map_name, fig_size=(10, 10), image_dim=1024):
    """
    Create a matplotlib figure with a CS:GO map as background for plotting.

    Parameters:
    -----------
    map_name : str
        Name of the map (without file extension)
    fig_size : tuple
        Figure size as (width, height) in inches
    image_dim : int
        Dimension of the map image (assumed square)

    Returns:
    --------
    fig : matplotlib.figure.Figure
        The figure with the map as background
    ax : matplotlib.axes.Axes
        The axes for adding additional plots
    """
    # Create a new Figure and Axes
    fig = Figure(figsize=fig_size)
    ax = fig.add_subplot(111)

    # Construct the path to the map image
    map_path = f".awpy/maps/{map_name}.png"

    # Check if the file exists
    if not os.path.exists(map_path):
        # If the file doesn't exist, create a placeholder
        ax.text(
            0.5,
            0.5,
            f"Map not found: {map_name}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    else:
        # Load and display the map image
        map_img = plt.imread(map_path)
        ax.imshow(map_img, extent=[0, image_dim, 0, image_dim])

        # Set plot limits and title
        ax.set_xlim(0, image_dim)
        ax.set_ylim(0, image_dim)

    ax.set_title(map_name.title())
    fig.tight_layout()

    return fig, ax


def count_colorbar(fig):
    result = 0
    for ax in fig.axes:
        if "colorbar" in ax.get_label():
            result += 1
    return result


def plot_loc_unicode(
    player_loc,
    gradient_by,
    size,
    color_by=None,
    color_dict=None,
    default_color="viridis",  # Default colormap when color_by is None
    alpha=0.5,
    marker_by=None,
    marker_dict=None,
    default_marker="o",  # Default marker when marker_by is None
    fig=None,
    ax=None,
):

    if fig is None and ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))

    selected_col = ["x", "y", gradient_by]
    if color_by is not None:
        selected_col.append(color_by)
    if marker_by is not None:
        selected_col.append(marker_by)

    transformed = player_loc.reset_index()[selected_col]

    # Normalize gradient
    vmin = transformed[gradient_by].min()
    vmax = transformed[gradient_by].max()
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    if color_by is not None:
        transformed[color_by] = transformed[color_by].str.lower()

    side = ["left", "right"]
    n_colorbar = count_colorbar(fig)

    previous_cmap = plt.get_cmap(default_color)  # Initial cmap

    for idx, row in transformed.iterrows():
        # Determine colormap
        if color_by is not None and pd.notna(row[color_by]):
            color_key = row[color_by]
            if color_key in color_dict:
                cmap = plt.get_cmap(color_dict[color_key])
                previous_cmap = cmap
            else:
                cmap = previous_cmap
        else:
            cmap = previous_cmap

        # Normalize and get color
        color_value = norm(row[gradient_by])
        color = cmap(color_value)

        # Determine marker
        if marker_by is None:
            marker_char = default_marker
        else:
            marker_key = row[marker_by]
            marker_char = marker_dict.get(marker_key, default_marker)

        ax.text(
            row["x"],
            row["y"],
            marker_char,
            fontsize=size,
            color=color,
            ha="center",
            va="center",
            alpha=alpha,
        )

    ax.set_xlabel("X Coordinate (pixels)")
    ax.set_ylabel("Y Coordinate (pixels)")

    # Add colorbars if color_by is provided
    if color_by is not None:
        for idx, (color_cat, cmap_name) in enumerate(
            list(color_dict.items())[: 2 - n_colorbar]
        ):
            positions = transformed[transformed[color_by] == color_cat]
            dummy_scatter = ax.scatter(
                positions["x"],
                positions["y"],
                c=positions[gradient_by],
                cmap=cmap_name,
                s=0,
                alpha=0.5,
                norm=norm,
            )
            cbar = fig.colorbar(
                dummy_scatter,
                ax=ax,
                location=side[idx],
                pad=0.02,
                fraction=0.046,
                shrink=0.6,
            )
            cbar.set_label(f"{color_cat.upper()} {gradient_by.title()}", fontsize=8)
            cbar.ax.tick_params(labelsize=7)

    return fig, ax


def plot_line(
    actions,
    status1,
    status2,
    gradient_by,
    color_by=None,
    color_dict={},
    default_color="Greys",
    linewidth=1,
    alpha=1,
    fig=None,
    ax=None,
):
    if fig is None and ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))

    vmin = actions[gradient_by].min()
    vmax = actions[gradient_by].max()
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    for _, row in actions.iterrows():
        cmap = plt.get_cmap(
            color_dict.get(row[color_by], default_color)
            if color_by is not None
            else default_color
        )

        color_value = norm(row[gradient_by])
        color = cmap(color_value)

        ax.plot(
            [row[f"{status1}_x"], row[f"{status2}_x"]],
            [row[f"{status1}_y"], row[f"{status2}_y"]],
            alpha=alpha,
            linewidth=linewidth,
            color=color,
        )

    return fig, ax


def plot_actions_by_max_tick(
    round_dfs,
    max_tick,
    show_loc,
    show_flash,
    show_kills,
    show_grenades,
    flash_alpha,
    kill_alpha,
    grenade_alpha,
    flash_size,
    kill_size,
    grenade_size,
    show_lines,
    transformed_data,
):
    """
    Plot game actions filtered by max tick (min_tick always 0)
    """
    min_tick = 0  # Always start from tick 0

    # Start with map
    img_fig, img_ax = plot_map(transformed_data["map"], (12, 10))
    current_fig, current_ax = img_fig, img_ax

    loc_mask = (round_dfs["player_locations"]["tick"] >= min_tick) & (
        round_dfs["player_locations"]["tick"] <= max_tick
    )
    # Filter actions by tick range
    flash_mask = (round_dfs["flashes"]["tick"] >= min_tick) & (
        round_dfs["flashes"]["tick"] <= max_tick
    )
    kill_mask = (round_dfs["kills"]["tick"] >= min_tick) & (
        round_dfs["kills"]["tick"] <= max_tick
    )
    grenade_mask = (round_dfs["grenades"]["throw_tick"] >= min_tick) & (
        round_dfs["grenades"]["throw_tick"] <= max_tick
    )
    filtered_loc = (
        round_dfs["player_locations"][loc_mask]
        if isinstance(round_dfs["player_locations"], pd.DataFrame)
        else round_dfs["player_locations"]
    )

    filtered_flash = (
        round_dfs["flashes"][flash_mask]
        if isinstance(round_dfs["flashes"], pd.DataFrame)
        else round_dfs["flashes"]
    )
    filtered_kills = (
        round_dfs["kills"][kill_mask]
        if isinstance(round_dfs["kills"], pd.DataFrame)
        else round_dfs["kills"]
    )
    filtered_grenades = (
        round_dfs["grenades"][grenade_mask]
        if isinstance(round_dfs["grenades"], pd.DataFrame)
        else round_dfs["grenades"]
    )

    flash_count = (
        filtered_flash.attacker_side.notnull().sum()
        if isinstance(filtered_flash, pd.DataFrame)
        else 0
    )
    kill_count = (
        filtered_kills.attacker_side.notnull().sum()
        if isinstance(filtered_kills, pd.DataFrame)
        else 0
    )
    grenade_count = (
        filtered_grenades.thrower_side.notnull().sum()
        if isinstance(filtered_grenades, pd.DataFrame)
        else 0
    )

    if show_loc and len(filtered_loc) > 0:
        loc_fig, loc_ax = plot_loc_unicode(
            filtered_loc,
            gradient_by="tick",
            size=5,
            color_by="side",
            color_dict=side_color,
            default_marker="$\u2B24$",
            alpha=0.4,
            fig=current_fig,
            ax=current_ax,
        )
        current_fig, current_ax = loc_fig, loc_ax

    # Plot flashes
    if show_flash and len(filtered_flash) > 0:
        flash_fig, flash_ax = plot_loc_unicode(
            filtered_flash,
            gradient_by="tick",
            size=flash_size,
            color_by="side",
            color_dict=side_color,
            marker_by="status",
            marker_dict=flash_marker,
            alpha=flash_alpha,
            fig=current_fig,
            ax=current_ax,
        )
        current_fig, current_ax = flash_fig, flash_ax

        if show_lines:
            flash_co_mask = (round_dfs["flash_lines"]["tick"] >= min_tick) & (
                round_dfs["flash_lines"]["tick"] <= max_tick
            )
            filtered_f_co = round_dfs["flash_lines"][flash_co_mask]
            if len(filtered_f_co) > 0:
                cf_fig, cf_ax = plot_line(
                    filtered_f_co,
                    "attacker",
                    "player",
                    "tick",
                    default_color="viridis",
                    fig=current_fig,
                    ax=current_ax,
                )
                current_fig, current_ax = cf_fig, cf_ax

    # Plot kills
    if show_kills and len(filtered_kills) > 0:
        kill_fig, kill_ax = plot_loc_unicode(
            filtered_kills,
            gradient_by="tick",
            size=kill_size,
            color_by="side",
            color_dict=side_color,
            marker_by="status",
            marker_dict=kill_marker,
            alpha=kill_alpha,
            fig=current_fig,
            ax=current_ax,
        )
        current_fig, current_ax = kill_fig, kill_ax

        if show_lines:
            kill_co_mask = (round_dfs["kill_lines"]["tick"] >= min_tick) & (
                round_dfs["kill_lines"]["tick"] <= max_tick
            )
            filtered_k_co = round_dfs["kill_lines"][kill_co_mask]
            if len(filtered_k_co) > 0:
                ck_fig, ck_ax = plot_line(
                    filtered_k_co,
                    "attacker",
                    "victim",
                    "tick",
                    default_color="Reds",
                    fig=current_fig,
                    ax=current_ax,
                )
                current_fig, current_ax = ck_fig, ck_ax

    # Plot grenades
    if show_grenades and len(filtered_grenades) > 0:
        grenade_fig, grenade_ax = plot_loc_unicode(
            filtered_grenades,
            gradient_by="throw_tick",
            size=grenade_size,
            color_by="side",
            color_dict=side_color,
            marker_by="status",
            marker_dict=grenade_marker,
            alpha=grenade_alpha,
            fig=current_fig,
            ax=current_ax,
        )
        current_fig, current_ax = grenade_fig, grenade_ax

        if show_lines:
            grenade_co_mask = (round_dfs["grenade_lines"]["throw_tick"] >= min_tick) & (
                round_dfs["grenade_lines"]["throw_tick"] <= max_tick
            )
            filtered_g_co = round_dfs["grenade_lines"][grenade_co_mask]
            if len(filtered_g_co) > 0:
                cg_fig, cg_ax = plot_line(
                    filtered_g_co,
                    "thrower",
                    "grenade",
                    "throw_tick",
                    default_color="Greens",
                    fig=current_fig,
                    ax=current_ax,
                )
                current_fig, current_ax = cg_fig, cg_ax

    # Add title with tick range info
    plt.title(f"Game Actions (Tick range: 0 - {max_tick})", fontsize=14)
    info_text = f"Events in range: {flash_count} flashes, {kill_count} kills, {grenade_count} grenades"
    plt.figtext(
        0.5,
        0.01,
        info_text,
        ha="center",
        fontsize=12,
        bbox=dict(facecolor="white", alpha=0.8),
    )

    plt.tight_layout()
    return current_fig, current_ax


def plot_round_timeline_plotly(df):
    colors = [
        "skyblue" if row["ct_win"] == 1 else "lightcoral" for _, row in df.iterrows()
    ]
    labels = df["round_end_reason"]
    rounds = df["round_num"]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=rounds,
            y=[1] * len(rounds),
            marker_color=colors,
            text=labels,
            hovertext=labels,
            hoverinfo="text+x",
            textposition="inside",
            insidetextanchor="middle",
            width=0.9,
        )
    )

    fig.update_layout(
        title="Round Timeline",
        xaxis_title="Round Number",
        yaxis=dict(visible=False),
        showlegend=False,
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
    )

    return fig


def plot_scaled_feature_difference(rounds_sum_df: pd.DataFrame):
    """
    Plots percentage difference between CT and T round wins.

    Returns:
        percentage_df (pd.DataFrame): DataFrame of percentage differences.
        fig (plotly.graph_objects.Figure): Plotly bar chart figure.
    """
    # Split by winning side
    ct_win_df = rounds_sum_df[rounds_sum_df["winning_side"] == 1]
    t_win_df = rounds_sum_df[rounds_sum_df["winning_side"] == 0]

    # Select relevant features
    features_to_compare = rounds_sum_df.columns.to_list()
    for col in ["bomb_plant_tick", "winning_side"]:
        if col in features_to_compare:
            features_to_compare.remove(col)

    features_to_compare = [
        col for col in features_to_compare if not col.startswith("round_end_reason_")
    ]

    # Calculate percentage difference
    percentage_df = pd.DataFrame()
    for feature in features_to_compare:
        t_mean = t_win_df[feature].mean()
        ct_mean = ct_win_df[feature].mean()
        if t_mean != 0:
            pct_change = ((ct_mean / t_mean) - 1) * 100
        else:
            pct_change = float("inf") if ct_mean > 0 else float("-inf")
        percentage_df.loc[feature, "%diff"] = pct_change

    # Prepare for plotting
    percentage_df.reset_index(inplace=True)
    percentage_df.rename(columns={"index": "Feature"}, inplace=True)
    percentage_df.sort_values("%diff", ascending=False, inplace=True)
    percentage_df.dropna(how="any", inplace=True)

    # Plot
    fig = px.bar(
        percentage_df,
        x="Feature",
        y="%diff",
        color=percentage_df["%diff"].apply(lambda x: "CT Win" if x > 0 else "T Win"),
        color_discrete_map={"CT Win": "green", "T Win": "red"},
        title="Percentage Difference Between CT and T Win Rounds",
        labels={"%diff": "Percentage Difference (%)"},
    )

    fig.update_layout(
        xaxis_tickangle=45,
        yaxis=dict(gridcolor="lightgray"),
        height=600,
        showlegend=True,
        legend_title="Winning Side",
    )

    return percentage_df, fig


def plot_location_change_analysis(clean_dfs, round_num):

    # Create subplots with 3 rows and 1 column
    fig = make_subplots(
        rows=3,
        cols=1,
        subplot_titles=[
            "<b>Location Change with Flash</b>",
            "<b>Location Change with Kills</b>",
            "<b>Location Change with Grenade</b>",
        ],
        vertical_spacing=0.15,
        shared_xaxes=True,
    )

    # Preprocessing: Location Change
    sel_loc = (
        clean_dfs["player_frames"].loc[round_num][["tick", "side", "x", "y"]].copy()
    )
    first_tick = clean_dfs["rounds"].loc[round_num]["start_tick"]
    sel_loc["tick"] -= first_tick
    curr_x = sel_loc.iloc[1:]["x"].values
    prev_x = sel_loc.iloc[:-1]["x"].values
    curr_y = sel_loc.iloc[1:]["y"].values
    prev_y = sel_loc.iloc[:-1]["y"].values
    loc_change = [0] + list(np.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2))
    sel_loc["loc_change"] = loc_change
    sel_team_loc = sel_loc.groupby(["side", "tick"]).agg(
        avg_loc_change=("loc_change", "mean")
    )

    ct_loc_df = sel_team_loc.loc["CT"].reset_index()
    t_loc_df = sel_team_loc.loc["T"].reset_index()

    # Colors - bright colors for dark theme
    ct_color = "rgba(0, 150, 255, 1)"
    t_color = "rgba(255, 80, 80, 1)"

    # Add traces for all three subplots - Team location changes
    for i in range(1, 4):
        # CT Location Change
        fig.add_trace(
            go.Scatter(
                x=ct_loc_df["tick"],
                y=ct_loc_df["avg_loc_change"],
                name="CT Avg. Loc. Change",
                line=dict(color=ct_color, width=2.5),
                hovertemplate="Tick: %{x}<br>Avg. Location Change: %{y:.2f}<extra></extra>",
                legendgroup="ct_loc",
                showlegend=True if i == 1 else False,
            ),
            row=i,
            col=1,
        )

        # T Location Change
        fig.add_trace(
            go.Scatter(
                x=t_loc_df["tick"],
                y=t_loc_df["avg_loc_change"],
                name="T Avg. Loc. Change",
                line=dict(color=t_color, width=2.5),
                hovertemplate="Tick: %{x}<br>Avg. Location Change: %{y:.2f}<extra></extra>",
                legendgroup="t_loc",
                showlegend=True if i == 1 else False,
            ),
            row=i,
            col=1,
        )

    # Get y-axis ranges for proper vertical line scaling
    y_ranges = []
    for i in range(1, 4):
        max_ct = max(ct_loc_df["avg_loc_change"])
        max_t = max(t_loc_df["avg_loc_change"])
        y_max = max(max_ct, max_t) * 1.1  # Add some padding
        y_ranges.append([0, y_max])

        fig.update_yaxes(range=[0, y_max], row=i, col=1)

    # Subplot 1: Add Flash events - each to its specific subplot
    sel_f = clean_dfs["flashes"].loc[round_num].reset_index()
    sel_f["tick"] -= first_tick

    flash_events = []
    for attacker_side in ["CT", "T"]:
        flash_ticks = sel_f[sel_f.attacker_side == attacker_side]["tick"]
        color = (
            "rgba(0, 150, 255, 0.8)"
            if attacker_side == "CT"
            else "rgba(255, 80, 80, 0.8)"
        )

        if len(flash_ticks) > 0:
            flash_events.append(
                {"side": attacker_side, "ticks": flash_ticks, "color": color}
            )

            # Add a single legend item for each side's flashes
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="lines",
                    line=dict(color=color, width=2, dash="dash"),
                    name=f"{attacker_side} Flash",
                    legendgroup=f"{attacker_side}_flash",
                    showlegend=True,
                ),
                row=1,
                col=1,
            )

    # Add vertical lines for flashes
    for event in flash_events:
        for tick_value in event["ticks"]:
            fig.add_shape(
                type="line",
                x0=tick_value,
                x1=tick_value,
                y0=0,
                y1=y_ranges[0][1],
                line=dict(color=event["color"], width=1.5, dash="dash"),
                row=1,
                col=1,
            )

    # Subplot 2: Add Kill events
    sel_k = clean_dfs["kills"].loc[round_num].reset_index()
    sel_k["tick"] -= first_tick

    kill_events = []
    for attacker_side in ["CT", "T"]:
        kill_ticks = sel_k[sel_k.attacker_side == attacker_side]["tick"]
        color = (
            "rgba(200, 0, 200, 0.8)"
            if attacker_side == "CT"
            else "rgba(255, 200, 0, 0.8)"
        )

        if len(kill_ticks) > 0:
            kill_events.append(
                {"side": attacker_side, "ticks": kill_ticks, "color": color}
            )

            # Add a single legend item for each side's kills
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="lines",
                    line=dict(color=color, width=2, dash="dash"),
                    name=f"{attacker_side} Kill",
                    legendgroup=f"{attacker_side}_kill",
                    showlegend=True,
                ),
                row=2,
                col=1,
            )

    # Add vertical lines for kills
    for event in kill_events:
        for tick_value in event["ticks"]:
            fig.add_shape(
                type="line",
                x0=tick_value,
                x1=tick_value,
                y0=0,
                y1=y_ranges[1][1],
                line=dict(color=event["color"], width=1.5, dash="dash"),
                row=2,
                col=1,
            )

    # Subplot 3: Add Grenade events
    sel_g = clean_dfs["grenades"].loc[round_num].reset_index()
    sel_g["throw_tick"] -= first_tick

    grenade_events = []
    for thrower_side in ["CT", "T"]:
        grenade_ticks = sel_g[sel_g.thrower_side == thrower_side]["throw_tick"]
        color = (
            "rgba(255, 105, 180, 0.8)"
            if thrower_side == "CT"
            else "rgba(0, 255, 255, 0.8)"
        )

        if len(grenade_ticks) > 0:
            grenade_events.append(
                {"side": thrower_side, "ticks": grenade_ticks, "color": color}
            )

            # Add a single legend item for each side's grenades
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="lines",
                    line=dict(color=color, width=2, dash="dash"),
                    name=f"{thrower_side} Grenade",
                    legendgroup=f"{thrower_side}_grenade",
                    showlegend=True,
                ),
                row=3,
                col=1,
            )

    # Add vertical lines for grenades
    for event in grenade_events:
        for tick_value in event["ticks"]:
            fig.add_shape(
                type="line",
                x0=tick_value,
                x1=tick_value,
                y0=0,
                y1=y_ranges[2][1],
                line=dict(color=event["color"], width=1.5, dash="dash"),
                row=3,
                col=1,
            )

    # Update layout with dark theme
    fig.update_layout(
        height=800,
        width=900,
        title=dict(
            text=f"Location Change Analysis - Round {round_num}",
            font=dict(size=22, color="white"),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",  # Changed from "bottom" to "top"
            y=-0.15,  # Changed from 1.05 to -0.15
            xanchor="center",
            x=0.5,
            font=dict(size=12, color="white"),
            bgcolor="rgba(30, 30, 30, 0.8)",
            bordercolor="rgba(100, 100, 100, 0.8)",
            borderwidth=1,
            itemsizing="constant",
            itemwidth=40,
            tracegroupgap=5,
        ),
        hovermode="closest",
        plot_bgcolor="rgb(17, 17, 17)",
        paper_bgcolor="rgb(17, 17, 17)",
        font=dict(family="Arial, sans-serif", size=14, color="white"),
        margin=dict(
            l=80, r=50, t=120, b=120
        ),  # Increased bottom margin to accommodate legend
    )

    # Update axes
    fig.update_xaxes(
        title=dict(text="Tick", font=dict(size=16, color="white")),
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(70, 70, 70, 1)",
        zeroline=True,
        zerolinewidth=1,
        zerolinecolor="rgba(100, 100, 100, 1)",
        showline=True,
        linewidth=1,
        linecolor="rgba(150, 150, 150, 1)",
        row=3,
        col=1,  # Only show x-axis title on bottom plot
    )

    # Update y-axes for each subplot
    for i in range(1, 4):
        fig.update_yaxes(
            title=dict(
                text="Average Location Change", font=dict(size=16, color="white")
            ),
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(70, 70, 70, 1)",
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="rgba(100, 100, 100, 1)",
            showline=True,
            linewidth=1,
            linecolor="rgba(150, 150, 150, 1)",
            row=i,
            col=1,
        )

    return fig


def plot_combined_economy_with_reasons(rounds_sum_df: pd.DataFrame):
    # Reconstruct `round_end_reason` from one-hot
    reason_cols = [
        col for col in rounds_sum_df.columns if col.startswith("round_end_reason_")
    ]
    rounds_sum_df = rounds_sum_df.copy()
    rounds_sum_df["round_end_reason"] = rounds_sum_df[reason_cols].idxmax(axis=1)
    rounds_sum_df["round_end_reason"] = rounds_sum_df["round_end_reason"].str.replace(
        "round_end_reason_", ""
    )

    # Color mapping
    win_reason_colors = {
        "TerroristsWin": "#e74c3c",
        "TargetBombed": "#f39c12",
        "TargetSaved": "#27ae60",
        "CTWin": "#3498db",
        "BombDefused": "#9b59b6",
    }

    rounds_sum_df["round"] = range(len(rounds_sum_df))

    fig = go.Figure()

    # Economy lines
    fig.add_trace(
        go.Scatter(
            x=rounds_sum_df["round"],
            y=rounds_sum_df["ct_freeze_time_end_eq_val"],
            name="CT Economy",
            mode="lines+markers",
            line=dict(color="blue"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=rounds_sum_df["round"],
            y=rounds_sum_df["t_freeze_time_end_eq_val"],
            name="T Economy",
            mode="lines+markers",
            line=dict(color="red"),
        )
    )

    # Vertical lines + rotated annotations
    for _, row in rounds_sum_df.iterrows():
        reason = row["round_end_reason"]
        color = win_reason_colors.get(reason, "#888888")
        round_num = row["round"]

        # Vertical line
        fig.add_vline(
            x=round_num, line=dict(color=color, width=2, dash="dot"), opacity=0.5
        )

        # Rotated annotation (above the top of the y-axis)
        fig.add_annotation(
            x=round_num,
            y=max(
                rounds_sum_df["ct_freeze_time_end_eq_val"].max(),
                rounds_sum_df["t_freeze_time_end_eq_val"].max(),
            )
            * 1.05,  # position above the lines
            text=reason,
            showarrow=False,
            textangle=-90,  # vertical rotation
            font=dict(size=10, color=color),
            yanchor="bottom",
        )

    fig.update_layout(
        title="T and CT Economy with Round End Reasons",
        xaxis_title="Round",
        yaxis_title="Freeze Time End Equipment Value",
        legend_title="Team",
        height=700,
        margin=dict(t=50, b=50),
        showlegend=True,
    )

    return fig
