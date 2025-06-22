# ESTA CSGO Data Modelling
This project Featured in CPE232 Data Models, KMUTT


# Table of Contents
- [Overview](#Overview)
- [Features](#Features)
- [Installation](#Installation)
- [Usage](#Usage)
- [Contribution](#Contribution)
- [Roadmap](#Roadmap)

# Overview
> As mentioned, this project was featured in CPE232 Data Models course, KMUTT. But later on, the repository owner decided to extend this project as per his desired.

This project aims to provide a tools for CS:GO match analysis with tool such that covering most aspect of the match as possible to help reduce the time that take to watch the VODs. Also suggesting systematically analysis based mostly on statistic and machine learning, to make sure every match analysis come out consistently. Final tools will be web based by [Streamlit](https://streamlit.io/) for mobility and flexilibility. (More details will be addressed in [Roadmap](#Roadmaps))

# Features
- CS:GO match analysis via parsed Demo match in [ESTA](https://github.com/pnxenopoulos/esta)
- Round Overview : Players Stats, Round Tracking, Value Different to see what is important for the game
- Action Over Location : Visualization prioritizing location of each action
  - Players Movement
  - Kills, Grenades, Flashes
  - Action's Trajectories to show which action direction and where are the result
- Action Over Time : Visualization prioritizing action over time and its result for the movement
- Game Economy : Showing Economy and round end reason
- Round Prediction Machine Learning Model : Predicting the economy different of each round to resulted in which side would win by value captured from previous round(s)
- Movement Clustering Analysis : New way of systematically analyse how players move in the map as a team, how they split and join over time

# Installation
> Personally I use it via `nix`, but if you using traditional python with pip, it could be easily follows it by reading in the [flake.nix](https://github.com/khemingkapat/csgo_model/blob/main/flake.nix) file to see what is used

for `nix` user you could
``` bash
git clone github.com/khemingkapat/csgo_model
cd csgo_model
nix develop
```

and then for running `streamlit` app
```bash
streamlit run app.py
```

and for running `jupyter lab` for further analysis
```bash
jupyter lab
```
# Usage
So if you choose to run the `streamlit` app, you could just find any ***Decompressed*** `json` file from the [ESTA](https://github.com/pnxenopoulos/esta). the upload it into the app. Now you can navigate through the app where it struck your interest.

# Contribution
So just normally how you contribute to any github project. Creating a fork and branch for features
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Also another thing to mention here, Any idea from any perspective of the game would be appricated. Since not having any experience on real world game analysis is the main limit here. You could contact me via this github for further discussion.

# Roadmap
> This project still on its very early stage. Still many more things I wanted to implement to make it really work in the real world. Also many things to improve for better usage and performance.

- Improvements
  - Better responsiveness on action over location visualization, less to no reloading between tick window,
  - Animation Like with Tick Slider, to be able to see game on specific tick
  - Interactive visualization for more information

- Future Plans
  - Cluster Analysis and Path Decomposition, more systematic way to compare between each round of movement
 
---
*This project was a part of academic course work at KMUTT which I continue to work since it spark some passion in me and keeping me wanting to do something.*
