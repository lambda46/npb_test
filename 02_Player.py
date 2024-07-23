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
st.title("Player Stats")

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

def partial_match_merge(batting_df, stealing_df, on_batting, on_stealing):
    merged_df = batting_df.copy()
    merged_df['SB'] = 0
    merged_df['CS'] = 0
    
    for idx, batting_row in batting_df.iterrows():
        batting_team = batting_row['Team']
        batter_name = batting_row[on_batting]
        
        for _, stealing_row in stealing_df.iterrows():
            stealing_team = stealing_row['Team']
            runner_name = stealing_row[on_stealing]
            
            if batting_team == stealing_team and batter_name.startswith(runner_name):
                merged_df.loc[idx, 'SB'] = stealing_row['SB']
                merged_df.loc[idx, 'CS'] = stealing_row['CS']
                break
    
    return merged_df

def partial_match_merge_2(df1, df2, key1, key2, additional_keys):
    # Create a copy of df2 to avoid modifying the original dataframe
    df2_copy = df2.copy()

    # Remove spaces from key1 and key2 columns for matching
    df1['key1_no_space'] = df1[key1].str.replace(' ', '')
    df2_copy['key2_no_space'] = df2_copy[key2].str.replace(' ', '')

    # Merge on the first few characters of key1_no_space and key2_no_space
    df1['key1_prefix'] = df1['key1_no_space'].apply(lambda x: x[:len(df2_copy['key2_no_space'].iloc[0])])
    df2_copy['key2_prefix'] = df2_copy['key2_no_space'].apply(lambda x: x[:len(df1['key1_no_space'].iloc[0])])

    # Merge dataframes on prefix keys and additional_keys
    merge_keys = ['key1_prefix'] + additional_keys
    df2_merge_keys = ['key2_prefix'] + additional_keys
    
    merged_df = pd.merge(df1, df2_copy, left_on=merge_keys, right_on=df2_merge_keys, how='left')

    # Drop temporary columns used for matching
    merged_df.drop(columns=['key1_no_space', 'key2_no_space', 'key1_prefix', 'key2_prefix'], inplace=True)

    return merged_df

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

pn_dict = {'ストレート': 'Four-Seam Fastball', 'フォーク': 'Forkball', 'スライダー': 'Slider',
                'ナックルカーブ': 'Knuckle Curve', 'チェンジアップ': 'Changeup', 'スプリット': 'Split-Finger', 
                'シンカー': 'Sinker', 'カーブ': 'Curveball', 'カットボール': 'Cutter', 'シュート': 'Shoot', 'スローボール': 'Eephus Pitch',
                'ツーシーム': 'Two-Seam Fastball', 'パワーカーブ': 'Power Curve','スローカーブ': 'Slow Curve', 'スクリュー': 'Screwball',
                'パーム': 'Palmball', 'ワンシーム': 'One-Seam Fastball', '縦スライダー': 'Vertical Slider', 'スラーブ': 'Slurve', 'ナックル': 'Knuckleball'}


color_dict = {'ストレート': 'crimson', 'フォーク': 'mediumspringgreen', 'スライダー': 'goldenrod', 
              'ナックルカーブ': 'steelblue', 'チェンジアップ': 'limegreen', 'スプリット': 'lightseagreen', 
              'シンカー': 'orange', 'カーブ': 'deepskyblue', 'カットボール': 'saddlebrown', 
              'シュート': 'khaki', 'ツーシーム': 'orange', 'パワーカーブ': 'dodgerblue', 
              'スローカーブ': 'lightskyblue', 'パーム': 'seagreen', 'ワンシーム': 'rosybrown', 
              '縦スライダー': 'gold', 'スラーブ': 'wheat', 'スローボール': 'gray', 'スクリュー': '#fdcdac', 'ナックル': '#cccccc'}

pn_en_dict = {v: k for k, v in pn_dict.items()}

color_dict_en = {'Four-Seam Fastball': '#c13d4d',
                'Forkball': '#76c9ad',
                'Slider': '#c2bd3f',
                'Knuckle Curve': '#3e44c5',
                'Changeup': '#5abb4e',
                'Split-Finger': '#5daaab',
                'Sinker': '#82d852',
                'Curveball': '#5fcee9',
                'Cutter': '#894432',
                'Shoot': '#f0a239',
                'Two-Seam Fastball': '#f0a239',
                'Power Curve': '#186587',
                'Slow Curve': '#2b66f6',
                'Palmball': '#1e3458',
                'One-Seam Fastball': '#893f59',
                'Vertical Slider': '#d6b552',
                'Slurve': '#98aed1',
                'Eephus Pitch': '#888888',
                'Screwball': '#82d852',
                'Knuckleball': '#3e44c5',
                'All Pitches': 'red',
                'Fastball': 'red',
                'Offspeed': 'green',
                'Breaking': 'blue',
                'Other Pitches': '#888888'
                }

lr_en_dict = {"右": "R", "左": "L", "両": "S"}


info_data = pd.read_csv("~/Python/baseball/NPB/スポナビ/Player_info/NPB_people.csv")
info_data["Career"] = info_data["Career"].astype("Int64")

team_list = ["All", "阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日",
             "オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム",
             "オイシックス", "くふうハヤテ"]

month_dict = {3: "03_March / April", 4: "03_March / April", 5: "05_May", 6: "06_June", 
              7: "07_July", 8: "08_August", 9: "09_September", 10: "10_October", 11: "11_November", 12: "12_December"}

order_dict = {1: "Batting 1st", 2: "Batting 2nd", 3: "Batting 3rd", 4: "Batting 4th", 5: "Batting 5th", 
              6: "Batting 6th", 7: "Batting 7th", 8: "Batting 8th", 9: "Batting 9th"}

runner_dict = {"000": "Bases Empty", "111": "Bases Loaded", "100": "Runner at 1st", "110": "Runners at 1st & 2nd", 
               "101": "Runners at 1st & 3rd", "010": "Runner at 2nd", "011": "Runners at 2nd and 3rd", "001": "Runner at 3rd"}

outs_dict = {0: "No Outs",  1: "One Out", 2: "Two Outs"}

inning_dict = {1: "1st Inning", 2: "2nd Inning", 3: "3rd Inning", 4: "4th Inning", 5: "5th Inning", 
              6: "6th Inning", 7: "7th Inning", 8: "8th Inning", 9: "9th Inning"}

cols = st.columns(4)
with cols[0]:
    team = st.selectbox(
        "Team",
        team_list,
        index = 0)
    
with cols[1]:
    pos = st.selectbox(
        "Position",
        pos_list,
        index = 0)
    
with cols[2]:
    player_type = st.selectbox(
        "Register",
        ["All", "支配下", "育成"],
        index = 0)
    
if team != "All":
    info_data = info_data[info_data["Team"] == team]

if pos != "All":
    info_data = info_data[info_data["Pos"] == pos_en_jp[pos]]

ikusei_condition = ((info_data["Number"].str.len() == 4)|((info_data["Team"] == "オイシックス")|(info_data["Team"] == "くふうハヤテ")))
if player_type == "育成":
    info_data = info_data[ikusei_condition]
elif player_type == "支配下":
    info_data = info_data[~ikusei_condition]

with cols[3]:
    input_name = st.text_input('Player Name', placeholder='Player Name')

if input_name != "":
    input_name = input_name.replace(" ", "")
    suggest_names = info_data[info_data["Player"].str.replace(" ", "").str[:len(input_name)] == input_name].reset_index(drop=True)
    suggest_n = suggest_names[["Team", "Number", "Player", "Pos", "Throw", "Stand", "Born", "Birthday", "Height", "Weight", "Career"]]
    st.table(suggest_n)

    if len(suggest_names) == 1:
        name = suggest_names.loc[0]["Player"]
        player_id = suggest_names.loc[0]["ID"]
        dob = suggest_names.loc[0]["Birthday"]
        position = suggest_names.loc[0]["Pos"]
        height = suggest_names.loc[0]["Height"]
        wight = suggest_names.loc[0]["Weight"]
        team_jp = suggest_names.loc[0]["Team"]
        team_en = team_en_dict[team_jp]
        team_long = team_long_dict[team_jp]
        player_num = suggest_names.loc[0]["Number"]
        throw_jp = suggest_names.loc[0]["Throw"]
        stand_jp = suggest_names.loc[0]["Stand"]
        throw_en = lr_en_dict[throw_jp]
        stand_en = lr_en_dict[stand_jp]
        age = calculate_age(dob)
        
        img_path = f'Player_IMG/{team_jp}/{player_id}.jpg'
        img = Image.open(img_path)
        cols = st.columns([1, 7])
        with cols[0]:
            st.image(img, use_column_width=True)

        with cols[1]:
            st.markdown(f"## {name}")
            st.markdown(f"#### {team_long} {player_num}")
            st.write(f"Age: {age} | Bats/Throws: {stand_en}/{throw_en} | {height}cm/{wight}kg")
            st.write(f"DOB: {dob}")

        league_type = st.radio("League Type", ("1軍", "2軍"), horizontal=True)

        if league_type == "1軍":
            data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
        elif league_type == "2軍":
            data = pd.read_csv("~/Python/baseball/NPB/スポナビ/2軍/farm2024.csv")
        data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
        data["game_year"] = data['game_date'].dt.year
        data["game_month"] = data['game_date'].dt.month
        data["Year/Month"] = data['game_year'].astype(str).str.cat(data['game_month'].astype(str), sep="/")
        data['Inning'] = data['game_date'].dt.strftime("%Y/%m/%d").str.cat(data["inning"].astype(str), sep="-")
        latest_date = data["game_date"].max()
        latest_date_str = latest_date.strftime("%Y/%m/%d")
        year_list = list(data['game_date'].dt.year.unique())
        year_list.sort(reverse=True)
        data["runner_id"] = data["runner_id"].astype(str).str.zfill(3)
        data["post_runner_id"] = data["post_runner_id"].astype(str).str.zfill(3)
        data["B-S"] = data["balls"].astype(str).str.cat(data["strikes"].astype(str), sep="-")

        heart = data[((data["plate_x"] <= heart_right)&(data["plate_x"] >= heart_left)&(data["plate_z"] <=heart_top)&(data["plate_z"] >= heart_bot))]
        heart = heart.assign(Heart = 1)
        data = pd.merge(data, heart, on=list(data.columns), how="left")
        data["Heart"] = data["Heart"].fillna(0)

        o = data[data["Heart"] != 1]
        shadow = o[((o["plate_x"] <= shadow_right)&(o["plate_x"] >= shadow_left)&(o["plate_z"] <= shadow_top)&(o["plate_z"] >= shadow_bot))]
        shadow = shadow.assign(Shadow = 1)
        data = pd.merge(data, shadow, on=list(data.columns), how="left")
        data["Shadow"] = data["Shadow"].fillna(0)

        o = data[(data["Heart"] != 1)&(data["Shadow"] != 1)]
        chase = o[((o["plate_x"] <= chase_right)&(o["plate_x"] >= chase_left)&(o["plate_z"] <= chase_top)&(o["plate_z"] >= chase_bot))]
        chase = chase.assign(Chase = 1)
        data = pd.merge(data, chase, on=list(data.columns), how="left")
        data["Chase"] = data["Chase"].fillna(0)

        waste = data[(data["Heart"] != 1)&(data["Shadow"] != 1)&(data["Chase"] != 1)]
        waste = waste.assign(Waste = 1)
        data = pd.merge(data, waste, on=list(data.columns), how="left")
        data["Waste"] = data["Waste"].fillna(0)

        data['swing'] = np.where(data['description'].isin(['ball', 'called_strike']), 0, 1)

        events_df = data.dropna(subset="events")

        sb_df = data[(data["des"].str.contains("盗塁"))&(~data["des"].str.contains("代走"))&(~data["des"].str.contains("成功率"))].dropna(subset="events")
        
        pa_count_list = []
        count_list = []
        event_df_list = []
        for i in range(len(data)):
            count = data["B-S"][i]
            des = data["description"][i]
            event = data["events"][i]
            # イベントがNaNでない場合は、打席結果の行であるかどうかを確認
            if not pd.isnull(event):
                pa_count_list.append(count)
                count_list.append(pa_count_list)
                event_df_list.append(data.loc[i])
                if (event != "pickoff_1b") and (event != "pickoff_2b") and (event != "pickoff_catcher") and (event != "caught_stealing") and (event != "stolen_base") and (event != "wild_pitch") and (event != "balk") and (event != "passed_ball") and (event != "caught_stealing") and (event != "runner_out"):
                    # 打席結果がある場合、カウントのリストを保存し、新しい打席のカウントを初期化
                    pa_count_list = []
                else:
                    pass
            else:
                # イベントがNaNの場合は、カウントを打席のカウントリストに追加
                pa_count_list.append(count)

        count_str_list = []
        for c in count_list:
            count_str = "|".join(c)
            count_str_list.append(count_str)

        events_df["pa_counts"] = count_str_list

        PA_df = events_df[(events_df["events"] != "pickoff_1b")&
                        (events_df["events"] != "pickoff_2b")&
                        (events_df["events"] != "pickoff_catcher")&
                        (events_df["events"] != "caught_stealing")&
                        (events_df["events"] != "stolen_base")&
                        (events_df["events"] != "wild_pitch")&
                        (events_df["events"] != "balk")&
                        (events_df["events"] != "passed_ball")&
                        (events_df["events"] != "caught_stealing")&
                        (events_df["events"] != "runner_out")]

        starting_lineup = PA_df.groupby(['game_date', 'bat_team']).head(9)
        starting_lineup = starting_lineup[starting_lineup["batter_pos"] != "打"]

        sl = starting_lineup.groupby(["game_date", "bat_team", "batter_name", "batter_pos"], as_index=False).size()
        sl = sl.assign(S = "S")
        sl = sl[["game_date", "bat_team", "batter_name", "batter_pos", "S"]]

        PA_df = pd.merge(PA_df, sl, on=["game_date", "bat_team", "batter_name", "batter_pos"], how="left")


        if league_type == "1軍":
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

            pf_PA_df = pf_PA_df[(pf_PA_df["game_type"] == "パ・リーグ")|(pf_PA_df["game_type"] == "セ・リーグ")]

        elif league_type == "2軍":
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

            pf_PA_df = pf_PA_df[(pf_PA_df["game_type"] == "イ・リーグ")|(pf_PA_df["game_type"] == "ウ・リーグ")]

        ev_away = pf_PA_df.groupby(["away_league", "away_team"], as_index=False).agg(
            away_g=('game_date', 'nunique'),
            away_pa=('away_team', 'size'),
            away_score = ("runs_scored", "sum"),
            away_con = ("description", lambda x: (x == "hit_into_play").sum()),
            away_hr = ("events", lambda x: (x == "home_run").sum()),
            away_1b = ("events", lambda x: (x == "single").sum()),
            away_2b = ("events", lambda x: (x == "double").sum()),
            away_3b = ("events", lambda x: (x == "triple").sum()),
            away_bb = ("events", lambda x: ((x == "walk")|(x == "intentional_walk")).sum()),
            away_k = ('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),
            away_hbp = ("events", lambda x: (x == "hit_by_pitch").sum()),
            away_sf = ('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
            away_sh = ('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
            away_obstruction=('events', lambda x: (x == "obstruction").sum()),
            away_interference=('events', lambda x: (x == "interference").sum()),
        )
        ev_away["away_h"] = ev_away["away_1b"] + ev_away["away_2b"] + ev_away["away_3b"] + ev_away["away_hr"]
        ev_away["away_score/g"] = ev_away["away_score"]/ev_away["away_g"]
        ev_away["away_hr/g"] = ev_away["away_hr"]/ev_away["away_g"]
        ev_away["away_1b/g"] = ev_away["away_1b"]/ev_away["away_g"]
        ev_away["away_2b/g"] = ev_away["away_2b"]/ev_away["away_g"]
        ev_away["away_3b/g"] = ev_away["away_3b"]/ev_away["away_g"]
        ev_away["away_h/g"] = ev_away["away_h"]/ev_away["away_g"]
        ev_away["away_bb/g"] = ev_away["away_bb"]/ev_away["away_g"]
        ev_away["away_k/g"] = ev_away["away_k"]/ev_away["away_g"]
        ev_away = ev_away.rename(columns={"away_league": "League", "away_team": "Team"})

        ev_home = pf_PA_df.groupby(["home_league", "home_team"], as_index=False).agg(
            home_g=('game_date', 'nunique'),
            home_pa=('home_team', 'size'),
            home_score = ("runs_scored", "sum"),
            home_con = ("description", lambda x: (x == "hit_into_play").sum()),
            home_hr = ("events", lambda x: (x == "home_run").sum()),
            home_1b = ("events", lambda x: (x == "single").sum()),
            home_2b = ("events", lambda x: (x == "double").sum()),
            home_3b = ("events", lambda x: (x == "triple").sum()),
            home_bb = ("events", lambda x: ((x == "walk")|(x == "intentional_walk")).sum()),
            home_k = ('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),
            home_hbp = ("events", lambda x: (x == "hit_by_pitch").sum()),
            home_sf = ('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
            home_sh = ('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
            home_obstruction=('events', lambda x: (x == "obstruction").sum()),
            home_interference=('events', lambda x: (x == "interference").sum()),
        )
        ev_home["home_h"] = ev_home["home_1b"] + ev_home["home_2b"] + ev_home["home_3b"] + ev_home["home_hr"]
        ev_home["home_score/g"] = ev_home["home_score"]/ev_home["home_g"]
        ev_home["home_hr/g"] = ev_home["home_hr"]/ev_home["home_g"]
        ev_home["home_1b/g"] = ev_home["home_1b"]/ev_home["home_g"]
        ev_home["home_2b/g"] = ev_home["home_2b"]/ev_home["home_g"]
        ev_home["home_3b/g"] = ev_home["home_3b"]/ev_home["home_g"]
        ev_home["home_h/g"] = ev_home["home_h"]/ev_home["home_g"]
        ev_home["home_bb/g"] = ev_home["home_bb"]/ev_home["home_g"]
        ev_home["home_k/g"] = ev_home["home_k"]/ev_home["home_g"]
        ev_home = ev_home.rename(columns={"home_league": "League", "home_team": "Team"})

        pf = pd.merge(ev_away, ev_home, on=["League", "Team"])
        league_counts = pf['League'].value_counts().reset_index()
        league_counts.columns = ['League', 'League_Count']
        pf = pd.merge(pf, league_counts, on="League", how="left")

        #ev_compare["pf"] = ev_compare["home_hr_event"]/(ev_compare["home_hr_event"] * ev_compare["away/home"] + ev_compare["away_hr_event"] * (1 - ev_compare["away/home"]))
        pf["hr_pf"] = pf["home_hr/g"]/((pf["away_hr/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_hr/g"] * 1/pf["League_Count"]))
        pf["1b_pf"] = pf["home_1b/g"]/((pf["away_1b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_1b/g"] * 1/pf["League_Count"]))
        pf["2b_pf"] = pf["home_2b/g"]/((pf["away_2b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_2b/g"] * 1/pf["League_Count"]))
        pf["3b_pf"] = pf["home_3b/g"]/((pf["away_3b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_3b/g"] * 1/pf["League_Count"]))
        pf["h_pf"] = pf["home_h/g"]/((pf["away_h/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_h/g"] * 1/pf["League_Count"]))
        pf["bb_pf"] = pf["home_bb/g"]/((pf["away_bb/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_bb/g"] * 1/pf["League_Count"]))
        pf["k_pf"] = pf["home_k/g"]/((pf["away_k/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_k/g"] * 1/pf["League_Count"]))
        pf["runs_pf"] = pf["home_score/g"]/((pf["away_score/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_score/g"] * 1/pf["League_Count"]))
        pf["HR_PF"] = my_round(pf["hr_pf"],2)
        pf["1B_PF"] = my_round(pf["1b_pf"],2)
        pf["2B_PF"] = my_round(pf["2b_pf"],2)
        pf["3B_PF"] = my_round(pf["3b_pf"],2)
        pf["H_PF"] = my_round(pf["h_pf"],2)
        pf["K_PF"] = my_round(pf["bb_pf"],2)
        pf["BB_PF"] = my_round(pf["k_pf"],2)
        pf["RUNS_PF"] = my_round(pf["runs_pf"],2)
        pf["bpf/100"] = pf["runs_pf"] * pf["home_g"]/(pf["home_g"] + pf["away_g"]) + (pf["League_Count"]-pf["runs_pf"])/(pf["League_Count"] - 1) * pf["away_g"]/(pf["home_g"] + pf["away_g"])
        pf = pf[["League", "Team", "RUNS_PF", "HR_PF", "H_PF", "1B_PF", "2B_PF", "3B_PF", "K_PF", "BB_PF", "bpf/100"]]

        df2024 = PA_df

        df2024["RUNS"] = df2024["bat_score"]
        df2024["HALF.INNING"] = df2024["game_id"].astype(str).str.cat([df2024["inning"].astype(str), df2024["top_bot"]], sep="-")
        half_inning = df2024.groupby(["HALF.INNING"], as_index=False).agg(
            Outs_Inning = ("event_out", "sum"),
            Runs_Inning = ("runs_scored", "sum"),
            Runs_Start = ("RUNS", "first")
        )
        half_inning["MAX_RUNS"] = half_inning["Runs_Inning"] + half_inning["Runs_Start"]
        df2024 = pd.merge(df2024, half_inning, on="HALF.INNING", how="left")
        df2024["RUNS.ROI"] = df2024["MAX_RUNS"] - df2024["RUNS"]
        df2024["STATE"] = df2024["runner_id"].str.cat(df2024["out_count"].astype(str), sep="-")
        sb_df["STATE"] = sb_df["runner_id"].str.cat(sb_df["out_count"].astype(str), sep="-")
        df2024["NEW.STATE"] = df2024["post_runner_id"].str.cat(df2024["post_out_count"].astype(str), sep="-")
        sb_df["NEW.STATE"] = sb_df["post_runner_id"].str.cat(sb_df["post_out_count"].astype(str), sep="-")
        df2024 = df2024[(df2024["STATE"] != df2024["NEW.STATE"])|(df2024["runs_scored"] > 0)]
        df2024C = df2024[df2024["Outs_Inning"] == 3]
        RUNS = df2024C.groupby(["STATE"], as_index=False).agg(
            Mean = ("RUNS.ROI", "mean")
        )
        RUNS["Outs"] = RUNS["STATE"].str[-1]
        RUNS["RUNNER"] = RUNS["STATE"].str[:3]
        RUNS = RUNS.sort_values("Outs")
        df2024 = pd.merge(df2024, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})
        sb_df = pd.merge(sb_df, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})
        df2024 = pd.merge(df2024, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
        sb_df = pd.merge(sb_df, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
        df2024["Runs.New.State"] = df2024["Runs.New.State"].fillna(0)
        sb_df["Runs.New.State"] = sb_df["Runs.New.State"].fillna(0)
        df2024["run_value"] = df2024["Runs.New.State"] - df2024["Runs.State"] + df2024["runs_scored"]
        sb_df["run_value"] = sb_df["Runs.New.State"] - sb_df["Runs.State"] + sb_df["runs_scored"]
        sb_df['sb'] = sb_df['des'].str.count('盗塁成功')
        sb_df['cs'] = sb_df['des'].str.count('盗塁失敗')
        sb_n = sb_df["sb"].sum()
        cs_n = sb_df["cs"].sum()
        run_values = df2024.groupby(["events"], as_index=False).agg(
            Mean = ("run_value", "mean")
        )
        run_values = run_values.rename(columns={"Mean": "Run_Value"}).sort_values("Run_Value", ascending=False)

        out_df = df2024[(df2024["event_out"] > 0)]
        out_value = out_df["run_value"].sum()/out_df["event_out"].sum()

        bb_run = df2024[df2024["events"] == "walk"]["run_value"].mean()
        walk_run = df2024[(df2024["events"] == "walk")|(df2024["events"] == "intentional_walk")]["run_value"].mean()
        k_run = df2024[(df2024["events"] == "strike_out")|(df2024["events"] == "uncaught_third_strike")]["run_value"].mean()
        hbp_run = df2024[df2024["events"] == "hit_by_pitch"]["run_value"].mean()
        single_run = df2024[df2024["events"] == "single"]["run_value"].mean()
        double_run = df2024[df2024["events"] == "double"]["run_value"].mean()
        triple_run = df2024[df2024["events"] == "triple"]["run_value"].mean()
        hr_run = df2024[df2024["events"] == "home_run"]["run_value"].mean()
        sb_run = sb_df[sb_df["sb"] > 0]["run_value"].sum()/sb_n
        cs_run = sb_df[sb_df["cs"] > 0]["run_value"].sum()/cs_n
        if league_type == "1軍":
            gb_run = df2024[df2024["GB"] == 1]["run_value"].mean()
            ld_run = df2024[df2024["LD"] == 1]["run_value"].mean()
            iffb_run = df2024[df2024["IFFB"] == 1]["run_value"].mean()
            offb_run = df2024[df2024["OFFB"] == 1]["run_value"].mean()
            fb_run = df2024[df2024["FB"] == 1]["run_value"].mean()

        bb_value = bb_run - out_value
        hbp_value = hbp_run - out_value
        single_value = single_run - out_value
        double_value = double_run - out_value
        triple_value = triple_run - out_value
        hr_value = hr_run - out_value
        if league_type == "1軍":
            gb_value = gb_run - out_value
            fb_value = fb_run - out_value
            ld_value = ld_run - out_value
            iffb_value = iffb_run - out_value
            offb_value = offb_run - out_value

        events_sum = df2024["events"].value_counts().to_dict()

        sh_sum = events_sum.get("sac_bunt", 0) + events_sum.get("bunt_error", 0) + events_sum.get("bunt_fielders_choice", 0)
        sf_sum = events_sum.get("sac_fly", 0) + events_sum.get("sac_fly_error", 0)
        bb_sum = events_sum.get("walk") + events_sum.get("intentional_walk", 0)
        ibb_sum = events_sum.get("intentional_walk", 0)
        hbp_sum = events_sum.get("hit_by_pitch", 0)
        obstruction_sum = events_sum.get("obstruction", 0)
        interference_sum = events_sum.get("interference", 0)
        single_sum = events_sum.get("single", 0)
        double_sum = events_sum.get("double", 0)
        triple_sum = events_sum.get("triple", 0)
        hr_sum = events_sum.get("home_run", 0)
        h_sum = single_sum + double_sum + triple_sum + hr_sum
        ab_sum = len(df2024) - (bb_sum + hbp_sum + sh_sum + sf_sum + interference_sum + obstruction_sum)

        mean_woba = (bb_value * (bb_sum - ibb_sum) + hbp_value * hbp_sum + single_value * single_sum + double_value * double_sum + triple_value * triple_sum + hr_value * hr_sum)/(ab_sum + bb_sum - ibb_sum + hbp_sum + sf_sum)
        mean_obp = (h_sum + bb_sum + hbp_sum)/(ab_sum + bb_sum + hbp_sum + sf_sum)
        wOBA_scale = mean_obp/mean_woba

        pa_count_list = []
        count_list = []
        event_df_list = []
        for i in range(len(data)):
            count = data["B-S"][i]
            des = data["description"][i]
            event = data["events"][i]
            # イベントがNaNでない場合は、打席結果の行であるかどうかを確認
            if not pd.isnull(event):
                # イベントが打席結果であるかどうかを確認
                if (event != "pickoff_1b") and (event != "pickoff_2b") and (event != "pickoff_catcher") and (event != "caught_stealing") and (event != "stolen_base") and (event != "wild_pitch") and (event != "balk") and (event != "passed_ball") and (event != "caught_stealing") and (event != "runner_out"):
                    # 打席結果がある場合、カウントのリストを保存し、新しい打席のカウントを初期化
                    pa_count_list.append(count)
                    count_list.append(pa_count_list)
                    event_df_list.append(data.loc[i])
                    pa_count_list = []
                else:
                    pa_count_list.append(count)
            else:
                # イベントがNaNの場合は、カウントを打席のカウントリストに追加
                pa_count_list.append(count)

        count_str_list = []
        for c in count_list:
            count_str = "|".join(c)
            count_str_list.append(count_str)

        df2024["pa_counts"] = count_str_list

        from collections import defaultdict

        counts_list = ["0-0", "0-1", "0-2", "1-0", "1-1", "1-2", "2-0", "2-1", "2-2", "3-0", "3-1", "3-2"]
        c_df_list = []
        def events_count(event):
            res = len(count_pa_df[count_pa_df["events"] == event])
            return res

        for count in counts_list:
            count_pa_df = df2024[df2024["pa_counts"].str.contains(count)]
            pa = len(count_pa_df)
            single = events_count("single")
            double = events_count("double")
            triple = events_count("triple")
            home_run = events_count("home_run")
            hit = single + double + triple + home_run
            bb = events_count("walk") + events_count("intentional_walk")
            k = events_count("strike_out") + events_count("uncaught_third_strike")
            ibb = events_count("intentional_walk")
            hbp = events_count("hit_by_pitch")
            sf = events_count("sac_fly") + events_count("sac_fly_error")
            sh = events_count("sac_bunt") + events_count("bunt_error") + events_count("bunt_fielders_choice")
            obstruction = events_count("obstruction")
            ab = pa - bb - ibb - hbp - sf - sh - obstruction
            runs = count_pa_df["runs_scored"].sum()
            c_woba = wOBA_scale * (bb_value * (bb - ibb) + hbp_value * hbp + single_value * single + double_value * double + triple_value * triple + hr_value * home_run)/(ab + bb - ibb + hbp + sf)
            c_wOBA = my_round(c_woba, 3)
            avg = hit/ab
            AVG = my_round(avg, 3)
            obp = (hit+bb+hbp)/(ab+bb+hbp+sf)
            OBP = my_round(obp, 3)
            slg = (single+2*double+3*triple+4*home_run)/ab
            SLG = my_round(slg, 3)
            ops = obp+slg
            OPS = my_round(ops, 3)
            bb_pct = 100*bb/pa
            k_pct = 100*k/pa
            hr_pct = 100*home_run/pa
            BB_pct = my_round(bb_pct, 1)
            K_pct = my_round(k_pct, 1)
            HR_pct = my_round(hr_pct, 1)
            iso = slg - avg
            ISO = my_round(iso, 3)
            count_stats_list = [count, pa, ab, hit, single, double, triple, home_run, k, bb, ibb, hbp, runs, bb_pct, BB_pct, k_pct, K_pct, hr_pct, HR_pct, avg, AVG, obp, OBP, slg, SLG, ops, OPS, iso, ISO, c_woba, c_wOBA]
            c_df_list.append(count_stats_list)

        count_bat_stats = pd.DataFrame(c_df_list, columns=["B-S", "PA", "AB", "H", "1B", "2B", "3B", "HR", "K", "BB", "IBB", "HBP", "R", "bb%", "BB%", "k%", "K%", "hr%", "HR%", "avg", "AVG", "obp", "OBP", "slg", "SLG", "ops", "OPS", "iso", "ISO", "woba", "wOBA"])
        zero_woba = count_bat_stats.loc[count_bat_stats['B-S'] == '0-0', 'woba'].iloc[0]
        count_bat_stats["run_value"] = (count_bat_stats["woba"] - zero_woba)/wOBA_scale
        count_bat_stats["Run Value"] = my_round(count_bat_stats["run_value"], 3)
        count_bat_stats["balls"] = count_bat_stats["B-S"].str[0].astype(int)
        count_bat_stats["post_balls"] = count_bat_stats["B-S"].str[0].astype(int)+1
        count_bat_stats["strikes"] = count_bat_stats["B-S"].str[-1].astype(int)
        count_bat_stats["post_strikes"] = count_bat_stats["B-S"].str[-1].astype(int)+1
        count_bat_stats["s_B-S"] = count_bat_stats["balls"].astype(str).str.cat(count_bat_stats["post_strikes"].astype(str), sep="-")
        count_bat_stats["b_B-S"] = count_bat_stats["post_balls"].astype(str).str.cat(count_bat_stats["strikes"].astype(str), sep="-")
        strike_run_value = count_bat_stats[["B-S", "run_value"]].rename(columns={"B-S": "s_B-S", "run_value": "s_run_value"})
        ball_run_value = count_bat_stats[["B-S", "run_value"]].rename(columns={"B-S": "b_B-S", "run_value": "b_run_value"})
        count_bat_stats = pd.merge(count_bat_stats, strike_run_value, on="s_B-S", how="left")
        count_bat_stats = pd.merge(count_bat_stats, ball_run_value, on="b_B-S", how="left")
        count_bat_stats["s_run_value"] = count_bat_stats["s_run_value"].fillna(k_run)
        count_bat_stats["b_run_value"] = count_bat_stats["b_run_value"].fillna(walk_run)
        count_bat_stats["v_strike"] = count_bat_stats["s_run_value"] - count_bat_stats["run_value"]
        count_bat_stats["v_ball"] = count_bat_stats["b_run_value"] - count_bat_stats["run_value"]
        count_bat_stats["v_home_run"] = (hr_value*wOBA_scale- count_bat_stats["woba"])/wOBA_scale
        if league_type == "1軍":
            count_bat_stats["v_gb"] = (gb_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_fb"] = (fb_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_iffb"] = (iffb_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_offb"] = (offb_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_ld"] = (ld_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_hbp"] = (hbp_value - count_bat_stats["woba"])/wOBA_scale
            count_bat_stats["v_out"] = (out_value - count_bat_stats["woba"])/wOBA_scale

        plate_df = data.dropna(subset="pitch_number")

        pv_df = data[data["batter_pos"] != "投"].dropna(subset="pitch_number")
        pv_df = pv_df[(pv_df["events"] != "sac_bunt")&(pv_df["events"] != "bunt_error")&(pv_df["events"] != "bunt_fielders_choice")].reset_index()

        merged_data = pd.merge(pv_df, count_bat_stats.drop(columns=["balls", "strikes"]), on="B-S", how="left")
        # イベントごとのランバリューを取得
        event_run_values = df2024.groupby('events')['run_value'].mean().to_dict()

        # カウントごとのvalueとwOBAを取得
        count_value = merged_data.set_index('B-S')['wOBA'].to_dict()
        merged_data['PV'] = 0
        merged_data['RV'] = 0
        strike_2_foul = (merged_data['strikes'] == 2) & (merged_data['description'] == 'foul')
        merged_data.loc[strike_2_foul, ['PV', 'RV']] = 0
        swing_or_called_strike = merged_data['description'].isin(['swing_strike', 'called_strike', 'foul', 'missed_bunt'])
        merged_data.loc[swing_or_called_strike, 'PV'] = merged_data['v_strike']
        merged_data.loc[swing_or_called_strike, 'RV'] = merged_data['v_strike']
        ball = merged_data['description'] == 'ball'
        merged_data.loc[ball, 'PV'] = merged_data['v_ball']
        merged_data.loc[ball, 'RV'] = merged_data['v_ball']
        other_events = ~strike_2_foul & ~swing_or_called_strike & ~ball
        merged_data.loc[other_events, 'run_value'] = merged_data['events'].map(event_run_values)
        merged_data.loc[other_events, 'value'] = (merged_data['run_value'] - out_value) * wOBA_scale
        merged_data.loc[other_events, 'RV'] = (merged_data['value'] - merged_data['wOBA']) / wOBA_scale
        merged_data["batter_pitch_value"] = merged_data["RV"]
        merged_data["pitcher_pitch_value"] = merged_data["RV"] * -1

        game_runs = data.groupby(["game_year", "bat_league", "game_date", "home_team", "away_team"], as_index=False).tail(1)[["game_year", "bat_league", "home_score", "away_score"]].reset_index(drop=True)
        game_runs["game_score"] = game_runs["home_score"] + game_runs["away_score"]
        rpw_df = game_runs.groupby(["game_year", "bat_league"], as_index=False).agg(
            G = ("bat_league", "size"),
            R = ("game_score", "sum")
        )
        rpw_df["R/G"] = rpw_df["R"]/rpw_df["G"]
        rpw_df["RPW"] = 2*(rpw_df["R/G"] **0.715)
        rpw_df = rpw_df[["game_year", "bat_league", "RPW"]]
        rpw_df = rpw_df.set_axis(["Season", "League", "RPW"], axis=1)

        league_bat_data = PA_df.groupby(["game_year", "bat_league"], as_index=False).agg(
            g_1=('game_id', 'nunique'),  # ゲーム数
            R=('runs_scored', 'sum'), 
            PA=('events', 'size'),  # 許した得点数
            O=('event_out', 'sum'), 
            Single=('events', lambda x: (x == "single").sum()),
            Double=('events', lambda x: (x == "double").sum()),
            Triple=('events', lambda x: (x == "triple").sum()),
            SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
            SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
            GDP=('events', lambda x: (x == "double_play").sum()),
            K=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
            BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
            IBB=('events', lambda x: (x == "intentional_walk").sum()),
            HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
            HR=('events', lambda x: (x == "home_run").sum()),
            obstruction=('events', lambda x: (x == "obstruction").sum()),
            interference=('events', lambda x: (x == "interference").sum()),
        )
        league_bat_data = league_bat_data.rename(columns={"game_year": "Season", "bat_league": "League", "Single": "1B", "Double": "2B", "Triple": "3B"})
        league_bat_data["AB"] = league_bat_data["PA"] - (league_bat_data["BB"] + league_bat_data["HBP"] + league_bat_data["SH"] + league_bat_data["SF"] + league_bat_data["obstruction"] + league_bat_data["interference"])
        league_bat_data["H"] = league_bat_data["1B"] + league_bat_data["2B"] + league_bat_data["3B"] + league_bat_data["HR"]

        league_bat_data["woba"] = wOBA_scale * (bb_value * (league_bat_data["BB"] - league_bat_data["IBB"]) + hbp_value * league_bat_data["HBP"] + single_value * league_bat_data["1B"] + double_value * league_bat_data["2B"] + triple_value * league_bat_data["3B"] + hr_value * league_bat_data["HR"])/(league_bat_data["AB"] + league_bat_data["BB"] - league_bat_data["IBB"] + league_bat_data["HBP"] + league_bat_data["SF"])
        league_bat_data["wOBA"] = my_round(league_bat_data["woba"], 3)

        runner = ["100", "010", "001", "110", "101", "011", "111"]
        sb_data_list = []
        for r in runner:
            sb_data = sb_df[(sb_df["runner_id"] == r)]
            if r[0] == "1":
                sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                if len(sb_1b) > 0:
                    sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                    sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                    sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                        SB=("StolenBase", "sum"),
                        CS=("CaughtStealing", "sum")
                    )
                    sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                    sb_data_list.append(sb_data_1)
                
            if r[1] == "1":
                sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                if len(sb_2b) > 0:
                    sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                    sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                    sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                        SB=("StolenBase", "sum"),
                        CS=("CaughtStealing", "sum")
                    )
                    sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                    sb_data_list.append(sb_data_2)

            if r[2] == "1":
                sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                if len(sb_3b) > 0:
                    sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                    sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                    sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                        SB=("StolenBase", "sum"),
                        CS=("CaughtStealing", "sum")
                    )
                    sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                    sb_data_list.append(sb_data_3)

        sb_data = pd.concat(sb_data_list)

        runner_df = sb_data.groupby(["bat_league"], as_index=False).agg(
            SB=("SB", "sum"),
            CS=("CS", "sum"),
        ).sort_values("SB", ascending=False)
        runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League"})
        league_bat_data = pd.merge(league_bat_data, runner_df,on=["League"], how="left")

        league_wrc_mean = league_bat_data[["Season", "League", "woba", "R", "PA", "SB", "CS", "1B", "BB", "HBP", "IBB"]].rename(columns={
                "woba": "woba_league", "R": "R_league", "PA": "PA_league", "SB": "SB_league", "CS": "CS_league",
                "1B": "1B_league", "BB": "BB_league", "HBP": "HBP_league", "IBB": "IBB_league"
                })        

        starter_condition = (data['inning'] == 1) & (data['order'] == 1) & (data['pitch_number'] == 1) & (data['ab_pitch_number'] == 1) & (data['out_count'] == 0) & (data['bat_score'] == 0) & (data['runner_id'] == "000")

        pitcher_unique = data.groupby(["game_year", "game_id", "fld_team"], as_index=False).agg(
            CG=("pitcher_name", "nunique")
        )
        cg_df = pitcher_unique[pitcher_unique["CG"] == 1]

        sp_df = data[starter_condition].assign(StP = 1)
        events_df = pd.merge(events_df, sp_df[["game_year", "fld_team", "pitcher_name", "game_id", "StP"]], on=["game_year", "fld_team", "pitcher_name", "game_id"], how="left")
        events_df = pd.merge(events_df, cg_df, on=["game_year", "fld_team", "game_id"], how="left")
        events_df["StP"] = events_df["StP"].fillna(0)
        events_df["CG"] = events_df["CG"].fillna(0).astype(int)
        is_sho = events_df.groupby(["game_year", "game_id", "fld_team"], as_index=False).tail(1)
        sho_df = is_sho[(is_sho["CG"] == 1)&(is_sho["post_bat_score"] == 0)]
        sho_df = sho_df.assign(ShO = 1)
        events_df = pd.merge(events_df, sho_df[["game_year", "game_id", "fld_team", "pitcher_name", "ShO"]], on=["game_year", "game_id", "fld_team", "pitcher_name"], how="left")
        events_df["ShO"] = events_df["ShO"].fillna(0).astype(int)
        events_df['WP'] = events_df['des'].apply(lambda x: 1 if '暴投' in x else 0)

        league_fip_data = events_df.groupby(["game_year", 'fld_league'], as_index=False).agg(
            R=('runs_scored', 'sum'),  # 許した得点数
            O=('event_out', 'sum'), 
            K=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
            BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
            IBB=('events', lambda x: (x == "intentional_walk").sum()),
            HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
            HR=('events', lambda x: (x == "home_run").sum())
        )
        league_fip_data["inning"] = league_fip_data["O"]/3
        league_fip_data['lgRA'] = league_fip_data['R'] * 9 / league_fip_data['inning']
        league_fip_data["cFIP"] = league_fip_data["lgRA"] - (13*league_fip_data["HR"] + 3*(league_fip_data["BB"] - league_fip_data["IBB"] + league_fip_data["HBP"]) - 2*league_fip_data["K"])/league_fip_data["inning"]
        league_fip_data = league_fip_data[["game_year", "fld_league", "cFIP", "lgRA"]]
        

        plate_df = data.dropna(subset="pitch_number")

        data_type_list = ["Stats", "Charts", "Splits", "Game Logs"]

        cols = st.columns(2)
        with cols[0]:
            data_type = option_menu(None,
            data_type_list,
            menu_icon="cast", default_index=0, orientation="horizontal",
            styles={
                "container": {"padding": "0!important"},
                "icon": {"font-size": "15px"},
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px"},
            }
            )

        with cols[1]:
            if data_type == "Charts":
                stats_type_list = ["Batting", "Pitching", "Zone"]

                if position == "投手":
                    stats_index = 1
                else:
                    stats_index = 0
                stats_type = option_menu(None,
                    stats_type_list,
                    menu_icon="cast", default_index=stats_index, orientation="horizontal",
                    styles={
                        "container": {"padding": "0!important"},
                        "icon": {"font-size": "15px"},
                        "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px"},
                    }
                )

            else:
                stats_type_list = ["Batting", "Pitching"]

                if position == "投手":
                    stats_index = 1
                else:
                    stats_index = 0
                stats_type = option_menu(None,
                    stats_type_list,
                    menu_icon="cast", default_index=stats_index, orientation="horizontal",
                    styles={
                        "container": {"padding": "0!important"},
                        "icon": {"font-size": "15px"},
                        "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px"},
                    }
                )

        if stats_type == "Batting":
            split_list = ["No Splits", "Yesterday", "Last 7days", "Last 14days", "Last 30days", 
                "March/April", "May", "June", "July", "August", "Sept~", "vsRHP", "vsLHP", "Grounders", "Flies", "Liners",
                "Pull", "Center", "Opposite",
                "Home", "Away", "Bases Empty", "Runners on Base", "Runners on Scoring",
                "Batting 1st", "Batting 2nd", "Batting 3rd", "Batting 4th", "Batting 5th", 
                "Batting 6th", "Batting 7th", "Batting 8th", "Batting 9th",
                "vs 阪神", "vs 広島", "vs DeNA", "vs 巨人", "vs ヤクルト", "vs 中日",
                "vs オリックス", "vs ロッテ", "vs ソフトバンク", "vs 楽天", "vs 西武", "vs 日本ハム",
                "0-0経由", "0-1経由", "0-2経由", "1-0経由", "1-1経由", "1-2経由", "2-0経由", "2-1経由", "2-2経由", "3-0経由", "3-1経由", "3-2経由", 
                "ストレート", "ツーシーム", "カットボール", "スライダー", "カーブ", "フォーク", "チェンジアップ", "シンカー", "特殊級", "ストレート150以上", "ストレート140~149", "ストレート140未満"]
        elif stats_type == "Pitching":
            split_list = ["No Splits", "Yesterday", "Last 7days", "Last 14days", "Last 30days", 
                "March/April", "May", "June", "July", "August", "Sept~", "vsRHH", "vsLHH", "Grounders", "Flies", "Liners",
                "Home", "Away", "Bases Empty", "Runners on Base", "Runners on Scoring",
                "リード時", "同点時", "ビハインド時", "1回", "2回", "3回", "4回", "5回", "6回", "7回", "8回", "9回", "延長",
                "vs 阪神", "vs 広島", "vs DeNA", "vs 巨人", "vs ヤクルト", "vs 中日",
                "vs オリックス", "vs ロッテ", "vs ソフトバンク", "vs 楽天", "vs 西武", "vs 日本ハム",
                "0-0経由", "0-1経由", "0-2経由", "1-0経由", "1-1経由", "1-2経由", "2-0経由", "2-1経由", "2-2経由", "3-0経由", "3-1経由", "3-2経由"]
        elif stats_type == "Zone":
            split_list = ["No Splits"]
        

        if data_type == "Stats":
            cols = st.columns(4)
            with cols[0]:
                split = st.selectbox(
                    "Split",
                    split_list,
                    index=0
                )
            if stats_type == "Batting":
                
                PA_df = PA_df[PA_df["batter_id"] == player_id]
                plate_df = plate_df[plate_df["batter_id"] == player_id]
                merged_data = merged_data[merged_data["batter_id"] == player_id]

                if stand_en == "S":
                    with cols[1]:
                        st_split = st.selectbox(
                            "Bat Side",
                            ["Both", "Right", "Left"],
                            index=0
                        )

                if split == "No Split":
                    pass
                elif split == "Yesterday":
                    PA_df = PA_df[PA_df["game_date"] == latest_date]
                    plate_df = plate_df[plate_df["game_date"] == latest_date]
                    merged_data = merged_data[merged_data["game_date"] == latest_date]
                    sb_df = sb_df[sb_df["game_date"] == latest_date]
                elif split == "Last 7days":
                    PA_df = PA_df[PA_df["game_date"] >= (latest_date - timedelta(days=6))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=6))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=6))]
                    sb_df = sb_df[sb_df["game_date"] >= (latest_date - timedelta(days=6))]
                elif split == "Last 14days":
                    PA_df = PA_df[PA_df["game_date"] >= (latest_date - timedelta(days=13))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=13))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=13))]
                    sb_df = sb_df[sb_df["game_date"] >= (latest_date - timedelta(days=13))]
                elif split == "Last 30days":
                    PA_df = PA_df[PA_df["game_date"] >= (latest_date - timedelta(days=29))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=29))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=29))]
                    sb_df = sb_df[sb_df["game_date"] >= (latest_date - timedelta(days=29))]
                elif split == "March/April":
                    PA_df = PA_df[(PA_df["game_date"].dt.month == 3)|(PA_df["game_date"].dt.month == 4)]
                    plate_df = plate_df[(plate_df["game_date"].dt.month == 3)|(plate_df["game_date"].dt.month == 4)]
                    merged_data = merged_data[(merged_data["game_date"].dt.month == 3)|(merged_data["game_date"].dt.month == 4)]
                    sb_df = sb_df[(sb_df["game_date"].dt.month == 3)|(sb_df["game_date"].dt.month == 4)]
                elif split == "May":
                    PA_df = PA_df[PA_df["game_date"].dt.month == 5]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 5]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 5]
                    sb_df = sb_df[sb_df["game_date"].dt.month == 5]
                elif split == "June":
                    PA_df = PA_df[PA_df["game_date"].dt.month == 6]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 6]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 6]
                    sb_df = sb_df[sb_df["game_date"].dt.month == 6]
                elif split == "July":
                    PA_df = PA_df[PA_df["game_date"].dt.month == 7]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 7]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 7]
                    sb_df = sb_df[sb_df["game_date"].dt.month == 7]
                elif split == "August":
                    PA_df = PA_df[PA_df["game_date"].dt.month == 8]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 8]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 8]
                    sb_df = sb_df[sb_df["game_date"].dt.month == 8]
                elif split == "Sept~":
                    PA_df = PA_df[PA_df["game_date"].dt.month >= 9]
                    plate_df = plate_df[plate_df["game_date"].dt.month >= 9]
                    merged_data = merged_data[merged_data["game_date"].dt.month >= 9]
                    sb_df = sb_df[sb_df["game_date"].dt.month >= 9]
                elif split == "vsRHP":
                    PA_df = PA_df[PA_df["p_throw"] == "右"]
                    plate_df = plate_df[plate_df["p_throw"] == "右"]
                    merged_data = merged_data[merged_data["p_throw"] == "右"]
                    sb_df = sb_df[sb_df["p_throw"] == "右"]
                elif split == "vsLHP":
                    PA_df = PA_df[PA_df["p_throw"] == "左"]
                    plate_df = plate_df[plate_df["p_throw"] == "左"]
                    merged_data = merged_data[merged_data["p_throw"] == "左"]
                    sb_df = sb_df[sb_df["p_throw"] == "左"]
                elif split == "Home":
                    PA_df = PA_df[PA_df["bat_team"] == PA_df["home_team"]]
                    plate_df = plate_df[plate_df["bat_team"] == plate_df["home_team"]]
                    merged_data = merged_data[merged_data["bat_team"] == merged_data["home_team"]]
                    sb_df = sb_df[sb_df["bat_team"] == sb_df["home_team"]]
                elif split == "Away":
                    PA_df = PA_df[PA_df["bat_team"] == PA_df["away_team"]]
                    plate_df = plate_df[plate_df["bat_team"] == plate_df["away_team"]]
                    merged_data = merged_data[merged_data["bat_team"] == merged_data["away_team"]]
                    sb_df = sb_df[sb_df["bat_team"] == sb_df["away_team"]]
                elif split == "Bases Empty":
                    PA_df = PA_df[PA_df["runner_id"] == "000"]
                    plate_df = plate_df[plate_df["runner_id"] == "000"]
                    merged_data = merged_data[merged_data["runner_id"] == "000"]
                    sb_df = sb_df[sb_df["runner_id"] == "000"]
                elif split == "Runners on Base":
                    PA_df = PA_df[PA_df["runner_id"] != "000"]
                    plate_df = plate_df[plate_df["runner_id"] != "000"]
                    merged_data = merged_data[merged_data["runner_id"] != "000"]
                    sb_df = sb_df[sb_df["runner_id"] != "000"]
                elif split == "Runners on Scoring":
                    PA_df = PA_df[(PA_df["runner_id"] != "000")&(PA_df["runner_id"] != "100")]
                    plate_df = plate_df[(plate_df["runner_id"] != "000")&(plate_df["runner_id"] != "100")]
                    merged_data = merged_data[(merged_data["runner_id"] != "000")&(merged_data["runner_id"] != "100")]
                    sb_df = sb_df[(sb_df["runner_id"] != "000")&(sb_df["runner_id"] != "100")]
                elif split[:2] == "vs":
                    vs_team = split[3:]
                    PA_df = PA_df[PA_df["fld_team"] == vs_team]
                    plate_df = plate_df[plate_df["fld_team"] == vs_team]
                    merged_data = merged_data[merged_data["fld_team"] == vs_team]
                    sb_df = sb_df[sb_df["fld_team"] == vs_team]
                elif split[3:] == "経由":
                    count_s = split[:3]
                    PA_df = PA_df[PA_df["pa_counts"].str.contains(count_s)]
                    plate_df = plate_df[plate_df["pa_counts"].str.contains(count_s)]
                    merged_data = merged_data[merged_data["pa_counts"].str.contains(count_s)]
                    sb_df = sb_df[sb_df["pa_counts"].str.contains(count_s)]
                elif split == "Grounders":
                    PA_df = PA_df[PA_df["GB"] == 1]
                    plate_df = plate_df[plate_df["GB"] == 1]
                    merged_data = merged_data[merged_data["GB"] == 1]
                    sb_df = sb_df[sb_df["GB"] == 1]
                elif split == "Flies":
                    PA_df = PA_df[PA_df["FB"] == 1]
                    plate_df = plate_df[plate_df["FB"] == 1]
                    merged_data = merged_data[merged_data["FB"] == 1]
                    sb_df = sb_df[sb_df["FB"] == 1]
                elif split == "Liners":
                    PA_df = PA_df[PA_df["LD"] == 1]
                    plate_df = plate_df[plate_df["LD"] == 1]
                    merged_data = merged_data[merged_data["LD"] == 1]
                    sb_df = sb_df[sb_df["LD"] == 1]
                elif split == "Pull":
                    PA_df = PA_df[PA_df["Pull"] == 1]
                    plate_df = plate_df[plate_df["Pull"] == 1]
                    merged_data = merged_data[merged_data["Pull"] == 1]
                    sb_df = sb_df[sb_df["Pull"] == 1]
                elif split == "Center":
                    PA_df = PA_df[PA_df["Center"] == 1]
                    plate_df = plate_df[plate_df["Center"] == 1]
                    merged_data = merged_data[merged_data["Center"] == 1]
                    sb_df = sb_df[sb_df["Center"] == 1]
                elif split == "Opposite":
                    PA_df = PA_df[PA_df["Opposite"] == 1]
                    plate_df = plate_df[plate_df["Opposite"] == 1]
                    merged_data = merged_data[merged_data["Opposite"] == 1]
                    sb_df = sb_df[sb_df["Opposite"] == 1]
                elif split == "ストレート":
                    PA_df = PA_df[PA_df["FA"] == 1]
                    plate_df = plate_df[plate_df["FA"] == 1]
                    merged_data = merged_data[merged_data["FA"] == 1]
                    sb_df = sb_df[sb_df["FA"] == 1]
                elif split == "ツーシーム":
                    PA_df = PA_df[PA_df["FT"] == 1]
                    plate_df = plate_df[plate_df["FT"] == 1]
                    merged_data = merged_data[merged_data["FT"] == 1]
                    sb_df = sb_df[sb_df["FT"] == 1]
                elif split == "カットボール":
                    PA_df = PA_df[PA_df["CT"] == 1]
                    plate_df = plate_df[plate_df["CT"] == 1]
                    merged_data = merged_data[merged_data["CT"] == 1]
                    sb_df = sb_df[sb_df["CT"] == 1]
                elif split == "スライダー":
                    PA_df = PA_df[PA_df["SL"] == 1]
                    plate_df = plate_df[plate_df["SL"] == 1]
                    merged_data = merged_data[merged_data["SL"] == 1]
                    sb_df = sb_df[sb_df["SL"] == 1]
                elif split == "カーブ":
                    PA_df = PA_df[PA_df["CB"] == 1]
                    plate_df = plate_df[plate_df["CB"] == 1]
                    merged_data = merged_data[merged_data["CB"] == 1]
                    sb_df = sb_df[sb_df["CB"] == 1]
                elif split == "フォーク":
                    PA_df = PA_df[PA_df["SF"] == 1]
                    plate_df = plate_df[plate_df["SF"] == 1]
                    merged_data = merged_data[merged_data["SF"] == 1]
                    sb_df = sb_df[sb_df["SF"] == 1]
                elif split == "チェンジアップ":
                    PA_df = PA_df[PA_df["CH"] == 1]
                    plate_df = plate_df[plate_df["CH"] == 1]
                    merged_data = merged_data[merged_data["CH"] == 1]
                    sb_df = sb_df[sb_df["CH"] == 1]
                elif split == "シンカー":
                    PA_df = PA_df[PA_df["SI"] == 1]
                    plate_df = plate_df[plate_df["SI"] == 1]
                    merged_data = merged_data[merged_data["SI"] == 1]
                    sb_df = sb_df[sb_df["SI"] == 1]
                elif split == "特殊級":
                    PA_df = PA_df[PA_df["SP"] == 1]
                    plate_df = plate_df[plate_df["SP"] == 1]
                    merged_data = merged_data[merged_data["SP"] == 1]
                    sb_df = sb_df[sb_df["SP"] == 1]
                elif split == "ストレート150以上":
                    PA_df = PA_df[(PA_df["pitch_type"] == "FF")&(PA_df["velocity"] >= 150)]
                    plate_df = plate_df[(plate_df["pitch_type"] == "FF")&(plate_df["velocity"] >= 150)]
                    merged_data = merged_data[(merged_data["pitch_type"] == "FF")&(merged_data["velocity"] >= 150)]
                    sb_df = sb_df[(sb_df["pitch_type"] == "FF")&(sb_df["velocity"] >= 150)]
                elif split == "ストレート140~149":
                    PA_df = PA_df[(PA_df["pitch_type"] == "FF")&(PA_df["velocity"] >= 140)&(PA_df["velocity"] < 150)]
                    plate_df = plate_df[(plate_df["pitch_type"] == "FF")&(plate_df["velocity"] >= 140)&(plate_df["velocity"] < 150)]
                    merged_data = merged_data[(merged_data["pitch_type"] == "FF")&(merged_data["velocity"] >= 140)&(merged_data["velocity"] < 150)]
                    sb_df = sb_df[(sb_df["pitch_type"] == "FF")&(sb_df["velocity"] >= 140)&(sb_df["velocity"] < 150)]
                elif split == "ストレート140未満":
                    PA_df = PA_df[(PA_df["pitch_type"] == "FF")&(PA_df["velocity"] < 140)]
                    plate_df = plate_df[(plate_df["pitch_type"] == "FF")&(plate_df["velocity"] < 140)]
                    merged_data = merged_data[(merged_data["pitch_type"] == "FF")&(merged_data["velocity"] < 140)]
                    sb_df = sb_df[(sb_df["pitch_type"] == "FF")&(sb_df["velocity"] < 140)]
                elif split[:8] == "Batting ":
                    PA_df = PA_df[PA_df["order"] == int(split[8])]
                    plate_df = plate_df[plate_df["order"] == int(split[8])]
                    merged_data = merged_data[merged_data["order"] == int(split[8])]
                    sb_df = sb_df[sb_df["order"] == int(split[8])]
                if stand_en == "S":
                    if st_split == "Right":
                        PA_df = PA_df[PA_df["stand"] == "右"]
                        plate_df = plate_df[plate_df["stand"] == "右"]
                        merged_data = merged_data[merged_data["stand"] == "右"]
                        sb_df = sb_df[sb_df["stand"] == "右"]
                    elif st_split == "Left":
                        PA_df = PA_df[PA_df["stand"] == "左"]
                        plate_df = plate_df[plate_df["stand"] == "左"]
                        merged_data = merged_data[merged_data["stand"] == "左"]
                        sb_df = sb_df[sb_df["stand"] == "左"]
                
                player_bat_data = PA_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                if league_type == "1軍":
                    player_bb_data = PA_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                        GB = ("GB", "sum"),
                        FB = ("FB", "sum"),
                        IFFB = ("IFFB", "sum"),
                        OFFB = ("OFFB", "sum"),
                        LD = ("LD", "sum"),
                        Pull = ("Pull", "sum"),
                        Cent = ("Center", "sum"),
                        Oppo = ("Opposite", "sum")
                    )
                    player_bat_data = pd.merge(player_bat_data, player_bb_data, on=["game_year", "bat_league", "bat_team", "batter_name"], how="left")
                player_bat_data = player_bat_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                player_bat_data["AB"] = player_bat_data["PA"] - (player_bat_data["BB"] + player_bat_data["HBP"] + player_bat_data["SH"] + player_bat_data["SF"] + player_bat_data["obstruction"] + player_bat_data["interference"])
                player_bat_data["H"] = player_bat_data["1B"] + player_bat_data["2B"] + player_bat_data["3B"] + player_bat_data["HR"]
                player_bat_data["avg"] = player_bat_data["H"]/player_bat_data["AB"]
                player_bat_data["AVG"] = my_round(player_bat_data["avg"], 3)
                player_bat_data["obp"] = (player_bat_data["H"] + player_bat_data["BB"] + player_bat_data["HBP"])/(player_bat_data["AB"] + player_bat_data["BB"] + player_bat_data["HBP"] + player_bat_data["SF"])
                player_bat_data["OBP"] = my_round(player_bat_data["obp"], 3)
                player_bat_data["slg"] = (player_bat_data["1B"] + 2*player_bat_data["2B"] + 3*player_bat_data["3B"] + 4*player_bat_data["HR"])/player_bat_data["AB"]
                player_bat_data["SLG"] = my_round(player_bat_data["slg"], 3)
                player_bat_data["ops"] = player_bat_data["obp"] + player_bat_data["slg"]
                player_bat_data["OPS"] = my_round(player_bat_data["ops"], 3)
                player_bat_data["iso"] = player_bat_data["slg"] - player_bat_data["avg"]
                player_bat_data["ISO"] = my_round(player_bat_data["iso"], 3)
                player_bat_data["babip"] = (player_bat_data["H"] - player_bat_data["HR"])/(player_bat_data["AB"] - player_bat_data["SO"] - player_bat_data["HR"] + player_bat_data["SF"])
                player_bat_data["BABIP"] = my_round(player_bat_data["babip"], 3)
                player_bat_data["k%"] = player_bat_data["SO"]/player_bat_data["PA"]
                player_bat_data["bb%"] = player_bat_data["BB"]/player_bat_data["PA"]
                player_bat_data["K%"] = my_round(player_bat_data["k%"], 3)
                player_bat_data["BB%"] = my_round(player_bat_data["bb%"], 3)
                player_bat_data["BB/K"] = my_round(player_bat_data["BB"]/player_bat_data["SO"], 2)
                if league_type == "1軍":
                    player_bat_data["gb/fb"] = player_bat_data["GB"] / player_bat_data["FB"]
                    player_bat_data["gb%"] = player_bat_data["GB"]/(player_bat_data["GB"]+player_bat_data["FB"]+player_bat_data["LD"])
                    player_bat_data["fb%"] = player_bat_data["FB"]/(player_bat_data["GB"]+player_bat_data["FB"]+player_bat_data["LD"])
                    player_bat_data["ld%"] = player_bat_data["LD"] / (player_bat_data["GB"]+player_bat_data["FB"]+player_bat_data["LD"])
                    player_bat_data["iffb%"] = player_bat_data["IFFB"] / player_bat_data["FB"]
                    player_bat_data["hr/fb"] = player_bat_data["HR"] / player_bat_data["FB"]
                    player_bat_data["GB/FB"] = my_round(player_bat_data["gb/fb"], 2)
                    player_bat_data["GB%"] = my_round(player_bat_data["gb%"], 3)
                    player_bat_data["FB%"] = my_round(player_bat_data["fb%"], 3)
                    player_bat_data["LD%"] = my_round(player_bat_data["ld%"], 3)
                    player_bat_data["IFFB%"] = my_round(player_bat_data["iffb%"], 3)
                    player_bat_data["HR/FB"] = my_round(player_bat_data["hr/fb"], 3)
                    player_bat_data["pull%"] = player_bat_data["Pull"]/(player_bat_data["Pull"]+player_bat_data["Cent"]+player_bat_data["Oppo"])
                    player_bat_data["cent%"] = player_bat_data["Cent"]/(player_bat_data["Pull"]+player_bat_data["Cent"]+player_bat_data["Oppo"])
                    player_bat_data["oppo%"] = player_bat_data["Oppo"]/(player_bat_data["Pull"]+player_bat_data["Cent"]+player_bat_data["Oppo"])
                    player_bat_data["ifh%"] = player_bat_data["IFH"]/(player_bat_data["GB"])
                    player_bat_data["Pull%"] = my_round(player_bat_data["pull%"], 3)
                    player_bat_data["Cent%"] = my_round(player_bat_data["cent%"], 3)
                    player_bat_data["Oppo%"] = my_round(player_bat_data["oppo%"], 3)
                    player_bat_data["IFH%"] = my_round(player_bat_data["ifh%"], 3)
                elif league_type == "2軍":
                    player_bat_data["GB/FB"] = np.nan
                    player_bat_data["GB%"] = np.nan
                    player_bat_data["FB%"] = np.nan
                    player_bat_data["LD%"] = np.nan
                    player_bat_data["IFFB%"] = np.nan
                    player_bat_data["HR/FB"] = np.nan
                    player_bat_data["Pull%"] = np.nan
                    player_bat_data["Cent%"] = np.nan
                    player_bat_data["Oppo%"] = np.nan
                    player_bat_data["IFH%"] = np.nan
                player_bat_data["woba"] = wOBA_scale * (bb_value * (player_bat_data["BB"] - player_bat_data["IBB"]) + hbp_value * player_bat_data["HBP"] + single_value * player_bat_data["1B"] + double_value * player_bat_data["2B"] + triple_value * player_bat_data["3B"] + hr_value * player_bat_data["HR"])/(player_bat_data["AB"] + player_bat_data["BB"] - player_bat_data["IBB"] + player_bat_data["HBP"] + player_bat_data["SF"])
                player_bat_data["wOBA"] = my_round(player_bat_data["woba"], 3)
                player_bat_data = pd.merge(player_bat_data, league_wrc_mean, on=["Season", "League"], how="left")
                player_bat_data["wraa"] = ((player_bat_data["woba"] - player_bat_data["woba_league"])/wOBA_scale) * player_bat_data["PA"]
                player_bat_data["wrar"] = ((player_bat_data["woba"] - player_bat_data["woba_league"]*0.88)/wOBA_scale) * player_bat_data["PA"]
                player_bat_data["wRAA"] = my_round(player_bat_data["wraa"], 1)
                player_bat_data["wrc"] = (((player_bat_data["woba"] - player_bat_data["woba_league"])/wOBA_scale) + player_bat_data["R_league"]/player_bat_data["PA_league"])*player_bat_data["PA"]
                player_bat_data["wRC"] = my_round(player_bat_data["wrc"])
                player_bat_data = pd.merge(player_bat_data, rpw_df, on=["Season", "League"], how="left")
                player_bat_data = pd.merge(player_bat_data, pf[["Team", "bpf/100"]], on="Team", how="left")
                player_bat_data["wrc_pf"] = player_bat_data["wrc"] + (1-player_bat_data["bpf/100"])*player_bat_data["PA"]*(player_bat_data["R_league"]/player_bat_data["PA_league"]/player_bat_data["bpf/100"])
                player_bat_data["wrc+"] = 100*(player_bat_data["wrc_pf"]/player_bat_data["PA"])/(player_bat_data["R_league"]/player_bat_data["PA_league"])
                player_bat_data["wrar_pf"] = ((player_bat_data["woba"] - player_bat_data["woba_league"]*player_bat_data["bpf/100"]*0.88)/wOBA_scale) * player_bat_data["PA"]
                player_bat_data["batwar"] = player_bat_data["wrar_pf"]/player_bat_data["RPW"]
                player_bat_data["wRC+"] = my_round(player_bat_data["wrc+"])
                player_bat_data["batWAR"] = my_round(player_bat_data["batwar"], 1)
                plate_discipline = plate_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    N=("batter_name", "size"),
                    Swing=("swing", "sum"),
                    Contact=("contact", "sum"),
                    SwStr=('description', lambda x: (x == "swing_strike").sum()),  # 被本塁打数
                    CStr=('description', lambda x: (x == "called_strike").sum()),  # 被本塁打数
                    Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
                )
                plate_discipline["swing%"] = plate_discipline["Swing"]/plate_discipline["N"]
                plate_discipline["contact%"] = plate_discipline["Contact"]/plate_discipline["Swing"]
                plate_discipline["zone%"] = plate_discipline["Zone"]/plate_discipline["N"]
                plate_discipline["swstr%"] = plate_discipline["SwStr"]/plate_discipline["N"]
                plate_discipline["cstr%"] = plate_discipline["CStr"]/plate_discipline["N"]
                plate_discipline["whiff%"] = plate_discipline["SwStr"]/plate_discipline["Swing"]
                plate_discipline["csw%"] = (plate_discipline["SwStr"]+plate_discipline["CStr"])/plate_discipline["N"]
                plate_discipline["Swing%"] = my_round(plate_discipline["swing%"], 3)
                plate_discipline["Contact%"] = my_round(plate_discipline["contact%"], 3)
                plate_discipline["Zone%"] = my_round(plate_discipline["zone%"], 3)
                plate_discipline["SwStr%"] = my_round(plate_discipline["swstr%"], 3)
                plate_discipline["CStr%"] = my_round(plate_discipline["cstr%"], 3)
                plate_discipline["Whiff%"] = my_round(plate_discipline["whiff%"], 3)
                plate_discipline["CSW%"] = my_round(plate_discipline["csw%"], 3)

                o_plate_df = plate_df[plate_df["Zone"] == "Out"]
                o_disc = o_plate_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    O_N=("batter_name", "size"),
                    O_Swing=("swing", "sum"),
                    O_Contact=("contact", "sum"),
                )
                o_disc["o-swing%"] = o_disc["O_Swing"]/o_disc["O_N"]
                o_disc["o-contact%"] = o_disc["O_Contact"]/o_disc["O_N"]
                o_disc["O-Swing%"] = my_round(o_disc["o-swing%"], 3)
                o_disc["O-Contact%"] = my_round(o_disc["o-contact%"], 3)
                plate_discipline = pd.merge(plate_discipline, o_disc, on=["game_year", "bat_league", "bat_team", "batter_name"], how="left")

                z_plate_df = plate_df[plate_df["Zone"] == "In"]
                z_disc = z_plate_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    Z_N=("batter_name", "size"),
                    Z_Swing=("swing", "sum"),
                    Z_Contact=("contact", "sum"),
                )
                z_disc["z-swing%"] = z_disc["Z_Swing"]/z_disc["Z_N"]
                z_disc["z-contact%"] = z_disc["Z_Contact"]/z_disc["Z_N"]
                z_disc["Z-Swing%"] = my_round(z_disc["z-swing%"], 3)
                z_disc["Z-Contact%"] = my_round(z_disc["z-contact%"], 3)
                plate_discipline = pd.merge(plate_discipline, z_disc, on=["game_year", "bat_league", "bat_team", "batter_name"], how="left")

                f_plate_df = plate_df[plate_df["ab_pitch_number"] == 1]
                f_disc = f_plate_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    F_N=("batter_name", "size"),
                    F_Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
                )
                f_disc["f-strike%"] = f_disc["F_Zone"]/f_disc["F_N"]
                f_disc["F-Strike%"] = my_round(f_disc["f-strike%"], 3)
                plate_discipline = pd.merge(plate_discipline, f_disc, on=["game_year", "bat_league", "bat_team", "batter_name"], how="left")

                t_plate_df = plate_df[plate_df["strikes"] == 2]
                t_disc = t_plate_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    T_N=("batter_name", "size"),
                    T_SO=('events', lambda x: (x == "strike_out").sum()),  # 被本塁打数
                )
                t_disc["putaway%"] = t_disc["T_SO"]/t_disc["T_N"]
                t_disc["PutAway%"] = my_round(t_disc["putaway%"], 3)
                plate_discipline = pd.merge(plate_discipline, t_disc, on=["game_year", "bat_league", "bat_team", "batter_name"], how="left")
                plate_discipline = plate_discipline.rename(columns={"game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player"})
                player_bat_data = pd.merge(player_bat_data, plate_discipline, on=["Season", "League", "Team", "Player"], how="left")
                
                pt_list = ["FA", "FT", "SL", "CT", "CB", "CH", "SF", "SI", "SP", "XX"]
                for p in pt_list:
                    p_low = p.lower()
                    fa_df = plate_df[plate_df[p] == 1]
                    fa_v = fa_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                        p_n=("batter_name", "size"),
                        v=('velocity', "mean")
                    )
                    fa_v = fa_v.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                                "game_year": "Season",
                                                "p_n": p_low, "v": p + "_v"})

                    fa_pv_df = merged_data[merged_data[p] == 1]
                    fa_pv = fa_pv_df.groupby(["game_year", "bat_league", "bat_team", "batter_name"], as_index=False).agg(
                        w=('batter_pitch_value', "sum")
                    )
                    fa_pv = fa_pv.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                                "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                                "game_year": "Season",
                                                "w": p + "_w"})

                    player_bat_data = pd.merge(player_bat_data, fa_v, on=["Season", "League", "Team", "Player"], how="left")
                    player_bat_data = pd.merge(player_bat_data, fa_pv, on=["Season", "League", "Team", "Player"], how="left")
                    player_bat_data[f"{p}%"] = my_round(player_bat_data[p_low]/player_bat_data["N"], 3)
                    player_bat_data[f"{p}v"] = my_round(player_bat_data[p + "_v"], 1)
                    player_bat_data[f"w{p}"] = my_round(player_bat_data[p + "_w"], 1)
                    player_bat_data[f"w{p}/C"] = my_round(100*player_bat_data[f"w{p}"]/player_bat_data[p_low], 1)

                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = sb_df[(sb_df["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                try:
                    sb_data = pd.concat(sb_data_list)

                    runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                        SB=("SB", "sum"),
                        CS=("CS", "sum"),
                    ).sort_values("SB", ascending=False)
                    runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League"})

                    player_bat_data['batter_name_no_space'] = player_bat_data['Player'].str.replace(" ", "")
                    player_bat_data = partial_match_merge(player_bat_data, runner_df, 'batter_name_no_space', 'runner_name')
                
                    player_bat_data["SB"] = player_bat_data["SB"].fillna(0).astype(int)
                    player_bat_data["CS"] = player_bat_data["CS"].fillna(0).astype(int)
                except:
                    player_bat_data["SB"] = 0
                    player_bat_data["CS"] = 0

                player_bat_data["wSB_A"] = (player_bat_data["SB"] * sb_run) + (player_bat_data["CS"] * cs_run)
                player_bat_data["wSB_B"] = (
                    (player_bat_data["SB_league"] * sb_run) + (player_bat_data["CS_league"] * cs_run)
                    )/(player_bat_data["1B_league"] + player_bat_data["BB_league"] + player_bat_data["HBP_league"] + player_bat_data["IBB_league"])
                player_bat_data["wSB_C"] = player_bat_data["1B"] + player_bat_data["BB"] - player_bat_data["IBB"] + player_bat_data["HBP"]
                player_bat_data['wsb'] = np.where(
                    (player_bat_data['SB'] == 0) & (player_bat_data['CS'] == 0),
                    np.nan,
                    player_bat_data['wSB_A'] - player_bat_data['wSB_B'] * player_bat_data['wSB_C']
                )
                player_bat_data["wSB"] = my_round(player_bat_data["wsb"], 1)

                player_bat_data["Team"] = player_bat_data["Team"].replace(team_en_dict)
                
                st.write(f"{latest_date_str} 終了時点")

                st.markdown("### Dashboard")
                bat_cols = ["Season", "Team", "G", "PA", "HR", "SB", "BB%", "K%", "ISO", "BABIP", "AVG", "OBP", "SLG", "wOBA", "wRC+", "batWAR"]
                bat_0 = player_bat_data[bat_cols]
                df_style = bat_0.style.format({
                    'Season': '{:.0f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'BB/K': '{:.2f}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'wRC': '{:.0f}',
                    'wRAA': '{:.1f}',
                    'batWAR': '{:.1f}',
                    'wRC+': '{:.0f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Standard")
                bat_cols = ["Season", "Team", "G", "AB", "PA", "H", "1B", "2B", "3B", "HR", "BB", "IBB", "SO", "HBP", "SF", "SH", "GDP", "SB", "CS", "AVG"]
                bat_1 = player_bat_data[bat_cols]
                df_style = bat_1.style.format({
                    'Season': '{:.0f}',
                    'K%': '{:.2f}',
                    'BB%': '{:.2f}',
                    'BB/K': '{:.2f}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'wRC': '{:.0f}',
                    'wRAA': '{:.1f}',
                    'wRC+': '{:.0f}',
                    'GB%': '{:.2f}',
                    'FB%': '{:.2f}',
                    'LD%': '{:.2f}',
                    'IFFB%': '{:.2f}',
                    'HR/FB': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Advanced")
                bat_cols = ["Season", "Team", "PA", "BB%", "K%", "BB/K", "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP", "wRC", "wSB", "wRAA", "wOBA", "wRC+"]
                bat_2 = player_bat_data[bat_cols]
                df_style = bat_2.style.format({
                    'Season': '{:.0f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'BB/K': '{:.2f}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'wRC': '{:.0f}',
                    'wRAA': '{:.1f}',
                    'wSB': '{:.1f}',
                    'wRC+': '{:.0f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Batted Ball")
                bat_cols = ["Season", "Team", "BABIP", "GB/FB", "LD%", "GB%", "FB%", "IFFB%", "HR/FB", "IFH", "IFH%", "Pull%", "Cent%", "Oppo%"]
                bat_3 = player_bat_data[bat_cols]
                df_style = bat_3.style.format({
                    'Season': '{:.0f}',
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'IFH%': '{:.1%}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'Pull%': '{:.1%}',
                    'Cent%': '{:.1%}',
                    'Oppo%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'GB/FB': '{:.2f}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Plate Discipline")
                bat_cols = ["Season", "Team", "O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", 
                                    "Zone%", "F-Strike%", "Whiff%", "PutAway%", "SwStr%", "CStr%", "CSW%"]
                bat_4 = player_bat_data[bat_cols]
                df_style = bat_4.style.format({
                    'Season': '{:.0f}',
                    'O-Swing%': '{:.1%}',
                    'Z-Swing%': '{:.1%}',
                    'Swing%': '{:.1%}',
                    'O-Contact%': '{:.1%}',
                    'Z-Contact%': '{:.1%}',
                    'Contact%': '{:.1%}',
                    'Zone%': '{:.1%}',
                    'F-Strike%': '{:.1%}',
                    'Whiff%': '{:.1%}',
                    'PutAway%': '{:.1%}',
                    'SwStr%': '{:.1%}',
                    'CStr%': '{:.1%}',
                    'CSW%': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Pitch Type")
                bat_cols = ["Season", "Team", "FA%", "FAv", "FT%", "FTv", "SL%", "SLv", "CT%", "CTv", "CB%", "CBv", 
                                    "CH%", "CHv", "SF%", "SFv", "SI%", "SIv", "SP%", "SPv", "XX%", "XXv"]
                bat_5 = player_bat_data[bat_cols]
                df_style = bat_5.style.format({
                    'Season': '{:.0f}',
                    'FA%': '{:.1%}',
                    'FT%': '{:.1%}',
                    'SL%': '{:.1%}',
                    'CT%': '{:.1%}',
                    'CB%': '{:.1%}',
                    'CH%': '{:.1%}',
                    'SF%': '{:.1%}',
                    'SI%': '{:.1%}',
                    'SP%': '{:.1%}',
                    'XX%': '{:.1%}',
                    'FAv': '{:.1f}',
                    'FTv': '{:.1f}',
                    'SLv': '{:.1f}',
                    'CTv': '{:.1f}',
                    'CBv': '{:.1f}',
                    'CHv': '{:.1f}',
                    'SFv': '{:.1f}',
                    'SIv': '{:.1f}',
                    'SPv': '{:.1f}',
                    'XXv': '{:.1f}'
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Pitch Value")
                bat_cols = ["Season", "Team", "wFA", "wFT", "wSL", "wCT", "wCB", "wCH", "wSF", "wSI", "wSP", 
                                    "wFA/C", "wFT/C", "wSL/C", "wCT/C", "wCB/C", "wCH/C", "wSF/C", "wSI/C", "wSP/C"]
                bat_6 = player_bat_data[bat_cols]
                df_style = bat_6.style.format({
                    'Season': '{:.0f}',
                    'wFA': '{:.1f}',
                    'wFT': '{:.1f}',
                    'wSL': '{:.1f}',
                    'wCT': '{:.1f}',
                    'wCB': '{:.1f}',
                    'wCH': '{:.1f}',
                    'wSF': '{:.1f}',
                    'wSI': '{:.1f}',
                    'wSP': '{:.1f}',
                    'wFA/C': '{:.1f}',
                    'wFT/C': '{:.1f}',
                    'wSL/C': '{:.1f}',
                    'wCT/C': '{:.1f}',
                    'wCB/C': '{:.1f}',
                    'wCH/C': '{:.1f}',
                    'wSF/C': '{:.1f}',
                    'wSI/C': '{:.1f}',
                    'wSP/C': '{:.1f}',
                })
                st.dataframe(df_style, use_container_width=True)
            
            elif stats_type == "Pitching":

                events_df = events_df[events_df["pitcher_id"] == player_id]
                plate_df = plate_df[plate_df["pitcher_id"] == player_id]
                merged_data = merged_data[merged_data["pitcher_id"] == player_id]

                if split == "No Split":
                    pass
                elif split == "Yesterday":
                    events_df = events_df[events_df["game_date"] == latest_date]
                    plate_df = plate_df[plate_df["game_date"] == latest_date]
                    merged_data = merged_data[merged_data["game_date"] == latest_date]
                elif split == "Last 7days":
                    events_df = events_df[events_df["game_date"] >= (latest_date - timedelta(days=6))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=6))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=6))]
                elif split == "Last 14days":
                    events_df = events_df[events_df["game_date"] >= (latest_date - timedelta(days=13))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=13))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=13))]
                elif split == "Last 30days":
                    events_df = events_df[events_df["game_date"] >= (latest_date - timedelta(days=29))]
                    plate_df = plate_df[plate_df["game_date"] >= (latest_date - timedelta(days=29))]
                    merged_data = merged_data[merged_data["game_date"] >= (latest_date - timedelta(days=29))]
                elif split == "March/April":
                    events_df = PA_df[events_df["game_date"].dt.month <= 4]
                    plate_df = plate_df[plate_df["game_date"].dt.month <= 4]
                    merged_data = merged_data[merged_data["game_date"].dt.month <= 4]
                elif split == "May":
                    events_df = events_df[events_df["game_date"].dt.month == 5]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 5]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 5]
                elif split == "June":
                    events_df = events_df[events_df["game_date"].dt.month == 6]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 6]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 6]
                elif split == "July":
                    events_df = events_df[events_df["game_date"].dt.month == 7]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 7]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 7]
                elif split == "August":
                    events_df = events_df[events_df["game_date"].dt.month == 8]
                    plate_df = plate_df[plate_df["game_date"].dt.month == 8]
                    merged_data = merged_data[merged_data["game_date"].dt.month == 8]
                elif split == "Sept~":
                    events_df = events_df[events_df["game_date"].dt.month >= 9]
                    plate_df = plate_df[plate_df["game_date"].dt.month >= 9]
                    merged_data = merged_data[merged_data["game_date"].dt.month >= 9]
                elif split == "vsRHH":
                    events_df = events_df[events_df["stand"] == "右"]
                    plate_df = plate_df[plate_df["stand"] == "右"]
                    merged_data = merged_data[merged_data["stand"] == "右"]
                elif split == "vsLHH":
                    events_df = events_df[events_df["stand"] == "左"]
                    plate_df = plate_df[plate_df["stand"] == "左"]
                    merged_data = merged_data[merged_data["stand"] == "左"]
                elif split == "Home":
                    events_df = events_df[events_df["fld_team"] == events_df["home_team"]]
                    plate_df = plate_df[plate_df["fld_team"] == plate_df["home_team"]]
                    merged_data = merged_data[merged_data["fld_team"] == merged_data["home_team"]]
                elif split == "Away":
                    events_df = events_df[events_df["fld_team"] == events_df["away_team"]]
                    plate_df = plate_df[plate_df["fld_team"] == plate_df["away_team"]]
                    merged_data = merged_data[merged_data["fld_team"] == merged_data["away_team"]]
                elif split == "Bases Empty":
                    events_df = events_df[events_df["runner_id"] == "000"]
                    plate_df = plate_df[plate_df["runner_id"] == "000"]
                    merged_data = merged_data[merged_data["runner_id"] == "000"]
                elif split == "Runners on Base":
                    events_df = events_df[events_df["runner_id"] != "000"]
                    plate_df = plate_df[plate_df["runner_id"] != "000"]
                    merged_data = merged_data[merged_data["runner_id"] != "000"]
                elif split == "Runners on Scoring":
                    events_df = events_df[(events_df["runner_id"] != "000")&(events_df["runner_id"] != "100")]
                    plate_df = plate_df[(plate_df["runner_id"] != "000")&(plate_df["runner_id"] != "100")]
                    merged_data = merged_data[(merged_data["runner_id"] != "000")&(merged_data["runner_id"] != "100")]
                elif split[:2] == "vs":
                    vs_team = split[3:]
                    events_df = events_df[events_df["bat_team"] == vs_team]
                    plate_df = plate_df[plate_df["bat_team"] == vs_team]
                    merged_data = merged_data[merged_data["bat_team"] == vs_team]
                elif split[3:] == "経由":
                    count_s = split[:3]
                    events_df = events_df[events_df["pa_counts"].str.contains(count_s)]
                    plate_df = plate_df[plate_df["pa_counts"].str.contains(count_s)]
                    merged_data = merged_data[merged_data["pa_counts"].str.contains(count_s)]
                elif split == "Grounders":
                    events_df = events_df[events_df["GB"] == 1]
                    plate_df = plate_df[plate_df["GB"] == 1]
                    merged_data = merged_data[merged_data["GB"] == 1]
                elif split == "Flies":
                    events_df = events_df[events_df["FB"] == 1]
                    plate_df = plate_df[plate_df["FB"] == 1]
                    merged_data = merged_data[merged_data["FB"] == 1]
                elif split == "Liners":
                    events_df = events_df[events_df["LD"] == 1]
                    plate_df = plate_df[plate_df["LD"] == 1]
                    merged_data = merged_data[merged_data["LD"] == 1]
                elif split == "リード時":
                    events_df = events_df[events_df["fld_score"] > events_df["bat_score"]]
                    plate_df = plate_df[plate_df["fld_score"] > plate_df["bat_score"]]
                    merged_data = merged_data[merged_data["fld_score"] > merged_data["bat_score"]]
                elif split == "同点時":
                    events_df = events_df[events_df["fld_score"] == events_df["bat_score"]]
                    plate_df = plate_df[plate_df["fld_score"] == plate_df["bat_score"]]
                    merged_data = merged_data[merged_data["fld_score"] == merged_data["bat_score"]]
                elif split == "ビハインド時":
                    events_df = events_df[events_df["fld_score"] < events_df["bat_score"]]
                    plate_df = plate_df[plate_df["fld_score"] < plate_df["bat_score"]]
                    merged_data = merged_data[merged_data["fld_score"] < merged_data["bat_score"]]
                elif split[-1] == "回":
                    innning = int(split[0])
                    events_df = events_df[events_df["inning"] == innning]
                    plate_df = plate_df[plate_df["inning"] == innning]
                    merged_data = merged_data[merged_data["inning"] == innning]
                elif split == "延長":
                    events_df = events_df[events_df["inning"] > 9]
                    plate_df = plate_df[plate_df["inning"] > 9]
                    merged_data = merged_data[merged_data["inning"] > 9]

                player_outs_sum = events_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["game_year", "fld_league", "fld_team", "pitcher_name"] + ['IP']

                cg_count = events_df[events_df['CG'] == 1].groupby(["game_year", "fld_league", "fld_team", "pitcher_name"])['game_id'].nunique().reset_index(name='CG')
                sho_count = events_df[events_df['ShO'] == 1].groupby(["game_year", "fld_league", "fld_team", "pitcher_name"])['game_id'].nunique().reset_index(name='ShO')

                pitcher_gl = events_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    TBF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum())
                )
                if league_type == "1軍":
                    player_pb_data = events_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        GB = ("GB", "sum"),
                        FB = ("FB", "sum"),
                        IFFB = ("IFFB", "sum"),
                        OFFB = ("OFFB", "sum"),
                        LD = ("LD", "sum"),
                        Pull = ("Pull", "sum"),
                        Cent = ("Center", "sum"),
                        Oppo = ("Opposite", "sum")
                    )
                    pitcher_gl = pd.merge(pitcher_gl, player_pb_data, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how="left")
                pitcher_gl = pd.merge(pitcher_gl, player_ip_df, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how='left')
                pitcher_gl = pitcher_gl.merge(cg_count, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how='left').fillna(0)
                pitcher_gl = pitcher_gl.merge(sho_count, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how='left').fillna(0)
                pitcher_gl["CG"] = pitcher_gl["CG"].astype(int)
                pitcher_gl["ShO"] = pitcher_gl["ShO"].astype(int)
                pitcher_gl["inning"] = pitcher_gl["O"]/3
                pitcher_gl["AB"] = pitcher_gl["TBF"] - (pitcher_gl["BB"] + pitcher_gl["HBP"] + pitcher_gl["SH"] + pitcher_gl["SF"] + pitcher_gl["obstruction"] + pitcher_gl["interference"])
                pitcher_gl["H"] = pitcher_gl["single"] + pitcher_gl["double"] + pitcher_gl["triple"] + pitcher_gl["HR"]
                pitcher_gl['k/9'] = pitcher_gl['SO'] * 9 / pitcher_gl['inning']
                pitcher_gl['bb/9'] = pitcher_gl['BB'] * 9 / pitcher_gl['inning']
                pitcher_gl['K/9'] = my_round(pitcher_gl['k/9'], 2)
                pitcher_gl['BB/9'] = my_round(pitcher_gl['bb/9'], 2)
                pitcher_gl['k%'] = pitcher_gl["SO"]/pitcher_gl["TBF"]
                pitcher_gl['bb%'] = pitcher_gl["BB"]/pitcher_gl["TBF"]
                pitcher_gl['hr%'] = pitcher_gl["HR"]/pitcher_gl["TBF"]
                pitcher_gl["K%"] = my_round(pitcher_gl["k%"], 3)
                pitcher_gl["BB%"] = my_round(pitcher_gl["bb%"], 3)
                pitcher_gl["HR%"] = my_round(pitcher_gl["hr%"], 3)
                pitcher_gl["k-bb%"] = pitcher_gl["k%"] - pitcher_gl["bb%"]
                pitcher_gl["K-BB%"] = my_round(pitcher_gl["k-bb%"], 3)
                pitcher_gl['K/BB'] = my_round(pitcher_gl['SO'] / pitcher_gl['BB'], 2)
                pitcher_gl['HR/9'] = my_round(pitcher_gl['HR'] * 9 / pitcher_gl['inning'], 2)
                pitcher_gl['ra'] = pitcher_gl['R'] * 9 / pitcher_gl['inning']
                pitcher_gl['RA'] = my_round(pitcher_gl['ra'], 2)
                pitcher_gl = pd.merge(pitcher_gl, league_fip_data, on=["game_year", "fld_league"], how="left")
                pitcher_gl['fip'] = (13*pitcher_gl["HR"] + 3*(pitcher_gl["BB"] - pitcher_gl["IBB"] + pitcher_gl["HBP"]) - 2*pitcher_gl["SO"])/pitcher_gl["inning"] + pitcher_gl["cFIP"]
                pitcher_gl['FIP'] = my_round(pitcher_gl['fip'], 2)
                pitcher_gl["r-f"] = pitcher_gl["ra"] - pitcher_gl["fip"]
                pitcher_gl["R-F"] = my_round(pitcher_gl["r-f"], 2)
                pitcher_gl["avg"] = pitcher_gl["H"]/pitcher_gl["AB"]
                pitcher_gl["AVG"] = my_round(pitcher_gl["avg"], 3)
                pitcher_gl["babip"] = (pitcher_gl["H"] - pitcher_gl["HR"])/(pitcher_gl["AB"] - pitcher_gl["SO"] - pitcher_gl["HR"] + pitcher_gl["SF"])
                pitcher_gl["BABIP"] = my_round(pitcher_gl["babip"], 3)
                pitcher_gl = pitcher_gl.rename(columns={"game_year": "Season", "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player", "game_year": "Season"})        
                starter_games = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                st_games = st_games.rename(columns={"game_year": "Season", "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})        
                pitcher_gl = pd.merge(pitcher_gl, st_games, on=["Season", "League", "Team", "Player"], how='left')
                pitcher_gl['GS'] = pitcher_gl['GS'].fillna(0).astype(int)
                pitcher_gl = pd.merge(pitcher_gl, pf[["Team", "bpf/100"]], on="Team", how="left")
                pitcher_gl["fip-"] = 100*(pitcher_gl["FIP"] + (pitcher_gl["FIP"] - pitcher_gl["FIP"]*pitcher_gl["bpf/100"]))/pitcher_gl["cFIP"]
                pitcher_gl["ra-"] = 100*(pitcher_gl["RA"] + (pitcher_gl["RA"] - pitcher_gl["RA"]*pitcher_gl["bpf/100"]))/pitcher_gl["lgRA"]
                pitcher_gl["FIP-"] = my_round(pitcher_gl["fip-"])
                pitcher_gl["RA-"] = my_round(pitcher_gl["ra-"])
                pitcher_gl["lob%"] = (pitcher_gl["H"] + pitcher_gl["BB"] + pitcher_gl["HBP"] - pitcher_gl["R"])/(pitcher_gl["H"] + pitcher_gl["BB"] + pitcher_gl["HBP"] - 1.4+pitcher_gl["HR"])
                pitcher_gl["LOB%"] = my_round(pitcher_gl["lob%"], 3)
                if league_type == "1軍":
                    pitcher_gl["gb/fb"] = pitcher_gl["GB"] / pitcher_gl["FB"]
                    pitcher_gl["gb%"] = pitcher_gl["GB"]/(pitcher_gl["GB"]+pitcher_gl["FB"]+pitcher_gl["LD"])
                    pitcher_gl["fb%"] = pitcher_gl["FB"]/(pitcher_gl["GB"]+pitcher_gl["FB"]+pitcher_gl["LD"])
                    pitcher_gl["ld%"] = pitcher_gl["LD"] / (pitcher_gl["GB"]+pitcher_gl["FB"]+pitcher_gl["LD"])
                    pitcher_gl["iffb%"] = pitcher_gl["IFFB"] / pitcher_gl["FB"]
                    pitcher_gl["hr/fb"] = pitcher_gl["HR"] / pitcher_gl["FB"]
                    pitcher_gl["GB/FB"] = my_round(pitcher_gl["gb/fb"], 2)
                    pitcher_gl["GB%"] = my_round(pitcher_gl["gb%"], 3)
                    pitcher_gl["FB%"] = my_round(pitcher_gl["fb%"], 3)
                    pitcher_gl["LD%"] = my_round(pitcher_gl["ld%"], 3)
                    pitcher_gl["IFFB%"] = my_round(pitcher_gl["iffb%"], 3)
                    pitcher_gl["HR/FB"] = my_round(pitcher_gl["hr/fb"], 3)
                    pitcher_gl["pull%"] = pitcher_gl["Pull"]/(pitcher_gl["Pull"]+pitcher_gl["Cent"]+pitcher_gl["Oppo"])
                    pitcher_gl["cent%"] = pitcher_gl["Cent"]/(pitcher_gl["Pull"]+pitcher_gl["Cent"]+pitcher_gl["Oppo"])
                    pitcher_gl["oppo%"] = pitcher_gl["Oppo"]/(pitcher_gl["Pull"]+pitcher_gl["Cent"]+pitcher_gl["Oppo"])
                    pitcher_gl["Pull%"] = my_round(pitcher_gl["pull%"], 3)
                    pitcher_gl["Cent%"] = my_round(pitcher_gl["cent%"], 3)
                    pitcher_gl["Oppo%"] = my_round(pitcher_gl["oppo%"], 3)
                if league_type == "2軍":
                    pitcher_gl["GB/FB"] = np.nan
                    pitcher_gl["GB%"] = np.nan
                    pitcher_gl["FB%"] = np.nan
                    pitcher_gl["LD%"] = np.nan
                    pitcher_gl["IFFB%"] = np.nan
                    pitcher_gl["HR/FB"] = np.nan
                    pitcher_gl["Pull%"] = np.nan
                    pitcher_gl["Cent%"] = np.nan
                    pitcher_gl["Oppo%"] = np.nan

                plate_discipline = plate_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    N=("pitcher_name", "size"),
                    Swing=("swing", "sum"),
                    Contact=("contact", "sum"),
                    SwStr=('description', lambda x: (x == "swing_strike").sum()),  # 被本塁打数
                    CStr=('description', lambda x: (x == "called_strike").sum()),  # 被本塁打数
                    Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
                )
                plate_discipline["swing%"] = plate_discipline["Swing"]/plate_discipline["N"]
                plate_discipline["contact%"] = plate_discipline["Contact"]/plate_discipline["Swing"]
                plate_discipline["zone%"] = plate_discipline["Zone"]/plate_discipline["N"]
                plate_discipline["swstr%"] = plate_discipline["SwStr"]/plate_discipline["N"]
                plate_discipline["cstr%"] = plate_discipline["CStr"]/plate_discipline["N"]
                plate_discipline["whiff%"] = plate_discipline["SwStr"]/plate_discipline["Swing"]
                plate_discipline["csw%"] = (plate_discipline["SwStr"]+plate_discipline["CStr"])/plate_discipline["N"]
                plate_discipline["Swing%"] = my_round(plate_discipline["swing%"], 3)
                plate_discipline["Contact%"] = my_round(plate_discipline["contact%"], 3)
                plate_discipline["Zone%"] = my_round(plate_discipline["zone%"], 3)
                plate_discipline["SwStr%"] = my_round(plate_discipline["swstr%"], 3)
                plate_discipline["CStr%"] = my_round(plate_discipline["cstr%"], 3)
                plate_discipline["Whiff%"] = my_round(plate_discipline["whiff%"], 3)
                plate_discipline["CSW%"] = my_round(plate_discipline["csw%"], 3)

                o_plate_df = plate_df[plate_df["Zone"] == "Out"]
                o_disc = o_plate_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    O_N=("pitcher_name", "size"),
                    O_Swing=("swing", "sum"),
                    O_Contact=("contact", "sum"),
                )
                o_disc["o-swing%"] = o_disc["O_Swing"]/o_disc["O_N"]
                o_disc["o-contact%"] = o_disc["O_Contact"]/o_disc["O_N"]
                o_disc["O-Swing%"] = my_round(o_disc["o-swing%"], 3)
                o_disc["O-Contact%"] = my_round(o_disc["o-contact%"], 3)
                plate_discipline = pd.merge(plate_discipline, o_disc, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how="left")

                z_plate_df = plate_df[plate_df["Zone"] == "In"]
                z_disc = z_plate_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    Z_N=("pitcher_name", "size"),
                    Z_Swing=("swing", "sum"),
                    Z_Contact=("contact", "sum"),
                )
                z_disc["z-swing%"] = z_disc["Z_Swing"]/z_disc["Z_N"]
                z_disc["z-contact%"] = z_disc["Z_Contact"]/z_disc["Z_N"]
                z_disc["Z-Swing%"] = my_round(z_disc["z-swing%"], 3)
                z_disc["Z-Contact%"] = my_round(z_disc["z-contact%"], 3)
                plate_discipline = pd.merge(plate_discipline, z_disc, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how="left")

                f_plate_df = plate_df[plate_df["ab_pitch_number"] == 1]
                f_disc = f_plate_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    F_N=("pitcher_name", "size"),
                    F_Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
                )
                f_disc["f-strike%"] = f_disc["F_Zone"]/f_disc["F_N"]
                f_disc["F-Strike%"] = my_round(f_disc["f-strike%"], 3)
                plate_discipline = pd.merge(plate_discipline, f_disc, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how="left")

                t_plate_df = plate_df[plate_df["strikes"] == 2]
                t_disc = t_plate_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    T_N=("pitcher_name", "size"),
                    T_SO=('events', lambda x: (x == "strike_out").sum()),  # 被本塁打数
                )
                t_disc["putaway%"] = t_disc["T_SO"]/t_disc["T_N"]
                t_disc["PutAway%"] = my_round(t_disc["putaway%"], 3)
                plate_discipline = pd.merge(plate_discipline, t_disc, on=["game_year", "fld_league", "fld_team", "pitcher_name"], how="left")
                plate_discipline = plate_discipline.rename(columns={"game_year": "Season", "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player", "game_year": "Season"})
                pitcher_gl = pd.merge(pitcher_gl, plate_discipline, on=["Season", "League", "Team", "Player"], how="left")

                pt_list = ["FA", "FT", "SL", "CT", "CB", "CH", "SF", "SI", "SP", "XX"]
                for p in pt_list:
                    p_low = p.lower()
                    fa_df = plate_df[plate_df[p] == 1]
                    fa_v = fa_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        p_n=("pitcher_name", "size"),
                        v=('velocity', "mean")
                    )
                    fa_v = fa_v.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                                "game_year": "Season",
                                                "p_n": p_low, "v": p + "_v"})

                    fa_pv_df = merged_data[merged_data[p] == 1]
                    fa_pv = fa_pv_df.groupby(["game_year", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        w=('pitcher_pitch_value', "sum")
                    )
                    fa_pv = fa_pv.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                                "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                                "game_year": "Season",
                                                "w": p + "_w"})

                    pitcher_gl = pd.merge(pitcher_gl, fa_v, on=["Season", "League", "Team", "Player"], how="left")
                    pitcher_gl = pd.merge(pitcher_gl, fa_pv, on=["Season", "League", "Team", "Player"], how="left")
                    pitcher_gl[f"{p}%"] = my_round(pitcher_gl[p_low]/pitcher_gl["N"], 3)
                    pitcher_gl[f"{p}v"] = my_round(pitcher_gl[p + "_v"], 1)
                    pitcher_gl[f"w{p}"] = my_round(pitcher_gl[p + "_w"], 1)
                    pitcher_gl[f"w{p}/C"] = my_round(100*pitcher_gl[f"w{p}"]/pitcher_gl[p_low], 1)

                pitcher_gl["Team"] = pitcher_gl["Team"].replace(team_en_dict)

                st.markdown("### Dashboard")
                pitch_cols = ["Season", "Team", "G", "GS", "IP", "K/9", "BB/9", "HR/9", "BABIP", "LOB%", "GB%", "HR/FB", "RA", "FIP"]
                pitch_0 = pitcher_gl[pitch_cols]
                df_style = pitch_0.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'LOB%': '{:.1%}',
                    'RA': '{:.2f}',
                    'FIP': '{:.2f}',
                    'R-F': '{:.2f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)
            
                st.markdown("### Standard")
                pitch_cols = ["Season", "Team", "G", "GS", "IP", "CG", "ShO", "TBF", "H", "R", "HR", "BB", "IBB", "HBP", "WP", "BK", "SO"]
                pitch_1 = pitcher_gl[pitch_cols]
                df_style = pitch_1.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1f}',
                    'BB%': '{:.1f}',
                    'K-BB%': '{:.1f}',
                    'HR%': '{:.2f}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'LOB%': '{:.2f}',
                    'RA': '{:.2f}',
                    'FIP': '{:.2f}',
                    'R-F': '{:.2f}',
                    'GB%': '{:.2f}',
                    'FB%': '{:.2f}',
                    'LD%': '{:.2f}',
                    'IFFB%': '{:.2f}',
                    'HR/FB': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)
            
                st.markdown("### Advanced")
                pitch_cols = ["Season", "Team", "K/9", "BB/9", "K/BB", "HR/9", "K%", "BB%", "K-BB%", "AVG", "BABIP", "LOB%", "RA-", "FIP-", "RA", "FIP", "R-F"]
                pitch_2 = pitcher_gl[pitch_cols]
                df_style = pitch_2.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'LOB%': '{:.1%}',
                    'FIP-': '{:.0f}',
                    'FIP': '{:.2f}',
                    'RA-': '{:.0f}',
                    'RA': '{:.2f}',
                    'R-F': '{:.2f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Batted Ball")
                pitch_cols = ["Season", "Team", "BABIP", "GB/FB", "LD%", "GB%", "FB%", "IFFB%", "HR/FB", "Pull%", "Cent%", "Oppo%"]
                pitch_3 = pitcher_gl[pitch_cols]
                df_style = pitch_3.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'LOB%': '{:.1%}',
                    'FIP-': '{:.0f}',
                    'FIP': '{:.2f}',
                    'RA-': '{:.0f}',
                    'RA': '{:.2f}',
                    'R-F': '{:.2f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'Pull%': '{:.1%}',
                    'Cent%': '{:.1%}',
                    'Oppo%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'GB/FB': '{:.2f}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Plate Discipline")
                pitch_cols = ["Season", "Team", "O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", 
                                    "Zone%", "F-Strike%", "Whiff%", "PutAway%", "SwStr%", "CStr%", "CSW%"]
                pitch_4 = pitcher_gl[pitch_cols]
                df_style = pitch_4.style.format({
                    'O-Swing%': '{:.1%}',
                    'Z-Swing%': '{:.1%}',
                    'Swing%': '{:.1%}',
                    'O-Contact%': '{:.1%}',
                    'Z-Contact%': '{:.1%}',
                    'Contact%': '{:.1%}',
                    'Zone%': '{:.1%}',
                    'F-Strike%': '{:.1%}',
                    'Whiff%': '{:.1%}',
                    'PutAway%': '{:.1%}',
                    'SwStr%': '{:.1%}',
                    'CStr%': '{:.1%}',
                    'CSW%': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Pitch Type")
                pitch_cols = ["Season", "Team", "FA%", "FAv", "FT%", "FTv", "SL%", "SLv", "CT%", "CTv", "CB%", "CBv", 
                                    "CH%", "CHv", "SF%", "SFv", "SI%", "SIv", "SP%", "SPv", "XX%", "XXv"]
                pitch_5 = pitcher_gl[pitch_cols]
                df_style = pitch_5.style.format({
                    'FA%': '{:.1%}',
                    'FT%': '{:.1%}',
                    'SL%': '{:.1%}',
                    'CT%': '{:.1%}',
                    'CB%': '{:.1%}',
                    'CH%': '{:.1%}',
                    'SF%': '{:.1%}',
                    'SI%': '{:.1%}',
                    'SP%': '{:.1%}',
                    'XX%': '{:.1%}',
                    'FAv': '{:.1f}',
                    'FTv': '{:.1f}',
                    'SLv': '{:.1f}',
                    'CTv': '{:.1f}',
                    'CBv': '{:.1f}',
                    'CHv': '{:.1f}',
                    'SFv': '{:.1f}',
                    'SIv': '{:.1f}',
                    'SPv': '{:.1f}',
                    'XXv': '{:.1f}'
                })
                st.dataframe(df_style, use_container_width=True)

                st.markdown("### Pitch Value")
                pitch_cols = ["Season", "Team", "wFA", "wFT", "wSL", "wCT", "wCB", "wCH", "wSF", "wSI", "wSP", 
                                    "wFA/C", "wFT/C", "wSL/C", "wCT/C", "wCB/C", "wCH/C", "wSF/C", "wSI/C", "wSP/C"]
                pitch_6 = pitcher_gl[pitch_cols]
                df_style = pitch_6.style.format({
                    'wFA': '{:.1f}',
                    'wFT': '{:.1f}',
                    'wSL': '{:.1f}',
                    'wCT': '{:.1f}',
                    'wCB': '{:.1f}',
                    'wCH': '{:.1f}',
                    'wSF': '{:.1f}',
                    'wSI': '{:.1f}',
                    'wSP': '{:.1f}',
                    'wFA/C': '{:.1f}',
                    'wFT/C': '{:.1f}',
                    'wSL/C': '{:.1f}',
                    'wCT/C': '{:.1f}',
                    'wCB/C': '{:.1f}',
                    'wCH/C': '{:.1f}',
                    'wSF/C': '{:.1f}',
                    'wSI/C': '{:.1f}',
                    'wSP/C': '{:.1f}',
                })
                st.dataframe(df_style, use_container_width=True)

        elif data_type == "Game Logs":
            cols = st.columns(4)
            with cols[0]:
                year_select = st.selectbox(
                    "Season",
                    year_list,
                    index=0
                )
            data = data[data["game_year"] == year_select]
            PA_df = PA_df[PA_df["game_year"] == year_select]
            events_df = events_df[events_df["game_year"] == year_select]
            league_bat_data = league_bat_data[league_bat_data["Season"] == year_select]
            league_fip_data = league_fip_data[league_fip_data["game_year"] == year_select]
            sb_df = sb_df[sb_df["game_year"] == year_select]
            
            if stats_type == "Batting":
                PA_df = PA_df[PA_df["batter_id"] == player_id]
                plate_df = plate_df[plate_df["batter_id"] == player_id]
                merged_data = merged_data[merged_data["batter_id"] == player_id]

                game_pos = PA_df.groupby(["game_date", "bat_league", "bat_team", "batter_name"]).head(1)[["game_date", "bat_league", "bat_team", "batter_name", "order", "batter_pos"]]
                batter_gl = PA_df.groupby(["game_date", "bat_league", "bat_team", "home_team", "fld_team", "away_team", "batter_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    S=("Start", "max"),
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum())
                )
                batter_gl = pd.merge(batter_gl, game_pos, on=["game_date", "bat_league", "bat_team", "batter_name"], how="left")
                batter_gl = batter_gl.rename(columns={"game_date": "Date","batter_pos": "Pos", "order": "BO", "bat_league": "League", "bat_team": "Team", "fld_team": "Opp", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                batter_gl["AB"] = batter_gl["PA"] - (batter_gl["BB"] + batter_gl["HBP"] + batter_gl["SH"] + batter_gl["SF"] + batter_gl["obstruction"] + batter_gl["interference"])
                batter_gl["H"] = batter_gl["1B"] + batter_gl["2B"] + batter_gl["3B"] + batter_gl["HR"]
                batter_gl["avg"] = batter_gl["H"]/batter_gl["AB"]
                batter_gl["AVG"] = my_round(batter_gl["avg"], 3)
                batter_gl["obp"] = (batter_gl["H"] + batter_gl["BB"] + batter_gl["HBP"])/(batter_gl["AB"] + batter_gl["BB"] + batter_gl["HBP"] + batter_gl["SF"])
                batter_gl["OBP"] = my_round(batter_gl["obp"], 3)
                batter_gl["slg"] = (batter_gl["1B"] + 2*batter_gl["2B"] + 3*batter_gl["3B"] + 4*batter_gl["HR"])/batter_gl["AB"]
                batter_gl["SLG"] = my_round(batter_gl["slg"], 3)
                batter_gl["ops"] = batter_gl["obp"] + batter_gl["slg"]
                batter_gl["OPS"] = my_round(batter_gl["ops"], 3)
                batter_gl["iso"] = batter_gl["slg"] - batter_gl["avg"]
                batter_gl["ISO"] = my_round(batter_gl["iso"], 3)
                batter_gl["babip"] = (batter_gl["H"] - batter_gl["HR"])/(batter_gl["AB"] - batter_gl["SO"] - batter_gl["HR"] + batter_gl["SF"])
                batter_gl["BABIP"] = my_round(batter_gl["babip"], 3)
                batter_gl["k%"] = batter_gl["SO"]/batter_gl["PA"]
                batter_gl["bb%"] = batter_gl["BB"]/batter_gl["PA"]
                batter_gl["K%"] = my_round(batter_gl["k%"], 3)
                batter_gl["BB%"] = my_round(batter_gl["bb%"], 3)
                batter_gl["BB/K"] = my_round(batter_gl["BB"]/batter_gl["SO"], 2)
                batter_gl["woba"] = wOBA_scale * (bb_value * (batter_gl["BB"] - batter_gl["IBB"]) + hbp_value * batter_gl["HBP"] + single_value * batter_gl["1B"] + double_value * batter_gl["2B"] + triple_value * batter_gl["3B"] + hr_value * batter_gl["HR"])/(batter_gl["AB"] + batter_gl["BB"] - batter_gl["IBB"] + batter_gl["HBP"] + batter_gl["SF"])
                batter_gl["wOBA"] = my_round(batter_gl["woba"], 3)
                batter_gl = pd.merge(batter_gl, league_wrc_mean, on=["League"], how="left")
                batter_gl["wraa"] = ((batter_gl["woba"] - batter_gl["woba_league"])/wOBA_scale) * batter_gl["PA"]
                batter_gl["wrar"] = ((batter_gl["woba"] - batter_gl["woba_league"]*0.88)/wOBA_scale) * batter_gl["PA"]
                batter_gl["wRAA"] = my_round(batter_gl["wraa"], 1)
                batter_gl["wrc"] = (((batter_gl["woba"] - batter_gl["woba_league"])/wOBA_scale) + batter_gl["R_league"]/batter_gl["PA_league"])*batter_gl["PA"]
                batter_gl["wRC"] = my_round(batter_gl["wrc"])
                batter_gl = pd.merge(batter_gl, rpw_df, on=["League"], how="left")
                batter_gl = pd.merge(batter_gl, pf[["Team", "bpf/100"]], on="Team", how="left")
                batter_gl["wrc_pf"] = batter_gl["wrc"] + (1-batter_gl["bpf/100"])*batter_gl["PA"]*(batter_gl["R_league"]/batter_gl["PA_league"]/batter_gl["bpf/100"])
                batter_gl["wrc+"] = 100*(batter_gl["wrc_pf"]/batter_gl["PA"])/(batter_gl["R_league"]/batter_gl["PA_league"])
                batter_gl["wrar_pf"] = ((batter_gl["woba"] - batter_gl["woba_league"]*batter_gl["bpf/100"]*0.88)/wOBA_scale) * batter_gl["PA"]
                batter_gl["batwar"] = batter_gl["wrar_pf"]/batter_gl["RPW"]
                batter_gl["wRC+"] = my_round(batter_gl["wrc+"])
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = sb_df[(sb_df["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["game_date", "bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["game_date", "bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["game_date", "bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["game_date", "bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["game_date", "bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["game_date", "bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["game_date", "bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "game_date": "Date"})

                batter_gl['batter_name_no_space'] = batter_gl['Player'].str.replace(" ", "")
                batter_gl = partial_match_merge_2(batter_gl, runner_df, 'batter_name_no_space', 'runner_name', ['Date', 'Team'])
                batter_gl["SB"] = batter_gl["SB"].fillna(0).astype(int)
                batter_gl["CS"] = batter_gl["CS"].fillna(0).astype(int)
                batter_gl.loc[batter_gl['home_team'] == batter_gl['Opp'], 'Opp'] = '@' + batter_gl['Opp']
                batter_gl["Date"] = batter_gl["Date"].dt.strftime("%m/%d")
                batter_gl["Pos"] = batter_gl["Pos"].replace(pos_ja_dict)
                batter_gl["BO"] = batter_gl["BO"].astype(int)
                batter_gl['Start'] = batter_gl['S'].apply(lambda x: 'S' if x == 1 else np.nan)

                batter_gl = batter_gl.sort_values("Date", ascending=False).reset_index(drop=True)
                batter_gl = batter_gl[[
                    "Date", "Team", "Opp", "Start", "BO", "Pos", "PA", "H", "2B", "3B", "HR", "SB", "CS", "BB%", "K%", 
                    "ISO", "BABIP", "AVG", "OBP", "SLG", "OPS", "wOBA", "wRC+"]]
                df_style = batter_gl.style.format({
                    'K%': '{:.0f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'BB/K': '{:.2f}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'wRC': '{:.0f}',
                    'wRAA': '{:.1f}',
                    'wRC+': '{:.0f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)
            elif stats_type == "Pitching":
                events_df = events_df[events_df["pitcher_id"] == player_id]
                plate_df = plate_df[plate_df["pitcher_id"] == player_id]
                merged_data = merged_data[merged_data["pitcher_id"] == player_id]
                PA_df = PA_df[PA_df["pitcher_id"] == player_id]

                player_outs_sum = events_df.groupby(["game_date", "fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["game_date", "fld_league", "fld_team", "pitcher_name"] + ['IP']

                pitcher_gl = events_df.groupby(["game_date", "game_id", "fld_league", "fld_team", "home_team", "bat_team", "away_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    TBF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum())
                )
                if league_type == "1軍":
                    player_pb_data = events_df.groupby(["game_date", "fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        GB = ("GB", "sum"),
                        FB = ("FB", "sum"),
                        IFFB = ("IFFB", "sum"),
                        OFFB = ("OFFB", "sum"),
                        LD = ("LD", "sum"),
                        Pull = ("Pull", "sum"),
                        Cent = ("Center", "sum"),
                        Oppo = ("Opposite", "sum")
                    )
                    pitcher_gl = pd.merge(pitcher_gl, player_pb_data, on=["game_date", "fld_league", "fld_team", "pitcher_name"], how="left")

                pitcher_gl = pd.merge(pitcher_gl, player_ip_df, on=["game_date", "fld_league", "fld_team", "pitcher_name"], how='left')
                pitcher_gl["inning"] = pitcher_gl["O"]/3
                pitcher_gl["AB"] = pitcher_gl["TBF"] - (pitcher_gl["BB"] + pitcher_gl["HBP"] + pitcher_gl["SH"] + pitcher_gl["SF"] + pitcher_gl["obstruction"] + pitcher_gl["interference"])
                pitcher_gl["H"] = pitcher_gl["single"] + pitcher_gl["double"] + pitcher_gl["triple"] + pitcher_gl["HR"]
                pitcher_gl['k/9'] = pitcher_gl['SO'] * 9 / pitcher_gl['inning']
                pitcher_gl['bb/9'] = pitcher_gl['BB'] * 9 / pitcher_gl['inning']
                pitcher_gl['K/9'] = my_round(pitcher_gl['k/9'], 2)
                pitcher_gl['BB/9'] = my_round(pitcher_gl['bb/9'], 2)
                pitcher_gl['k%'] = pitcher_gl["SO"]/pitcher_gl["TBF"]
                pitcher_gl['bb%'] = pitcher_gl["BB"]/pitcher_gl["TBF"]
                pitcher_gl['hr%'] = pitcher_gl["HR"]/pitcher_gl["TBF"]
                pitcher_gl["K%"] = my_round(pitcher_gl["k%"], 3)
                pitcher_gl["BB%"] = my_round(pitcher_gl["bb%"], 3)
                pitcher_gl["HR%"] = my_round(pitcher_gl["hr%"], 3)
                pitcher_gl["k-bb%"] = pitcher_gl["k%"] - pitcher_gl["bb%"]
                pitcher_gl["K-BB%"] = my_round(pitcher_gl["k-bb%"], 3)
                pitcher_gl['K/BB'] = my_round(pitcher_gl['SO'] / pitcher_gl['BB'], 2)
                pitcher_gl['HR/9'] = my_round(pitcher_gl['HR'] * 9 / pitcher_gl['inning'], 2)
                pitcher_gl['ra'] = pitcher_gl['R'] * 9 / pitcher_gl['inning']
                pitcher_gl['RA'] = my_round(pitcher_gl['ra'], 2)
                pitcher_gl = pd.merge(pitcher_gl, league_fip_data, on="fld_league", how="left")
                pitcher_gl['fip'] = (13*pitcher_gl["HR"] + 3*(pitcher_gl["BB"] - pitcher_gl["IBB"] + pitcher_gl["HBP"]) - 2*pitcher_gl["SO"])/pitcher_gl["inning"] + pitcher_gl["cFIP"]
                pitcher_gl['FIP'] = my_round(pitcher_gl['fip'], 2)
                pitcher_gl["r-f"] = pitcher_gl["ra"] - pitcher_gl["fip"]
                pitcher_gl["R-F"] = my_round(pitcher_gl["r-f"], 2)
                pitcher_gl["avg"] = pitcher_gl["H"]/pitcher_gl["AB"]
                pitcher_gl["AVG"] = my_round(pitcher_gl["avg"], 3)
                pitcher_gl["babip"] = (pitcher_gl["H"] - pitcher_gl["HR"])/(pitcher_gl["AB"] - pitcher_gl["SO"] - pitcher_gl["HR"] + pitcher_gl["SF"])
                pitcher_gl["BABIP"] = my_round(pitcher_gl["babip"], 3)
                starter_games = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                pitcher_gl = pd.merge(pitcher_gl, st_games, on=["fld_league", "fld_team", "pitcher_name", "game_id"], how='left')
                pitcher_gl['GS'] = pitcher_gl['GS'].fillna(0).astype(int)
                pitcher_gl["lob%"] = (pitcher_gl["H"] + pitcher_gl["BB"] + pitcher_gl["HBP"] - pitcher_gl["R"])/(pitcher_gl["H"] + pitcher_gl["BB"] + pitcher_gl["HBP"] - 1.4+pitcher_gl["HR"])
                pitcher_gl["LOB%"] = my_round(pitcher_gl["lob%"], 3)
                if league_type == "1軍":
                    pitcher_gl["gb%"] = pitcher_gl["GB"]/(pitcher_gl["GB"]+pitcher_gl["FB"]+pitcher_gl["LD"])
                    pitcher_gl["hr/fb"] = pitcher_gl["HR"] / pitcher_gl["FB"]
                    pitcher_gl["GB%"] = my_round(pitcher_gl["gb%"], 3)
                    pitcher_gl["HR/FB"] = my_round(pitcher_gl["hr/fb"], 3)
                elif league_type == "2軍":
                    pitcher_gl["GB%"] = np.nan
                    pitcher_gl["HR/FB"] = np.nan

                pitcher_gl = pitcher_gl.rename(columns={"game_date": "Date", "fld_team": "Team", "bat_team": "Opp"})
                pitcher_gl.loc[pitcher_gl['home_team'] == pitcher_gl['Opp'], 'Opp'] = '@' + pitcher_gl['Opp']
                pitcher_gl["Date"] = pitcher_gl["Date"].dt.strftime("%m/%d")
                pitcher_gl = pitcher_gl.sort_values("Date", ascending=False).reset_index(drop=True)
                pitcher_gl = pitcher_gl[[
                    "Date", "Team", "Opp", "GS", "IP", "TBF", "H", "R", "HR", "BB", "SO",
                    "K/9", "BB/9", "HR/9", "BABIP", "LOB%", "GB%", "HR/FB", "FIP"]]
                df_style = pitcher_gl.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'LOB%': '{:.1%}',
                    'FIP-': '{:.0f}',
                    'FIP': '{:.2f}',
                    'RA-': '{:.0f}',
                    'RA': '{:.2f}',
                    'R-F': '{:.2f}',
                    'GB%': '{:.1%}',
                    'FB%': '{:.1%}',
                    'LD%': '{:.1%}',
                    'Pull%': '{:.1%}',
                    'Cent%': '{:.1%}',
                    'Oppo%': '{:.1%}',
                    'IFFB%': '{:.1%}',
                    'GB/FB': '{:.2f}',
                    'HR/FB': '{:.1%}',
                })
                st.dataframe(df_style, use_container_width=True)

        elif data_type == "Charts":
            if stats_type == "Batting":
                PA_df = PA_df[PA_df["batter_id"] == player_id]
                plate_df = plate_df[plate_df["batter_id"] == player_id]
                merged_data = merged_data[merged_data["batter_id"] == player_id]

                cols = st.columns(6)
                with cols[0]:
                    rolling_pa = st.selectbox(
                        "PA",
                        [50, 100, 150, 200],
                        index=1
                    )

                PA_df["woba_denom"] = PA_df['events'].apply(lambda x: 0 if x in ["sac_bunt", "bunt_error", "bunt_fielders_choice", "obstruction", "intentional_walk", "interference"] else 1)
                woba_rolling_df = PA_df[["events", "woba_denom"]].reset_index(drop=True)
                woba_rolling_df["woba_value"] = woba_rolling_df['events'].apply(lambda x: single_value if x == "single" 
                                                                                else double_value if x == "double" 
                                                                                else triple_value if x == "triple" 
                                                                                else hr_value if x == "home_run" 
                                                                                else bb_value if x == "walk" 
                                                                                else hbp_value if x == "hit_by_pitch" 
                                                                                else 0)
                woba_rolling_df['at_bat_number'] = range(1, len(woba_rolling_df) + 1)
                woba_rolling_df['rolling_value'] = woba_rolling_df['woba_value'].rolling(window=rolling_pa).sum()
                woba_rolling_df['rolling_denom'] = woba_rolling_df['woba_denom'].rolling(window=rolling_pa).sum()
                woba_rolling_df["rolling_wOBA"] = my_round(wOBA_scale*woba_rolling_df["rolling_value"]/woba_rolling_df["rolling_denom"], 3)
                if 0.2 < woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].min():
                    y_min = 0.180
                else:
                    y_min = woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].min() - 0.2
                if 0.5 > woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].max():
                    y_max = 0.520
                else:
                    y_max = woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].max() + 0.2
                # Plotlyの折れ線グラフを作成
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=woba_rolling_df['at_bat_number'], 
                    y=woba_rolling_df['rolling_wOBA'], 
                    mode='lines',
                    name='wOBA'))
                fig.update_layout(
                    title=f'{name} {rolling_pa} PAs Rolling wOBA',
                    xaxis_title='PA',
                    yaxis_title='wOBA',
                    xaxis=dict(range=[rolling_pa, len(woba_rolling_df)]),
                    yaxis=dict(range=[y_min, y_max], tickformat='.3f'),
                    legend=dict(x=0, y=1, traceorder="normal", bgcolor="rgba(0,0,0,0)", bordercolor="Black", borderwidth=1)
                )

                # リーグ平均wOBAの直線を追加
                fig.add_shape(
                    type="line",
                    x0=rolling_pa,
                    y0=mean_woba*wOBA_scale,
                    x1=len(woba_rolling_df),
                    y1=mean_woba*wOBA_scale,
                    line=dict(color='gray', dash='dash'),
                    name='Lg. Avg'
                )

                # リーグ平均wOBAの注釈を追加
                fig.add_annotation(
                    x=len(woba_rolling_df)-10,
                    y=mean_woba*wOBA_scale,
                    text=f'Lg. Avg: {mean_woba*wOBA_scale:.3f}',
                    showarrow=False,
                    yshift=10,
                    font=dict(color='gray')
                )

                # Streamlitで表示
                st.plotly_chart(fig, use_container_width=True)

                pitch_t = plate_df["pitch_type"].value_counts()
                pitch_arsenal = plate_df["pitch_name"].value_counts()
                # 'FF'のピッチのみをフィルター
                p_t_list = list(pitch_t.index)
                p_a_list = list(pitch_arsenal.index)


                graph_lits = ["Pitch %", "Average Pitch Velocity", "Max Pitch Velocity", 
                              "Swing %", "Swing & Miss %",
                              "In Zone %", "Out Zone %", "In Zone Swing %", "Chase %", 
                              "In Zone Swing & Miss %", "Chase Miss %", "Base on Balls %", 
                              "K %", "Hits", "Singles", "Doubles", "Triples", "home Runs", "Pitches",
                              "GB %", "LD %", "FB %", "IFFB %"]
                cols_2 = st.columns([1, 5])
                with cols_2[0]:
                    graph_type = st.selectbox(
                        "",
                        graph_lits,
                        index=0
                    )
                with cols_2[1]:
                    cols = st.columns(6)
                    with cols[0]:
                        pitch_group = st.selectbox(
                            "",
                            ["Pitches", "Pitch Group", "All Pitches"],
                            index=1
                        )
                        
                    with cols[1]:
                        date_split = st.selectbox(
                            "",
                            ["Season", "Month", "Game"],
                            index=1
                        )

                    with cols[2]:
                        throw_split = st.selectbox(
                            "",
                            ["Handedness", "Right", "Left"],
                            index=0
                        )
                    with cols[3]:
                        count_split = st.selectbox(
                            "",
                            ["Count", "0-0", "0-1", "0-2", "1-0", "1-1", "1-2", "2-0", "2-1", "2-2", "3-0", "3-1", "3-2", 
                            "Batter Ahead", "Batter Behind", "2 Strikes", "3 Balls"],
                            index=0
                        )

                    pt_split_list = ["All Pitches"]
                    if pitch_group == "Pitches":
                        pt_split_list += p_a_list
                    elif pitch_group == "Pitch Group":
                        pt_split_list += ["Fastball", "Offspeed", "Breaking"]

                    with cols[4]:
                        pitch_type_split = st.selectbox(
                            "",
                            pt_split_list,
                            index=0
                        )
                    with cols[5]:
                        season_split = st.selectbox(
                            "",
                            ["All Seasons"] + year_list,
                            index=0
                        )
                    
                pitch_graph_df = plate_df

                if count_split == "Count":
                    pass
                elif count_split == "Batter Ahead":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] < pitch_graph_df["balls"]]
                elif count_split == "Batter Behind":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] > pitch_graph_df["balls"]]
                elif count_split == "2 Strikes":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] == 2]
                elif count_split == "3 Balls":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["balls"] == 3]
                else:
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["B-S"] == count_split]
                
                if throw_split == "Right":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["p_throw"] == "右"]
                elif throw_split == "Left":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["p_throw"] == "左"]
                
                if date_split == "Season":
                    group_l = ["game_year"]
                    p_c_list = ["Season"]
                elif date_split == "Month":
                    group_l = ["Year/Month"]
                    p_c_list = ["Year/Month"]
                elif date_split == "Game":
                    group_l = ["game_date"]
                    p_c_list = ["Date"]
                if pitch_group == "Pitches":
                    group_l += ["pitch_name"]
                elif pitch_group == "Pitch Group":
                    group_l += ["pitch_group"]
                
                events_graph_df = pitch_graph_df.dropna(subset="events")
                pa_graph_df = events_graph_df[(events_graph_df["events"] != "pickoff_1b")&(events_graph_df["events"] != "pickoff_2b")&(events_graph_df["events"] != "pickoff_catcher")&(events_graph_df["events"] != "caught_stealing")&(events_graph_df["events"] != "stolen_base")&(events_graph_df["events"] != "wild_pitch")&(events_graph_df["events"] != "balk")&(events_graph_df["events"] != "passed_ball")&(events_graph_df["events"] != "caught_stealing")]
                n_graph_df = pitch_graph_df.groupby(group_l[0], as_index=False).agg(
                    N=(group_l[-1], "size")
                )
                
                p_graph_df = pitch_graph_df.groupby(group_l, as_index=False).agg(
                    P_N=(group_l[-1], "size"),
                    avg_velo=("velocity", "mean"),
                    Max_Velocity=("velocity", "max"),
                    swing=("swing", "sum"),
                    swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, n_graph_df, on=group_l[0], how="left")
                p_graph_df["p%"] = 100*p_graph_df["P_N"]/p_graph_df["N"]
                p_graph_df["%"] = my_round(p_graph_df["p%"], 1)
                p_graph_df["AVG Velocity"] = my_round(p_graph_df["avg_velo"], 1)

                p_pa_graph_df = events_graph_df.groupby(group_l, as_index=False).agg(
                    R=('runs_scored', 'sum'), 
                    PA=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum())
                )
                if league_type == "1軍":
                    p_bb_df = events_graph_df.groupby(group_l, as_index=False).agg(
                        GB = ("GB", "sum"),
                        FB = ("FB", "sum"),
                        IFFB = ("IFFB", "sum"),
                        OFFB = ("OFFB", "sum"),
                        LD = ("LD", "sum"),
                        Pull = ("Pull", "sum"),
                        Cent = ("Center", "sum"),
                        Oppo = ("Opposite", "sum")
                    )
                    p_pa_graph_df = pd.merge(p_pa_graph_df, p_bb_df, on=group_l, how="left")
                p_pa_graph_df["inning"] = p_pa_graph_df["O"]/3
                p_pa_graph_df["AB"] = p_pa_graph_df["PA"] - (p_pa_graph_df["BB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SH"] + p_pa_graph_df["SF"] + p_pa_graph_df["obstruction"] + p_pa_graph_df["interference"])
                p_pa_graph_df["H"] = p_pa_graph_df["single"] + p_pa_graph_df["double"] + p_pa_graph_df["triple"] + p_pa_graph_df["HR"]
                p_pa_graph_df['k/9'] = p_pa_graph_df['SO'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['bb/9'] = p_pa_graph_df['BB'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['K/9'] = my_round(p_pa_graph_df['k/9'], 2)
                p_pa_graph_df['BB/9'] = my_round(p_pa_graph_df['bb/9'], 2)
                p_pa_graph_df['k%'] = 100*p_pa_graph_df["SO"]/p_pa_graph_df["PA"]
                p_pa_graph_df['bb%'] = 100*p_pa_graph_df["BB"]/p_pa_graph_df["PA"]
                p_pa_graph_df['hr%'] = p_pa_graph_df["HR"]/p_pa_graph_df["PA"]
                p_pa_graph_df["K %"] = my_round(p_pa_graph_df["k%"], 1)
                p_pa_graph_df["BB %"] = my_round(p_pa_graph_df["bb%"], 1)
                p_pa_graph_df['ra'] = p_pa_graph_df['R'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['RA'] = my_round(p_pa_graph_df['ra'], 2)
                p_pa_graph_df["avg"] = p_pa_graph_df["H"]/p_pa_graph_df["AB"]
                p_pa_graph_df["BA"] = my_round(p_pa_graph_df["avg"], 3)
                p_pa_graph_df = p_pa_graph_df.rename(columns={"single": "1B", "double": "2B", "triple": "3B"})
                p_pa_graph_df["obp"] = (p_pa_graph_df["H"] + p_pa_graph_df["BB"] + p_pa_graph_df["HBP"])/(p_pa_graph_df["AB"] + p_pa_graph_df["BB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SF"])
                p_pa_graph_df["OBP"] = my_round(p_pa_graph_df["obp"], 3)
                p_pa_graph_df["slg"] = (p_pa_graph_df["1B"] + 2*p_pa_graph_df["2B"] + 3*p_pa_graph_df["3B"] + 4*p_pa_graph_df["HR"])/p_pa_graph_df["AB"]
                p_pa_graph_df["SLG"] = my_round(p_pa_graph_df["slg"], 3)
                p_pa_graph_df["woba"] = wOBA_scale * (bb_value * (p_pa_graph_df["BB"] - p_pa_graph_df["IBB"]) + hbp_value * p_pa_graph_df["HBP"] + single_value * p_pa_graph_df["1B"] + double_value * p_pa_graph_df["2B"] + triple_value * p_pa_graph_df["3B"] + hr_value * p_pa_graph_df["HR"])/(p_pa_graph_df["AB"] + p_pa_graph_df["BB"] - p_pa_graph_df["IBB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SF"])
                p_pa_graph_df["wOBA"] = my_round(p_pa_graph_df["woba"], 3)
                if league_type == "1軍":
                    p_pa_graph_df["gb/fb"] = p_pa_graph_df["GB"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["gb%"] = 100*p_pa_graph_df["GB"]/(p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["fb%"] = 100*p_pa_graph_df["FB"]/(p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["ld%"] = 100*p_pa_graph_df["LD"] / (p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["iffb%"] = 100*p_pa_graph_df["IFFB"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["hr/fb"] = 100*p_pa_graph_df["HR"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["GB/FB"] = my_round(p_pa_graph_df["gb/fb"], 2)
                    p_pa_graph_df["GB %"] = my_round(p_pa_graph_df["gb%"], 1)
                    p_pa_graph_df["FB %"] = my_round(p_pa_graph_df["fb%"], 1)
                    p_pa_graph_df["LD %"] = my_round(p_pa_graph_df["ld%"], 1)
                    p_pa_graph_df["IFFB %"] = my_round(p_pa_graph_df["iffb%"], 1)
                    p_pa_graph_df["HR/FB"] = my_round(p_pa_graph_df["hr/fb"], 1)
                    p_pa_graph_df["pull%"] = 100*p_pa_graph_df["Pull"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["cent%"] = 100*p_pa_graph_df["Cent"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["oppo%"] = 100*p_pa_graph_df["Oppo"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["Pull%"] = my_round(p_pa_graph_df["pull%"], 1)
                    p_pa_graph_df["Cent%"] = my_round(p_pa_graph_df["cent%"], 1)
                    p_pa_graph_df["Oppo%"] = my_round(p_pa_graph_df["oppo%"], 1)
                if league_type == "2軍":
                    p_pa_graph_df["GB/FB"] = np.nan
                    p_pa_graph_df["GB%"] = np.nan
                    p_pa_graph_df["FB%"] = np.nan
                    p_pa_graph_df["LD%"] = np.nan
                    p_pa_graph_df["IFFB%"] = np.nan
                    p_pa_graph_df["HR/FB"] = np.nan
                    p_pa_graph_df["Pull%"] = np.nan
                    p_pa_graph_df["Cent%"] = np.nan
                    p_pa_graph_df["Oppo%"] = np.nan

                p_graph_df = pd.merge(p_graph_df, p_pa_graph_df, on=group_l, how="left")

                z_pitch_df = pitch_graph_df[pitch_graph_df["Zone"] == "In"]
                z_bb_df = z_pitch_df.groupby(group_l, as_index=False).agg(
                    Z_N=(group_l[-1], "size"),
                    Z_swing=("swing", "sum"),
                    Z_swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, z_bb_df, on=group_l, how="left")

                o_pitch_df = pitch_graph_df[pitch_graph_df["Zone"] == "Out"]
                o_bb_df = o_pitch_df.groupby(group_l, as_index=False).agg(
                    O_N=(group_l[-1], "size"),
                    O_swing=("swing", "sum"),
                    O_swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, o_bb_df, on=group_l, how="left")
                p_graph_df["Swing %"] = 100*p_graph_df["swing"]/p_graph_df["N"]
                p_graph_df["Swing & Miss %"] = 100*p_graph_df["swstr"]/p_graph_df["swing"]
                p_graph_df["In Zone %"] = 100*p_graph_df["Z_N"]/p_graph_df["N"]
                p_graph_df["Out Zone %"] = 100*p_graph_df["O_N"]/p_graph_df["N"]
                p_graph_df["In Zone Swing %"] = 100*p_graph_df["Z_swing"]/p_graph_df["Z_N"]
                p_graph_df["Chase %"] = 100*p_graph_df["O_swing"]/p_graph_df["O_N"]
                p_graph_df["In Zone Swing & Miss %"] = 100*p_graph_df["Z_swstr"]/p_graph_df["Z_swing"]
                p_graph_df["Chase Miss %"] = 100*p_graph_df["O_swstr"]/p_graph_df["O_swing"]

                if pitch_group == "All Pitches":
                    p_graph_df["pitch_name"] = "All Pitches"
                p_graph_df = p_graph_df.rename(columns={"game_year": "Season", "pitch_name": "Pitch Type", "pitch_group": "Pitch Type", "game_date": "Date", "Max_Velocity": "Max Velocity", "P_N": "#"})
                if pitch_type_split != "All Pitches":
                    p_graph_df = p_graph_df[p_graph_df["Pitch Type"] == pitch_type_split]
                p_graph_df = p_graph_df.sort_values(p_c_list + ["%"], ascending=[True, False]).reset_index(drop=True)
                p_graph_cols = p_c_list + ["Pitch Type", "#", "%", "AVG Velocity", "Max Velocity", "PA", "AB", "H", "1B", "2B", "3B", "HR", "SO", "BB", "BA", "OBP", "SLG", "wOBA"]
                p_statistics = p_graph_df[p_graph_cols]
                p_statistics = p_statistics.sort_values(p_c_list + ["%"], ascending=False).reset_index(drop=True)
                if date_split == "Game":
                    p_statistics["Date"] = p_statistics["Date"].dt.strftime("%Y/%m/%d")
                df_style = p_statistics.style.format({
                    'AVG Velocity': '{:.1f}',
                    'Max Velocity': '{:.0f}',
                    'PA': '{:.0f}',
                    'AB': '{:.0f}',
                    'H': '{:.0f}',
                    '1B': '{:.0f}',
                    '2B': '{:.0f}',
                    '3B': '{:.0f}',
                    'HR': '{:.0f}',
                    'SO': '{:.0f}',
                    'BB': '{:.0f}',
                    '%': '{:.1f}',
                    'K %': '{:.1f}',
                    'BB %': '{:.1f}',
                    'BA': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'BA': '{:.3f}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'IFH%': '{:.1f}',
                    'GB %': '{:.1f}',
                    'FB %': '{:.1f}',
                    'LD %': '{:.1f}',
                    'Pull%': '{:.1f}',
                    'Cent%': '{:.1f}',
                    'Oppo%': '{:.1f}',
                    'IFFB %': '{:.1f}',
                    'GB/FB': '{:.2f}',
                    'HR/FB': '{:.1f}',
                })
                if graph_type == "Pitch %":
                    graph_y = "%"
                elif graph_type == "Average Pitch Velocity":
                    graph_y = "AVG Velocity"
                elif graph_type == "Max Pitch Velocity":
                    graph_y = "Max Velocity"
                elif graph_type == "Base on Balls %" :
                    graph_y = "BB %"
                elif graph_type == "Hits":
                    graph_y = "H"
                elif graph_type == "Singles":
                    graph_y = "1B"
                elif graph_type == "Doubles":
                    graph_y = "2B"
                elif graph_type == "Triples":
                    graph_y = "3B"
                elif graph_type == "Home Runs":
                    graph_y = "HR"
                elif graph_type == "Pitches":
                    graph_y = "#"
                else:
                    graph_y = graph_type

                if throw_split == "Right":
                    bat_str = "vs RHP "
                elif throw_split == "Left":
                    bat_str = "vs LHP "
                else:
                    bat_str = ""
                # Plotlyを使用して各球種の投球割合の推移を折れ線グラフで表示
                graph_title = f"{name} {graph_type} {bat_str}by {date_split}"
                fig = px.line(p_graph_df, x=p_c_list[0], y=graph_y, color='Pitch Type', 
                              title=graph_title,
                              color_discrete_map=color_dict_en,
                              markers=True)
                                
                if graph_type.endswith("%"):
                    fig.update_yaxes(range=[0, p_graph_df[graph_y].max() * 1.1])

                # Streamlitにプロットを表示
                st.plotly_chart(fig, use_container_width=True)


                st.header("Pitch Statistic")
                st.dataframe(df_style, use_container_width=True)


                st.header("Pitch Plot")

                cols = st.columns(5)
                hand_split_lits = ["All", "vsRHP", "vsLHP"]
                with cols[0]:
                    hand_split = st.selectbox(
                        "Throw",
                        hand_split_lits,
                        index=0
                    )
                pitch_split_list = ["All Pitchs", "Swing", "Take", "Swing & Miss", "Called Strike", "Base Hits", "Home Runs",
                                    "Ahead in count", "Behind in count", "Even count", "2 Strikes"]
                with cols[1]:
                    pitch_split = st.selectbox(
                        "Pitch Split",
                        pitch_split_list,
                        index=0
                    )
                zone_split_list = ["All Zone", "In Zone", "Out of Zone",
                                    "Heart", "Shadow", "Chase", "Waste"]
                with cols[2]:
                    zone_split = st.selectbox(
                        "Zone",
                        zone_split_list,
                        index=0
                    )
                pitch_team_list = ["All Team"] + list(plate_df["fld_team"].value_counts().index)
                with cols[3]:
                    team_split = st.selectbox(
                        "Team",
                        pitch_team_list,
                        index=0
                    )
                
                pitch_plt_df = plate_df
                if hand_split == "vsRHP":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["p_throw"] == "右"]
                elif hand_split == "vsLHP":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["p_throw"] == "左"]

                if pitch_split == "Swing":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["swing"] == 1]
                if pitch_split == "Take":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["swing"] == 0]
                if pitch_split == "Swing & Miss":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["description"] == "swing_strike"]
                elif pitch_split == "Called Strike":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["description"] == "called_strike"]
                elif pitch_split == "Base Hits":
                    pitch_plt_df = pitch_plt_df[(pitch_plt_df["events"] == "single")|(pitch_plt_df["events"] == "double")|(pitch_plt_df["events"] == "triple")|(pitch_plt_df["events"] == "home_run")]
                elif pitch_split == "Ahead in count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] > pitch_plt_df["balls"]]
                elif pitch_split == "Behind in count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] < pitch_plt_df["balls"]]
                elif pitch_split == "Even count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] == pitch_plt_df["balls"]]
                elif pitch_split == "2 Strikes":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] == 2]
                elif pitch_split == "Home Runs":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["events"] == "home_run"]

                if zone_split == "In Zone":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Zone"] == "In"]
                elif zone_split == "Out of Zone":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Zone"] == "Out"]
                elif zone_split == "Heart":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Heart"] == 1]
                elif zone_split == "Shadow":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Shadow"] == 1]
                elif zone_split == "Chase":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Chase"] == 1]
                elif zone_split == "Waste":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Waste"] == 1]

                if team_split != "All Team":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["fld_team"] == team_split]

                pitcher_list = ["All"] + list(pitch_plt_df["pitcher_name"].value_counts().index)
                with cols[4]:
                    pitcher_split = st.selectbox(
                        "Pitcher",
                        pitcher_list,
                        index=0
                    )

                cols = st.columns(5)
                with cols[0]:
                    color_split = st.selectbox(
                        "Color",
                        ["pitch_name", "pitch_group", "events", "description"],
                        index=0
                    )
            
                if pitcher_split != "All":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["pitcher_name"] == pitcher_split]

                fig = px.scatter(pitch_plt_df, x='plate_x', y='plate_z', 
                                color=color_split,
                                color_discrete_map=color_dict_en,
                                hover_data={
                                    'game_date': True, 'fld_team': True, 'pitcher_name': True,
                                    'inning': True, 'top_bot': True, 'velocity': True})

                # ストライクゾーンの枠を追加
                fig.add_shape(type="rect",
                            x0=sz_left, x1=sz_right, y0=sz_bot, y1=sz_top,
                            line=dict(color="Black"))
                
                hplt_y = 60

                # ホームベースのSVGパス
                home_plate_path = f"M {home_plate_coords[0]} {home_plate_coords[1]-hplt_y} " \
                                f"L {home_plate_coords[2]} {home_plate_coords[3]-hplt_y} " \
                                f"L {home_plate_coords[4]} {home_plate_coords[5]-hplt_y} " \
                                f"L {home_plate_coords[6]} {home_plate_coords[7]-hplt_y} " \
                                f"L {home_plate_coords[8]} {home_plate_coords[9]-hplt_y} Z"
                
                # ホームベースの形を追加
                fig.add_shape(
                    type="path",
                    path=home_plate_path,
                    line=dict(color="Black")
                )


                fig.update_yaxes(range=[sz_bot-85, sz_top+80], showticklabels=False, title='')
                fig.update_xaxes(range=[sz_left-80, sz_right+80], showticklabels=False, title='')
                plt_w = 550
                fig.update_layout(width=plt_w, height=plt_w*5/4.3) 
                st.plotly_chart(fig)
                st.write("Pitcher Viewpoint")

            elif stats_type == "Pitching":
                events_df = events_df[events_df["pitcher_id"] == player_id]
                plate_df = plate_df[plate_df["pitcher_id"] == player_id]
                merged_data = merged_data[merged_data["pitcher_id"] == player_id]
                PA_df = PA_df[PA_df["pitcher_id"] == player_id]

                pitch_t = plate_df["pitch_type"].value_counts()
                pitch_arsenal = plate_df["pitch_name"].value_counts()
                p_t_list = list(pitch_t.index)
                p_a_list = list(pitch_arsenal.index)

                cols = st.columns(6)
                with cols[0]:
                    rolling_pa = st.selectbox(
                        "PA",
                        [50, 100, 150, 200],
                        index=1
                    )

                PA_df["woba_denom"] = PA_df['events'].apply(lambda x: 0 if x in ["sac_bunt", "bunt_error", "bunt_fielders_choice", "obstruction", "intentional_walk", "interference"] else 1)
                woba_rolling_df = PA_df[["events", "woba_denom"]].reset_index(drop=True)
                woba_rolling_df["woba_value"] = woba_rolling_df['events'].apply(lambda x: single_value if x == "single" 
                                                                                else double_value if x == "double" 
                                                                                else triple_value if x == "triple" 
                                                                                else hr_value if x == "home_run" 
                                                                                else bb_value if x == "walk" 
                                                                                else hbp_value if x == "hit_by_pitch" 
                                                                                else 0)
                woba_rolling_df['at_bat_number'] = range(1, len(woba_rolling_df) + 1)
                woba_rolling_df['rolling_value'] = woba_rolling_df['woba_value'].rolling(window=rolling_pa).sum()
                woba_rolling_df['rolling_denom'] = woba_rolling_df['woba_denom'].rolling(window=rolling_pa).sum()
                woba_rolling_df["rolling_wOBA"] = my_round(wOBA_scale*woba_rolling_df["rolling_value"]/woba_rolling_df["rolling_denom"], 3)
                if 0.2 < woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].min():
                    y_min = 0.180
                else:
                    y_min = woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].min() - 0.2
                if 0.5 > woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].max():
                    y_max = 0.520
                else:
                    y_max = woba_rolling_df["rolling_wOBA"].iloc[rolling_pa:].max() + 0.2
                # Plotlyの折れ線グラフを作成
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=woba_rolling_df['at_bat_number'], 
                    y=woba_rolling_df['rolling_wOBA'], 
                    mode='lines',
                    name='wOBA'))
                fig.update_layout(
                    title=f'{name} {rolling_pa} PAs Rolling wOBA',
                    xaxis_title='PA',
                    yaxis_title='wOBA',
                    xaxis=dict(range=[rolling_pa, len(woba_rolling_df)]),
                    yaxis=dict(range=[y_min, y_max], tickformat='.3f'),
                    legend=dict(x=0, y=1, traceorder="normal", bgcolor="rgba(0,0,0,0)", bordercolor="Black", borderwidth=1)
                )

                # リーグ平均wOBAの直線を追加
                fig.add_shape(
                    type="line",
                    x0=rolling_pa,
                    y0=mean_woba*wOBA_scale,
                    x1=len(woba_rolling_df),
                    y1=mean_woba*wOBA_scale,
                    line=dict(color='gray', dash='dash'),
                    name='Lg. Avg'
                )

                # リーグ平均wOBAの注釈を追加
                fig.add_annotation(
                    x=len(woba_rolling_df)-10,
                    y=mean_woba*wOBA_scale,
                    text=f'Lg. Avg: {mean_woba*wOBA_scale:.3f}',
                    showarrow=False,
                    yshift=10,
                    font=dict(color='gray')
                )

                # Streamlitで表示
                st.plotly_chart(fig, use_container_width=True)

                p_data = plate_df.dropna(subset="velocity")
                if len(p_data) != 0:
                    p_a_2 = p_data["pitch_name"].value_counts()
                    p_a_2 = p_a_2[p_a_2 > 1]
                    p_a_2_list = list(p_a_2.index)

                    overall_min = p_data["velocity"].min()*0.9
                    overall_max = p_data["velocity"].max()*1.1
                    all_hist_data = [p_data[p_data["pitch_name"] == pitch_type].velocity.values for pitch_type in p_a_2_list]
                    all_fig = ff.create_distplot(all_hist_data, p_a_2_list, bin_size=.2, show_hist=False, colors=[color_dict_en[pitch] for pitch in p_a_2_list])
                    all_y_max = max([max(trace.y) for trace in all_fig.data[:len(p_a_2_list)]])*1.1

                    hist_data = []
                    group_labels = []
                    colors = []
                    plot_height = 100
                    st.header("Pitch Distribution")
                    for i in range(len(p_a_2_list)):
                        pitch_type = p_a_2_list[i]
                        hist_data = [p_data[p_data["pitch_name"] == pitch_type].velocity.values]
                        group_labels = [pitch_type]
                        colors = [color_dict_en[pitch_type]]
                        mean_velocity = data[data["pitch_name"] == pitch_type]["velocity"].mean()
                        p_mean = my_round(plate_df[plate_df["pitch_name"] == pitch_type]["velocity"].mean(), 1)
                        p_percent = my_round(100*len(plate_df[plate_df["pitch_name"] == pitch_type])/len(plate_df),1)

                        # ヒストプロットを作成
                        fig = ff.create_distplot(hist_data, group_labels, bin_size=.2, show_hist=False, colors=colors, show_rug=False)
                        if i == 0:
                            mean_txt = 'Lg. AVG'
                        else:
                            mean_txt = ""
                        fig.add_vline(x=mean_velocity, line=dict(color='#4a8991', width=2, dash='dash'), annotation_text=mean_txt, annotation_position='top')

                        
                        # グラフのサイズとx軸およびy軸範囲を設定
                        fig.update_layout(
                            height=plot_height,  # 高さを指定
                            margin=dict(l=10, r=10, t=30, b=10),  # 余白を調整
                            xaxis=dict(range=[overall_min, overall_max], title=''),
                            yaxis=dict(range=[0, all_y_max], title='%', tickformat='.0%'),
                            showlegend=False
                        )
                        
                        fig.update_layout(
                            yaxis=dict(
                                tickvals=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
                            )
                        )

                        if i != len(p_a_2_list)-1:
                            fig.update_layout(xaxis_title='')
                            fig.update_xaxes(showticklabels=False)  # x軸のテキストを表示
                        
                        # グラフを順番に表示
                        cols = st.columns(3)

                        with cols[0]:
                            st.markdown(f'<span style="color: black;">{p_percent}%, AVG: {p_mean}km/h, </span><span style="color: {color_dict_en[pitch_type]};">{pitch_type}</span>', unsafe_allow_html=True)
                        with cols[1]:
                            st.plotly_chart(fig)

                # 'FF'のピッチのみをフィルター
                st.header("Pitch Arsenal")
                
                p_a_str = f"{name} relies on {len(p_a_list)} pitches. "
                for i in range(len(p_a_list)):
                    pitch_name = p_a_list[i]
                    pitch_num = pitch_arsenal[i]
                    p_per = my_round(100*pitch_num/pitch_arsenal.sum(), 1)
                    p_color = color_dict_en.get(pitch_name, 'black')  # デフォルトの色を黒に設定
                    p_a_str += f'<span style="color: {p_color};">{pitch_name} <span style="color: black;">({p_per}%) </span></span> '
                st.markdown(p_a_str, unsafe_allow_html=True)

                cols = st.columns(5)
                
                stand_split_lits = ["All", "vsRHH", "vsLHH"]
                with cols[0]:
                    stand_split = st.selectbox(
                        "Bat Side",
                        stand_split_lits,
                        index=0
                    )
                pitch_split_list = ["All Pitchs", "Swing & Miss", "Called Strike", "Base Hits",
                                    "Ahead in count", "Behind in count", "Even count", "2 Strikes"]
                with cols[1]:
                    pitch_split = st.selectbox(
                        "Pitch Split",
                        pitch_split_list,
                        index=0
                    )
                zone_split_list = ["All Zone", "In Zone", "Out of Zone",
                                    "Heart", "Shadow", "Chase", "Waste"]
                with cols[2]:
                    zone_split = st.selectbox(
                        "Zone",
                        zone_split_list,
                        index=0
                    )
                catcher_list = ["All"] + list(plate_df["fld_2"].value_counts().index)
                with cols[3]:
                    catcher_split = st.selectbox(
                        "Catcher",
                        catcher_list,
                        index=0
                    )
                pitch_plt_df = plate_df
                if stand_split == "vsRHH":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["stand"] == "右"]
                elif stand_split == "vsLHH":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["stand"] == "左"]
                    
                if pitch_split == "Swing & Miss":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["description"] == "swing_strike"]
                elif pitch_split == "Called Strike":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["description"] == "called_strike"]
                elif pitch_split == "Base Hits":
                    pitch_plt_df = pitch_plt_df[(pitch_plt_df["events"] == "single")|(pitch_plt_df["events"] == "double")|(pitch_plt_df["events"] == "triple")|(pitch_plt_df["events"] == "home_run")]
                elif pitch_split == "Ahead in count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] > pitch_plt_df["balls"]]
                elif pitch_split == "Behind in count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] < pitch_plt_df["balls"]]
                elif pitch_split == "Even count":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] == pitch_plt_df["balls"]]
                elif pitch_split == "2 Strikes":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["strikes"] == 2]

                if zone_split == "In Zone":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Zone"] == "In"]
                elif zone_split == "Out of Zone":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Zone"] == "Out"]
                elif zone_split == "Heart":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Heart"] == 1]
                elif zone_split == "Shadow":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Shadow"] == 1]
                elif zone_split == "Chase":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Chase"] == 1]
                elif zone_split == "Waste":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["Waste"] == 1]
            
                if catcher_split != "All":
                    pitch_plt_df = pitch_plt_df[pitch_plt_df["fld_2"] == catcher_split]

                if len(p_t_list) < 5:
                    col_num = 5
                else:
                    col_num = len(p_t_list)

                if len(p_t_list) <= 5:
                    cols = st.columns(5)
                    for i in range(len(p_t_list)):
                        with cols[i]:
                            pitch_type = p_t_list[i]
                            pitch_name = p_a_list[i]
                            pitch_num = pitch_arsenal[i]
                            p_per = my_round(100*pitch_num/pitch_arsenal.sum(), 1)
                            p_color = color_dict_en.get(pitch_name, 'black') 
                            st.markdown(f'<span style="color: {p_color};">{pitch_name}</span>', unsafe_allow_html=True)
                            st.write(f"<span style='font-size:15px;'>{pitch_num} Pitches ({p_per}%)</span>", unsafe_allow_html=True)
                            ff_plt = pitch_plt_df[pitch_plt_df["pitch_type"] == pitch_type][["plate_x", "plate_z"]]
                            ff_plt = ff_plt.reset_index(drop=True)
                            # Seabornを使ってKDEプロットを作成
                            fig, ax = plt.subplots(figsize=(4, 5))
                            seaborn.kdeplot(data=ff_plt, x="plate_x", y="plate_z", levels=20, cmap="bwr", shade=True, ax=ax)
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
                
                if len(p_t_list) > 5 and len(p_t_list) <= 10:
                    cols = st.columns(5)
                    for i in range(5):
                        with cols[i]:
                            pitch_type = p_t_list[i]
                            pitch_name = p_a_list[i]
                            pitch_num = pitch_arsenal[i]
                            p_per = my_round(100*pitch_num/pitch_arsenal.sum(), 1)
                            p_color = color_dict_en.get(pitch_name, 'black') 
                            st.markdown(f'<span style="color: {p_color};">{pitch_name}</span>', unsafe_allow_html=True)
                            st.write(f"<span style='font-size:15px;'>{pitch_num} Pitches ({p_per}%)</span>", unsafe_allow_html=True)
                            ff_plt = pitch_plt_df[pitch_plt_df["pitch_type"] == pitch_type][["plate_x", "plate_z"]]
                            ff_plt = ff_plt.reset_index(drop=True)
                            # Seabornを使ってKDEプロットを作成
                            fig, ax = plt.subplots(figsize=(4, 5))
                            seaborn.kdeplot(data=ff_plt, x="plate_x", y="plate_z", levels=20, cmap="bwr", shade=True, ax=ax)
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
                    cols = st.columns(5)
                    for i in range(5, len(p_t_list)):
                        with cols[i-5]:
                            pitch_type = p_t_list[i]
                            pitch_name = p_a_list[i]
                            pitch_num = pitch_arsenal[i]
                            p_per = my_round(100*pitch_num/pitch_arsenal.sum(), 1)
                            p_color = color_dict_en.get(pitch_name, 'black') 
                            st.markdown(f'<span style="color: {p_color};">{pitch_name}</span>', unsafe_allow_html=True)
                            st.write(f"<span style='font-size:15px;'>{pitch_num} Pitches ({p_per}%)</span>", unsafe_allow_html=True)
                            ff_plt = pitch_plt_df[pitch_plt_df["pitch_type"] == pitch_type][["plate_x", "plate_z"]]
                            ff_plt = ff_plt.reset_index(drop=True)
                            # Seabornを使ってKDEプロットを作成
                            fig, ax = plt.subplots(figsize=(4, 5))
                            seaborn.kdeplot(data=ff_plt, x="plate_x", y="plate_z", levels=20, cmap="bwr", shade=True, ax=ax)
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
                st.write("Pitcher Viewpoint")

                graph_lits = ["Pitch %", "Average Pitch Velocity", "Max Pitch Velocity", 
                              "Swing %", "Swing & Miss %",
                              "In Zone %", "Out Zone %", "In Zone Swing %", "Chase %", 
                              "In Zone Swing & Miss %", "Chase Miss %", "Base on Balls %", 
                              "K %", "Hits", "Singles", "Doubles", "Triples", "home Runs", "Pitches",
                              "GB %", "LD %", "FB %", "IFFB %"]
                cols_2 = st.columns([1, 5])
                with cols_2[0]:
                    graph_type = st.selectbox(
                        "",
                        graph_lits,
                        index=0
                    )
                with cols_2[1]:
                    cols = st.columns(6)
                    with cols[0]:
                        pitch_group = st.selectbox(
                            "",
                            ["Pitches", "Pitch Group", "All Pitches"],
                            index=0
                        )
                        
                    with cols[1]:
                        date_split = st.selectbox(
                            "",
                            ["Season", "Month", "Game", "Inning"],
                            index=1
                        )

                    with cols[2]:
                        bat_split = st.selectbox(
                            "",
                            ["Handedness", "Right", "Left"],
                            index=0
                        )
                    with cols[3]:
                        count_split = st.selectbox(
                            "",
                            ["Count", "0-0", "0-1", "0-2", "1-0", "1-1", "1-2", "2-0", "2-1", "2-2", "3-0", "3-1", "3-2", 
                            "Batter Ahead", "Batter Behind", "2 Strikes", "3 Balls"],
                            index=0
                        )
                    
                    pt_split_list = ["All Pitches"]
                    if pitch_group == "Pitches":
                        pt_split_list += p_a_list
                    elif pitch_group == "Pitch Group":
                        pt_split_list += ["Fastball", "Offspeed", "Breaking"]

                    with cols[4]:
                        pitch_type_split = st.selectbox(
                            "",
                            pt_split_list,
                            index=0
                        )
                    with cols[5]:
                        season_split = st.selectbox(
                            "",
                            ["All Seasons"] + year_list,
                            index=0
                        )
                    
                pitch_graph_df = plate_df

                if count_split == "Count":
                    pass
                elif count_split == "Batter Ahead":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] < pitch_graph_df["balls"]]
                elif count_split == "Batter Behind":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] > pitch_graph_df["balls"]]
                elif count_split == "2 Strikes":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["strikes"] == 2]
                elif count_split == "3 Balls":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["balls"] == 3]
                else:
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["B-S"] == count_split]
                
                if bat_split == "Right":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["stand"] == "右"]
                elif bat_split == "Left":
                    pitch_graph_df = pitch_graph_df[pitch_graph_df["stand"] == "左"]
                
                if date_split == "Season":
                    group_l = ["game_year"]
                    p_c_list = ["Season"]
                elif date_split == "Month":
                    group_l = ["Year/Month"]
                    p_c_list = ["Year/Month"]
                elif date_split == "Game":
                    group_l = ["game_date"]
                    p_c_list = ["Date"]
                elif date_split == "Inning":
                    group_l = ["Inning"]
                    p_c_list = ["Inning"]
                if pitch_group == "Pitches":
                    group_l += ["pitch_name"]
                elif pitch_group == "Pitch Group":
                    group_l += ["pitch_group"]
                
                events_graph_df = pitch_graph_df.dropna(subset="events")
                pa_graph_df = events_graph_df[(events_graph_df["events"] != "pickoff_1b")&(events_graph_df["events"] != "pickoff_2b")&(events_graph_df["events"] != "pickoff_catcher")&(events_graph_df["events"] != "caught_stealing")&(events_graph_df["events"] != "stolen_base")&(events_graph_df["events"] != "wild_pitch")&(events_graph_df["events"] != "balk")&(events_graph_df["events"] != "passed_ball")&(events_graph_df["events"] != "caught_stealing")]
                n_graph_df = pitch_graph_df.groupby(group_l[0], as_index=False).agg(
                    N=(group_l[-1], "size")
                )
                
                p_graph_df = pitch_graph_df.groupby(group_l, as_index=False).agg(
                    P_N=(group_l[-1], "size"),
                    avg_velo=("velocity", "mean"),
                    Max_Velocity=("velocity", "max"),
                    swing=("swing", "sum"),
                    swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, n_graph_df, on=group_l[0], how="left")
                p_graph_df["p%"] = 100*p_graph_df["P_N"]/p_graph_df["N"]
                p_graph_df["%"] = my_round(p_graph_df["p%"], 1)
                p_graph_df["AVG Velocity"] = my_round(p_graph_df["avg_velo"], 1)

                p_pa_graph_df = events_graph_df.groupby(group_l, as_index=False).agg(
                    R=('runs_scored', 'sum'), 
                    PA=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum())
                )
                if league_type == "1軍":
                    p_bb_df = events_graph_df.groupby(group_l, as_index=False).agg(
                        GB = ("GB", "sum"),
                        FB = ("FB", "sum"),
                        IFFB = ("IFFB", "sum"),
                        OFFB = ("OFFB", "sum"),
                        LD = ("LD", "sum"),
                        Pull = ("Pull", "sum"),
                        Cent = ("Center", "sum"),
                        Oppo = ("Opposite", "sum")
                    )
                    p_pa_graph_df = pd.merge(p_pa_graph_df, p_bb_df, on=group_l, how="left")
                p_pa_graph_df["inning"] = p_pa_graph_df["O"]/3
                p_pa_graph_df["AB"] = p_pa_graph_df["PA"] - (p_pa_graph_df["BB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SH"] + p_pa_graph_df["SF"] + p_pa_graph_df["obstruction"] + p_pa_graph_df["interference"])
                p_pa_graph_df["H"] = p_pa_graph_df["single"] + p_pa_graph_df["double"] + p_pa_graph_df["triple"] + p_pa_graph_df["HR"]
                p_pa_graph_df['k/9'] = p_pa_graph_df['SO'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['bb/9'] = p_pa_graph_df['BB'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['K/9'] = my_round(p_pa_graph_df['k/9'], 2)
                p_pa_graph_df['BB/9'] = my_round(p_pa_graph_df['bb/9'], 2)
                p_pa_graph_df['k%'] = 100*p_pa_graph_df["SO"]/p_pa_graph_df["PA"]
                p_pa_graph_df['bb%'] = 100*p_pa_graph_df["BB"]/p_pa_graph_df["PA"]
                p_pa_graph_df['hr%'] = p_pa_graph_df["HR"]/p_pa_graph_df["PA"]
                p_pa_graph_df["K %"] = my_round(p_pa_graph_df["k%"], 1)
                p_pa_graph_df["BB %"] = my_round(p_pa_graph_df["bb%"], 1)
                p_pa_graph_df['ra'] = p_pa_graph_df['R'] * 9 / p_pa_graph_df['inning']
                p_pa_graph_df['RA'] = my_round(p_pa_graph_df['ra'], 2)
                p_pa_graph_df["avg"] = p_pa_graph_df["H"]/p_pa_graph_df["AB"]
                p_pa_graph_df["BA"] = my_round(p_pa_graph_df["avg"], 3)
                p_pa_graph_df = p_pa_graph_df.rename(columns={"single": "1B", "double": "2B", "triple": "3B"})
                p_pa_graph_df["obp"] = (p_pa_graph_df["H"] + p_pa_graph_df["BB"] + p_pa_graph_df["HBP"])/(p_pa_graph_df["AB"] + p_pa_graph_df["BB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SF"])
                p_pa_graph_df["OBP"] = my_round(p_pa_graph_df["obp"], 3)
                p_pa_graph_df["slg"] = (p_pa_graph_df["1B"] + 2*p_pa_graph_df["2B"] + 3*p_pa_graph_df["3B"] + 4*p_pa_graph_df["HR"])/p_pa_graph_df["AB"]
                p_pa_graph_df["SLG"] = my_round(p_pa_graph_df["slg"], 3)
                p_pa_graph_df["woba"] = wOBA_scale * (bb_value * (p_pa_graph_df["BB"] - p_pa_graph_df["IBB"]) + hbp_value * p_pa_graph_df["HBP"] + single_value * p_pa_graph_df["1B"] + double_value * p_pa_graph_df["2B"] + triple_value * p_pa_graph_df["3B"] + hr_value * p_pa_graph_df["HR"])/(p_pa_graph_df["AB"] + p_pa_graph_df["BB"] - p_pa_graph_df["IBB"] + p_pa_graph_df["HBP"] + p_pa_graph_df["SF"])
                p_pa_graph_df["wOBA"] = my_round(p_pa_graph_df["woba"], 3)
                if league_type == "1軍":
                    p_pa_graph_df["gb/fb"] = p_pa_graph_df["GB"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["gb%"] = 100*p_pa_graph_df["GB"]/(p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["fb%"] = 100*p_pa_graph_df["FB"]/(p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["ld%"] = 100*p_pa_graph_df["LD"] / (p_pa_graph_df["GB"]+p_pa_graph_df["FB"]+p_pa_graph_df["LD"])
                    p_pa_graph_df["iffb%"] = 100*p_pa_graph_df["IFFB"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["hr/fb"] = 100*p_pa_graph_df["HR"] / p_pa_graph_df["FB"]
                    p_pa_graph_df["GB/FB"] = my_round(p_pa_graph_df["gb/fb"], 2)
                    p_pa_graph_df["GB %"] = my_round(p_pa_graph_df["gb%"], 1)
                    p_pa_graph_df["FB %"] = my_round(p_pa_graph_df["fb%"], 1)
                    p_pa_graph_df["LD %"] = my_round(p_pa_graph_df["ld%"], 1)
                    p_pa_graph_df["IFFB %"] = my_round(p_pa_graph_df["iffb%"], 1)
                    p_pa_graph_df["HR/FB"] = my_round(p_pa_graph_df["hr/fb"], 1)
                    p_pa_graph_df["pull%"] = 100*p_pa_graph_df["Pull"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["cent%"] = 100*p_pa_graph_df["Cent"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["oppo%"] = 100*p_pa_graph_df["Oppo"]/(p_pa_graph_df["Pull"]+p_pa_graph_df["Cent"]+p_pa_graph_df["Oppo"])
                    p_pa_graph_df["Pull%"] = my_round(p_pa_graph_df["pull%"], 1)
                    p_pa_graph_df["Cent%"] = my_round(p_pa_graph_df["cent%"], 1)
                    p_pa_graph_df["Oppo%"] = my_round(p_pa_graph_df["oppo%"], 1)
                if league_type == "2軍":
                    p_pa_graph_df["GB/FB"] = np.nan
                    p_pa_graph_df["GB%"] = np.nan
                    p_pa_graph_df["FB%"] = np.nan
                    p_pa_graph_df["LD%"] = np.nan
                    p_pa_graph_df["IFFB%"] = np.nan
                    p_pa_graph_df["HR/FB"] = np.nan
                    p_pa_graph_df["Pull%"] = np.nan
                    p_pa_graph_df["Cent%"] = np.nan
                    p_pa_graph_df["Oppo%"] = np.nan

                p_graph_df = pd.merge(p_graph_df, p_pa_graph_df, on=group_l, how="left")

                z_pitch_df = pitch_graph_df[pitch_graph_df["Zone"] == "In"]
                z_bb_df = z_pitch_df.groupby(group_l, as_index=False).agg(
                    Z_N=(group_l[-1], "size"),
                    Z_swing=("swing", "sum"),
                    Z_swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, z_bb_df, on=group_l, how="left")

                o_pitch_df = pitch_graph_df[pitch_graph_df["Zone"] == "Out"]
                o_bb_df = o_pitch_df.groupby(group_l, as_index=False).agg(
                    O_N=(group_l[-1], "size"),
                    O_swing=("swing", "sum"),
                    O_swstr=("description", lambda x: (x == "swing_strike").sum()),
                )
                p_graph_df = pd.merge(p_graph_df, o_bb_df, on=group_l, how="left")
                p_graph_df["Swing %"] = 100*p_graph_df["swing"]/p_graph_df["N"]
                p_graph_df["Swing & Miss %"] = 100*p_graph_df["swstr"]/p_graph_df["swing"]
                p_graph_df["In Zone %"] = 100*p_graph_df["Z_N"]/p_graph_df["N"]
                p_graph_df["Out Zone %"] = 100*p_graph_df["O_N"]/p_graph_df["N"]
                p_graph_df["In Zone Swing %"] = 100*p_graph_df["Z_swing"]/p_graph_df["Z_N"]
                p_graph_df["Chase %"] = 100*p_graph_df["O_swing"]/p_graph_df["O_N"]
                p_graph_df["In Zone Swing & Miss %"] = 100*p_graph_df["Z_swstr"]/p_graph_df["Z_swing"]
                p_graph_df["Chase Miss %"] = 100*p_graph_df["O_swstr"]/p_graph_df["O_swing"]

                if pitch_group == "All Pitches":
                    p_graph_df["pitch_name"] = "All Pitches"
                p_graph_df = p_graph_df.rename(columns={"game_year": "Season", "pitch_name": "Pitch Type", "pitch_group": "Pitch Type", "game_date": "Date", "Max_Velocity": "Max Velocity", "P_N": "#"})
                if pitch_type_split != "All Pitches":
                    p_graph_df = p_graph_df[p_graph_df["Pitch Type"] == pitch_type_split]
                p_graph_df = p_graph_df.sort_values(p_c_list + ["%"], ascending=[True, False]).reset_index(drop=True)
                p_graph_cols = p_c_list + ["Pitch Type", "#", "%", "AVG Velocity", "Max Velocity", "PA", "AB", "H", "1B", "2B", "3B", "HR", "SO", "BB", "BA", "OBP", "SLG", "wOBA"]
                p_statistics = p_graph_df[p_graph_cols]
                p_statistics = p_statistics.sort_values(p_c_list + ["%"], ascending=False).reset_index(drop=True)
                if date_split == "Game":
                    p_statistics["Date"] = p_statistics["Date"].dt.strftime("%Y/%m/%d")
                df_style = p_statistics.style.format({
                    'AVG Velocity': '{:.1f}',
                    'Max Velocity': '{:.0f}',
                    'PA': '{:.0f}',
                    'AB': '{:.0f}',
                    'H': '{:.0f}',
                    '1B': '{:.0f}',
                    '2B': '{:.0f}',
                    '3B': '{:.0f}',
                    'HR': '{:.0f}',
                    'SO': '{:.0f}',
                    'BB': '{:.0f}',
                    '%': '{:.1f}',
                    'K %': '{:.1f}',
                    'BB %': '{:.1f}',
                    'BA': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'wOBA': '{:.3f}',
                    'BA': '{:.3f}',
                    'K-BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'HR/9': '{:.2f}',
                    'AVG': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'IFH%': '{:.1f}',
                    'GB %': '{:.1f}',
                    'FB %': '{:.1f}',
                    'LD %': '{:.1f}',
                    'Pull%': '{:.1f}',
                    'Cent%': '{:.1f}',
                    'Oppo%': '{:.1f}',
                    'IFFB %': '{:.1f}',
                    'GB/FB': '{:.2f}',
                    'HR/FB': '{:.1f}',
                })
                if graph_type == "Pitch %":
                    graph_y = "%"
                elif graph_type == "Average Pitch Velocity":
                    graph_y = "AVG Velocity"
                elif graph_type == "Max Pitch Velocity":
                    graph_y = "Max Velocity"
                elif graph_type == "Base on Balls %" :
                    graph_y = "BB %"
                elif graph_type == "Hits":
                    graph_y = "H"
                elif graph_type == "Singles":
                    graph_y = "1B"
                elif graph_type == "Doubles":
                    graph_y = "2B"
                elif graph_type == "Triples":
                    graph_y = "3B"
                elif graph_type == "Home Runs":
                    graph_y = "HR"
                elif graph_type == "Pitches":
                    graph_y = "#"
                else:
                    graph_y = graph_type

                if bat_split == "Right":
                    bat_str = "vs RHH "
                elif bat_split == "Left":
                    bat_str = "vs LHH "
                else:
                    bat_str = ""
                # Plotlyを使用して各球種の投球割合の推移を折れ線グラフで表示
                graph_title = f"{name} {graph_type} {bat_str}by {date_split}"
                fig = px.line(p_graph_df, x=p_c_list[0], y=graph_y, color='Pitch Type', 
                              title=graph_title,
                              color_discrete_map=color_dict_en,
                              markers=True)
                                
                if graph_type.endswith("%"):
                    fig.update_yaxes(range=[0, p_graph_df[graph_y].max() * 1.1])

                # Streamlitにプロットを表示
                st.plotly_chart(fig, use_container_width=True)


                st.header("Pitch Statistic")
                st.dataframe(df_style, use_container_width=True)

                pitch_date = plate_df.groupby(["game_date", "pitcher_name"], as_index=False).agg(
                    N=("pitcher_name", "size")
                )
                pitch_date = pitch_date.rename(columns={"game_date": "Date"})[["Date", "N"]]
                dates = pitch_date['Date'].dt.date.tolist()
                values = pitch_date['N'].tolist()

                st.header('Pitch Count Calendar')
                cols = st.columns(4)
                month_list_1 = list(events_df['game_date'].dt.month.unique())
                for i in range(len(month_list_1)):
                    with cols[i]:
                        fig, ax = plt.subplots()
                        month = month_list_1[i]
                        july.month_plot(dates, values, month=month, date_label=True, ax=ax, 
                                        colorbar=True, cmap="Reds")
                        st.pyplot(fig)

            elif stats_type == "Zone":
                if position == "投手":
                    events_df = events_df[events_df["pitcher_id"] == player_id]
                    plate_df = plate_df[plate_df["pitcher_id"] == player_id]
                    merged_data = merged_data[merged_data["pitcher_id"] == player_id]
                    PA_df = PA_df[PA_df["pitcher_id"] == player_id]
                else:
                    events_df = events_df[events_df["batter_id"] == player_id]
                    plate_df = plate_df[plate_df["batter_id"] == player_id]
                    merged_data = merged_data[merged_data["batter_id"] == player_id]
                    PA_df = PA_df[PA_df["batter_id"] == player_id]
                if len(plate_df) > 0:
                    zone_df = pd.DataFrame([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14],columns=["detailed_zone"])

                    z_df = plate_df.groupby("detailed_zone", as_index=False).agg(
                        N=("detailed_zone", "size")
                    )
                    zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                    zone_df["Total Pitches"] = zone_df["N"].fillna(0)
                    zone_df["Pitch %"] = my_round(100*zone_df["Total Pitches"]/zone_df["Total Pitches"].sum(), 1).fillna(0)

                    swing_df = plate_df[plate_df["swing"] == 1]

                    z_df = swing_df.groupby("detailed_zone", as_index=False).agg(
                        swing=("detailed_zone", "size"),
                        whiff=('description', lambda x: (x == "swing_strike").sum())
                    )
                    zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                    zone_df["Swings"] = zone_df["swing"].fillna(0)
                    zone_df["Missed"] = zone_df["whiff"].fillna(0)
                    zone_df["Swing %"] = my_round(100*zone_df["Swings"]/zone_df["Total Pitches"].sum(), 1).fillna(0)
                    zone_df["Whiff %"] = my_round(100*zone_df["Missed"]/zone_df["Swings"], 1).fillna(0)
                    z_df = PA_df.groupby("detailed_zone", as_index=False).agg(
                        PA=("detailed_zone", "size"),
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        bb=('events', lambda x: ((x == "walk")|(x == "intentional_walk")).sum()),   # ストライクアウト数
                        batted_ball=('description', lambda x: (x == "hit_into_play").sum()),   # ストライクアウト数
                        hr=('events', lambda x: (x == "home_run").sum()),   # ストライクアウト数
                        Singles=('events', lambda x: (x == "single").sum()),   # ストライクアウト数
                        Doubles=('events', lambda x: (x == "double").sum()),   # ストライクアウト数
                        Triples=('events', lambda x: (x == "Triple").sum()),   # ストライクアウト数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        BK=('events', lambda x: (x == "balk").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum())
                    )
                    zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                    zone_df["PA"] = zone_df["PA"].fillna(0)
                    zone_df["AB"] = zone_df["PA"] - (zone_df["bb"] + zone_df["HBP"] + zone_df["SH"] + zone_df["SF"] + zone_df["obstruction"] + zone_df["interference"])
                    zone_df["BB"] = zone_df["bb"].fillna(0)
                    zone_df["Strikeouts"] = zone_df["SO"].fillna(0)
                    zone_df["Home Runs"] = zone_df["hr"].fillna(0)
                    zone_df["Singles"] = zone_df["Singles"].fillna(0)
                    zone_df["Doubles"] = zone_df["Doubles"].fillna(0)
                    zone_df["Triples"] = zone_df["Triples"].fillna(0)
                    zone_df["Hits"] = zone_df["Singles"] + zone_df["Doubles"] + zone_df["Triples"] + zone_df["Home Runs"]
                    zone_df["Batted Balls"] = zone_df["batted_ball"].fillna(0)
                    zone_df["K %"] = my_round(100*zone_df["Strikeouts"]/zone_df["PA"], 1).fillna(0)
                    zone_df["BB %"] = my_round(100*zone_df["BB"]/zone_df["PA"], 1).fillna(0)
                    zone_df["BABIP"] = my_round((zone_df["Hits"] - zone_df["Home Runs"])/(zone_df["AB"] - zone_df["SO"] - zone_df["Home Runs"] + zone_df["SF"]), 3).fillna(0)
                    zone_df["ba"] = zone_df["Hits"]/zone_df["AB"]
                    zone_df["Batting Average (Contact)"] = my_round(zone_df["Hits"]/zone_df["Batted Balls"],3).fillna(0)
                    zone_df["obp"] = (zone_df["Hits"] + zone_df["bb"] + zone_df["HBP"])/(zone_df["AB"] + zone_df["bb"] + zone_df["HBP"] + zone_df["SF"])
                    zone_df["slg"] = (zone_df["Singles"] + 2*zone_df["Doubles"] + 3*zone_df["Triples"] + 4*zone_df["Home Runs"])/zone_df["AB"]
                    zone_df["Batting Average"] = my_round(zone_df["ba"], 3).fillna(0)
                    zone_df["OBP"] = my_round(zone_df["obp"], 3).fillna(0)
                    zone_df["SLG"] = my_round(zone_df["slg"], 3).fillna(0)
                    zone_df["OPS"] = my_round(zone_df["obp"]+zone_df["slg"], 3)
                    zone_df["ISO"] = my_round(zone_df["slg"] - zone_df["ba"], 3)
                    zone_df["woba"] = wOBA_scale * (bb_value * (zone_df["bb"] - zone_df["IBB"]) + hbp_value * zone_df["HBP"] + single_value * zone_df["Singles"] + double_value * zone_df["Doubles"] + triple_value * zone_df["Triples"] + hr_value * zone_df["Home Runs"])/(zone_df["AB"] + zone_df["bb"] - zone_df["IBB"] + zone_df["HBP"] + zone_df["SF"])
                    zone_df["wobacon"] = wOBA_scale * (single_value * zone_df["Singles"] + double_value * zone_df["Doubles"] + triple_value * zone_df["Triples"] + hr_value * zone_df["Home Runs"])/(zone_df["Batted Balls"] - zone_df["SH"])
                    zone_df["wOBA"] = my_round(zone_df["woba"], 3).fillna(0)
                    zone_df["wOBA (Contact)"] = my_round(zone_df["wobacon"], 3).fillna(0)
                    if position == "投手":
                        z_df = merged_data.groupby("detailed_zone", as_index=False).agg(
                            rv=("pitcher_pitch_value", "sum")
                        )
                        zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                        zone_df["Pitcher Run Value"] = my_round(zone_df["rv"], 1).fillna(0)
                        rv_columns = ["Pitcher Run Value"]
                        
                    else:
                        z_df = merged_data.groupby("detailed_zone", as_index=False).agg(
                            rv=("batter_pitch_value", "sum")
                        )
                        zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                        zone_df["Batter Run Value"] = my_round(zone_df["rv"], 1).fillna(0)
                        rv_columns = ["Batter Run Value"]

                    if league_type == "1軍":
                        z_df = PA_df.groupby("detailed_zone", as_index=False).agg(
                            GB=('GB', 'sum'),
                            LD=('LD', 'sum'),
                            FB=('FB', 'sum'),
                            IFFB=('IFFB', 'sum'),
                        )
                        zone_df = pd.merge(zone_df, z_df, on="detailed_zone", how="left")
                        zone_df["GB"] = zone_df["GB"].fillna(0)
                        zone_df["LD"] = zone_df["LD"].fillna(0)
                        zone_df["FB"] = zone_df["FB"].fillna(0)
                        zone_df["IFFB"] = zone_df["IFFB"].fillna(0)
                        zone_df["Ground Ball %"] = my_round(100*zone_df["GB"]/(zone_df["GB"] + zone_df["FB"] + zone_df["LD"]),1).fillna(0)
                        zone_df["Line Drive %"] = my_round(100*zone_df["LD"]/(zone_df["GB"] + zone_df["FB"] + zone_df["LD"]),1).fillna(0)
                        zone_df["Fly Ball %"] = my_round(100*zone_df["FB"]/(zone_df["GB"] + zone_df["FB"] + zone_df["LD"]),1).fillna(0)
                        zone_df["IFFB %"] = my_round(100*zone_df["IFFB"]/(zone_df["FB"]),1).fillna(0)                    


                    def get_color_for_value(value, min_value, max_value, r=False):
                        """
                        最大値を赤、最小値を青のRdBuカラースケールで、データの値の色を返す関数。

                        Parameters:
                        value (float): データの値
                        min_value (float): 最小値
                        max_value (float): 最大値

                        Returns:
                        str: 対応する色の16進数表現
                        """
                        # RdBuカラーマップを取得
                        if r == True:
                            cmap = plt.get_cmap('RdBu_r')
                        else:
                            cmap = plt.get_cmap('RdBu')


                        # min_valueとmax_valueの間の値を0から1の範囲に正規化
                        normalized_value = (value - min_value) / (max_value - min_value)

                        # 正規化された値に対応する色を取得
                        color = cmap(normalized_value)

                        # 色を16進数表現に変換
                        hex_color = matplotlib.colors.rgb2hex(color[:3])

                        return hex_color
                    
                    fig = go.Figure()

                    # 各ゾーンの頂点座標
                    zones = [
                        ([1, 1, 2, 2, 1], [4, 3, 3, 4, 4]),   # Zone 1
                        ([2, 2, 3, 3, 2], [4, 3, 3, 4, 4]),   # Zone 2
                        ([3, 3, 4, 4, 3], [4, 3, 3, 4, 4]),   # Zone 3
                        ([1, 1, 2, 2, 1], [3, 2, 2, 3, 3]),   # Zone 4
                        ([2, 2, 3, 3, 2], [3, 2, 2, 3, 3]),   # Zone 5
                        ([3, 3, 4, 4, 3], [3, 2, 2, 3, 3]),   # Zone 6
                        ([1, 1, 2, 2, 1], [2, 1, 1, 2, 2]),   # Zone 7
                        ([2, 2, 3, 3, 2], [2, 1, 1, 2, 2]),   # Zone 8
                        ([3, 3, 4, 4, 3], [2, 1, 1, 2, 2]),   # Zone 9
                        ([0, 0, 1, 1, 2.5, 2.5, 0], [5, 2.5, 2.5, 4, 4, 5, 5]),    # Zone 10 (outside)
                        ([2.5, 2.5, 4, 4, 5, 5, 2.5], [5, 4, 4, 2.5, 2.5, 5, 5]),  # Zone 11 (outside)
                        ([0, 0, 2.5, 2.5, 1, 1, 0], [2.5, 0, 0, 1, 1, 2.5, 2.5]),  # Zone 12 (outside)
                        ([2.5, 2.5, 5, 5, 4, 4, 2.5], [1, 0, 0, 2.5, 2.5, 1, 1])   # Zone 13 (outside)
                    ]
                    zone_text = [
                        [1.5, 3.5], [2.5, 3.5], [3.5, 3.5], [1.5, 2.5], [2.5, 2.5], [3.5, 2.5],
                        [1.5, 1.5], [2.5, 1.5], [3.5, 1.5], [0.5, 4.5], [4.5, 4.5], [0.5, 0.5], [4.5, 0.5] 
                    ]

                    if league_type == "1軍":
                        map_d_list = ["Total Pitches", "Pitch %", "Swing %", "Swings", "K %", "Whiff %", 
                                    "Missed", "Batted Balls", "Home Runs", "Hits", "Singles", "Doubles", 
                                    "Triples", "Strikeouts", "BB %", "Ground Ball %", "Line Drive %", "Fly Ball %",
                                    "IFFB %", "BABIP", "Batting Average", "Batting Average (Contact)", "OBP", "SLG", "ISO", 
                                    "OPS", "wOBA", "wOBA (Contact)"] + rv_columns
                    else:
                        map_d_list = ["Total Pitches", "Pitch %", "Swing %", "Swings", "K %", "Whiff %", 
                                    "Missed", "Batted Balls", "Home Runs", "Hits", "Singles", "Doubles", 
                                    "Triples", "Strikeouts", "BB %", "BABIP", "Batting Average", "Batting Average (Contact)", 
                                    "OPS", "OBP", "SLG", "ISO", "wOBA", "wOBA (Contact)"] + rv_columns
                    st.header("Zone Charts")
                    st.markdown(f"#### {name}")

                    cols = st.columns(5)
                    for k in range((len(map_d_list)//5)):
                        for j in range(k*5, k*5+5):
                            with cols[j%5]:
                                m_d = map_d_list[j]
                                map_data = zone_df[m_d]
                                

                                for i, (x, y) in enumerate(zones):
                                    if m_d[-1] == "%":
                                        f_txt = f'{map_data[i]:.1f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = map_data.min()-0.5
                                            max_value = map_data.max()+0.5
                                    elif m_d == rv_columns[0]:
                                        f_txt = f'{map_data[i]:.1f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = -6
                                            max_value = 6
                                    elif m_d == "BABIP" or m_d == "Batting Average" or m_d == "Batting Average (Contact)" or m_d == "OBP" or m_d == "SLG" or m_d == "ISO" or m_d == "OPS":
                                        f_txt = f'{map_data[i]:.3f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = map_data.min()
                                            max_value = map_data.max()+0.05
                                    elif m_d == "wOBA" or m_d == "wOBA (Contact)":
                                        f_txt = f'{map_data[i]:.3f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = 0
                                            max_value = map_data.max()+0.05
                                    else:
                                        f_txt = f'{map_data[i]:.0f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 100
                                        else:
                                            min_value = map_data.min()-0.5
                                            max_value = map_data.max()+0.5
                                            
                                    if position == "投手":
                                        if (m_d == "Line Drive %" or m_d == "Fly Ball %" or m_d == "OBP" or m_d == "SLG" or m_d == "BABIP" 
                                            or m_d == "Batting Average" or m_d == "Batting Average (Contact)" or m_d == "OPS" or m_d == "wOBA" 
                                            or m_d == "wOBA (Contact)"or m_d == "ISO" or m_d == "BB %"):
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=False)
                                        else:
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=True)
                                    else:
                                        if m_d == "Whiff %" or m_d == "K %" or m_d == "Missed" or m_d == "IFFB %":
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=False)
                                        else:
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=True)


                                    fig.add_trace(go.Scatter(
                                        x=x, y=y, fill="toself", mode='lines', line=dict(color='black'), fillcolor=color,
                                        showlegend=False, text=f_txt, textposition='top center'
                                    ))

                                    # 中心に値を表示
                                    fig.add_trace(go.Scatter(
                                        x=[zone_text[i][0]], y=[zone_text[i][1]], mode='text', text=f_txt,
                                        showlegend=False, 
                                        textfont=dict(color='black')
                                    ))

                                fig.add_trace(go.Scatter(
                                    x=[1, 1.2, 2.5, 3.8, 4, 1], y=[-1.5, -1, -0.5, -1, -1.5, -1.5], fill=None, mode='lines', line=dict(color='black'),
                                    showlegend=False
                                ))

                                fig.update_yaxes(range=[-2, 6], showticklabels=False, title='', showgrid=False)
                                fig.update_xaxes(range=[-0.1, 6.1], showticklabels=False, title='', showgrid=False)
                                fig.update_layout(width=400, height=450, showlegend=False, 
                                                title={
                                                    'text': m_d,
                                                    'y':0.9,
                                                    'x':0.5,
                                                    'xanchor': 'center',
                                                    'yanchor': 'top'
                                                })

                                st.plotly_chart(fig, use_container_width=True)

                    if len(map_d_list) % 5 != 0:
                        map_d_list_2 = map_d_list[-(len(map_d_list)%5):]
                        cols = st.columns(5)
                        for j in range(len(map_d_list_2)):
                            with cols[j]:
                                m_d = map_d_list_2[j]
                                map_data = zone_df[m_d]
                                

                                for i, (x, y) in enumerate(zones):
                                    if m_d[-1] == "%":
                                        f_txt = f'{map_data[i]:.1f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = map_data.min()-0.5
                                            max_value = map_data.max()+0.5
                                    elif m_d == rv_columns[0]:
                                        f_txt = f'{map_data[i]:.1f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = -6
                                            max_value = 6
                                    elif m_d == "BABIP" or m_d == "Batting Average" or m_d == "Batting Average (Contact)" or m_d == "OBP" or m_d == "SLG" or m_d == "ISO" or m_d == "OPS":
                                        f_txt = f'{map_data[i]:.3f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = map_data.min()
                                            max_value = map_data.max()+0.05
                                    elif m_d == "wOBA" or m_d == "wOBA (Contact)":
                                        f_txt = f'{map_data[i]:.3f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 1
                                        else:
                                            min_value = 0.1
                                            max_value = 0.6
                                    else:
                                        f_txt = f'{map_data[i]:.0f}'
                                        if map_data.min() == map_data.max():
                                            min_value = 0
                                            max_value = 100
                                        else:
                                            min_value = map_data.min()-0.5
                                            max_value = map_data.max()+0.5

                                    if position == "投手":
                                        if (m_d == "Line Drive %" or m_d == "Fly Ball %" or m_d == "OBP" or m_d == "SLG" or m_d == "BABIP" 
                                            or m_d == "Batting Average" or m_d == "Batting Average (Contact)" or m_d == "OPS" or m_d == "wOBA" 
                                            or m_d == "wOBA (Contact)"or m_d == "ISO" or m_d == "BB %"):
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=False)
                                        else:
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=True)
                                    else:
                                        if m_d == "Whiff %" or m_d == "K %" or m_d == "Missed" or m_d == "IFFB %":
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=False)
                                        else:
                                            color = get_color_for_value(value=map_data[i], min_value=min_value, max_value=max_value, r=True)

                                    fig.add_trace(go.Scatter(
                                        x=x, y=y, fill="toself", mode='lines', line=dict(color='black'), fillcolor=color,
                                        showlegend=False, text=f_txt, textposition='top center'
                                    ))

                                    # 中心に値を表示
                                    fig.add_trace(go.Scatter(
                                        x=[zone_text[i][0]], y=[zone_text[i][1]], mode='text', text=f_txt,
                                        showlegend=False, 
                                        textfont=dict(color='black')
                                    ))

                                fig.add_trace(go.Scatter(
                                    x=[1, 1.2, 2.5, 3.8, 4, 1], y=[-1.5, -1, -0.5, -1, -1.5, -1.5], fill=None, mode='lines', line=dict(color='black'),
                                    showlegend=False
                                ))

                                fig.update_yaxes(range=[-2, 6], showticklabels=False, title='', showgrid=False)
                                fig.update_xaxes(range=[-0.1, 6.1], showticklabels=False, title='', showgrid=False)
                                fig.update_layout(width=400, height=450, showlegend=False, 
                                                title={
                                                    'text': m_d,
                                                    'y':0.9,
                                                    'x':0.5,
                                                    'xanchor': 'center',
                                                    'yanchor': 'top'
                                                })

                                st.plotly_chart(fig, use_container_width=True)

        elif data_type == "Splits":
            cols = st.columns(5)
            with cols[0]:
                season_split = st.selectbox(
                    "",
                    year_list,
                    index=0
                )

            with cols[1]:
                game_type = st.selectbox(
                    "",
                    ["レギュラーシーズン", "交流戦", "交流戦以外"],
                    index=0)
                    
            events_df = events_df[events_df["game_year"] == season_split]
            plate_df = plate_df[plate_df["game_year"] == season_split]
            merged_data = merged_data[merged_data["game_year"] == season_split]
            PA_df = PA_df[PA_df["game_year"] == season_split]

            if league_type == "1軍":
                if game_type == "レギュラーシーズン":
                    PA_df = PA_df[(PA_df["game_type"] == "セ・リーグ")|(PA_df["game_type"] == "パ・リーグ")|(PA_df["game_type"] == "セ・パ交流戦")]
                    plate_df = plate_df[(plate_df["game_type"] == "セ・リーグ")|(plate_df["game_type"] == "パ・リーグ")|(plate_df["game_type"] == "セ・パ交流戦")]
                    merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")|(merged_data["game_type"] == "セ・パ交流戦")]
                    events_df = events_df[(events_df["game_type"] == "セ・リーグ")|(events_df["game_type"] == "パ・リーグ")|(events_df["game_type"] == "セ・パ交流戦")]
                elif game_type == "交流戦":
                    PA_df = PA_df[PA_df["game_type"] == "セ・パ交流戦"]
                    plate_df = plate_df[plate_df["game_type"] == "セ・パ交流戦"]
                    merged_data = merged_data[merged_data["game_type"] == "セ・パ交流戦"]
                    events_df = events_df[events_df["game_type"] == "セ・パ交流戦"]
                elif game_type == "交流戦以外":
                    PA_df = PA_df[(PA_df["game_type"] == "セ・リーグ")|(PA_df["game_type"] == "パ・リーグ")]
                    plate_df = plate_df[(plate_df["game_type"] == "セ・リーグ")|(plate_df["game_type"] == "パ・リーグ")]
                    merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")]
                    events_df = events_df[(events_df["game_type"] == "セ・リーグ")|(events_df["game_type"] == "パ・リーグ")]
            else:
                if game_type == "レギュラーシーズン":
                    PA_df = PA_df[(PA_df["game_type"] == "イ・リーグ") | (PA_df["game_type"] == "ウ・リーグ") | (PA_df["game_type"] == "ファーム交流戦")]
                    plate_df = plate_df[(plate_df["game_type"] == "イ・リーグ") | (plate_df["game_type"] == "ウ・リーグ") | (plate_df["game_type"] == "ファーム交流戦")]
                    merged_data = merged_data[(merged_data["game_type"] == "イ・リーグ") | (merged_data["game_type"] == "ウ・リーグ") | (merged_data["game_type"] == "ファーム交流戦")]
                    events_df = events_df[(events_df["game_type"] == "イ・リーグ") | (events_df["game_type"] == "ウ・リーグ") | (events_df["game_type"] == "ファーム交流戦")]
                elif game_type == "交流戦":
                    PA_df = PA_df[PA_df["game_type"] == "ファーム交流戦"]
                    plate_df = plate_df[plate_df["game_type"] == "ファーム交流戦"]
                    merged_data = merged_data[merged_data["game_type"] == "ファーム交流戦"]
                    events_df = events_df[events_df["game_type"] == "ファーム交流戦"]
                elif game_type == "交流戦以外":
                    PA_df = PA_df[(PA_df["game_type"] == "イ・リーグ") | (PA_df["game_type"] == "ウ・リーグ")]
                    plate_df = plate_df[(plate_df["game_type"] == "イ・リーグ") | (plate_df["game_type"] == "ウ・リーグ")]
                    merged_data = merged_data[(merged_data["game_type"] == "イ・リーグ") | (merged_data["game_type"] == "ウ・リーグ")]
                    events_df = events_df[(events_df["game_type"] == "イ・リーグ") | (events_df["game_type"] == "ウ・リーグ")]

            if stats_type == "Pitching":
                events_df = events_df[events_df["pitcher_id"] == player_id]
                plate_df = plate_df[plate_df["pitcher_id"] == player_id]
                merged_data = merged_data[merged_data["pitcher_id"] == player_id]
                PA_df = PA_df[PA_df["pitcher_id"] == player_id]
                
                st.header("Platoon Splits")
                player_outs_sum = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "stand"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "stand", "IP"]

                platoon_data = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "stand"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                platoon_data = pd.merge(platoon_data, player_ip_df, on=["fld_league", "fld_team", "pitcher_name", "stand"], how='left')
                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data['K/BB'] = my_round(platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int), 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)
                platoon_data['GS'] = np.nan
                platoon_data['G'] = np.nan
                platoon_data["stand"] = platoon_data["stand"].str.replace("右", "vs Right")
                platoon_data["stand"] = platoon_data["stand"].str.replace("左", "vs Left")
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player", "stand": "Type"})
                platoon_data = platoon_data.sort_values("Type").reset_index(drop=True)
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)


                st.header("Monthly Splits")
                events_df["month_en"] = events_df["game_month"].replace(month_dict)
                player_outs_sum = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "month_en"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "month_en", "IP"]

                platoon_data = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "month_en"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                platoon_data = pd.merge(platoon_data, player_ip_df, on=["fld_league", "fld_team", "pitcher_name", "month_en"], how='left')
                starter_games = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name", "month_en"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                platoon_data = pd.merge(platoon_data, st_games, on=["fld_league", "fld_team", "pitcher_name", "month_en"], how='left')
                platoon_data['GS'] = platoon_data['GS'].fillna(0).astype(int)
                platoon_data = platoon_data.rename(columns={"month_en": "Type"})
                platoon_data = platoon_data.sort_values("Type")
                platoon_data["Type"] = platoon_data["Type"].str[3:]
                if league_type == "1軍":
 
                    pre_allstar_data = events_df = events_df[events_df["game_date"] < datetime(2024, 7, 23)]

                    player_outs_sum = pre_allstar_data.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()
                    player_ip = player_outs_sum.apply(calculate_ip)
                    player_ip_df = player_ip.reset_index()
                    player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                    pre_allstar = pre_allstar_data.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        G=('game_id', 'nunique'),  # ゲーム数
                        R=('runs_scored', 'sum'),  # 許した得点数
                        BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                        O=('event_out', 'sum'), 
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                        single=('events', lambda x: (x == "single").sum()),
                        double=('events', lambda x: (x == "double").sum()),
                        triple=('events', lambda x: (x == "triple").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        WP=("WP", "sum"),
                        BK=('events', lambda x: (x == "balk").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    )
                    pre_allstar = pre_allstar.assign(Type = "Pre All-Star")
                    pre_allstar = pd.merge(pre_allstar, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                    starter_games = pre_allstar_data.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                    st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                        GS=("StP", "sum")
                    )
                    pre_allstar = pd.merge(pre_allstar, st_games, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                    pre_allstar['GS'] = pre_allstar['GS'].fillna(0).astype(int)
                    platoon_data = pd.concat([platoon_data, pre_allstar]).reset_index(drop=True)

                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data['K/BB'] = my_round(platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int), 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)                
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Baserunner Splits")
                runner_df_list = []
                for r in list(runner_dict):
                    runner_pa = events_df[events_df["runner_id"] == r]

                    player_outs_sum = runner_pa.groupby(["fld_league", "fld_team", "pitcher_name", "runner_id"])['event_out'].sum()
                    player_ip = player_outs_sum.apply(calculate_ip)
                    player_ip_df = player_ip.reset_index()
                    player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "runner_id", "IP"]

                    runner_df = runner_pa.groupby(["fld_league", "fld_team", "pitcher_name", "runner_id"], as_index=False).agg(
                        G=('game_id', 'nunique'),  # ゲーム数
                        R=('runs_scored', 'sum'),  # 許した得点数
                        BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                        O=('event_out', 'sum'), 
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                        single=('events', lambda x: (x == "single").sum()),
                        double=('events', lambda x: (x == "double").sum()),
                        triple=('events', lambda x: (x == "triple").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        WP=("WP", "sum"),
                        BK=('events', lambda x: (x == "balk").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    )
                    runner_df = pd.merge(runner_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name", "runner_id"], how='left')
                    runner_df['GS'] = np.nan
                    runner_df['G'] = np.nan
                    runner_df_list.append(runner_df)

                platoon_data = pd.concat(runner_df_list).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"runner_id": "Type"})
                platoon_data["Type"] = platoon_data["Type"].replace(runner_dict)
                scoring_data = events_df[(events_df["runner_id"] != "000")&(events_df["runner_id"] != "100")]

                player_outs_sum = scoring_data.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()
                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                scoring_df = scoring_data.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                scoring_df = pd.merge(scoring_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                scoring_df['GS'] = np.nan
                scoring_df['G'] = np.nan
                scoring_df = scoring_df.assign(Type = "Scoring Position")
                platoon_data = pd.concat([platoon_data, scoring_df]).reset_index(drop=True)
                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data["k/bb"] = platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int)
                platoon_data['K/BB'] = my_round(platoon_data["k/bb"], 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)                
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)


                st.header("Game Type Splits")

                home_pa = events_df[events_df["fld_team"] == events_df["home_team"] ]

                player_outs_sum = home_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                home_df = home_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                home_df = pd.merge(home_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                starter_games = home_pa.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                home_df = pd.merge(home_df, st_games, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                home_df['GS'] = home_df['GS'].fillna(0).astype(int)
                home_df = home_df.assign(Type="Home Games")

                away_pa = events_df[events_df["fld_team"] == events_df["away_team"] ]

                player_outs_sum = away_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                away_df = away_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                away_df = pd.merge(away_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                starter_games = away_pa.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                away_df = pd.merge(away_df, st_games, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                away_df['GS'] = away_df['GS'].fillna(0).astype(int)
                away_df = away_df.assign(Type="Away Games")

                events_df['start_time'] = pd.to_datetime(events_df['start_time'], format='%H:%M:%S').dt.time

                day_pa = events_df[events_df["start_time"] < dt.time(17, 0, 0)]

                player_outs_sum = day_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                day_df = day_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                day_df = pd.merge(day_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                starter_games = day_pa.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                day_df = pd.merge(day_df, st_games, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                day_df['GS'] = day_df['GS'].fillna(0).astype(int)
                day_df = day_df.assign(Type="Day Games")

                night_pa = events_df[events_df["start_time"] >= dt.time(17, 0, 0)]

                player_outs_sum = night_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                night_df = night_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                night_df = pd.merge(night_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                starter_games = night_pa.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
                st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    GS=("StP", "sum")
                )
                night_df = pd.merge(night_df, st_games, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                night_df['GS'] = night_df['GS'].fillna(0).astype(int)
                night_df = night_df.assign(Type="Night Games")

                leading_pa = events_df[events_df["fld_score"] > events_df["bat_score"] ]

                player_outs_sum = leading_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                leading_df = leading_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                leading_df = pd.merge(leading_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                leading_df['GS'] = np.nan
                leading_df['G'] = np.nan
                leading_df = leading_df.assign(Type="Leading Off")

                late_pa = events_df[events_df["fld_score"] <= events_df["bat_score"] ]

                player_outs_sum = late_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                late_df = late_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                late_df = pd.merge(late_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                late_df['G'] = np.nan
                late_df['GS'] = np.nan
                late_df = late_df.assign(Type="Late / Close")

                platoon_data = pd.concat([home_df, away_df, day_df, night_df, leading_df, late_df]).reset_index(drop=True)

                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data['K/BB'] = my_round(platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int), 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'GS': '{:.0f}',
                    'G': '{:.0f}',
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Outs Splits")
                player_outs_sum = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "out_count"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "out_count", "IP"]

                platoon_data = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "out_count"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                platoon_data = pd.merge(platoon_data, player_ip_df, on=["fld_league", "fld_team", "pitcher_name", "out_count"], how='left')
                platoon_data['GS'] = np.nan
                platoon_data['G'] = np.nan
                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data['K/BB'] = my_round(platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int), 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)
                platoon_data = platoon_data.rename(columns={"out_count": "Type"})
                platoon_data = platoon_data.sort_values("Type").reset_index(drop=True)
                platoon_data["Type"] = platoon_data["Type"].replace(outs_dict)
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'GS': '{:.0f}',
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Inning Splits")

                inning_df_list = []

                for i in list(inning_dict):
                    inning_pa = events_df[events_df["inning"] == i]

                    player_outs_sum = inning_pa.groupby(["fld_league", "fld_team", "pitcher_name", "inning"])['event_out'].sum()

                    player_ip = player_outs_sum.apply(calculate_ip)
                    player_ip_df = player_ip.reset_index()
                    player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "inning", "IP"]

                    inning_df = inning_pa.groupby(["fld_league", "fld_team", "pitcher_name", "inning"], as_index=False).agg(
                        G=('game_id', 'nunique'),  # ゲーム数
                        R=('runs_scored', 'sum'),  # 許した得点数
                        BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                        O=('event_out', 'sum'), 
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                        single=('events', lambda x: (x == "single").sum()),
                        double=('events', lambda x: (x == "double").sum()),
                        triple=('events', lambda x: (x == "triple").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        WP=("WP", "sum"),
                        BK=('events', lambda x: (x == "balk").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    )
                    inning_df = pd.merge(inning_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name", "inning"], how='left')
                    inning_df['GS'] = np.nan
                    inning_df['G'] = np.nan
                    inning_df = inning_df.rename(columns={"inning": "Type"})
                    inning_df = inning_df.sort_values("Type").reset_index(drop=True)
                    inning_df["Type"] = inning_df["Type"].replace(inning_dict)
                    inning_df_list.append(inning_df)
                platoon_data = pd.concat(inning_df_list)
                
                extra_pa = events_df[events_df["inning"] > 9]

                player_outs_sum = extra_pa.groupby(["fld_league", "fld_team", "pitcher_name"])['event_out'].sum()

                player_ip = player_outs_sum.apply(calculate_ip)
                player_ip_df = player_ip.reset_index()
                player_ip_df.columns = ["fld_league", "fld_team", "pitcher_name", "IP"]

                extra_df = extra_pa.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                    G=('game_id', 'nunique'),  # ゲーム数
                    R=('runs_scored', 'sum'),  # 許した得点数
                    BF=("events", lambda x: ((x != "pickoff_1b")&(x != "pickoff_2b")&(x != "pickoff_catcher")&(x != "caught_stealing")&(x != "stolen_base")&(x != "wild_pitch")&(x != "balk")&(x != "passed_ball")&(x != "caught_stealing")&(x != "runner_out")).sum()),
                    O=('event_out', 'sum'), 
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),  # 被本塁打数
                    single=('events', lambda x: (x == "single").sum()),
                    double=('events', lambda x: (x == "double").sum()),
                    triple=('events', lambda x: (x == "triple").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    WP=("WP", "sum"),
                    BK=('events', lambda x: (x == "balk").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                )
                extra_df = pd.merge(extra_df, player_ip_df, on=["fld_league", "fld_team", "pitcher_name"], how='left')
                extra_df['GS'] = np.nan
                extra_df['G'] = np.nan
                extra_df = extra_df.assign(Type="Extra Innings")

                platoon_data = pd.concat([platoon_data, extra_df]).reset_index(drop=True)
                
                platoon_data["inning"] = platoon_data["O"]/3
                platoon_data["AB"] = platoon_data["BF"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])
                platoon_data["H"] = platoon_data["single"] + platoon_data["double"] + platoon_data["triple"] + platoon_data["HR"]
                platoon_data['k/9'] = platoon_data['SO'] * 9 / platoon_data['inning']
                platoon_data['bb/9'] = platoon_data['BB'] * 9 / platoon_data['inning']
                platoon_data['K/9'] = my_round(platoon_data['k/9'], 2)
                platoon_data['BB/9'] = my_round(platoon_data['bb/9'], 2)
                platoon_data['k%'] = platoon_data["SO"]/platoon_data["BF"]
                platoon_data['bb%'] = platoon_data["BB"]/platoon_data["BF"]
                platoon_data['hr%'] = platoon_data["HR"]/platoon_data["BF"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["HR%"] = my_round(platoon_data["hr%"], 3)
                platoon_data["k-bb%"] = platoon_data["k%"] - platoon_data["bb%"]
                platoon_data["K-BB%"] = my_round(platoon_data["k-bb%"], 3)
                platoon_data['K/BB'] = my_round(platoon_data['SO'].astype(int) / platoon_data['BB'].astype(int), 2)
                platoon_data['HR/9'] = my_round(platoon_data['HR'] * 9 / platoon_data['inning'], 2)
                platoon_data['ra'] = platoon_data['R'] * 9 / platoon_data['inning']
                platoon_data['RA'] = my_round(platoon_data['ra'], 2)
                platoon_data = pd.merge(platoon_data, league_fip_data, on="fld_league", how="left")
                platoon_data['fip'] = (13*platoon_data["HR"] + 3*(platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"]) - 2*platoon_data["SO"])/platoon_data["inning"] + platoon_data["cFIP"]
                platoon_data['FIP'] = my_round(platoon_data['fip'], 2)
                platoon_data["r-f"] = platoon_data["ra"] - platoon_data["fip"]
                platoon_data["R-F"] = my_round(platoon_data["r-f"], 2)
                
                platoon_data = platoon_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
                platoon_data = platoon_data[["Team", "Type", "G", "GS", "IP", "BF", "H", "R", "HR", "BB", "SO", "HBP", "K%", "BB%", "HR%", "K/9", "BB/9", "K/BB", "FIP"]]
                df_style = platoon_data.style.format({
                    'GS': '{:.0f}',
                    'IP': '{:.1f}',
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'HR%': '{:.1%}',
                    'K/9': '{:.2f}',
                    'BB/9': '{:.2f}',
                    'K/BB': '{:.2f}',
                    'FIP': '{:.2f}',
                })
                st.dataframe(df_style, use_container_width=True)

            elif stats_type == "Batting":
                events_df = events_df[events_df["batter_id"] == player_id]
                plate_df = plate_df[plate_df["batter_id"] == player_id]
                merged_data = merged_data[merged_data["batter_id"] == player_id]
                PA_df = PA_df[PA_df["batter_id"] == player_id]

                st.header("Platoon Splits")
                platoon_data = PA_df.groupby(["bat_league", "bat_team", "batter_name", "p_throw"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["SB"] = np.nan
                platoon_data["CS"] = np.nan
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data["p_throw"] = platoon_data["p_throw"].str.replace("右", "vs Right")
                platoon_data["p_throw"] = platoon_data["p_throw"].str.replace("左", "vs Left")
                platoon_data = platoon_data.rename(columns={"p_throw": "Type"})
                platoon_data = platoon_data.sort_values("Type").reset_index(drop=True)
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SB", "CS", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Monthly Splits")
                PA_df["month_en"] = PA_df["game_month"].replace(month_dict)
                sb_df["month_en"] = sb_df["game_month"].replace(month_dict)

                platoon_data = PA_df.groupby(["bat_league", "bat_team", "batter_name", "month_en"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                platoon_data = platoon_data.rename(columns={"month_en": "Type", "bat_team": "Team"})
                platoon_data = platoon_data.sort_values("Type")
                platoon_data["Type"] = platoon_data["Type"].str[3:]
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = sb_df[(sb_df["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["month_en", "bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["month_en", "bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["month_en", "bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["month_en", "bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["month_en", "bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["month_en", "bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["month_en", "bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})
                runner_df["Type"] = runner_df["Type"].str[3:]
                platoon_data['batter_name_no_space'] = platoon_data['batter_name'].str.replace(" ", "")
                platoon_data = partial_match_merge_2(platoon_data, runner_df, 'batter_name_no_space', 'runner_name', ["Type", "Team"])

                if league_type == "1軍":
                    pre_allstar_data = PA_df = PA_df[PA_df["game_date"] < datetime(2024, 7, 23)]
                    pre_allstar_sb = sb_df = sb_df[sb_df["game_date"] < datetime(2024, 7, 23)]
                    pre_allstar = pre_allstar_data.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                        PA=('events', 'size'),  # 許した得点数
                        O=('event_out', 'sum'), 
                        Single=('events', lambda x: (x == "single").sum()),
                        Double=('events', lambda x: (x == "double").sum()),
                        Triple=('events', lambda x: (x == "triple").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                        GDP=('events', lambda x: (x == "double_play").sum()),
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        IFH = ("IFH", "sum"),
                    )
                    pre_allstar = pre_allstar.rename(columns={"month_en": "Type", "bat_team": "Team"})


                    runner = ["100", "010", "001", "110", "101", "011", "111"]
                    sb_data_list = []
                    for r in runner:
                        sb_data = pre_allstar_sb[(pre_allstar_sb["runner_id"] == r)]
                        if r[0] == "1":
                            sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                            if len(sb_1b) > 0:
                                sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                                sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                                sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                                sb_data_list.append(sb_data_1)
                            
                        if r[1] == "1":
                            sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                            if len(sb_2b) > 0:
                                sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                                sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                                sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                                sb_data_list.append(sb_data_2)

                        if r[2] == "1":
                            sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                            if len(sb_3b) > 0:
                                sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                                sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                                sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                                sb_data_list.append(sb_data_3)

                    sb_data = pd.concat(sb_data_list)

                    runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                        SB=("SB", "sum"),
                        CS=("CS", "sum"),
                    ).sort_values("SB", ascending=False)
                    runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                    pre_allstar['batter_name_no_space'] = pre_allstar['batter_name'].str.replace(" ", "")
                    pre_allstar = partial_match_merge(pre_allstar, runner_df, 'batter_name_no_space', 'runner_name')
                    pre_allstar = pre_allstar.assign(Type = "Pre All-Star")
                    platoon_data = pd.concat([platoon_data, pre_allstar]).reset_index(drop=True)
                    
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data["SB"] = platoon_data["SB"].fillna(0).astype(int)
                platoon_data["CS"] = platoon_data["CS"].fillna(0).astype(int)
                
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SB", "CS", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Batting Order Splits")

                platoon_data = PA_df.groupby(["bat_league", "bat_team", "batter_name", "order"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data = platoon_data.rename(columns={"order": "Type"})
                platoon_data = platoon_data.sort_values("Type").reset_index(drop=True)
                platoon_data["Type"] = platoon_data["Type"].replace(order_dict)
                platoon_data["SB"] = np.nan
                platoon_data["CS"] = np.nan
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SB", "CS", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Baserunner Splits")
                runner_df_list = []
                for r in list(runner_dict):
                    runner_pa = PA_df[PA_df["runner_id"] == r]
                    platoon_data = runner_pa.groupby(["bat_league", "bat_team", "batter_name", "runner_id"], as_index=False).agg(
                        PA=('events', 'size'),  # 許した得点数
                        O=('event_out', 'sum'), 
                        Single=('events', lambda x: (x == "single").sum()),
                        Double=('events', lambda x: (x == "double").sum()),
                        Triple=('events', lambda x: (x == "triple").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                        GDP=('events', lambda x: (x == "double_play").sum()),
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        IFH = ("IFH", "sum"),
                    )
                    runner_df_list.append(platoon_data)

                platoon_data = pd.concat(runner_df_list).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"runner_id": "Type"})
                platoon_data["Type"] = platoon_data["Type"].replace(runner_dict)
                scoring_data = PA_df[(PA_df["runner_id"] != "000")&(PA_df["runner_id"] != "100")]
                scoring_df = scoring_data.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                scoring_df = scoring_df.assign(Type = "Scoring Position")
                platoon_data = pd.concat([platoon_data, scoring_df]).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data["SB"] = np.nan
                platoon_data["CS"] = np.nan
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "GDP", "SB", "CS", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)
                st.header("Game Type Splits")

                home_pa = PA_df[PA_df["bat_team"] == PA_df["home_team"]]
                home_sb = sb_df[sb_df["bat_team"] == sb_df["home_team"]]
                home_df = home_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                home_df = home_df.rename(columns={"bat_team": "Team"})
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = home_sb[(home_sb["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                home_df['batter_name_no_space'] = home_df['batter_name'].str.replace(" ", "")
                home_df = partial_match_merge(home_df, runner_df, 'batter_name_no_space', 'runner_name')
                home_df = home_df.drop(columns = "batter_name_no_space")
                home_df = home_df.assign(Type = "Home Games")

                away_pa = PA_df[PA_df["bat_team"] == PA_df["away_team"]]
                away_sb = sb_df[sb_df["bat_team"] == sb_df["away_team"]]
                away_df = away_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                away_df = away_df.rename(columns={"bat_team": "Team"})
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = away_sb[(away_sb["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                away_df['batter_name_no_space'] = away_df['batter_name'].str.replace(" ", "")
                away_df = partial_match_merge(away_df, runner_df, 'batter_name_no_space', 'runner_name')
                away_df = away_df.drop(columns = "batter_name_no_space")
                away_df = away_df.assign(Type = "Away Games")

                PA_df['start_time'] = pd.to_datetime(PA_df['start_time'], format='%H:%M:%S').dt.time
                sb_df['start_time'] = pd.to_datetime(sb_df['start_time'], format='%H:%M:%S').dt.time

                day_pa = PA_df[PA_df["start_time"] < dt.time(17, 0, 0)]
                day_sb = sb_df[sb_df["start_time"] < dt.time(17, 0, 0)]
                day_df = day_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                day_df = day_df.rename(columns={"bat_team": "Team"})
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = day_sb[(day_sb["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                day_df['batter_name_no_space'] = day_df['batter_name'].str.replace(" ", "")
                day_df = partial_match_merge(day_df, runner_df, 'batter_name_no_space', 'runner_name')
                day_df = day_df.drop(columns = "batter_name_no_space")
                day_df = day_df.assign(Type = "Day Games")

                night_pa = PA_df[PA_df["start_time"] >= dt.time(17, 0, 0)]
                night_sb = sb_df[sb_df["start_time"] >= dt.time(17, 0, 0)]
                night_df = night_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                night_df = night_df.rename(columns={"bat_team": "Team"})
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = night_sb[(night_sb["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                night_df['batter_name_no_space'] = night_df['batter_name'].str.replace(" ", "")
                night_df = partial_match_merge(night_df, runner_df, 'batter_name_no_space', 'runner_name')
                night_df = night_df.assign(Type = "Night Games")
                night_df = night_df.drop(columns = "batter_name_no_space")

                leading_pa = PA_df[PA_df["bat_score"] > PA_df["fld_score"]]
                leading_df = leading_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                leading_df = leading_df.rename(columns={"bat_team": "Team"})
                leading_df["SB"] = np.nan
                leading_df["CS"] = np.nan
                leading_df = leading_df.assign(Type = "Leading Off")

                late_pa = PA_df[PA_df["bat_score"] <= PA_df["fld_score"]]
                late_df = late_pa.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                )
                late_df = late_df.rename(columns={"bat_team": "Team"})
                late_df["SB"] = np.nan
                late_df["CS"] = np.nan
                late_df = late_df.assign(Type = "Late / Close")

                platoon_data = pd.concat([home_df, away_df, day_df, night_df, leading_df, late_df]).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SB", "CS", "GDP","K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'SB': '{:.0f}',
                    'CS': '{:.0f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Outs Splits")

                platoon_data = PA_df.groupby(["bat_league", "bat_team", "batter_name", "out_count"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data = platoon_data.rename(columns={"out_count": "Type"})
                platoon_data = platoon_data.sort_values("Type").reset_index(drop=True)
                platoon_data["Type"] = platoon_data["Type"].replace(outs_dict)
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                st.header("Inning Splits")

                inning_df_list = []
                for i in list(inning_dict):
                    inning_pa = PA_df[PA_df["inning"] == i]
                    inning_sb = sb_df[sb_df["inning"] == i]
                    platoon_data = inning_pa.groupby(["bat_league", "bat_team", "batter_name", "inning"], as_index=False).agg(
                        PA=('events', 'size'),  # 許した得点数
                        O=('event_out', 'sum'), 
                        Single=('events', lambda x: (x == "single").sum()),
                        Double=('events', lambda x: (x == "double").sum()),
                        Triple=('events', lambda x: (x == "triple").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                        GDP=('events', lambda x: (x == "double_play").sum()),
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        IFH = ("IFH", "sum"),
                    )
                    platoon_data = platoon_data.rename(columns={"bat_team": "Team"})
                    runner = ["100", "010", "001", "110", "101", "011", "111"]
                    sb_data_list = []
                    for r in runner:
                        sb_data = inning_sb[(inning_sb["runner_id"] == r)]
                        if r[0] == "1":
                            sb_1b = sb_data[["bat_league", "bat_team", "inning", "on_1b", "des"]]
                            if len(sb_1b) > 0:
                                sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                                sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                                sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "inning", "on_1b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                                sb_data_list.append(sb_data_1)
                            
                        if r[1] == "1":
                            sb_2b = sb_data[["bat_league", "bat_team", "inning", "on_2b", "des"]]
                            if len(sb_2b) > 0:
                                sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                                sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                                sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "inning", "on_2b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                                sb_data_list.append(sb_data_2)

                        if r[2] == "1":
                            sb_3b = sb_data[["bat_league", "bat_team", "inning", "on_3b", "des"]]
                            if len(sb_3b) > 0:
                                sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                                sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                                sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "inning", "on_3b"], as_index=False).agg(
                                    SB=("StolenBase", "sum"),
                                    CS=("CaughtStealing", "sum")
                                )
                                sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                                
                                sb_data_list.append(sb_data_3)

                    sb_data = pd.concat(sb_data_list)

                    runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name", "inning"], as_index=False).agg(
                        SB=("SB", "sum"),
                        CS=("CS", "sum"),
                    ).sort_values("SB", ascending=False)
                    runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                    platoon_data['batter_name_no_space'] = platoon_data['batter_name'].str.replace(" ", "")
                    platoon_data = partial_match_merge_2(platoon_data, runner_df, 'batter_name_no_space', 'runner_name', ["Team", "inning"])
                    inning_df_list.append(platoon_data)

                platoon_data = pd.concat(inning_df_list).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"inning": "Type"})
                platoon_data["Type"] = platoon_data["Type"].replace(inning_dict)
                extra_data = PA_df[PA_df["inning"] > 9]
                extra_sb = sb_df[sb_df["inning"] > 9]
                extra_df = extra_data.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                extra_df = extra_df.rename(columns={"bat_team": "Team"})
                runner = ["100", "010", "001", "110", "101", "011", "111"]
                sb_data_list = []
                for r in runner:
                    sb_data = extra_sb[(extra_sb["runner_id"] == r)]
                    if r[0] == "1":
                        sb_1b = sb_data[["bat_league", "bat_team", "on_1b", "des"]]
                        if len(sb_1b) > 0:
                            sb_1b['StolenBase'] = sb_1b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_1b['CaughtStealing'] = sb_1b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_1b'] in row['des']) else 0, axis=1)
                            sb_data_1 = sb_1b.groupby(["bat_league", "bat_team", "on_1b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_1 = sb_data_1.rename(columns={"on_1b": "runner_name"})
                            sb_data_list.append(sb_data_1)
                        
                    if r[1] == "1":
                        sb_2b = sb_data[["bat_league", "bat_team", "on_2b", "des"]]
                        if len(sb_2b) > 0:
                            sb_2b['StolenBase'] = sb_2b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_2b['CaughtStealing'] = sb_2b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_2b'] in row['des']) else 0, axis=1)
                            sb_data_2 = sb_2b.groupby(["bat_league", "bat_team", "on_2b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_2 = sb_data_2.rename(columns={"on_2b": "runner_name"})
                            sb_data_list.append(sb_data_2)

                    if r[2] == "1":
                        sb_3b = sb_data[["bat_league", "bat_team", "on_3b", "des"]]
                        if len(sb_3b) > 0:
                            sb_3b['StolenBase'] = sb_3b.apply(lambda row: 1 if ('盗塁成功' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_3b['CaughtStealing'] = sb_3b.apply(lambda row: 1 if ('盗塁失敗' in row['des'] and row['on_3b'] in row['des']) else 0, axis=1)
                            sb_data_3 = sb_3b.groupby(["bat_league", "bat_team", "on_3b"], as_index=False).agg(
                                SB=("StolenBase", "sum"),
                                CS=("CaughtStealing", "sum")
                            )
                            sb_data_3 = sb_data_3.rename(columns={"on_3b": "runner_name"})
                            
                            sb_data_list.append(sb_data_3)

                sb_data = pd.concat(sb_data_list)

                runner_df =sb_data.groupby(["bat_league", "bat_team", "runner_name"], as_index=False).agg(
                    SB=("SB", "sum"),
                    CS=("CS", "sum"),
                ).sort_values("SB", ascending=False)
                runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League", "month_en": "Type"})

                extra_df['batter_name_no_space'] = extra_df['batter_name'].str.replace(" ", "")
                extra_df = partial_match_merge(extra_df, runner_df, 'batter_name_no_space', 'runner_name')
                extra_df = extra_df.assign(Type = "Extra Innings")
                platoon_data = pd.concat([platoon_data, extra_df]).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data["SB"] = platoon_data["SB"].fillna(0).astype(int)
                platoon_data["CS"] = platoon_data["CS"].fillna(0).astype(int)
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "SB", "CS", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)


                st.header("Positional Splits")
                position_list = []
                for i in range(len(pos_ja_dict)):
                    p_jp = list(pos_ja_dict)[i]
                    p_en = pos_ja_dict[p_jp]
                    position_pa = PA_df[PA_df["batter_pos"] == p_jp]
                    platoon_data = position_pa.groupby(["bat_league", "bat_team", "batter_name", "batter_pos"], as_index=False).agg(
                        PA=('events', 'size'),  # 許した得点数
                        O=('event_out', 'sum'), 
                        Single=('events', lambda x: (x == "single").sum()),
                        Double=('events', lambda x: (x == "double").sum()),
                        Triple=('events', lambda x: (x == "triple").sum()),
                        SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                        GDP=('events', lambda x: (x == "double_play").sum()),
                        SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                        IBB=('events', lambda x: (x == "intentional_walk").sum()),
                        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                        HR=('events', lambda x: (x == "home_run").sum()),
                        obstruction=('events', lambda x: (x == "obstruction").sum()),
                        interference=('events', lambda x: (x == "interference").sum()),
                        IFH = ("IFH", "sum"),
                    )
                    position_list.append(platoon_data)
                platoon_data = pd.concat(position_list).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"batter_pos": "Type"})
                platoon_data["Type"] = platoon_data["Type"].replace(pos_ja_dict)
                start_data = PA_df[PA_df["Start"] == 1]
                start_df = start_data.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                start_df = start_df.assign(Type = "Starting")
                platoon_data = pd.concat([platoon_data, start_df]).reset_index(drop=True)

                bench_data = PA_df[PA_df["Start"] == 0]
                bench_df = bench_data.groupby(["bat_league", "bat_team", "batter_name"], as_index=False).agg(
                    PA=('events', 'size'),  # 許した得点数
                    O=('event_out', 'sum'), 
                    Single=('events', lambda x: (x == "single").sum()),
                    Double=('events', lambda x: (x == "double").sum()),
                    Triple=('events', lambda x: (x == "triple").sum()),
                    SH=('events', lambda x: ((x == "sac_bunt") | (x == "bunt_error") | (x == "bunt_fielders_choice")).sum()),
                    SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
                    GDP=('events', lambda x: (x == "double_play").sum()),
                    SO=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
                    BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                    IBB=('events', lambda x: (x == "intentional_walk").sum()),
                    HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
                    HR=('events', lambda x: (x == "home_run").sum()),
                    obstruction=('events', lambda x: (x == "obstruction").sum()),
                    interference=('events', lambda x: (x == "interference").sum()),
                    IFH = ("IFH", "sum"),
                )
                bench_df = bench_df.assign(Type = "Bench")
                platoon_data = pd.concat([platoon_data, bench_df]).reset_index(drop=True)
                platoon_data = platoon_data.rename(columns={"game_year": "Season","game_year": "Season", "bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
                platoon_data["AB"] = (platoon_data["PA"] - (platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SH"] + platoon_data["SF"] + platoon_data["obstruction"] + platoon_data["interference"])).astype(int)
                platoon_data["H"] = (platoon_data["1B"] + platoon_data["2B"] + platoon_data["3B"] + platoon_data["HR"]).astype(int)
                platoon_data["avg"] = platoon_data["H"]/platoon_data["AB"]
                platoon_data["AVG"] = my_round(platoon_data["avg"], 3)
                platoon_data["obp"] = (platoon_data["H"] + platoon_data["BB"] + platoon_data["HBP"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["OBP"] = my_round(platoon_data["obp"], 3)
                platoon_data["slg"] = (platoon_data["1B"] + 2*platoon_data["2B"] + 3*platoon_data["3B"] + 4*platoon_data["HR"]).astype(int)/platoon_data["AB"]
                platoon_data["SLG"] = my_round(platoon_data["slg"], 3)
                platoon_data["ops"] = platoon_data["obp"] + platoon_data["slg"]
                platoon_data["OPS"] = my_round(platoon_data["ops"], 3)
                platoon_data["iso"] = platoon_data["slg"] - platoon_data["avg"]
                platoon_data["ISO"] = my_round(platoon_data["iso"], 3)
                platoon_data["babip"] = (platoon_data["H"] - platoon_data["HR"]).astype(int)/(platoon_data["AB"] - platoon_data["SO"] - platoon_data["HR"] + platoon_data["SF"]).astype(int)
                platoon_data["BABIP"] = my_round(platoon_data["babip"], 3)
                platoon_data["k%"] = platoon_data["SO"]/platoon_data["PA"]
                platoon_data["bb%"] = platoon_data["BB"]/platoon_data["PA"]
                platoon_data["K%"] = my_round(platoon_data["k%"], 3)
                platoon_data["BB%"] = my_round(platoon_data["bb%"], 3)
                platoon_data["BB/K"] = my_round(platoon_data["BB"].astype(int)/platoon_data["SO"].astype(int), 2)
                platoon_data["woba"] = wOBA_scale * (bb_value * (platoon_data["BB"] - platoon_data["IBB"]) + hbp_value * platoon_data["HBP"] + single_value * platoon_data["1B"] + double_value * platoon_data["2B"] + triple_value * platoon_data["3B"] + hr_value * platoon_data["HR"]).astype(int)/(platoon_data["AB"] + platoon_data["BB"] - platoon_data["IBB"] + platoon_data["HBP"] + platoon_data["SF"]).astype(int)
                platoon_data["wOBA"] = my_round(platoon_data["woba"], 3)
                platoon_data = platoon_data[["Team", "Type", "PA", "AB", "H", "2B", "3B", "HR", "BB", "SO", "HBP", "GDP", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wOBA"]]
                df_style = platoon_data.style.format({
                    'K%': '{:.1%}',
                    'BB%': '{:.1%}',
                    'AVG': '{:.3f}',
                    'OBP': '{:.3f}',
                    'SLG': '{:.3f}',
                    'OPS': '{:.3f}',
                    'ISO': '{:.3f}',
                    'BABIP': '{:.3f}',
                    'wOBA': '{:.3f}',
                })
                st.dataframe(df_style, use_container_width=True)

                    
                    


            

