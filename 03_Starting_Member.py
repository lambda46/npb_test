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
from datetime import datetime, timedelta
import datetime as dt
import time
import math
import requests
from bs4 import BeautifulSoup
from PIL import Image
import seaborn as seaborn
import plotly.express as px
import plotly.figure_factory as ff
import july
from july.utils import date_range
import matplotlib.ticker as mtick
import plotly.graph_objects as go
import matplotlib.cm as cm



st.set_page_config(layout='wide')
st.title("Starting Member")

def team_pitcher(df, team_name):
    team_p = df[df["fld_team"] == team_name].reset_index(drop=True)
    return team_p

def extract_date(filename):
    # ファイル名から日付部分を抽出して返す
    parts = filename.split('_')
    date_str = parts[0].split("/")[-1]  # 拡張子を除いた部分を取得
    return datetime.strptime(date_str, '%Y年%m月%d日')

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

def calculate_age(birth_date_str):
    # yyyy-mm-dd形式の文字列をdatetimeオブジェクトに変換
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    
    # 現在の日付を取得
    today = datetime.today()
    
    # 年齢を計算
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    return age

d = 10

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

heart_right = sz_right - ((sz_right - sz_left) * 0.17)
heart_left = sz_left + ((sz_right - sz_left) * 0.17)
heart_top = sz_top - ((sz_top - sz_bot) * 0.17)
heart_bot = sz_bot + ((sz_top - sz_bot) * 0.17)

shadow_right = sz_right + ((sz_right - sz_left) * 0.06)
shadow_left = sz_left - ((sz_right - sz_left) * 0.06)
shadow_top = sz_top + ((sz_top - sz_bot) * 0.06)
shadow_bot = sz_bot - ((sz_top - sz_bot) * 0.06)

chase_right = sz_right + ((sz_right - sz_left) * 0.17)
chase_left = sz_left - ((sz_right - sz_left) * 0.17)
chase_top = sz_top + ((sz_top - sz_bot) * 0.17)
chase_bot = sz_bot - ((sz_top - sz_bot) * 0.17)

pl_list = ["オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム"]
cl_list = ["阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日"]

wl_list = ["オリックス", "阪神", "ソフトバンク", "広島", "くふうハヤテ", "中日"]
el_list = ["日本ハム", "楽天", "DeNA", "巨人", "ヤクルト", "ロッテ", "オイシックス", "西武"]

pos_list = ["All", "P", "C", "IF", "OF"]

pos_en_jp = {"P": "投手", "C": "捕手", "IF": "内野手", "OF": "外野手"}

team_en_dict = {
    "オリックス": "B", "ロッテ": "M", "ソフトバンク": "H", "楽天": "E", "西武": "L", "日本ハム": "F", 
    "阪神": "T", "広島": "C", "DeNA": "DB", "巨人": "G", "ヤクルト": "S", "中日": "D",
    "オイシックス": "A", "くふうハヤテ": "V"
}

team_long_dict = {
    "オリックス": "オリックス・バファローズ", "ロッテ": "千葉ロッテマリーンズ", "ソフトバンク": "福岡ソフトバンクホークス", 
    "楽天": "東北楽天ゴールデンイーグルス", "西武": "埼玉西武ライオンズ", "日本ハム": "北海道日本ハムファイターズ", 
    "阪神": "阪神タイガース", "広島": "広島東洋カープ", "DeNA": "横浜DeNAベイスターズ", 
    "巨人": "読売ジャイアンツ", "ヤクルト": "東京ヤクルトスワローズ", "中日": "中日ドラゴンズ",
    "オイシックス": "オイシックス新潟アルビレックスBC", "くふうハヤテ": "くふうハヤテベンチャーズ静岡"
}

pos_ja_dict = {
    "投": "P", "捕": "C", "一": "1B", "二": "2B", "三": "3B", "遊": "SS",
    "左": "LF", "中": "CF", "右": "RF", "指": "DH", "打": "PH", "走": "PR"
}

order_dict = {1: "Batting 1st", 2: "Batting 2nd", 3: "Batting 3rd", 4: "Batting 4th", 5: "Batting 5th", 
              6: "Batting 6th", 7: "Batting 7th", 8: "Batting 8th", 9: "Batting 9th"}

lr_en_dict = {"右": "R", "左": "L", "両": "S"}

cols = st.columns(5)
with cols[0]:
    league_type = st.radio("", ("1軍", "2軍"), horizontal=True)

if league_type == "1軍":
    team_list = ["Team"] + cl_list + pl_list
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
    data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
    data["game_month"] = data['game_date'].dt.month
    data['start_time'] = pd.to_datetime(data["start_time"], format='%H:%M:%S')
    sutamen = pd.read_csv("~/Python/baseball/NPB/スタメン/1軍/all2024_スタメン.csv")
    sutamen['game_date'] = pd.to_datetime(sutamen['game_date'], format='%Y-%m-%d')
    sutamen["game_month"] = sutamen['game_date'].dt.month
else:
    team_list = ["Team"] + el_list + wl_list
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/2軍/farm2024.csv")
    data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
    data["game_month"] = data['game_date'].dt.month
    data['start_time'] = pd.to_datetime(data["start_time"], format='%H:%M:%S')
    sutamen = pd.read_csv("~/Python/baseball/NPB/スタメン/2軍/farm2024_スタメン.csv")
    sutamen['game_date'] = pd.to_datetime(sutamen['game_date'], format='%Y-%m-%d')
    sutamen["game_month"] = sutamen['game_date'].dt.month

with cols[1]:
    team = st.selectbox(
        "",
        team_list,
        index = 0)
    
with cols[2]:
    month = st.selectbox(
        "",
        ["All Month", "March/April", "May", "June", "July", "August", "Sept~"],
        index = 0)

if month == "March/April":
    data = data[data["game_month"] <= 4]
    sutamen = sutamen[sutamen["game_month"] <= 4]
elif month == "May":
    data = data[data["game_month"] == 5]
    sutamen = sutamen[sutamen["game_month"] == 5]
elif month == "June":
    data = data[data["game_month"] == 6]
    sutamen = sutamen[sutamen["game_month"] == 6]
elif month == "July":
    data = data[data["game_month"] == 7]
    sutamen = sutamen[sutamen["game_month"] == 7]
elif month == "August":
    data = data[data["game_month"] == 8]
    sutamen = sutamen[sutamen["game_month"] == 8]
elif month == "Sept~":
    data = data[data["game_month"] >= 9]
    sutamen = sutamen[sutamen["game_month"] >= 9]

if team != "Team":
    bat_data = data[data["bat_team"] == team]
    sutamen = sutamen[sutamen["bat_team"] == team]
    p_data = data[data["fld_team"] == team]
    game_info = bat_data.groupby("game_id", as_index=False).head(1)
    game_info = game_info[["game_date", "start_time", "fld_team", "stadium", "pitcher_name", "game_id"]]
    game_info["game_date"] = game_info["game_date"].dt.strftime("%m/%d")
    game_info["start_time"] = game_info["start_time"].dt.strftime("%H:%M")
    sp_df = p_data.groupby("game_id", as_index=False).head(1)[["game_id", "pitcher_name"]]
    sp_df = sp_df.rename(columns={"pitcher_name": "SP"})
    
    starting_df = game_info

    for i in range(1, 10):
        order_en = order_dict[i]
        order_pos = order_en.split(" ")[-1] + " Pos"
        order_df = sutamen[sutamen["order"] == i][["game_id", "batter_name", "batter_pos"]]
        order_df["batter_pos"] = order_df["batter_pos"].replace(pos_ja_dict)
        order_df[order_en] = order_df["batter_name"].str.cat(order_df["batter_pos"], sep=" (") + ")"
        order_df = order_df.drop(columns=["batter_name", "batter_pos"])
        starting_df = pd.merge(starting_df, order_df, on=["game_id"], how="left")
        
    starting_df = starting_df.rename(columns={
            "game_date": "Date", "start_time": "Time", "fld_team": "vsTeam", "stadium": "Venue",
            "pitcher_name": "vs P"
        })
    starting_df = pd.merge(starting_df, sp_df, on="game_id", how="left")
    starting_df = starting_df.drop(columns="game_id")
    starting_df = starting_df.reset_index(drop=True)
    styler = starting_df.style.hide_index()

    # フォントサイズを小さくするスタイルを追加
    styler = styler.set_table_styles(
        [{'selector': 'td, th', 'props': [('font-size', '7pt')]}]
    )

if team != "Team":
    st.write(styler.to_html(), unsafe_allow_html=True, use_container_width=True)
