import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
import japanize_matplotlib
import glob
from matplotlib.patches import Polygon
import datetime as dt
import time
import math
import requests
from bs4 import BeautifulSoup
import seaborn
st.set_page_config(layout='wide')

st.title("Umpire")

sz_left = 20.3
sz_right = 114.8
sz_top = 26.8*-1+200
sz_bot = 146.3*-1+200

home_plate_coords = [sz_left, sz_bot -10,  # 中心から左
                     sz_right, sz_bot-10,  # 中心から右
                     sz_right-7, sz_bot,  # 右上
                     (sz_left + sz_right) / 2, sz_bot+10,
                     sz_left+7, sz_bot  # 左上
                     ]


cols = st.columns(5)
with cols[0]:
    league = st.selectbox(
        "Season",
        ["2024"],
        index = 0)
with cols[1]:
    league = st.selectbox(
        "League Type",
        ["1軍", "2軍"],
        index = 0)

def team_pitcher(df, team_name):
    team_p = df[df["fld_team"] == team_name].reset_index(drop=True)
    return team_p

def extract_date(filename):
    # ファイル名から日付部分を抽出して返す
    parts = filename.split('_')
    date_str = parts[0].split("/")[-1]  # 拡張子を除いた部分を取得
    return dt.datetime.strptime(date_str, '%Y年%m月%d日')

def calculate_ip(outs):
    ip = (outs // 3) + (outs % 3) * 0.1
    return ip

def my_round(x, decimals=0):
    return np.floor(x * 10**decimals + 0.5) / 10**decimals

# FIPを計算する関数
def calculate_fip(hr, bb, ibb, hbp, k, ip, league_hr_rate):
    fip_constant = (league_hr_rate * 13 + 3 * (bb - ibb + hbp) - 2 * k) / ip
    fip = ((13 * hr + 3 * (bb - ibb + hbp) - 2 * k) / ip) + fip_constant
    return fip

if league == "1軍":
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
elif league == "2軍":
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/2軍/farm2024.csv")

data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
latest_date = data["game_date"].max()
latest_date_str = latest_date.strftime("%Y/%m/%d")
year_list = list(data['game_date'].dt.year.unique())
year_list.sort(reverse=True)

game_df = data.groupby("game_id", as_index=False).head(1).reset_index(drop=True)
game_df = game_df[["game_date", "home_team", "away_team", "stadium", "start_time", "umpire", "umpire_1b", "umpire_2b", "umpire_3b"]]
game_df["game_date"] = game_df["game_date"].dt.strftime("%Y/%m/%d")
game_df = game_df.set_axis(["Date", "Home Team", "Away Team", "Venue", "Start Time", "Plate", "1B", "2B", "3B"], axis=1)

ump_list = list(game_df["Plate"].value_counts().index)

with cols[2]:
    ump = st.selectbox(
        "Plate Umpire",
        ["All"] + ump_list,
        index = 0)

if ump == "All":
    pass
else:
    game_df = game_df[game_df["Plate"] == ump]
    game_df = game_df.reset_index(drop=True)

st.dataframe(game_df, use_container_width=True)

pitch_df = data[data["description"] == "called_strike"]

fig, ax = plt.subplots(figsize=(4, 5))
seaborn.kdeplot(data=pitch_df, x="plate_x", y="plate_z", levels=20, cmap="bwr", shade=True, ax=ax)
ax.plot([sz_left, sz_right], [sz_top, sz_top], color='black')  # 上辺
ax.plot([sz_left, sz_right], [sz_bot, sz_bot], color='black')  # 下辺
ax.plot([sz_left, sz_left], [sz_top, sz_bot], color='black')   # 左辺
ax.plot([sz_right, sz_right], [sz_top, sz_bot], color='black') # 右辺
hplt_y = 60

home_plate = plt.Polygon([[home_plate_coords[0], home_plate_coords[1]-hplt_y], 
                        [home_plate_coords[2], home_plate_coords[3]-hplt_y], 
                        [home_plate_coords[4], home_plate_coords[5]-hplt_y], 
                        [home_plate_coords[6], home_plate_coords[7]-hplt_y], 
                        [home_plate_coords[8], home_plate_coords[9]-hplt_y]], 
                        closed=True, edgecolor='black', facecolor='none')
ax.add_patch(home_plate)

ax.set_xlim(sz_left-80, sz_right+80)
ax.set_ylim(sz_bot-85, sz_top+80)

ax.xaxis.set_ticks([])
ax.yaxis.set_ticks([])
ax.xaxis.set_ticklabels([])
ax.yaxis.set_ticklabels([])
ax.set_xlabel('')
ax.set_ylabel('')
# プロットを表示
st.pyplot(fig)