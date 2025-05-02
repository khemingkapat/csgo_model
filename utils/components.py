import streamlit as st
import matplotlib.pyplot as plt
import os
from matplotlib.figure import Figure
import json
import pandas as pd


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
