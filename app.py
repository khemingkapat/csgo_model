import streamlit as st
import json
import pandas as pd
from utils.components import (
    plot_combined_economy_with_reasons,
    plot_location_change_analysis,
    plot_scaled_feature_difference,
    upload_and_parse_json,
    plot_actions_by_max_tick,
    plot_round_timeline_plotly,
)
from utils.parsers import parse_json_to_dfs
from utils.preprocessing import preprocess
from utils.transformers import transform_all_data
from utils.symbols import *

# Set page config for full width layout
st.set_page_config(
    page_title="CS:GO Match Analysis Dashboard",
    page_icon="🎮",
    layout="wide",  # This makes the app use the full width of the screen
    initial_sidebar_state="expanded",
)

# Initialize session state variables
if "page" not in st.session_state:
    st.session_state.page = "home"
if "json_data" not in st.session_state:
    st.session_state.json_data = None
if "clean_dfs" not in st.session_state:
    st.session_state.clean_dfs = None
if "transformed_data" not in st.session_state:
    st.session_state.transformed_data = None
if "visualization_updated" not in st.session_state:
    st.session_state.visualization_updated = False


# Load map data once
@st.cache_resource
def load_map_data():
    with open(".awpy/maps/map-data.json", "r") as f:
        return json.load(f)


all_map_data = load_map_data()


# Cache the preprocessing steps to avoid redundant computations
@st.cache_data
def load_and_preprocess_data(json_data):
    """Load and preprocess all data at once"""
    dfs = dict(parse_json_to_dfs(json_data))
    clean_dfs = preprocess(dfs)
    return clean_dfs


# Get tick range for a specific round
def get_round_tick_range(clean_dfs, round_num):
    round_data = clean_dfs["rounds"].loc[round_num]
    start_tick = round_data["start_tick"]
    end_tick = round_data["end_tick"]
    return start_tick, end_tick


# Home page for file upload
def home_page():
    st.title("CS:GO Match Analysis Dashboard")
    st.subheader("Upload Match Data")

    st.write(
        """
    Welcome to the CS:GO Match Analysis Dashboard! 
    
    This tool helps you analyze Counter-Strike: Global Offensive match data with detailed visualizations of player movements, kills, flashes, and grenades.
    
    To begin, please upload a CS:GO match JSON file below.
    """
    )

    # Center the upload button in a container with max width
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_data = upload_and_parse_json(preview_limit=0)

    if uploaded_data is not None:
        # Store data in session state
        st.session_state.json_data = uploaded_data

        # Process data immediately and store in session state
        with st.spinner("Processing data... This may take a moment."):
            # Parse and preprocess
            dfs = dict(parse_json_to_dfs(uploaded_data))
            st.session_state.clean_dfs = preprocess(dfs)

            # Transform data
            st.session_state.transformed_data = transform_all_data(
                st.session_state.clean_dfs, all_map_data
            )

        # Set page to overview
        st.session_state.page = "overview"
        st.success("File successfully uploaded! Redirecting to Overview page...")
        st.rerun()


# Overview page (empty for now)
def overview_page():
    st.title("Match Overview")

    if st.session_state.json_data is None:
        st.warning("No data available. Please upload a file first.")
        st.session_state.page = "home"
        st.rerun()
        return

    # Add match information
    clean_dfs = st.session_state.clean_dfs
    transformed_data = st.session_state.transformed_data
    match_info = clean_dfs["matches"].iloc[0]

    st.subheader("Match Information")
    st.info(f"Map: {match_info['map_name']} | Date: {match_info['match_date']}")

    fig = plot_round_timeline_plotly(transformed_data["round_results"])
    st.plotly_chart(fig, use_container_width=True)

    # Use columns to better organize content in full width
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Player Statistics")
        st.dataframe(transformed_data["player_stats"], use_container_width=True)
    with col2:
        st.subheader("Side Win Features' Different")
        _, fig = plot_scaled_feature_difference(transformed_data["rounds_sum"])
        st.plotly_chart(fig, use_container_width=True)


# Location page with visualizations
def location_page():
    st.title("Location Analysis")

    if st.session_state.json_data is None:
        st.warning("No data available. Please upload a file first.")
        st.session_state.page = "home"
        st.rerun()
        return

    # Get processed data from session state
    clean_dfs = st.session_state.clean_dfs
    transformed_data = st.session_state.transformed_data

    # Get available rounds for selection
    available_rounds = clean_dfs["rounds"].reset_index()["round_num"].unique()
    available_rounds = sorted(available_rounds)

    # Create two columns for the match info and round selection
    match_col, round_col = st.columns([3, 1])

    with match_col:
        # Match information
        match_info = clean_dfs["matches"].iloc[0]
        st.subheader("Match Information")
        st.info(f"Map: {match_info['map_name']} | Date: {match_info['match_date']}")

    with round_col:
        # Round selection
        st.subheader("Round Selection")
        selected_round = st.selectbox(
            "Select Round",
            options=available_rounds,
            format_func=lambda x: f"Round {x}",
            key="round_selector",
        )

    # Display round information
    round_info = clean_dfs["rounds"].loc[selected_round]
    round_result = f"Winner: {round_info['winning_side'].upper()} | Reason: {round_info['round_end_reason']}"
    st.info(round_result)

    # Get tick range for selected round
    _, end_tick = get_round_tick_range(clean_dfs, selected_round)

    round_dfs = {
        k: v[v.index == selected_round] if isinstance(v, pd.DataFrame) else v
        for k, v in transformed_data.items()
    }

    # Create sidebar for controls
    st.sidebar.header("Visualization Controls")

    # Use round's end tick as the default max_tick
    st.sidebar.subheader("Tick Control")
    max_tick = st.sidebar.slider(
        "Max Tick",
        min_value=0,
        max_value=int(end_tick),
        value=end_tick // 2,
        help="Show events from tick 0 up to this tick value",
    )

    # Event visibility controls
    st.sidebar.subheader("Event Types")
    show_loc = st.sidebar.checkbox("Show Location", value=True)
    show_flash = st.sidebar.checkbox("Show Flashes", value=True)
    show_kills = st.sidebar.checkbox("Show Kills", value=True)
    show_grenades = st.sidebar.checkbox("Show Grenades", value=True)
    show_lines = st.sidebar.checkbox("Show Lines", value=True)

    # Visual styling controls
    with st.sidebar.expander("Visual Settings", expanded=False):
        col1, col2 = st.sidebar.columns(2)

        with col1:
            st.subheader("Opacity")
            flash_alpha = st.slider("Flash Alpha", 0.1, 1.0, 0.7)
            kill_alpha = st.slider("Kill Alpha", 0.1, 1.0, 0.7)
            grenade_alpha = st.slider("Grenade Alpha", 0.1, 1.0, 0.7)

        with col2:
            st.subheader("Size")
            flash_size = 10 + int(st.checkbox("Big Flash", value=False)) * 20
            kill_size = 10 + int(st.checkbox("Big Kill", value=False)) * 20
            grenade_size = 10 + int(st.checkbox("Big Grenade", value=False)) * 20

    st.subheader(f"Game Actions - Round {selected_round}")

    # Update visualization button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        update_button = st.button("Update Visualization", use_container_width=True)

    # Update visualization if button clicked or parameters changed
    if update_button or not st.session_state.visualization_updated:
        fig, _ = plot_actions_by_max_tick(
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
        )
        st.pyplot(fig, use_container_width=True)
        st.session_state.visualization_updated = True

    # Show statistics
    with st.expander("Round Statistics", expanded=False):
        st.subheader(f"Statistics for Round {selected_round}")

        # Filter actions by max tick for statistics
        flash_mask = (round_dfs["flashes"]["tick"] >= 0) & (
            round_dfs["flashes"]["tick"] <= max_tick
        )
        kill_mask = (round_dfs["kills"]["tick"] >= 0) & (
            round_dfs["kills"]["tick"] <= max_tick
        )
        grenade_mask = (round_dfs["grenades"]["throw_tick"] >= 0) & (
            round_dfs["grenades"]["throw_tick"] <= max_tick
        )

        filtered_flash = (
            round_dfs["flashes"][flash_mask][
                round_dfs["flashes"][flash_mask].status.isin(["flahser", "both"])
            ]
            if isinstance(round_dfs["flashes"], pd.DataFrame)
            else pd.DataFrame()
        )
        filtered_kills = (
            round_dfs["kills"][kill_mask][
                round_dfs["kills"][kill_mask].status.isin(["attacker", "suicide"])
            ]
            if isinstance(round_dfs["kills"], pd.DataFrame)
            else pd.DataFrame()
        )
        filtered_grenades = (
            round_dfs["grenades"][grenade_mask]
            if isinstance(round_dfs["grenades"], pd.DataFrame)
            else pd.DataFrame()
        )

        # Display basic statistics - use more columns in full width
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Flashes",
                (
                    len(filtered_flash)
                    if isinstance(filtered_flash, pd.DataFrame)
                    else 0
                ),
            )
            if not filtered_flash.empty:
                st.write("Flash Distribution:")
                side_counts = filtered_flash["attacker_side"].value_counts()
                st.bar_chart(side_counts, use_container_width=True)

        with col2:
            st.metric(
                "Kills",
                (
                    len(filtered_kills)
                    if isinstance(filtered_kills, pd.DataFrame)
                    else 0
                ),
            )
            if not filtered_kills.empty:
                st.write("Kill Distribution:")
                side_counts = filtered_kills["attacker_side"].value_counts()
                st.bar_chart(side_counts, use_container_width=True)

        with col3:
            st.metric(
                "Grenades",
                (
                    len(filtered_grenades) / 2
                    if isinstance(filtered_grenades, pd.DataFrame)
                    else 0
                ),
            )
            if not filtered_grenades.empty:
                st.write("Grenade Distribution:")
                side_counts = filtered_grenades["thrower_side"].value_counts()
                st.bar_chart(side_counts, use_container_width=True)


# Action page (empty for now)
def action_page():
    st.title("Action Analysis")

    if st.session_state.json_data is None:
        st.warning("No data available. Please upload a file first.")
        st.session_state.page = "home"
        st.rerun()
        return

    clean_dfs = st.session_state.clean_dfs
    available_rounds = clean_dfs["rounds"].reset_index()["round_num"].unique()
    available_rounds = sorted(available_rounds)[1:]

    # Create two columns for the match info and round selection
    match_col, round_col = st.columns([3, 1])

    with match_col:
        # Match information
        match_info = clean_dfs["matches"].iloc[0]
        st.subheader("Match Information")
        st.info(f"Map: {match_info['map_name']} | Date: {match_info['match_date']}")

    with round_col:
        # Round selection
        st.subheader("Round Selection")
        selected_round = st.selectbox(
            "Select Round",
            options=available_rounds,
            format_func=lambda x: f"Round {x}",
            key="round_selector",
        )

    fig = plot_location_change_analysis(clean_dfs, selected_round)

    st.plotly_chart(fig, use_container_width=True)


# Economy page (empty for now)
def economy_page():
    st.title("Economy Analysis")

    if st.session_state.json_data is None:
        st.warning("No data available. Please upload a file first.")
        st.session_state.page = "home"
        st.rerun()
        return

    transformed_data = st.session_state.transformed_data
    # Create a nicer layout for "under development" message
    fig = plot_combined_economy_with_reasons(transformed_data["rounds_sum"])
    st.plotly_chart(fig, use_container_width=True)


# Main app function with navigation
def main():
    pages = {
        "home": home_page,
        "overview": overview_page,
        "location": location_page,
        "action": action_page,
        "economy": economy_page,
    }

    # Display the current page based on session state
    current_page = st.session_state.page

    # Show navigation bar only for non-home pages
    if current_page != "home":
        # Create the navigation bar
        st.sidebar.title("Navigation")
        nav_options = ["Overview", "Location", "Action", "Economy"]

        # Convert page name to title case for display
        current_nav_option = current_page.title()

        # Display navigation options
        selected_nav = st.sidebar.radio(
            "Go to", nav_options, index=nav_options.index(current_nav_option)
        )

        # Update page if selection changed
        if selected_nav.lower() != current_page:
            st.session_state.page = selected_nav.lower()
            st.rerun()

        # Add some space and a divider
        st.sidebar.markdown("---")
        st.sidebar.info("CS:GO Match Analysis Tool")

        # Add a button to return to upload page if needed
        if st.sidebar.button("Upload New File"):
            st.session_state.page = "home"
            st.session_state.json_data = None
            st.session_state.clean_dfs = None
            st.session_state.transformed_data = None
            st.session_state.visualization_updated = False
            st.rerun()

    # Call the selected page function
    pages[current_page]()


if __name__ == "__main__":
    main()
