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
st.title("Depth Chart")

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

pl_list = ["オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム"]
cl_list = ["阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日"]

wl_list = ["オリックス", "阪神", "ソフトバンク", "広島", "くふうハヤテ", "中日"]
el_list = ["日本ハム", "楽天", "DeNA", "巨人", "ヤクルト", "ロッテ", "オイシックス", "西武"]

pos_list = ["All", "P", "C", "IF", "OF"]

pos_en_jp = {"P": "投手", "C": "捕手", "IF": "内野手", "OF": "外野手"}
pos_jp_en = {"投手": "P", "捕手": "C", "内野手": "IF", "外野手": "OF"}

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

lr_en_dict = {"右": "R", "左": "L", "両": "S"}


info_data = pd.read_csv("~/Python/baseball/NPB/スポナビ/Player_info/NPB_people.csv")
info_data["Career"] = info_data["Career"].astype("Int64")

team_list = ["Team", "阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日",
             "オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム",
             "オイシックス", "くふうハヤテ"]

cols = st.columns(4)
with cols[0]:
    team = st.selectbox(
        "",
        team_list,
        index = 0)
    
if team == "オイシックス" or team == "くふうハヤテ":
    registor_list = ["All"]
else:
    registor_list = ["All", "支配下", "育成"]
with cols[1]:
    registor = st.selectbox(
        "Registor",
        registor_list,
        index = 0)

if team != "Team":
    team_player = info_data[info_data["Team"] == team]
    team_player["Pos"] = team_player["Pos"].replace(pos_jp_en)
    team_player["Throw"] = team_player["Throw"].replace(lr_en_dict)
    team_player["Stand"] = team_player["Stand"].replace(lr_en_dict)
    team_player["B/T"] = team_player["Stand"].str.cat(team_player["Throw"], sep="/")
    team_player = team_player.rename(columns={"Birthday": "DOB"})

    if registor == "育成":
        team_player = team_player[team_player["Number"].str.len() == 4]
    elif registor == "支配下":
        team_player = team_player[team_player["Number"].str.len() < 4]
    st.table(team_player)
