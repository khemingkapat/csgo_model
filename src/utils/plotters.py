from src.utils.constants import image_dim
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import requests
from io import BytesIO


def plot_map(map_name, fig_size, path=".awpy/maps/", fig=None, ax=None):
    fig, ax = plt.subplots(figsize=fig_size)
    map_img = plt.imread(f"{path}{map_name}.png")
    ax.imshow(map_img, extent=[0, image_dim, 0, image_dim])
    ax.set_xlim(0, image_dim)
    ax.set_ylim(0, image_dim)
    ax.set_title(map_name.title())
    return fig, ax


def count_colorbar(fig):
    result = 0
    for ax in fig.axes:
        if "colorbar" in ax.get_label():
            result += 1
    return result


def plot_loc_img_unicode(
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
    """
    Plot locations with unicode markers or images.

    Parameters:
    -----------
    size : int/float
        Size parameter that controls both text fontsize and image display size
    marker_dict : dict
        Dictionary mapping marker keys to either:
        - Unicode strings (e.g., '⚽', '🏀') for text markers
        - Image paths/URLs (e.g., 'path/to/image.png', 'https://...') for images
        - PIL Image objects
    """
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

    # Cache for loaded images to avoid reloading
    image_cache = {}

    # Calculate image parameters based on size
    # Convert fontsize to approximate pixel size for images
    # Typical conversion: fontsize * 1.3 gives approximate pixel height
    image_pixel_size = int(size * 1.3)
    image_size = (image_pixel_size, image_pixel_size)
    # Auto-calculate zoom to match the size parameter
    # Base zoom calculation to make image similar size to text
    auto_zoom = size / 100.0  # Adjust this ratio as needed

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

        # Check if marker_char is an image or unicode text
        if _is_image_marker(marker_char):
            # Handle image marker
            try:
                img_array = _load_and_process_image(
                    marker_char, image_size, image_cache
                )
                if img_array is not None:
                    # Apply color tint to image if needed (optional feature)
                    if len(img_array.shape) == 3 and img_array.shape[2] == 4:  # RGBA
                        tinted_img = _apply_color_tint(img_array, color, alpha)
                    else:
                        tinted_img = img_array

                    # Create OffsetImage with auto-calculated zoom
                    imagebox = OffsetImage(tinted_img, zoom=auto_zoom)
                    ab = AnnotationBbox(
                        imagebox, (row["x"], row["y"]), frameon=False, pad=0
                    )
                    ax.add_artist(ab)
                else:
                    # Fallback to text if image loading fails
                    ax.text(
                        row["x"],
                        row["y"],
                        "?",  # Question mark as fallback
                        fontsize=size,
                        color=color,
                        ha="center",
                        va="center",
                        alpha=alpha,
                    )
            except Exception as e:
                print(f"Error loading image for marker {marker_char}: {e}")
                # Fallback to text
                ax.text(
                    row["x"],
                    row["y"],
                    "?",
                    fontsize=size,
                    color=color,
                    ha="center",
                    va="center",
                    alpha=alpha,
                )
        else:
            # Handle unicode/text marker (original behavior)
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


def _is_image_marker(marker):
    """
    Determine if a marker is an image (file path, URL, or PIL Image object)
    """
    if isinstance(marker, Image.Image):
        return True

    if isinstance(marker, str):
        # Check if it's a file path or URL
        if (
            marker.startswith("http://")
            or marker.startswith("https://")
            or marker.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"))
        ):
            return True

    return False


def _load_and_process_image(marker, target_size, cache):
    """
    Load and process image from various sources
    """
    # Use cache key
    cache_key = str(marker) + str(target_size)
    if cache_key in cache:
        return cache[cache_key]

    try:
        img = None

        if isinstance(marker, Image.Image):
            # Already a PIL Image
            img = marker
        elif isinstance(marker, str):
            if marker.startswith("http://") or marker.startswith("https://"):
                # URL
                response = requests.get(marker, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
            else:
                # File path
                img = Image.open(marker)

        if img is not None:
            # Convert to RGBA for consistency
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Resize image
            img_resized = img.resize(target_size, Image.LANCZOS)

            # Convert to numpy array
            img_array = np.array(img_resized)

            # Cache the processed image
            cache[cache_key] = img_array

            return img_array

    except Exception as e:
        print(f"Failed to load image {marker}: {e}")
        cache[cache_key] = None
        return None

    return None


def _apply_color_tint(img_array, color, alpha_factor=1.0):
    """
    Apply color tint to RGBA image while preserving transparency
    """
    if len(img_array.shape) != 3 or img_array.shape[2] != 4:
        return img_array

    # Create a copy to avoid modifying original
    tinted = img_array.copy().astype(float)

    # Extract RGB components from matplotlib color (0-1 range)
    if len(color) >= 3:
        r, g, b = color[:3]

        # Apply tint to RGB channels where alpha > 0
        alpha_mask = tinted[:, :, 3] > 0
        tinted[alpha_mask, 0] = tinted[alpha_mask, 0] * r / 255.0 * 255.0
        tinted[alpha_mask, 1] = tinted[alpha_mask, 1] * g / 255.0 * 255.0
        tinted[alpha_mask, 2] = tinted[alpha_mask, 2] * b / 255.0 * 255.0

    # Apply alpha factor
    tinted[:, :, 3] = tinted[:, :, 3] * alpha_factor

    return tinted.astype(np.uint8)
