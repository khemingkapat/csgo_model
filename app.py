import streamlit as st
from utils.components import upload_and_parse_json, plot_map, plot_loc_unicode
from utils.parsers import parse_json_to_dfs
from utils.preprocessing import preprocess
from utils.transformers import transform_coord

import json

with open(".awpy/maps/map-data.json", "r") as f:
    all_map_data = json.load(f)

side_color = {"ct": "Blues", "t": "Reds"}

st.title("📄 JSON File Uploader Dashboard")

json_data = upload_and_parse_json(preview_limit=0)


if json_data is None:
    st.warning(
        "⚠️ No JSON file uploaded or failed to parse. Please upload a valid JSON file."
    )
    st.stop()  # Exit here and prevent the rest of the app from running

st.write("✅ JSON is ready for further processing.")
dfs = dict(parse_json_to_dfs(json_data))
clean_dfs = preprocess(dfs)
selected_map = clean_dfs["matches"]["map_name"][0]

round_numbers = sorted(clean_dfs["rounds"].reset_index().round_num.unique())

selected_round = st.selectbox(
    "Select Round:", options=round_numbers, format_func=lambda x: f"Round {x}"
)

fig, ax = plot_map(selected_map)


selected_idx = (clean_dfs["matches"]["match_id"][0], selected_round)
# st.dataframe(clean_dfs["player_frames"].loc[selected_idx].head())

transformed_loc = transform_coord(
    all_map_data[selected_map], clean_dfs["player_frames"].loc[selected_idx].iloc[::2]
)


loc_fig, loc_ax = plot_loc_unicode(
    transformed_loc,
    gradient_by="tick",
    size=5,
    color_by="side",
    color_dict=side_color,
    default_marker="$\u2B24$",
    fig=fig,
    ax=ax,
)

st.pyplot(loc_fig)

#
# for key, df in clean_dfs.items():
#     st.subheader(f"📊 DataFrame : {key}")
#     st.dataframe(df.head())  # Display only the first few rows
