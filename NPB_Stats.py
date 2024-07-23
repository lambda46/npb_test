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
import time
import math
import requests
from bs4 import BeautifulSoup
from source.my_func import cal_RE24, cal_PF, my_round

st.set_page_config(layout='wide')
st.title("NPB Stats")

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


# FIPを計算する関数
def calculate_fip(hr, bb, ibb, hbp, k, ip, league_hr_rate):
    fip_constant = (league_hr_rate * 13 + 3 * (bb - ibb + hbp) - 2 * k) / ip
    fip = ((13 * hr + 3 * (bb - ibb + hbp) - 2 * k) / ip) + fip_constant
    return fip


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

sz_left = 20.3
sz_right = 114.8
sz_top = 26.8*-1+200
sz_bot = 146.3*-1+200

# ストライクゾーンの範囲
strike_zone_x_range = (sz_left, sz_right)
strike_zone_z_range = (sz_bot, sz_top)

# 各投球のゾーンを計算する関数
zone_width = (sz_right - sz_left) / 3
zone_height = (sz_top - sz_bot) / 3
zone_w_half = (sz_right - sz_left) / 2
zone_h_half = (sz_top - sz_bot) / 2

# 各投球のゾーンを計算する関数
def calculate_frame_zone(row):
    plate_x = row['plate_x']
    plate_z = row['plate_z']
    if plate_x < zone_w_half:
        if plate_z > zone_h_half:
            return 1  # 左上
        elif plate_z < zone_h_half:
            return 2  # 左下
    elif plate_x > zone_w_half:
        if plate_z > zone_h_half:
            return 3  # 右上
        elif plate_z < zone_h_half:
            return 4  # 右下
    return None  # ゾーン外の他の位置（任意で11~14以外の番号に変更）

data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
latest_date = data["game_date"].max()
latest_date_str = latest_date.strftime("%Y/%m/%d")
year_list = list(data['game_date'].dt.year.unique())
year_list.sort(reverse=True)

game_type_list = ["レギュラーシーズン", "レギュラーシーズン(交流戦以外)", "交流戦"]

pl_list = ["オリックス", "ロッテ", "ソフトバンク", "楽天", "西武", "日本ハム"]
cl_list = ["阪神", "広島", "DeNA", "巨人", "ヤクルト", "中日"]
  
team_en_dict = {
    "オリックス": "B", "ロッテ": "M", "ソフトバンク": "H", "楽天": "E", "西武": "L", "日本ハム": "F", 
    "阪神": "T", "広島": "C", "DeNA": "DB", "巨人": "G", "ヤクルト": "S", "中日": "D",
    "オイシックス": "A", "くふうハヤテ": "V"
}

pos_en_dict = {
    "P": "投", "C": "捕", "1B": "一", "2B": "二", "3B": "三", "SS": "遊",
    "LF": "左", "CF": "中", "RF": "右", "DH": "指", "PH": "打", "PR": "走"
}

pos_en_dict = {
    "P": "投", "C": "捕", "1B": "一", "2B": "二", "3B": "三", "SS": "遊",
    "LF": "左", "CF": "中", "RF": "右", "DH": "指", "PH": "打", "PR": "走"
}

pos_ja_dict = {
    "投": "P", "捕": "C", "一": "1B", "二": "2B", "三": "3B", "遊": "SS",
    "左": "LF", "中": "CF", "右": "RF", "指": "DH", "打": "PH", "走": "PR"
}

runner_dict = {
    "Bases Empty": "000", "Bases Loaded": "111", "Runner at 1st": "100", 
    "Runners at 1st & 2nd": "110", "Runners at 1st & 3rd": "101", 
    "Runner at 2nd": "010", "Runners at 2nd and 3rd": "011", "Runner at 3rd": "001"
}

pos_num_dict = {
    1: "P", 2: "C", 3: "1B", 4: "2B", 5: "3B", 6: "SS", 7: "LF", 8: "CF", 9: "RF"
}

pos_ja_num_dict = {
    1: "投", 2: "捕", 3: "一", 4: "二", 5: "三", 6: "遊", 7: "左", 8: "中", 9: "右"
}

side_dict = {
    "Right": "右", "Left": "左"
}

stats_type_list = ["Batting", "Pitching", "Fielding"]

cols = st.columns(2)
with cols[0]:
    stats_type = option_menu(None,
    stats_type_list,
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "0!important"},
        "icon": {"font-size": "15px"},
        "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px"},
    }
    )

leaderboard_list = ["Player Stats", "Team Stats", "League Stats"]

with cols[1]:
    mode = option_menu(None,
    leaderboard_list,
    menu_icon="cast", default_index=0, orientation="horizontal",
    styles={
        "container": {"padding": "0!important"},
        "icon": {"font-size": "15px"},
        "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px"},
    }
    )

group_index = leaderboard_list.index(mode)

columns_list = ["League", "Team", "Player"]
col_list = columns_list[:(3-group_index)]
if group_index == 0:
    c_list = columns_list[1:]
else:
    c_list = [columns_list[2-group_index]]

cols = st.columns(4)
with cols[0]:
    game_year = st.selectbox(
        "Season",
        year_list,
        index=0)
with cols[1]:
    game_type = st.selectbox(
        "Season Type",
        game_type_list,
        index=0)
data = data[data["game_date"].dt.year == game_year].reset_index(drop=True)
with cols[2]:
    league_select = st.selectbox(
        "League",
        ["All Leagues", "セ・リーグ", "パ・リーグ"],
        index=0
    )
    
if league_select == "All Leagues":
    team_list = ["All Teams"] + pl_list + cl_list
elif league_select == "セ・リーグ":
    team_list = ["All Teams"] + cl_list
elif league_select == "パ・リーグ":
    team_list = ["All Teams"] + pl_list
with cols[3]:
    if group_index <= 1:
        team_select = st.selectbox(
            "Team",
            team_list,
            index=0
        )
    else:
        team_select = st.selectbox(
            "Team",
            ["All Teams"],
            index=0
        )

cols = st.columns(4)
if stats_type == "Batting":
    pos_list = ["All", "IF", "OF", "NP"] + list(pos_en_dict)
elif stats_type == "Pitching":
    pos_list = ["All", "SP", "RP"]
elif stats_type == "Fielding":
    pos_list = ["All"] + list(pos_en_dict)[:9]
with cols[0]:
    pos_select = st.selectbox(
        "Positional Split",
        pos_list,
        index=0
    )

with cols[1]:
    side_select = st.selectbox(
        "Side",
        ["Both", "Right", "Left"],
        index=0
    )

if stats_type == "Batting":
    split_list = ["No Splits", "Yesterday", "Last 7days", "Last 14days", "Last 30days", 
         "March/April", "May", "June", "July", "August", "Sept~", "vsRHP", "vsLHP", "Grounders", "Flies", "Liners",
         "Pull", "Center", "Opposite",
         "Home", "Away", "Bases Empty", "Runners on Base", "Runners on Scoring", "Bases Loaded",
         "Runner at 1st", "Runner at 2nd", "Runner at 3rd", 
         "Runners at 1st & 2nd", "Runners at 1st & 3rd", "Runners at 2nd & 3rd", 
         "Batting 1st", "Batting 2nd", "Batting 3rd", "Batting 4th", "Batting 5th", 
         "Batting 6th", "Batting 7th", "Batting 8th", "Batting 9th",
         "vs 阪神", "vs 広島", "vs DeNA", "vs 巨人", "vs ヤクルト", "vs 中日",
         "vs オリックス", "vs ロッテ", "vs ソフトバンク", "vs 楽天", "vs 西武", "vs 日本ハム",
         "0 Outs", "1 Out", "2 Outs", 
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
elif stats_type == "Fielding":
    split_list = ["No Splits"]
with cols[2]:
    split = st.selectbox(
        "Split",
        split_list,
        index=0
    )
if group_index == 0:
    if stats_type == "Batting":
        pa_list = ['Qualified', '0', '1', '5', '10', '20', '30', '40', '50', '60', '70', '80', '90', 
                   '100', '110', '120', '130', '140', '150', '160', '170', '180', '190', 
                   '200', '210', '220', '230', '240', '250', '300', '350', '400', '450',
                   '500'
                   ]
    elif stats_type == "Pitching":
        pa_list = ['Qualified', '0', '1', '5', '10', '20', '30', '40', '50', '60', '70', '80', '90', 
                   '100', '110', '120', '130', '140', '150', '160', '170', '180', '190', '200']
    elif stats_type == "Fielding":
        pa_list = ['Qualified', '0', '1', '5', '10', '20', '30', '40', '50', '60', '70', '80', '90', 
                   '100', '110', '120', '130', '140', '150', '160', '170', '180', '190', 
                   '200', '210', '220', '230', '240', '250', '300', '350', '400', '450',
                   '500', '550', '600', '650', '700', '750', '800', '850', '900', '950'
                   ]
else:
    pa_list = ["Qualified"]
if stats_type == "Batting":
    min_text = 'Min PA'
elif stats_type == "Pitching":
    min_text = 'Min IP'
elif stats_type == "Fielding":
    min_text = 'Min Inn'

with cols[3]:
    min_PA = st.selectbox(
        min_text,
        pa_list,
        index = 0)
    if min_PA == "Qualified":
        q = 'Q == 1'
    else:
        if stats_type == "Batting":
            q = 'PA >=' + min_PA
        elif stats_type == "Pitching":
            q = 'IP >=' + min_PA
        elif stats_type == "Fielding":
            q = 'Inn >=' + min_PA


            


st.markdown(f"{latest_date_str} 終了時点")

if stats_type == "Fielding":
    tabs_list = ["Standard", "Advanced"]
else:
    tabs_list = ["Dashboard", "Standard", "Advanced", "Batted Ball", "Plate Discipline", "Pitch Type", "Pitch Value"]
tab = st.tabs(tabs_list)

data["runner_id"] = data["runner_id"].astype(str).str.zfill(3)
data["post_runner_id"] = data["post_runner_id"].astype(str).str.zfill(3)
data["B-S"] = data["balls"].astype(str).str.cat(data["strikes"].astype(str), sep="-")
starter_condition = (data['inning'] == 1) & (data['order'] == 1) & (data['pitch_number'] == 1) & (data['ab_pitch_number'] == 1) & (data['out_count'] == 0) & (data['bat_score'] == 0) & (data['runner_id'] == "000")
sp_df = data[starter_condition].assign(StP = 1)
data = pd.merge(data, sp_df[["fld_team", "pitcher_name", "game_id", "StP"]], on=["fld_team", "pitcher_name", "game_id"], how="left")
data["StP"] = data["StP"].fillna(0)


d = 10

sz_left = 20.3
sz_right = 114.8
sz_top = 26.8*-1+200
sz_bot = 146.3*-1+200

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

pf = cal_PF(PA_df=PA_df, league_type="1軍")

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
events_df["STATE"] = events_df["runner_id"].str.cat(events_df["out_count"].astype(str), sep="-")

df2024["NEW.STATE"] = df2024["post_runner_id"].str.cat(df2024["post_out_count"].astype(str), sep="-")
sb_df["NEW.STATE"] = sb_df["post_runner_id"].str.cat(sb_df["post_out_count"].astype(str), sep="-")
events_df["NEW.STATE"] = events_df["post_runner_id"].str.cat(events_df["post_out_count"].astype(str), sep="-")

RUNS = cal_RE24(PA_df=df2024)

df2024 = pd.merge(df2024, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})
sb_df = pd.merge(sb_df, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})
events_df = pd.merge(events_df, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})

df2024 = pd.merge(df2024, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
sb_df = pd.merge(sb_df, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
events_df = pd.merge(events_df, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
df2024["Runs.New.State"] = df2024["Runs.New.State"].fillna(0)
sb_df["Runs.New.State"] = sb_df["Runs.New.State"].fillna(0)
events_df["Runs.New.State"] = events_df["Runs.New.State"].fillna(0)
df2024["run_value"] = df2024["Runs.New.State"] - df2024["Runs.State"] + df2024["runs_scored"]
sb_df["run_value"] = sb_df["Runs.New.State"] - sb_df["Runs.State"] + sb_df["runs_scored"]
events_df["run_value"] = events_df["Runs.New.State"] - events_df["Runs.State"] + events_df["runs_scored"]
events_df['WP'] = events_df['des'].apply(lambda x: 1 if '暴投' in x else 0)
events_df['PB'] = events_df['des'].apply(lambda x: 1 if '捕逸' in x else 0)
events_df['TE'] = events_df['des'].str.count('悪送球（')
events_df['FE'] = events_df['des'].apply(lambda x: 1 if '後逸（' in x or '失策（' in x or 'ファンブル（' in x else 0)
events_df['Scp_n'] = ((events_df['GB'] == 1) & (events_df['des'].str.contains("送球がバウンド", na=False))).astype(int)
events_df['Scp'] = ((events_df['GB'] == 1) & 
                    (events_df['des'].str.contains("送球がバウンド", na=False)) & 
                    (~events_df['des'].str.contains("悪送球", na=False))).astype(int)

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
gb_run = df2024[df2024["GB"] == 1]["run_value"].mean()
ld_run = df2024[df2024["LD"] == 1]["run_value"].mean()
iffb_run = df2024[df2024["IFFB"] == 1]["run_value"].mean()
offb_run = df2024[df2024["OFFB"] == 1]["run_value"].mean()
fb_run = df2024[df2024["FB"] == 1]["run_value"].mean()

sb_run = sb_df[sb_df["sb"] > 0]["run_value"].sum()/sb_n
cs_run = sb_df[sb_df["cs"] > 0]["run_value"].sum()/cs_n
wp_run = events_df[events_df["WP"] == 1]["run_value"].mean()
pb_run = events_df[events_df["PB"] == 1]["run_value"].mean()

hr_out = df2024[df2024["events"] == "home_run"]["event_out"].mean()
walk_out = df2024[(df2024["events"] == "walk")|(df2024["events"] == "intentional_walk")]["event_out"].mean()
hbp_out = df2024[df2024["events"] == "hit_by_pitch"]["event_out"].mean()
k_out = df2024[(df2024["events"] == "strike_out")|(df2024["events"] == "uncaught_third_strike")]["event_out"].mean()
gb_out = df2024[df2024["GB"] == 1]["event_out"].mean()
iffb_out = df2024[df2024["IFFB"] == 1]["event_out"].mean()
offb_out = df2024[df2024["OFFB"] == 1]["event_out"].mean()
ld_out = df2024[df2024["LD"] == 1]["event_out"].mean()

bb_value = bb_run - out_value
hbp_value = hbp_run - out_value
single_value = single_run - out_value
double_value = double_run - out_value
triple_value = triple_run - out_value
hr_value = hr_run - out_value
gb_value = gb_run - out_value
fb_value = fb_run - out_value
ld_value = ld_run - out_value
iffb_value = iffb_run - out_value
offb_value = offb_run - out_value

events_sum = df2024["events"].value_counts().to_dict()

sh_sum = events_sum.get("sac_bunt", 0) + events_sum.get("bunt_error", 0) + events_sum.get("bunt_fielders_choice", 0)
sf_sum = events_sum.get("sac_fly", 0) + events_sum.get("sac_fly_error", 0)
bb_sum = events_sum.get("walk", 0) + events_sum.get("intentional_walk", 0)
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
# 各イベントに対するpvを設定
merged_data.loc[other_events & (merged_data['events'] == 'home_run'), 'PV'] = merged_data['v_home_run']
merged_data.loc[other_events & (merged_data['events'] == 'hit_by_pitch'), 'PV'] = merged_data['v_hbp']
merged_data.loc[other_events & (merged_data['GB'] == 1), 'PV'] = merged_data['v_gb']
merged_data.loc[other_events & (merged_data['OFFB'] == 1), 'PV'] = merged_data['v_offb']
merged_data.loc[other_events & (merged_data['IFFB'] == 1), 'PV'] = merged_data['v_iffb']
merged_data.loc[other_events & (merged_data['LD'] == 1), 'PV'] = merged_data['v_ld']
if stats_type == "Batting":
    merged_data["pitch_value"] = merged_data["RV"]
elif stats_type == "Pitching":
    merged_data["pitch_value"] = merged_data["RV"] * -1

game_runs = data.groupby(["bat_league", "game_date", "home_team", "away_team"], as_index=False).tail(1)[["bat_league", "home_score", "away_score"]].reset_index(drop=True)
game_runs["game_score"] = game_runs["home_score"] + game_runs["away_score"]
rpw_df = game_runs.groupby(["bat_league"], as_index=False).agg(
    G = ("bat_league", "size"),
    R = ("game_score", "sum")
)
rpw_df["R/G"] = rpw_df["R"]/rpw_df["G"]
rpw_df["RPW"] = 2*(rpw_df["R/G"] **0.715)
rpw_df = rpw_df[["bat_league", "RPW"]]
rpw_df = rpw_df.set_axis(["League", "RPW"], axis=1)

plate_df = data.dropna(subset="pitch_number")

if stats_type == "Batting":
    group_list = ["bat_league", "bat_team", "batter_name"]
    
    league_bat_data = PA_df.groupby("bat_league", as_index=False).agg(
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
    league_bat_data = league_bat_data.rename(columns={"bat_league": "League", "Single": "1B", "Double": "2B", "Triple": "3B"})
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

    league_wrc_mean = league_bat_data[["League", "woba", "R", "PA", "SB", "CS", "1B", "BB", "HBP", "IBB"]].rename(columns={
        "woba": "woba_league", "R": "R_league", "PA": "PA_league", "SB": "SB_league", "CS": "CS_league",
        "1B": "1B_league", "BB": "BB_league", "HBP": "HBP_league", "IBB": "IBB_league"
        })

    team_game = PA_df.groupby(['bat_league', 'bat_team'], as_index=False).agg(
        G=('game_id', 'nunique')
    )
    player_pa = PA_df.groupby(['bat_league', 'bat_team', 'batter_name'], as_index=False).agg(
        PA=('events', 'size'),  # 許した得点数
    )

    player_pa = pd.merge(player_pa, team_game[['bat_team', 'G']].rename(columns={"G": "team_g"}), left_on='bat_team', right_on='bat_team', how='left')
    player_pa['threshold_pa'] = player_pa['team_g'] * 3.1
    player_pa['Q'] = np.where(player_pa['PA'] >= player_pa['threshold_pa'], 1, 0)
    player_pa = player_pa.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player"})

    
    if pos_select == "All":
        pass
    elif pos_select == "IF":
        PA_df = PA_df.query('batter_pos == "一" or batter_pos == "二" or batter_pos == "三" or batter_pos == "遊"')
        plate_df = plate_df.query('batter_pos == "一" or batter_pos == "二" or batter_pos == "三" or batter_pos == "遊"')
        merged_data = merged_data.query('batter_pos == "一" or batter_pos == "二" or batter_pos == "三" or batter_pos == "遊"')
        sb_df = sb_df.query('batter_pos == "一" or batter_pos == "二" or batter_pos == "三" or batter_pos == "遊"')
    elif pos_select == "OF":
        PA_df = PA_df.query('batter_pos == "左" or batter_pos == "中" or batter_pos == "右"')
        plate_df = plate_df.query('batter_pos == "左" or batter_pos == "中" or batter_pos == "右"')
        merged_data = merged_data.query('batter_pos == "左" or batter_pos == "中" or batter_pos == "右"')
        sb_df = sb_df.query('batter_pos == "左" or batter_pos == "中" or batter_pos == "右"')
    elif pos_select == "NP":
        PA_df = PA_df.query('batter_pos != "投"')
        plate_df = plate_df.query('batter_pos != "投"')
        merged_data = merged_data.query('batter_pos != "投"')
        sb_df = sb_df.query('batter_pos != "投"')
    else:
        PA_df = PA_df.query('batter_pos == "' + pos_en_dict[pos_select] + '"' )
        plate_df = plate_df.query('batter_pos == "' + pos_en_dict[pos_select] + '"' )
        merged_data = merged_data.query('batter_pos == "' + pos_en_dict[pos_select] + '"' )
        sb_df = sb_df.query('batter_pos == "' + pos_en_dict[pos_select] + '"' )

    if side_select != "Both":
        PA_df = PA_df[PA_df["stand"] == side_dict[side_select]]
        plate_df = plate_df[plate_df["stand"] == side_dict[side_select]]
        merged_data = merged_data[merged_data["stand"] == side_dict[side_select]]
        sb_df = sb_df[sb_df["stand"] == side_dict[side_select]]

    if game_type == "レギュラーシーズン":
        PA_df = PA_df[(PA_df["game_type"] == "セ・リーグ")|(PA_df["game_type"] == "パ・リーグ")|(PA_df["game_type"] == "セ・パ交流戦")]
        plate_df = plate_df[(plate_df["game_type"] == "セ・リーグ")|(plate_df["game_type"] == "パ・リーグ")|(plate_df["game_type"] == "セ・パ交流戦")]
        merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")|(merged_data["game_type"] == "セ・パ交流戦")]
        sb_df = sb_df[(sb_df["game_type"] == "セ・リーグ")|(sb_df["game_type"] == "パ・リーグ")|(sb_df["game_type"] == "セ・パ交流戦")]
    elif game_type == "交流戦":
        PA_df = PA_df[PA_df["game_type"] == "セ・パ交流戦"]
        plate_df = plate_df[plate_df["game_type"] == "セ・パ交流戦"]
        merged_data = merged_data[merged_data["game_type"] == "セ・パ交流戦"]
        sb_df = sb_df[sb_df["game_type"] == "セ・パ交流戦"]
    elif game_type == "レギュラーシーズン(交流戦以外)":
        PA_df = PA_df[(PA_df["game_type"] == "セ・リーグ")|(PA_df["game_type"] == "パ・リーグ")]
        plate_df = plate_df[(plate_df["game_type"] == "セ・リーグ")|(plate_df["game_type"] == "パ・リーグ")]
        merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")]
        sb_df = sb_df[(sb_df["game_type"] == "セ・リーグ")|(sb_df["game_type"] == "パ・リーグ")]
        
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
    elif "Out" in split:
        o = int(split.split(" ")[0])
        PA_df = PA_df[PA_df["out_count"] == o]
        plate_df = plate_df[plate_df["out_count"] == o]
        merged_data = merged_data[merged_data["out_count"] == o]
        sb_df = sb_df[sb_df["out_count"] == o]
    elif split == "Bases Empty":
        PA_df = PA_df[PA_df["runner_id"] == "000"]
        plate_df = plate_df[plate_df["runner_id"] == "000"]
        merged_data = merged_data[merged_data["runner_id"] == "000"]
        sb_df = sb_df[sb_df["runner_id"] == "000"]
    elif split == "Bases Loaded":
        PA_df = PA_df[PA_df["runner_id"] == "111"]
        plate_df = plate_df[plate_df["runner_id"] == "111"]
        merged_data = merged_data[merged_data["runner_id"] == "111"]
        sb_df = sb_df[sb_df["runner_id"] == "111"]
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
    elif "Runner at" in split:
        r = runner_dict[split]
        PA_df = PA_df[PA_df["runner_id"] == r]
        plate_df = plate_df[plate_df["runner_id"] == r]
        merged_data = merged_data[merged_data["runner_id"] == r]
        sb_df = sb_df[sb_df["runner_id"] == r]
    elif "Runners at" in split:
        r = runner_dict[split]
        PA_df = PA_df[PA_df["runner_id"] == r]
        plate_df = plate_df[plate_df["runner_id"] == r]
        merged_data = merged_data[merged_data["runner_id"] == r]
        sb_df = sb_df[sb_df["runner_id"] == r]
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

    lg_game = PA_df.groupby(["game_type"], as_index=False)["game_id"].nunique()
    lg_game["League"] = lg_game["game_type"]
    lg_game = lg_game.drop(columns="game_type")

    try:
        kouryusen = lg_game.loc[lg_game['League'] == "セ・パ交流戦", 'game_id'].iloc[0]
    except:
        kouryusen = 0

    player_bat_data = PA_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
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
        GB = ("GB", "sum"),
        FB = ("FB", "sum"),
        IFFB = ("IFFB", "sum"),
        OFFB = ("OFFB", "sum"),
        IFH = ("IFH", "sum"),
        LD = ("LD", "sum"),
        Pull = ("Pull", "sum"),
        Cent = ("Center", "sum"),
        Oppo = ("Opposite", "sum")
    )
    player_bat_data = player_bat_data.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player", "Single": "1B", "Double": "2B", "Triple": "3B"})
    if group_index == 2:
        player_bat_data["G"] = player_bat_data["G"]*2 - kouryusen
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
    player_bat_data["woba"] = wOBA_scale * (bb_value * (player_bat_data["BB"] - player_bat_data["IBB"]) + hbp_value * player_bat_data["HBP"] + single_value * player_bat_data["1B"] + double_value * player_bat_data["2B"] + triple_value * player_bat_data["3B"] + hr_value * player_bat_data["HR"])/(player_bat_data["AB"] + player_bat_data["BB"] - player_bat_data["IBB"] + player_bat_data["HBP"] + player_bat_data["SF"])
    player_bat_data["wOBA"] = my_round(player_bat_data["woba"], 3)
    player_bat_data = pd.merge(player_bat_data, league_wrc_mean, on="League", how="left")
    player_bat_data["wraa"] = ((player_bat_data["woba"] - player_bat_data["woba_league"])/wOBA_scale) * player_bat_data["PA"]
    player_bat_data["wrar"] = ((player_bat_data["woba"] - player_bat_data["woba_league"]*0.88)/wOBA_scale) * player_bat_data["PA"]
    player_bat_data["wRAA"] = my_round(player_bat_data["wraa"], 1)
    player_bat_data["wrc"] = (((player_bat_data["woba"] - player_bat_data["woba_league"])/wOBA_scale) + player_bat_data["R_league"]/player_bat_data["PA_league"])*player_bat_data["PA"]
    player_bat_data["wRC"] = my_round(player_bat_data["wrc"])
    player_bat_data = pd.merge(player_bat_data, rpw_df, on="League", how="left")
    if group_index == 2:
        player_bat_data["wrc+"] = 100*(player_bat_data["wrc"]/player_bat_data["PA"])/(player_bat_data["R_league"]/player_bat_data["PA_league"])
        player_bat_data["batwar"] = player_bat_data["wrar"]/player_bat_data["RPW"]
    else:
        player_bat_data = pd.merge(player_bat_data, pf[["Team", "bpf/100"]], on="Team", how="left")
        player_bat_data["wrc_pf"] = player_bat_data["wrc"] + (1-player_bat_data["bpf/100"])*player_bat_data["PA"]*(player_bat_data["R_league"]/player_bat_data["PA_league"]/player_bat_data["bpf/100"])
        player_bat_data["wrc+"] = 100*(player_bat_data["wrc_pf"]/player_bat_data["PA"])/(player_bat_data["R_league"]/player_bat_data["PA_league"])
        player_bat_data["wrar_pf"] = ((player_bat_data["woba"] - player_bat_data["woba_league"]*player_bat_data["bpf/100"]*0.88)/wOBA_scale) * player_bat_data["PA"]
        player_bat_data["batwar"] = player_bat_data["wrar_pf"]/player_bat_data["RPW"]
    player_bat_data["wRC+"] = my_round(player_bat_data["wrc+"])
    player_bat_data["batWAR"] = my_round(player_bat_data["batwar"], 1)
    
    if group_index == 0:
        player_bat_data = pd.merge(player_bat_data, player_pa[["League", "Team", "Player", "Q"]], on=["League", "Team", "Player"], how="left")
    plate_discipline = plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        N=(group_list[2-group_index], "size"),
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
    o_disc = o_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        O_N=(group_list[2-group_index], "size"),
        O_Swing=("swing", "sum"),
        O_Contact=("contact", "sum"),
    )
    o_disc["o-swing%"] = o_disc["O_Swing"]/o_disc["O_N"]
    o_disc["o-contact%"] = o_disc["O_Contact"]/o_disc["O_N"]
    o_disc["O-Swing%"] = my_round(o_disc["o-swing%"], 3)
    o_disc["O-Contact%"] = my_round(o_disc["o-contact%"], 3)
    plate_discipline = pd.merge(plate_discipline, o_disc, on=group_list[:(3-group_index)], how="left")

    z_plate_df = plate_df[plate_df["Zone"] == "In"]
    z_disc = z_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        Z_N=(group_list[2-group_index], "size"),
        Z_Swing=("swing", "sum"),
        Z_Contact=("contact", "sum"),
    )
    z_disc["z-swing%"] = z_disc["Z_Swing"]/z_disc["Z_N"]
    z_disc["z-contact%"] = z_disc["Z_Contact"]/z_disc["Z_N"]
    z_disc["Z-Swing%"] = my_round(z_disc["z-swing%"], 3)
    z_disc["Z-Contact%"] = my_round(z_disc["z-contact%"], 3)
    plate_discipline = pd.merge(plate_discipline, z_disc, on=group_list[:(3-group_index)], how="left")

    f_plate_df = plate_df[plate_df["ab_pitch_number"] == 1]
    f_disc = f_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        F_N=(group_list[2-group_index], "size"),
        F_Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
    )
    f_disc["f-strike%"] = f_disc["F_Zone"]/f_disc["F_N"]
    f_disc["F-Strike%"] = my_round(f_disc["f-strike%"], 3)
    plate_discipline = pd.merge(plate_discipline, f_disc, on=group_list[:(3-group_index)], how="left")

    t_plate_df = plate_df[plate_df["strikes"] == 2]
    t_disc = t_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        T_N=(group_list[2-group_index], "size"),
        T_SO=('events', lambda x: (x == "strike_out").sum()),  # 被本塁打数
    )
    t_disc["putaway%"] = t_disc["T_SO"]/t_disc["T_N"]
    t_disc["PutAway%"] = my_round(t_disc["putaway%"], 3)
    plate_discipline = pd.merge(plate_discipline, t_disc, on=group_list[:(3-group_index)], how="left")
    plate_discipline = plate_discipline.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player"})
    player_bat_data = pd.merge(player_bat_data, plate_discipline, on=col_list, how="left")
    
    pt_list = ["FA", "FT", "SL", "CT", "CB", "CH", "SF", "SI", "SP", "XX"]
    for p in pt_list:
        p_low = p.lower()
        fa_df = plate_df[plate_df[p] == 1]
        fa_v = fa_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
            p_n=(group_list[2-group_index], "size"),
            v=('velocity', "mean")
        )
        fa_v = fa_v.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                    "p_n": p_low, "v": p + "_v"})

        fa_pv_df = merged_data[merged_data[p] == 1]
        fa_pv = fa_pv_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
            w=('pitch_value', "sum")
        )
        fa_pv = fa_pv.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                    "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                    "w": p + "_w"})

        player_bat_data = pd.merge(player_bat_data, fa_v, on=col_list, how="left")
        player_bat_data = pd.merge(player_bat_data, fa_pv, on=col_list, how="left")
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

        if group_index == 0:
            runner_g = ["bat_league", "bat_team", "runner_name"]
        if group_index == 1:
            runner_g = ["bat_league", "bat_team"]
        if group_index == 2:
            runner_g = ["bat_league"]

        runner_df =sb_data.groupby(runner_g, as_index=False).agg(
            SB=("SB", "sum"),
            CS=("CS", "sum"),
        ).sort_values("SB", ascending=False)
        runner_df = runner_df.rename(columns={"bat_team": "Team", "bat_league": "League"})

        if group_index == 0:
            player_bat_data['batter_name_no_space'] = player_bat_data['Player'].str.replace(" ", "")
            player_bat_data = partial_match_merge(player_bat_data, runner_df, 'batter_name_no_space', 'runner_name')
        elif group_index == 1:
            player_bat_data = pd.merge(player_bat_data, runner_df,on=["League", "Team"], how="left")
        elif group_index == 2:
            player_bat_data = pd.merge(player_bat_data, runner_df,on="League", how="left")

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
    if group_index == 0:
        player_bat_data['Team'] = player_bat_data['Team'].replace(team_en_dict)
    #player_bat_data = player_bat_data[[
     #   "League", "Team", "Player", "G", "PA", "AB", "H", "1B", "2B", "3B", "HR", "SH", "SF" , "GDP", "K", "BB", "IBB", "HBP", 
      #  "K%", "BB%", "BB/K", "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP", "wOBA", "wRAA", "wRC", "wRC+", "GB%", "FB%", "LD%", "IFFB%", "HR/FB", "Q"
       # ]]

    df = player_bat_data.sort_values("wRC+", ascending=False)

    if league_select != "All Leagues":
        df = df.query("League == '" + league_select + "'")

    if team_select == "All Teams":
        pass
    else:
        if group_index == 0:
            df = df.query("Team == '" + team_en_dict[team_select] + "'")
        else:
            df = df.query("Team == '" + team_select + "'")


    if group_index == 0:
        df = df.query(q)

    df = df.reset_index(drop=True)
    with tab[0]:
        bat_cols = c_list + ["G", "PA", "HR", "SB", "BB%", "K%", "ISO", "BABIP", "AVG", "OBP", "SLG", "wOBA", "wRC+", "batWAR"]
        bat_0 = df[bat_cols]
        df_style = bat_0.style.format({
            'K%': '{:.1%}',
            'BB%': '{:.1%}',
            'SB': '{:.0f}',
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

    with tab[1]:
        bat_cols = c_list + ["G", "AB", "PA", "H", "1B", "2B", "3B", "HR", "BB", "IBB", "SO", "HBP", "SF", "SH", "GDP", "SB", "CS", "AVG"]
        bat_1 = df[bat_cols]
        df_style = bat_1.style.format({
            'K%': '{:.2f}',
            'BB%': '{:.2f}',
            'BB/K': '{:.2f}',
            'AVG': '{:.3f}',
            'OBP': '{:.3f}',
            'SB': '{:.0f}',
            'CS': '{:.0f}',
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

    with tab[2]:
        bat_cols = c_list + ["PA", "BB%", "K%", "BB/K", "AVG", "OBP", "SLG", "OPS", "ISO", "BABIP", "wSB", "wRC", "wRAA", "wOBA", "wRC+"]
        bat_2 = df[bat_cols]
        df_style = bat_2.style.format({
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
            'wSB': '{:.1f}',
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

    with tab[3]:
        bat_cols = c_list + ["BABIP", "GB/FB", "LD%", "GB%", "FB%", "IFFB%", "HR/FB", "IFH", "IFH%", "Pull%", "Cent%", "Oppo%"]
        bat_3 = df[bat_cols]
        df_style = bat_3.style.format({
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

    with tab[4]:
        bat_cols = c_list + ["O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", 
                               "Zone%", "F-Strike%", "Whiff%", "PutAway%", "SwStr%", "CStr%", "CSW%"]
        bat_4 = df[bat_cols]
        df_style = bat_4.style.format({
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

    with tab[5]:
        bat_cols = c_list + ["FA%", "FAv", "FT%", "FTv", "SL%", "SLv", "CT%", "CTv", "CB%", "CBv", 
                               "CH%", "CHv", "SF%", "SFv", "SI%", "SIv", "SP%", "SPv", "XX%", "XXv"]
        bat_5 = df[bat_cols]
        df_style = bat_5.style.format({
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

    with tab[6]:
        bat_cols = c_list + ["wFA", "wFT", "wSL", "wCT", "wCB", "wCH", "wSF", "wSI", "wSP", 
                            "wFA/C", "wFT/C", "wSL/C", "wCT/C", "wCB/C", "wCH/C", "wSF/C", "wSI/C", "wSP/C"]
        bat_6 = df[bat_cols]
        df_style = bat_6.style.format({
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
    group_list = ["fld_league", "fld_team", "pitcher_name"]

    team_game = PA_df.groupby(['fld_league', 'fld_team'], as_index=False).agg(
        G=('game_id', 'nunique')
    )
    player_ip_qua = PA_df.groupby(['fld_league', 'fld_team', 'pitcher_name'], as_index=False).agg(
        O=('event_out', 'sum'),  # 許した得点数
    )
    player_ip_qua["inning"] = player_ip_qua["O"]/3
    player_ip_qua = pd.merge(player_ip_qua, team_game[['fld_team', 'G']].rename(columns={"G": "team_g"}), left_on='fld_team', right_on='fld_team', how='left')
    player_ip_qua['threshold_ip'] = player_ip_qua['team_g'] * 1
    player_ip_qua['Q'] = np.where(player_ip_qua['inning'] >= player_ip_qua['threshold_ip'], 1, 0)
    player_ip_qua = player_ip_qua.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})

    
    pitcher_unique = data.groupby(["game_id", "fld_team"], as_index=False).agg(
        CG=("pitcher_name", "nunique")
    )
    cg_df = pitcher_unique[pitcher_unique["CG"] == 1]

    
    events_df = pd.merge(events_df, cg_df, on=["fld_team", "game_id"], how="left")
    events_df["CG"] = events_df["CG"].fillna(0).astype(int)
    is_sho = events_df.groupby(["game_id", "fld_team"], as_index=False).tail(1)
    sho_df = is_sho[(is_sho["CG"] == 1)&(is_sho["post_bat_score"] == 0)]
    sho_df = sho_df.assign(ShO = 1)
    events_df = pd.merge(events_df, sho_df[["game_id", "fld_team", "pitcher_name", "ShO"]], on=["game_id", "fld_team", "pitcher_name"], how="left")
    events_df["ShO"] = events_df["ShO"].fillna(0).astype(int)
    events_df['WP'] = events_df['des'].apply(lambda x: 1 if '暴投' in x else 0)

    league_fip_data = events_df.groupby('fld_league', as_index=False).agg(
        R=('runs_scored', 'sum'),  # 許した得点数
        O=('event_out', 'sum'), 
        K=('events', lambda x: ((x == "strike_out")|(x == "uncaught_third_strike")).sum()),   # ストライクアウト数
        BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
        IBB=('events', lambda x: (x == "intentional_walk").sum()),
        HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
        HR=('events', lambda x: (x == "home_run").sum()),
        OFFB=("OFFB", "sum"),
        IFFB=("IFFB", "sum"),
        GB=("GB", "sum"),
        LD=("LD", "sum")
    )
    league_fip_data["inning"] = league_fip_data["O"]/3
    league_fip_data['lgRA'] = league_fip_data['R'] * 9 / league_fip_data['inning']
    league_fip_data['ctRA'] = league_fip_data['lgRA'] - (
        (walk_run*league_fip_data['BB'] + hbp_run*league_fip_data['HBP'] + k_run*league_fip_data['K'] + 
        hr_run*league_fip_data['HR'] + gb_run*league_fip_data['GB'] + iffb_run*league_fip_data['IFFB'] + 
        offb_run*league_fip_data['OFFB'] + ld_run*league_fip_data['LD'])/
        (walk_out*league_fip_data['BB'] + hbp_out*league_fip_data['HBP'] + k_out*league_fip_data['K'] + 
        hr_out*league_fip_data['HR'] + gb_out*league_fip_data['GB'] + iffb_out*league_fip_data['IFFB'] + 
        offb_out*league_fip_data['OFFB'] + ld_out*league_fip_data['LD'])*27)
    league_fip_data["cFIP"] = league_fip_data["lgRA"] - (13*league_fip_data["HR"] + 3*(league_fip_data["BB"] - league_fip_data["IBB"] + league_fip_data["HBP"]) - 2*league_fip_data["K"])/league_fip_data["inning"]
    league_fip_data["cxFIP"] = league_fip_data["lgRA"] - (13*(league_fip_data["HR"]/(league_fip_data["OFFB"] + league_fip_data["HR"]))*league_fip_data["OFFB"] + 3*(league_fip_data["BB"] - league_fip_data["IBB"] + league_fip_data["HBP"]) - 2*league_fip_data["K"])/league_fip_data["inning"]
    league_fip_data = league_fip_data[["fld_league", "cFIP", "cxFIP", "lgRA", "ctRA"]]

    if pos_select == "All":
        pass
    elif pos_select == "SP":
        events_df = events_df.query("StP == 1")
        plate_df = plate_df.query("StP == 1")
        merged_data = merged_data.query("StP == 1")
    elif pos_select == "RP":
        events_df = events_df.query("StP == 0")
        plate_df = plate_df.query("StP == 0")
        merged_data = merged_data.query("StP == 0")

    if side_select != "Both":
        PA_df = PA_df[PA_df["p_throw"] == side_dict[side_select]]
        plate_df = plate_df[plate_df["p_throw"] == side_dict[side_select]]
        merged_data = merged_data[merged_data["p_throw"] == side_dict[side_select]]
        sb_df = sb_df[sb_df["p_throw"] == side_dict[side_select]]
    
    if game_type == "レギュラーシーズン":
        events_df = events_df[(events_df["game_type"] == "セ・リーグ")|(events_df["game_type"] == "パ・リーグ")|(events_df["game_type"] == "セ・パ交流戦")]
        merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")|(merged_data["game_type"] == "セ・パ交流戦")]
        events_df = events_df[(events_df["game_type"] == "セ・リーグ")|(events_df["game_type"] == "パ・リーグ")|(events_df["game_type"] == "セ・パ交流戦")]
    elif game_type == "交流戦":
        events_df = events_df[events_df["game_type"] == "セ・パ交流戦"]
        merged_data = merged_data[merged_data["game_type"] == "セ・パ交流戦"]
        events_df = events_df[events_df["game_type"] == "セ・パ交流戦"]
    elif game_type == "レギュラーシーズン(交流戦以外)":
        events_df = events_df[(events_df["game_type"] == "セ・リーグ")|(events_df["game_type"] == "パ・リーグ")]
        plate_df = plate_df[(plate_df["game_type"] == "セ・リーグ")|(plate_df["game_type"] == "パ・リーグ")]
        merged_data = merged_data[(merged_data["game_type"] == "セ・リーグ")|(merged_data["game_type"] == "パ・リーグ")]

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


    lg_game = events_df.groupby(["game_type"], as_index=False)["game_id"].nunique()
    lg_game["League"] = lg_game["game_type"].str.replace("・リーグ", "")
    lg_game = lg_game.drop(columns="game_type")
    try:
        kouryusen = lg_game.loc[lg_game['League'] == "セ・パ交流戦", 'game_id'].iloc[0]
    except:
        kouryusen = 0

    player_outs_sum = events_df.groupby(group_list[:(3-group_index)])['event_out'].sum()

    player_ip = player_outs_sum.apply(calculate_ip)
    player_ip_df = player_ip.reset_index()
    player_ip_df.columns = group_list[:(3-group_index)] + ['IP']

    cg_count = events_df[events_df['CG'] == 1].groupby(group_list[:(3-group_index)])['game_id'].nunique().reset_index(name='CG')
    sho_count = events_df[events_df['ShO'] == 1].groupby(group_list[:(3-group_index)])['game_id'].nunique().reset_index(name='ShO')

    player_pitch_data = events_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
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
        SF=('events', lambda x: ((x == "sac_fly")|(x == "sac_fly_error")).sum()),
        GB = ("GB", "sum"),
        FB = ("FB", "sum"),
        IFFB = ("IFFB", "sum"),
        OFFB = ("OFFB", "sum"),
        LD = ("LD", "sum"),
        Pull = ("Pull", "sum"),
        Cent = ("Center", "sum"),
        Oppo = ("Opposite", "sum")
    )
    player_pitch_data = pd.merge(player_pitch_data, player_ip_df, on=group_list[:(3-group_index)], how='left')
    player_pitch_data = player_pitch_data.merge(cg_count, on=group_list[:(3-group_index)], how='left').fillna(0)
    player_pitch_data = player_pitch_data.merge(sho_count, on=group_list[:(3-group_index)], how='left').fillna(0)
    player_pitch_data["CG"] = player_pitch_data["CG"].astype(int)
    player_pitch_data["ShO"] = player_pitch_data["ShO"].astype(int)
    player_pitch_data["inning"] = player_pitch_data["O"]/3
    player_pitch_data["AB"] = player_pitch_data["TBF"] - (player_pitch_data["BB"] + player_pitch_data["HBP"] + player_pitch_data["SH"] + player_pitch_data["SF"] + player_pitch_data["obstruction"] + player_pitch_data["interference"])
    player_pitch_data["H"] = player_pitch_data["single"] + player_pitch_data["double"] + player_pitch_data["triple"] + player_pitch_data["HR"]
    player_pitch_data['k/9'] = player_pitch_data['SO'] * 9 / player_pitch_data['inning']
    player_pitch_data['bb/9'] = player_pitch_data['BB'] * 9 / player_pitch_data['inning']
    player_pitch_data['K/9'] = my_round(player_pitch_data['k/9'], 2)
    player_pitch_data['BB/9'] = my_round(player_pitch_data['bb/9'], 2)
    player_pitch_data['k%'] = player_pitch_data["SO"]/player_pitch_data["TBF"]
    player_pitch_data['bb%'] = player_pitch_data["BB"]/player_pitch_data["TBF"]
    player_pitch_data['hr%'] = player_pitch_data["HR"]/player_pitch_data["TBF"]
    player_pitch_data["K%"] = my_round(player_pitch_data["k%"], 3)
    player_pitch_data["BB%"] = my_round(player_pitch_data["bb%"], 3)
    player_pitch_data["HR%"] = my_round(player_pitch_data["hr%"], 3)
    player_pitch_data["k-bb%"] = player_pitch_data["k%"] - player_pitch_data["bb%"]
    player_pitch_data["K-BB%"] = my_round(player_pitch_data["k-bb%"], 3)
    player_pitch_data['K/BB'] = my_round(player_pitch_data['SO'] / player_pitch_data['BB'], 2)
    player_pitch_data['HR/9'] = my_round(player_pitch_data['HR'] * 9 / player_pitch_data['inning'], 2)
    player_pitch_data['ra'] = player_pitch_data['R'] * 9 / player_pitch_data['inning']
    player_pitch_data['RA'] = my_round(player_pitch_data['ra'], 2)
    player_pitch_data = pd.merge(player_pitch_data, league_fip_data, on="fld_league", how="left")
    player_pitch_data['fip'] = (13*player_pitch_data["HR"] + 3*(player_pitch_data["BB"] - player_pitch_data["IBB"] + player_pitch_data["HBP"]) - 2*player_pitch_data["SO"])/player_pitch_data["inning"] + player_pitch_data["cFIP"]
    player_pitch_data['xfip'] = (13*(player_pitch_data["HR"]/(player_pitch_data["HR"]+player_pitch_data["OFFB"]))*player_pitch_data["OFFB"] + 3*(player_pitch_data["BB"] - player_pitch_data["IBB"] + player_pitch_data["HBP"]) - 2*player_pitch_data["SO"])/player_pitch_data["inning"] + player_pitch_data["cxFIP"]
    player_pitch_data['tra'] = (
        (walk_run*player_pitch_data['BB'] + hbp_run*player_pitch_data['HBP'] + k_run*player_pitch_data['SO'] + 
        hr_run*player_pitch_data['HR'] + gb_run*player_pitch_data['GB'] + iffb_run*player_pitch_data['IFFB'] + 
        offb_run*player_pitch_data['OFFB'] + ld_run*player_pitch_data['LD'])/
        (walk_out*player_pitch_data['BB'] + hbp_out*player_pitch_data['HBP'] + k_out*player_pitch_data['SO'] + 
        hr_out*player_pitch_data['HR'] + gb_out*player_pitch_data['GB'] + iffb_out*player_pitch_data['IFFB'] + 
        offb_out*player_pitch_data['OFFB'] + ld_out*player_pitch_data['LD'])*27) + player_pitch_data["ctRA"]
    player_pitch_data['FIP'] = my_round(player_pitch_data['fip'], 2)
    player_pitch_data['xFIP'] = my_round(player_pitch_data['xfip'], 2)
    player_pitch_data['tRA'] = my_round(player_pitch_data['tra'], 2)
    player_pitch_data["r-f"] = player_pitch_data["ra"] - player_pitch_data["fip"]
    player_pitch_data["R-F"] = my_round(player_pitch_data["r-f"], 2)
    player_pitch_data["avg"] = player_pitch_data["H"]/player_pitch_data["AB"]
    player_pitch_data["AVG"] = my_round(player_pitch_data["avg"], 3)
    player_pitch_data["babip"] = (player_pitch_data["H"] - player_pitch_data["HR"])/(player_pitch_data["AB"] - player_pitch_data["SO"] - player_pitch_data["HR"] + player_pitch_data["SF"])
    player_pitch_data["BABIP"] = my_round(player_pitch_data["babip"], 3)
    player_pitch_data = player_pitch_data.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})        
    if group_index == 0:
        player_pitch_data = pd.merge(player_pitch_data, player_ip_qua[["League", "Team", "Player", "Q"]], on=["League", "Team", "Player"], how="left")
        player_pitch_data["Q"] = player_pitch_data["Q"].fillna(0)
    if ((split[:2] != "vs") and (split != "Grounders") and (split != "Flies") and (split != "Liners") and (split != "Bases Empty") and
        (split[:10] != "Runners on") and (split[3:] != "経由")):
        if group_index == 2:
            player_pitch_data["G"] = player_pitch_data["G"]*2 - kouryusen
            player_pitch_data['GS'] = player_pitch_data['G']
        elif group_index == 1:
            player_pitch_data['GS'] = player_pitch_data['G']
        else:
            starter_games = events_df.groupby(["fld_league", "fld_team", "pitcher_name", "game_id"], as_index=False).head(1)
            st_games = starter_games.groupby(["fld_league", "fld_team", "pitcher_name"], as_index=False).agg(
                GS=("StP", "sum")
            )
            st_games = st_games.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})        
            player_pitch_data = pd.merge(player_pitch_data, st_games, on=["League", "Team", "Player"], how='left')
            player_pitch_data['GS'] = player_pitch_data['GS'].fillna(0).astype(int)
    else:
        if group_index == 2:
            player_pitch_data["G"] = player_pitch_data["G"]*2 - kouryusen
            player_pitch_data['GS'] = 0
        else:
            player_pitch_data['GS'] = 0

    if group_index <= 1:
        player_pitch_data = pd.merge(player_pitch_data, pf[["Team", "bpf/100"]], on="Team", how="left")
        player_pitch_data["fip-"] = 100*(player_pitch_data["fip"] + (player_pitch_data["fip"] - player_pitch_data["fip"]*player_pitch_data["bpf/100"]))/player_pitch_data["cFIP"]
        player_pitch_data["xfip-"] = 100*(player_pitch_data["xfip"] + (player_pitch_data["xfip"] - player_pitch_data["xfip"]*player_pitch_data["bpf/100"]))/player_pitch_data["cxFIP"]
        player_pitch_data["ra-"] = 100*(player_pitch_data["ra"] + (player_pitch_data["ra"] - player_pitch_data["ra"]*player_pitch_data["bpf/100"]))/player_pitch_data["lgRA"]
        player_pitch_data["tra-"] = 100*(player_pitch_data["tra"] + (player_pitch_data["tra"] - player_pitch_data["tra"]*player_pitch_data["bpf/100"]))/player_pitch_data["ctRA"]
    else:
        player_pitch_data["fip-"] = 100*(player_pitch_data["fip"] + (player_pitch_data["fip"] - player_pitch_data["fip"]))/player_pitch_data["cFIP"]
        player_pitch_data["xfip-"] = 100*(player_pitch_data["xfip"] + (player_pitch_data["xfip"] - player_pitch_data["xfip"]))/player_pitch_data["cxFIP"]
        player_pitch_data["ra-"] = 100*(player_pitch_data["ra"] + (player_pitch_data["ra"] - player_pitch_data["ra"]))/player_pitch_data["lgRA"]
        player_pitch_data["tra-"] = 100*(player_pitch_data["tra"] + (player_pitch_data["tra"] - player_pitch_data["tra"]))/player_pitch_data["ctRA"]
    player_pitch_data["FIP-"] = my_round(player_pitch_data["fip-"])
    player_pitch_data["xFIP-"] = my_round(player_pitch_data["xfip-"])
    player_pitch_data["RA-"] = my_round(player_pitch_data["ra-"])
    player_pitch_data["tRA-"] = my_round(player_pitch_data["tra-"])
    player_pitch_data["lob%"] = (player_pitch_data["H"] + player_pitch_data["BB"] + player_pitch_data["HBP"] - player_pitch_data["R"])/(player_pitch_data["H"] + player_pitch_data["BB"] + player_pitch_data["HBP"] - 1.4+player_pitch_data["HR"])
    player_pitch_data["LOB%"] = my_round(player_pitch_data["lob%"], 3)
    player_pitch_data["gb/fb"] = player_pitch_data["GB"] / player_pitch_data["FB"]
    player_pitch_data["gb%"] = player_pitch_data["GB"]/(player_pitch_data["GB"]+player_pitch_data["FB"]+player_pitch_data["LD"])
    player_pitch_data["fb%"] = player_pitch_data["FB"]/(player_pitch_data["GB"]+player_pitch_data["FB"]+player_pitch_data["LD"])
    player_pitch_data["ld%"] = player_pitch_data["LD"] / (player_pitch_data["GB"]+player_pitch_data["FB"]+player_pitch_data["LD"])
    player_pitch_data["iffb%"] = player_pitch_data["IFFB"] / player_pitch_data["FB"]
    player_pitch_data["offb%"] = player_pitch_data["OFFB"] / player_pitch_data["FB"]
    player_pitch_data["hr/fb"] = player_pitch_data["HR"] / player_pitch_data["FB"]
    player_pitch_data["GB/FB"] = my_round(player_pitch_data["gb/fb"], 2)
    player_pitch_data["GB%"] = my_round(player_pitch_data["gb%"], 3)
    player_pitch_data["FB%"] = my_round(player_pitch_data["fb%"], 3)
    player_pitch_data["LD%"] = my_round(player_pitch_data["ld%"], 3)
    player_pitch_data["IFFB%"] = my_round(player_pitch_data["iffb%"], 3)
    player_pitch_data["OFFB%"] = my_round(player_pitch_data["offb%"], 3)
    player_pitch_data["HR/FB"] = my_round(player_pitch_data["hr/fb"], 3)
    player_pitch_data["pull%"] = player_pitch_data["Pull"]/(player_pitch_data["Pull"]+player_pitch_data["Cent"]+player_pitch_data["Oppo"])
    player_pitch_data["cent%"] = player_pitch_data["Cent"]/(player_pitch_data["Pull"]+player_pitch_data["Cent"]+player_pitch_data["Oppo"])
    player_pitch_data["oppo%"] = player_pitch_data["Oppo"]/(player_pitch_data["Pull"]+player_pitch_data["Cent"]+player_pitch_data["Oppo"])
    player_pitch_data["Pull%"] = my_round(player_pitch_data["pull%"], 3)
    player_pitch_data["Cent%"] = my_round(player_pitch_data["cent%"], 3)
    player_pitch_data["Oppo%"] = my_round(player_pitch_data["oppo%"], 3)

    plate_discipline = plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        N=(group_list[2-group_index], "size"),
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
    o_disc = o_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        O_N=(group_list[2-group_index], "size"),
        O_Swing=("swing", "sum"),
        O_Contact=("contact", "sum"),
    )
    o_disc["o-swing%"] = o_disc["O_Swing"]/o_disc["O_N"]
    o_disc["o-contact%"] = o_disc["O_Contact"]/o_disc["O_N"]
    o_disc["O-Swing%"] = my_round(o_disc["o-swing%"], 3)
    o_disc["O-Contact%"] = my_round(o_disc["o-contact%"], 3)
    plate_discipline = pd.merge(plate_discipline, o_disc, on=group_list[:(3-group_index)], how="left")

    z_plate_df = plate_df[plate_df["Zone"] == "In"]
    z_disc = z_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        Z_N=(group_list[2-group_index], "size"),
        Z_Swing=("swing", "sum"),
        Z_Contact=("contact", "sum"),
    )
    z_disc["z-swing%"] = z_disc["Z_Swing"]/z_disc["Z_N"]
    z_disc["z-contact%"] = z_disc["Z_Contact"]/z_disc["Z_N"]
    z_disc["Z-Swing%"] = my_round(z_disc["z-swing%"], 3)
    z_disc["Z-Contact%"] = my_round(z_disc["z-contact%"], 3)
    plate_discipline = pd.merge(plate_discipline, z_disc, on=group_list[:(3-group_index)], how="left")

    f_plate_df = plate_df[plate_df["ab_pitch_number"] == 1]
    f_disc = f_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        F_N=(group_list[2-group_index], "size"),
        F_Zone=('Zone', lambda x: (x == "In").sum()),  # 被本塁打数
    )
    f_disc["f-strike%"] = f_disc["F_Zone"]/f_disc["F_N"]
    f_disc["F-Strike%"] = my_round(f_disc["f-strike%"], 3)
    plate_discipline = pd.merge(plate_discipline, f_disc, on=group_list[:(3-group_index)], how="left")

    t_plate_df = plate_df[plate_df["strikes"] == 2]
    t_disc = t_plate_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
        T_N=(group_list[2-group_index], "size"),
        T_SO=('events', lambda x: (x == "strike_out").sum()),  # 被本塁打数
    )
    t_disc["putaway%"] = t_disc["T_SO"]/t_disc["T_N"]
    t_disc["PutAway%"] = my_round(t_disc["putaway%"], 3)
    plate_discipline = pd.merge(plate_discipline, t_disc, on=group_list[:(3-group_index)], how="left")
    plate_discipline = plate_discipline.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player"})
    player_pitch_data = pd.merge(player_pitch_data, plate_discipline, on=col_list, how="left")

    pt_list = ["FA", "FT", "SL", "CT", "CB", "CH", "SF", "SI", "SP", "XX"]
    for p in pt_list:
        p_low = p.lower()
        fa_df = plate_df[plate_df[p] == 1]
        fa_v = fa_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
            p_n=(group_list[2-group_index], "size"),
            v=('velocity', "mean")
        )
        fa_v = fa_v.rename(columns={"fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                    "p_n": p_low, "v": p + "_v"})

        fa_pv_df = merged_data[merged_data[p] == 1]
        fa_pv = fa_pv_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
            w=('pitch_value', "sum")
        )
        fa_pv = fa_pv.rename(columns={"bat_league": "League", "bat_team": "Team", "batter_name": "Player",
                                    "fld_league": "League", "fld_team": "Team", "pitcher_name": "Player",
                                    "w": p + "_w"})

        player_pitch_data = pd.merge(player_pitch_data, fa_v, on=col_list, how="left")
        player_pitch_data = pd.merge(player_pitch_data, fa_pv, on=col_list, how="left")
        player_pitch_data[f"{p}%"] = my_round(player_pitch_data[p_low]/player_pitch_data["N"], 3)
        player_pitch_data[f"{p}v"] = my_round(player_pitch_data[p + "_v"], 1)
        player_pitch_data[f"w{p}"] = my_round(player_pitch_data[p + "_w"], 1)
        player_pitch_data[f"w{p}/C"] = my_round(100*player_pitch_data[f"w{p}"]/player_pitch_data[p_low], 1)

   
    if group_index == 0:
        player_pitch_data['Team'] = player_pitch_data['Team'].replace(team_en_dict)
    #player_pitch_data = player_pitch_data.reindex(columns=["League", "Team", "Player", "G", "GS", "IP", "R", "K", "BB", "IBB", "HR", 
    #                                                "K%", "BB%", "K-BB%", "HR%", "K/9", "BB/9", "K/BB", "HR/9", 
    #                                                "AVG", "RA", "FIP", "R-F", "GB%", "FB%", "LD%", "IFFB%", "HR/FB", "Q"])
    df = player_pitch_data.sort_values("FIP")

    if league_select != "All Leagues":
        df = df.query("League == '" + league_select + "'")

    if team_select == "All Teams":
        pass
    else:
        if group_index == 0:
            df = df.query("Team == '" + team_en_dict[team_select] + "'")
        else:
            df = df.query("Team == '" + team_select + "'")

    if group_index == 0:
        df = df.query(q)

    df = df.reset_index(drop=True)
    with tab[0]:
        pitch_cols = c_list + ["G", "GS", "IP", "K/9", "BB/9", "HR/9", "BABIP", "LOB%", "GB%", "HR/FB", "RA", "FIP"]
        pitch_0 = df[pitch_cols]
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
    
    with tab[1]:
        pitch_cols = c_list + ["G", "GS", "IP", "CG", "ShO", "TBF", "H", "R", "HR", "BB", "IBB", "HBP", "WP", "BK", "SO"]
        pitch_1 = df[pitch_cols]
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
    
    with tab[2]:
        pitch_cols = c_list + ["K/9", "BB/9", "K/BB", "HR/9", "K%", "BB%", "K-BB%", "AVG", "BABIP", "LOB%", "RA-", "tRA-", "FIP-", "xFIP-", "RA", "tRA", "FIP", "xFIP", "R-F"]
        pitch_2 = df[pitch_cols]
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
            'xFIP-': '{:.0f}',
            'FIP': '{:.2f}',
            'xFIP': '{:.2f}',
            'RA-': '{:.0f}',
            'tRA-': '{:.0f}',
            'RA': '{:.2f}',
            'tRA': '{:.2f}',
            'R-F': '{:.2f}',
            'GB%': '{:.1%}',
            'FB%': '{:.1%}',
            'LD%': '{:.1%}',
            'IFFB%': '{:.1%}',
            'HR/FB': '{:.1%}',
        })
        st.dataframe(df_style, use_container_width=True)

    with tab[3]:
        pitch_cols = c_list + ["BABIP", "GB/FB", "LD%", "GB%", "FB%", "OFFB%", "IFFB%", "HR/FB", "Pull%", "Cent%", "Oppo%"]
        pitch_3 = df[pitch_cols]
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
            'OFFB%': '{:.1%}',
            'IFFB%': '{:.1%}',
            'GB/FB': '{:.2f}',
            'HR/FB': '{:.1%}',
        })
        st.dataframe(df_style, use_container_width=True)

    with tab[4]:
        pitch_cols = c_list + ["O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", 
                               "Zone%", "F-Strike%", "Whiff%", "PutAway%", "SwStr%", "CStr%", "CSW%"]
        pitch_4 = df[pitch_cols]
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

    with tab[5]:
        pitch_cols = c_list + ["FA%", "FAv", "FT%", "FTv", "SL%", "SLv", "CT%", "CTv", "CB%", "CBv", 
                               "CH%", "CHv", "SF%", "SFv", "SI%", "SIv", "SP%", "SPv", "XX%", "XXv"]
        pitch_5 = df[pitch_cols]
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

    with tab[6]:
        pitch_cols = c_list + ["wFA", "wFT", "wSL", "wCT", "wCB", "wCH", "wSF", "wSI", "wSP", 
                            "wFA/C", "wFT/C", "wSL/C", "wCT/C", "wCB/C", "wCH/C", "wSF/C", "wSI/C", "wSP/C"]
        pitch_6 = df[pitch_cols]
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
    
elif stats_type == "Fielding":
    team_inn = events_df.groupby(["fld_team"], as_index=False).agg(
        team_o = ("event_out", "sum")
    )

    data['frame_zone'] = data.apply(calculate_frame_zone, axis=1)

    league_bat_data = PA_df.groupby("fld_league", as_index=False).agg(
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
    league_bat_data = league_bat_data[["fld_league", "Single", "BB", "IBB", "HBP"]]
    league_bat_data = league_bat_data.rename(columns={
        "Single": "1B_league", "BB": "BB_league", "IBB": "IBB_league", "HBP": "HBP_league"})

    league_steal = sb_df.groupby("fld_league", as_index=False).agg(
        SB_league=("sb", "sum"),
        CS_league=("cs", "sum"),
    )
    league_bat_data = pd.merge(league_bat_data, league_steal, on="fld_league", how="left")

    

    fld_df_list = []
    for i in range(1, 10):
        if i == 1:
            fld_str = "pitcher_name"
        else:
            fld_str = f"fld_{i}"
        
        
        player_inn_qua = PA_df.groupby(['fld_league', 'fld_team', fld_str], as_index=False).agg(
            O=('event_out', 'sum'),  # 許した得点数
        )
        player_inn_qua = pd.merge(player_inn_qua, team_inn[['fld_team', 'team_o']], left_on='fld_team', right_on='fld_team', how='left')
        player_inn_qua['threshold_inn'] = player_inn_qua['team_o'] * 1/2
        player_inn_qua['Q'] = np.where(player_inn_qua['O'] >= player_inn_qua['threshold_inn'], 1, 0)
        player_inn_qua = player_inn_qua.rename(columns={"fld_league": "League", "fld_team": "Team", fld_str: "Player"})
        group_list = ["fld_league", "fld_team", fld_str]
        player_outs_sum = events_df.groupby(group_list[:(3-group_index)])['event_out'].sum()

        player_ip = player_outs_sum.apply(calculate_ip)
        player_ip_df = player_ip.reset_index()
        player_ip_df.columns = group_list[:(3-group_index)] + ['Inn']
        first_data = events_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
            G=('game_id', 'nunique'),  # ゲーム数
            O=('event_out', 'sum'),
            DPS=('result', lambda x: (x == f"{pos_ja_num_dict[i]}併殺打").sum()),
        ) 
        first_data = first_data.assign(Pos=pos_num_dict[i])
        first_data = pd.merge(first_data, player_ip_df, on=group_list[:(3-group_index)], how='left')
        first_data["inning"] = first_data["O"]/3

        te_df = events_df[events_df["TE"] > 0]
        te_df["te_name"] = te_df["des"].str.split("悪送球（").str[-1].str.split("）").str[0]
        te_df = te_df[te_df.apply(lambda row: row[fld_str].startswith(row['te_name']), axis=1)]

        te_data = te_df.groupby(["fld_league", "fld_team", fld_str], as_index=False).agg(
            TE=(fld_str, "size")
        )

        fe_df = events_df[events_df["des"].str.contains("後逸（")]
        fe_df["te_name"] = fe_df["des"].str.split("後逸（").str[-1].str.split("）").str[0]
        fe_df = fe_df[fe_df.apply(lambda row: row[fld_str].startswith(row['te_name']), axis=1)]

        fe_data = fe_df.groupby(["fld_league", "fld_team", fld_str], as_index=False).agg(
            FE=(fld_str, "size")
        )

        oe_df = events_df[events_df["des"].str.contains("エラー（")]
        oe_df["te_name"] = oe_df["des"].str.split("エラー（").str[-1].str.split("）").str[0]
        oe_df = oe_df[oe_df.apply(lambda row: row[fld_str].startswith(row['te_name']), axis=1)]

        oe_data = oe_df.groupby(["fld_league", "fld_team", fld_str], as_index=False).agg(
            FE=(fld_str, "size")
        )

        fanb_df = events_df[events_df["des"].str.contains("ファンブル（")]
        fanb_df["te_name"] = fanb_df["des"].str.split("ファンブル（").str[-1].str.split("）").str[0]
        fanb_df = fanb_df[fanb_df.apply(lambda row: row[fld_str].startswith(row['te_name']), axis=1)]

        fanb_data = fanb_df.groupby(["fld_league", "fld_team", fld_str], as_index=False).agg(
            FE=(fld_str, "size")
        )


        fe_data = pd.concat([fe_data, oe_data])
        fe_data = pd.concat([fe_data, fanb_data])

        fe_data = fe_data.groupby(group_list[:(3-group_index)], as_index=False).agg(
            FE=("FE", "sum")
        )
        te_data = te_data.groupby(group_list[:(3-group_index)], as_index=False).agg(
            TE=("TE", "sum")
        )

        first_data = pd.merge(first_data, fe_data, on=group_list[:(3-group_index)], how="left")
        first_data = pd.merge(first_data, te_data, on=group_list[:(3-group_index)], how="left")
        first_data["FE"] = first_data["FE"].fillna(0).astype(int)
        first_data["TE"] = first_data["TE"].fillna(0).astype(int)
        first_data["E"] = first_data["FE"] + first_data["TE"]

        if i == 2:
            take = data[(data["Shadow"] == 1)&(data["swing"] != 1)].reset_index(drop=True)

            framing_group = ["p_throw", "umpire", "stand", "frame_zone", "B-S"]
            shadow_df = take.groupby(framing_group, as_index=False).agg(
                N=("p_throw", "size"),
                S = ("description", lambda x: (x == "called_strike").sum()),
            )
            shadow_df["s%"] = shadow_df["S"]/shadow_df["N"]
            shadow_df["S%"] = my_round(100*shadow_df["s%"], 1)
            shadow_df = shadow_df.drop(columns=["S"])
            shadow_df = shadow_df.drop(columns=["N"])
            take = pd.merge(take, shadow_df, on=framing_group, how="left")
            take = pd.merge(take, count_bat_stats[["B-S", "v_strike", "v_ball"]], on="B-S", how="left")
            take["vS-B"] = (take["v_strike"] - take["v_ball"])*-1
            take["s_or_b"] = [1 if x == "called_strike" else 0 for x in take["description"]]
            take["Framing_r"] = take["s_or_b"] - take["s%"]

            framing_df = take.groupby(group_list[:(3-group_index)], as_index=False).agg(
                N = ("fld_2", "size"),
                LFrame = ("Framing_r", "sum"),
            )
            framing_df["LFrame/C"] = framing_df["LFrame"]/framing_df["N"]
            framing_df["frm"] = framing_df["LFrame"]*0.125
            framing_df["FRM"] = my_round(framing_df["frm"], 1)
            framing_df["vLFrame/C"] = framing_df["frm"]/framing_df["N"]
            first_data = pd.merge(first_data, framing_df, on=group_list[:(3-group_index)], how="left")
            
            c_bat = PA_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
                Single=('events', lambda x: (x == "single").sum()),
                BB=('events', lambda x: ((x == "walk") | (x == "intentional_walk")).sum()),  # 与四球数
                IBB=('events', lambda x: (x == "intentional_walk").sum()),
                HBP=('events', lambda x: (x == "hit_by_pitch").sum()),
            )
            first_data = pd.merge(first_data, c_bat, on=group_list[:(3-group_index)], how="left")
            first_data["Single"] = first_data["Single"].fillna(0).astype(int)
            first_data["BB"] = first_data["BB"].fillna(0).astype(int)
            first_data["IBB"] = first_data["IBB"].fillna(0).astype(int)
            first_data["HBP"] = first_data["HBP"].fillna(0).astype(int)

            c_sb = sb_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
                SB=("sb", "sum"),
                CS=("cs", "sum")
            )
            first_data = pd.merge(first_data, c_sb, on=group_list[:(3-group_index)], how="left")
            first_data["SB"] = first_data["SB"].fillna(0).astype(int)
            first_data["CS"] = first_data["CS"].fillna(0).astype(int)
            first_data = pd.merge(first_data, league_bat_data, on="fld_league", how="left")
            first_data["wSB_A"] = (first_data["SB"] * sb_run) + (first_data["CS"] * cs_run)
            first_data["wSB_B"] = (
                (first_data["SB_league"] * sb_run) + (first_data["CS_league"] * cs_run)
                )/(first_data["1B_league"] + first_data["BB_league"] + first_data["HBP_league"] + first_data["IBB_league"])
            first_data["wSB_C"] = first_data["Single"] + first_data["BB"] - first_data["IBB"] + first_data["HBP"]
            first_data['wsb'] = np.where(
                (first_data['SB'] == 0) & (first_data['CS'] == 0),
                np.nan,
                (first_data['wSB_A'] - first_data['wSB_B'] * first_data['wSB_C'])*-1
            )
            first_data["rSB"] = my_round(first_data["wsb"], 1)

            pb_wp = events_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
                PB = ("PB", "sum"),
                WP = ("WP", "sum"),
            )
            first_data = pd.merge(first_data, pb_wp, on=group_list[:(3-group_index)], how="left")
            first_data["PB"] = first_data["PB"].fillna(0).astype(int)
            first_data["WP"] = first_data["WP"].fillna(0).astype(int)

        if i == 3:
            scp_df = events_df.groupby(group_list[:(3-group_index)], as_index=False).agg(
                Scp_n=("Scp_n", "sum"),
                Scp=("Scp", "sum")
            )
            first_data = pd.merge(first_data, scp_df, on=group_list[:(3-group_index)], how="left")
            first_data["Scp_n"] = first_data["Scp_n"].fillna(0).astype(int)
            first_data["Scp"] = first_data["Scp"].fillna(0).astype(int)
            first_data["Scp%"] = my_round(100*first_data["Scp"]/first_data["Scp_n"], 1)

        first_data = first_data.rename(columns={"fld_league": "League", "fld_team": "Team", fld_str: "Player"})
        if group_index == 0:
            first_data = pd.merge(first_data, player_inn_qua[["League", "Team", "Player", "Q"]], on=["League", "Team", "Player"], how="left")
            first_data["Q"] = first_data["Q"].fillna(0)

        
        fld_df_list.append(first_data)

    field_data = pd.concat(fld_df_list).reset_index(drop=True)

    if group_index == 0:
        field_data['Team'] = field_data['Team'].replace(team_en_dict)
    #player_pitch_data = player_pitch_data.reindex(columns=["League", "Team", "Player", "G", "GS", "IP", "R", "K", "BB", "IBB", "HR", 
    #                                                "K%", "BB%", "K-BB%", "HR%", "K/9", "BB/9", "K/BB", "HR/9", 
    #                                                "AVG", "RA", "FIP", "R-F", "GB%", "FB%", "LD%", "IFFB%", "HR/FB", "Q"])
    
    fld_cols = c_list + ["Pos", "G", "Inn", "E", "FE", "TE", "DPS", "Scp", "Scp%", "PB", "WP", "SB", "CS", "FRM", "rSB"]
    df = field_data
    if group_index == 0:
        df = df.query(q)

    df = df[fld_cols]

    if pos_select == "All":
        pass
    else:
        df = df[df["Pos"] == pos_select]
    
    if league_select != "All Leagues":
        df = df.query("League == '" + league_select + "'")

    if team_select == "All Teams":
        pass
    else:
        if group_index == 0:
            df = df.query("Team == '" + team_en_dict[team_select] + "'")
        else:
            df = df.query("Team == '" + team_select + "'")

    df = df.reset_index(drop=True)

    st.dataframe(df, use_container_width=True)

