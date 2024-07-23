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

st.set_page_config(layout='wide')

st.title("Attendance")

def my_round(x, decimals=0):
    return np.floor(x * 10**decimals + 0.5) / 10**decimals

pl_list = ["オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム"]
cl_list = ["阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日"]

wl_list = ["オリックス", "阪神", "ソフトバンク", "広島", "くふうハヤテ", "中日"]
el_list = ["日本ハム", "楽天", "DeNA", "巨人", "ヤクルト", "ロッテ", "オイシックス", "西武"]

cols = st.columns(5)
with cols[0]:
    season = st.selectbox(
        "Season",
        ["2024"],
        index = 0)
    
with cols[1]:
    group = st.selectbox(
        "Data Type",
        ["Team", "Venue", "Game"],
        index = 0)
if group == "Team":
    group_list = ["home_team"]
    df_cols = ["Team"]
elif group == "Venue":
    group_list = ["home_team", "stadium"]
    df_cols = ["Team", "Venue"]
elif group == "Game":
    group_list = ["home_team", "stadium", "game_date"]
    df_cols = ["Team", "Venue", "Date"]

with cols[2]:
    league = st.selectbox(
        "League Type",
        ["1軍", "2軍"],
        index = 0)
    
cols = st.columns(5)

if league == "1軍":
    team_list = ["All Team"] + cl_list + pl_list
elif league == "2軍":
    team_list = ["All Team"] + el_list + wl_list

with cols[0]:
    team = st.selectbox(
        "Team",
        team_list,
        index = 0)

with cols[1]:
    week = st.selectbox(
        "Day of Week",
        ["All", "Weekday", "Weekend", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        index = 0)
    
with cols[2]:
    condition = st.selectbox(
        "Game Time",
        ["All", "Day", "Night"],
        index = 0)
    
if league == "1軍":
    venue_list = ["All", "本拠地", "本拠地以外"]
else:
    venue_list = ["All"]

with cols[3]:
    venue = st.selectbox(
        "Venue",
        venue_list,
        index = 0)
    
if league == "1軍":
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
elif league == "2軍":
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/2軍/farm2024.csv")

data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
latest_date = data["game_date"].max()
latest_date_str = latest_date.strftime("%Y/%m/%d")
year_list = list(data['game_date'].dt.year.unique())
year_list.sort(reverse=True)

st.markdown(f"{latest_date_str} 終了時点")

events_df = data.dropna(subset="events")
PA_df = events_df[(events_df["events"] != "pickoff_1b")&(events_df["events"] != "pickoff_2b")&(events_df["events"] != "pickoff_catcher")&(events_df["events"] != "caught_stealing")&(events_df["events"] != "stolen_base")&(events_df["events"] != "wild_pitch")&(events_df["events"] != "balk")&(events_df["events"] != "passed_ball")&(events_df["events"] != "caught_stealing")]


if venue == "本拠地":
    if league == "1軍":
        pf_PA_df = PA_df[((PA_df["home_team"] == "巨人")&(PA_df["stadium"] == "東京ドーム"))|
                    ((PA_df["home_team"] == "阪神")&(PA_df["stadium"] == "甲子園"))|
                    ((PA_df["home_team"] == "ヤクルト")&(PA_df["stadium"] == "神宮"))|
                    ((PA_df["home_team"] == "DeNA")&(PA_df["stadium"] == "横浜"))|
                    ((PA_df["home_team"] == "広島")&(PA_df["stadium"] == "マツダスタジアム"))|
                    ((PA_df["home_team"] == "中日")&(PA_df["stadium"] == "バンテリンドーム"))|
                    ((PA_df["home_team"] == "オリックス")&(PA_df["stadium"] == "京セラD大阪"))|
                    ((PA_df["home_team"] == "ソフトバンク")&((PA_df["stadium"] == "PayPayドーム")|(PA_df["stadium"] == "みずほPayPay")))|
                    ((PA_df["home_team"] == "ロッテ")&(PA_df["stadium"] == "ZOZOマリン"))|
                    ((PA_df["home_team"] == "日本ハム")&(PA_df["stadium"] == "エスコンF"))|
                    ((PA_df["home_team"] == "楽天")&(PA_df["stadium"] == "楽天モバイル"))|
                    ((PA_df["home_team"] == "西武")&(PA_df["stadium"] == "ベルーナドーム"))]

    elif league == "2軍":
        pf_PA_df = PA_df[((PA_df["home_team"] == "巨人")&(PA_df["stadium"] == "ジャイアンツ"))|
                        ((PA_df["home_team"] == "阪神")&(PA_df["stadium"] == "鳴尾浜"))|
                        ((PA_df["home_team"] == "ヤクルト")&(PA_df["stadium"] == "戸田"))|
                        ((PA_df["home_team"] == "DeNA")&((PA_df["stadium"] == "横須賀")|(PA_df["stadium"] == "平塚")))|
                        ((PA_df["home_team"] == "広島")&(PA_df["stadium"] == "由宇"))|
                        ((PA_df["home_team"] == "中日")&(PA_df["stadium"] == "ナゴヤ球場"))|
                        ((PA_df["home_team"] == "オリックス")&(PA_df["stadium"] == "杉本商事BS"))|
                        ((PA_df["home_team"] == "ソフトバンク")&(PA_df["stadium"] == "タマスタ筑後"))|
                        ((PA_df["home_team"] == "ロッテ")&(PA_df["stadium"] == "ロッテ"))|
                        ((PA_df["home_team"] == "日本ハム")&(PA_df["stadium"] == "鎌スタ"))|
                        ((PA_df["home_team"] == "楽天")&(PA_df["stadium"] == "森林どり泉"))|
                        ((PA_df["home_team"] == "西武")&(PA_df["stadium"] == "カーミニーク"))|
                        ((PA_df["home_team"] == "くふうハヤテ")&(PA_df["stadium"] == "ちゅ～る"))|
                        ((PA_df["home_team"] == "オイシックス")&((PA_df["stadium"] == "ハードオフ新潟")|(PA_df["stadium"] == "新潟みどり森")|(PA_df["stadium"] == "長岡悠久山")))]
elif venue == "本拠地以外":
    if league == "1軍":
        pf_PA_df = PA_df[((PA_df["home_team"] == "巨人")&(PA_df["stadium"] != "東京ドーム"))|
                    ((PA_df["home_team"] == "阪神")&(PA_df["stadium"] != "甲子園"))|
                    ((PA_df["home_team"] == "ヤクルト")&(PA_df["stadium"] != "神宮"))|
                    ((PA_df["home_team"] == "DeNA")&(PA_df["stadium"] != "横浜"))|
                    ((PA_df["home_team"] == "広島")&(PA_df["stadium"] != "マツダスタジアム"))|
                    ((PA_df["home_team"] == "中日")&(PA_df["stadium"] != "バンテリンドーム"))|
                    ((PA_df["home_team"] == "オリックス")&(PA_df["stadium"] != "京セラD大阪"))|
                    ((PA_df["home_team"] == "ソフトバンク")&((PA_df["stadium"] != "PayPayドーム")&(PA_df["stadium"] != "みずほPayPay")))|
                    ((PA_df["home_team"] == "ロッテ")&(PA_df["stadium"] != "ZOZOマリン"))|
                    ((PA_df["home_team"] == "日本ハム")&(PA_df["stadium"] != "エスコンF"))|
                    ((PA_df["home_team"] == "楽天")&(PA_df["stadium"] != "楽天モバイル"))|
                    ((PA_df["home_team"] == "西武")&(PA_df["stadium"] != "ベルーナドーム"))]

    elif league == "2軍":
        pf_PA_df = PA_df[((PA_df["home_team"] == "巨人")&(PA_df["stadium"] != "ジャイアンツ"))|
                        ((PA_df["home_team"] == "阪神")&(PA_df["stadium"] != "鳴尾浜"))|
                        ((PA_df["home_team"] == "ヤクルト")&(PA_df["stadium"] != "戸田"))|
                        ((PA_df["home_team"] == "DeNA")&((PA_df["stadium"] != "横須賀")|(PA_df["stadium"] != "平塚")))|
                        ((PA_df["home_team"] == "広島")&(PA_df["stadium"] != "由宇"))|
                        ((PA_df["home_team"] == "中日")&(PA_df["stadium"] != "ナゴヤ球場"))|
                        ((PA_df["home_team"] == "オリックス")&(PA_df["stadium"] != "杉本商事BS"))|
                        ((PA_df["home_team"] == "ソフトバンク")&(PA_df["stadium"] != "タマスタ筑後"))|
                        ((PA_df["home_team"] == "ロッテ")&(PA_df["stadium"] != "ロッテ"))|
                        ((PA_df["home_team"] == "日本ハム")&(PA_df["stadium"] != "鎌スタ"))|
                        ((PA_df["home_team"] == "楽天")&(PA_df["stadium"] != "森林どり泉"))|
                        ((PA_df["home_team"] == "西武")&(PA_df["stadium"] != "カーミニーク"))|
                        ((PA_df["home_team"] == "くふうハヤテ")&(PA_df["stadium"] != "ちゅ～る"))|
                        ((PA_df["home_team"] == "オイシックス")&((PA_df["stadium"] != "ハードオフ新潟")|(PA_df["stadium"] != "新潟みどり森")|(PA_df["stadium"] != "長岡悠久山")))]
    
else:
    pf_PA_df = PA_df

if week != "All":
    if week == "Weekday":
        pf_PA_df = pf_PA_df[pf_PA_df["game_date"].dt.weekday.isin([0, 1, 2, 3, 4])]
    elif week == "Weekend":
        pf_PA_df = pf_PA_df[(pf_PA_df["game_date"].dt.weekday == 5)|(pf_PA_df["game_date"].dt.weekday == 6)]
    else:
        pf_PA_df = pf_PA_df[(pf_PA_df["game_date"].dt.strftime("%a") == week)]

pf_PA_df['start_time'] = pd.to_datetime(pf_PA_df['start_time'], format='%H:%M:%S').dt.time

if condition == "Day":
    pf_PA_df = pf_PA_df[pf_PA_df["start_time"] < dt.time(17, 0, 0)]
elif condition == "Night":
    pf_PA_df = pf_PA_df[pf_PA_df["start_time"] >= dt.time(17, 0, 0)]

if team != "All Team":
    pf_PA_df = pf_PA_df[pf_PA_df["home_team"] == team]

attendance_df = pf_PA_df.groupby(["home_team", "game_id"], as_index=False).head(1)[["home_team", "away_team", "game_date", "start_time", "stadium", "attendance"]]
attendance_df['stadium'] = attendance_df['stadium'].replace({'PayPayドーム': '(みずほ)PayPay', 'みずほPayPay': '(みずほ)PayPay'})
if group != "Game":
    attendance = attendance_df.groupby(group_list, as_index=False).agg(
        G = ("home_team", "size"),
        mean=("attendance", "mean"),
        Max=("attendance", "max"),
        Total=("attendance", "sum")
    )
    attendance["Mean"] = my_round(attendance["mean"])
    attendance = attendance.rename(columns={"home_team": "Team", "stadium": "Venue"})
    attendance = attendance.drop(columns=["mean"])
    attendance = attendance[df_cols + ["G", "Total", "Mean", "Max"]]
    attendance = attendance.sort_values("Mean", ascending=False).reset_index(drop=True)
else:
    attendance_df = pf_PA_df.groupby(["home_team", "game_id"], as_index=False).head(1)[["home_team", "away_team", "game_date", "start_time", "stadium", "attendance"]]
    attendance = attendance_df.rename(columns={
        "home_team": "Home Team", "away_team": "Away Team", "start_time": "Start Time",
        "game_date": "Date", "stadium": "Venue", "attendance": "Attendance"
        })
    attendance = attendance[["Home Team", "Away Team", "Venue", "Date", "Start Time", "Attendance"]]
    attendance["Date"] = attendance["Date"].dt.strftime("%Y/%m/%d")
    attendance = attendance.sort_values(["Date", "Start Time"]).reset_index(drop=True)

st.dataframe(attendance, use_container_width=True)