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

st.title("Park Factors")

cols = st.columns(4)
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
with cols[2]:
    stand = st.selectbox(
        "Bat Side",
        ["Both", "R", "L"],
        index = 0)
with cols[3]:
    condition = st.selectbox(
        "Condition",
        ["All", "Day", "Night"],
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

data["runner_id"] = data["runner_id"].astype(str).str.zfill(3)
data["post_runner_id"] = data["post_runner_id"].astype(str).str.zfill(3)
data["B-S"] = data["balls"].astype(str).str.cat(data["strikes"].astype(str), sep="-")

events_df = data.dropna(subset="events")
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
df2024["NEW.STATE"] = df2024["post_runner_id"].str.cat(df2024["post_out_count"].astype(str), sep="-")
df2024 = df2024[(df2024["STATE"] != df2024["NEW.STATE"])|(df2024["runs_scored"] > 0)]
df2024C = df2024[df2024["Outs_Inning"] == 3]
RUNS = df2024C.groupby(["STATE"], as_index=False).agg(
    Mean = ("RUNS.ROI", "mean")
)
RUNS["Outs"] = RUNS["STATE"].str[-1]
RUNS["RUNNER"] = RUNS["STATE"].str[:3]
RUNS = RUNS.sort_values("Outs")
df2024 = pd.merge(df2024, RUNS[["STATE", "Mean"]], on="STATE", how="left").rename(columns={"Mean": "Runs.State"})
df2024 = pd.merge(df2024, RUNS.rename(columns={"STATE": "NEW.STATE"})[["NEW.STATE", "Mean"]], on="NEW.STATE", how="left").rename(columns={"Mean": "Runs.New.State"})
df2024["Runs.New.State"] = df2024["Runs.New.State"].fillna(0)
df2024["run_value"] = df2024["Runs.New.State"] - df2024["Runs.State"] + df2024["runs_scored"]
run_values = df2024.groupby(["events"], as_index=False).agg(
    Mean = ("run_value", "mean")
)
run_values = run_values.rename(columns={"Mean": "Run_Value"}).sort_values("Run_Value", ascending=False)

out_df = df2024[(df2024["event_out"] > 0)]
out_value = out_df["run_value"].sum()/out_df["event_out"].sum()

bb_run = df2024[df2024["events"] == "walk"]["run_value"].mean()
hbp_run = df2024[df2024["events"] == "hit_by_pitch"]["run_value"].mean()
single_run = df2024[df2024["events"] == "single"]["run_value"].mean()
double_run = df2024[df2024["events"] == "double"]["run_value"].mean()
triple_run = df2024[df2024["events"] == "triple"]["run_value"].mean()
hr_run = df2024[df2024["events"] == "home_run"]["run_value"].mean()

bb_value = bb_run - out_value
hbp_value = hbp_run - out_value
single_value = single_run - out_value
double_value = double_run - out_value
triple_value = triple_run - out_value
hr_value = hr_run - out_value


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

    pf_PA_df = pf_PA_df[(pf_PA_df["game_type"] == "パ・リーグ")|(pf_PA_df["game_type"] == "セ・リーグ")]

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

    pf_PA_df = pf_PA_df[(pf_PA_df["game_type"] == "イ・リーグ")|(pf_PA_df["game_type"] == "ウ・リーグ")]


if stand == "R":
    pf_PA_df = pf_PA_df[pf_PA_df["stand"] == "右"]
elif stand == "L":
    pf_PA_df = pf_PA_df[pf_PA_df["stand"] == "左"]

pf_PA_df['start_time'] = pd.to_datetime(pf_PA_df['start_time'], format='%H:%M:%S').dt.time

if condition == "Day":
    pf_PA_df = pf_PA_df[pf_PA_df["start_time"] < dt.time(17, 0, 0)]
elif condition == "Night":
    pf_PA_df = pf_PA_df[pf_PA_df["start_time"] >= dt.time(17, 0, 0)]

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
ev_away["away_ba"] = ev_away["away_h"]/ev_away["away_con"]
ev_away["away_woba"] = (single_value * ev_away["away_1b"] + double_value * ev_away["away_2b"] + triple_value * ev_away["away_3b"] + hr_value * ev_away["away_hr"])/(ev_away["away_con"])
ev_away["away_score/g"] = ev_away["away_score"]/ev_away["away_g"]
ev_away["away_hr/g"] = ev_away["away_hr"]/ev_away["away_g"]
ev_away["away_1b/g"] = ev_away["away_1b"]/ev_away["away_g"]
ev_away["away_2b/g"] = ev_away["away_2b"]/ev_away["away_g"]
ev_away["away_3b/g"] = ev_away["away_3b"]/ev_away["away_g"]
ev_away["away_h/g"] = ev_away["away_h"]/ev_away["away_g"]
ev_away["away_bb/g"] = ev_away["away_bb"]/ev_away["away_g"]
ev_away["away_k/g"] = ev_away["away_k"]/ev_away["away_g"]
if league == "1軍":
    ev_bat_away = pf_PA_df.groupby(["away_league", "away_team"], as_index=False).agg(
        away_gb=('GB', 'sum'),
        away_fb=('FB', 'sum'),
        away_ld=('LD', 'sum'),
        away_iffb=('IFFB', 'sum'),
    )
    ev_away = pd.merge(ev_away, ev_bat_away, on=["away_league", "away_team"], how="left")
    ev_away["away_gb/g"] = ev_away["away_gb"]/ev_away["away_g"]
    ev_away["away_fb/g"] = ev_away["away_fb"]/ev_away["away_g"]
    ev_away["away_ld/g"] = ev_away["away_ld"]/ev_away["away_g"]
    ev_away["away_iffb/g"] = ev_away["away_iffb"]/ev_away["away_g"]

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
ev_home["home_ba"] = ev_home["home_h"]/ev_home["home_con"]
ev_home["home_woba"] = (single_value * ev_home["home_1b"] + double_value * ev_home["home_2b"] + triple_value * ev_home["home_3b"] + hr_value * ev_home["home_hr"])/(ev_home["home_con"])
ev_home["home_score/g"] = ev_home["home_score"]/ev_home["home_g"]
ev_home["home_hr/g"] = ev_home["home_hr"]/ev_home["home_g"]
ev_home["home_1b/g"] = ev_home["home_1b"]/ev_home["home_g"]
ev_home["home_2b/g"] = ev_home["home_2b"]/ev_home["home_g"]
ev_home["home_3b/g"] = ev_home["home_3b"]/ev_home["home_g"]
ev_home["home_h/g"] = ev_home["home_h"]/ev_home["home_g"]
ev_home["home_bb/g"] = ev_home["home_bb"]/ev_home["home_g"]
ev_home["home_k/g"] = ev_home["home_k"]/ev_home["home_g"]

if league == "1軍":
    ev_bat_home = pf_PA_df.groupby(["home_league", "home_team"], as_index=False).agg(
        home_gb=('GB', 'sum'),
        home_fb=('FB', 'sum'),
        home_ld=('LD', 'sum'),
        home_iffb=('IFFB', 'sum'),
    )
    ev_home = pd.merge(ev_home, ev_bat_home, on=["home_league", "home_team"], how="left")
    ev_home["home_gb/g"] = ev_home["home_gb"]/ev_home["home_g"]
    ev_home["home_fb/g"] = ev_home["home_fb"]/ev_home["home_g"]
    ev_home["home_ld/g"] = ev_home["home_ld"]/ev_home["home_g"]
    ev_home["home_iffb/g"] = ev_home["home_iffb"]/ev_home["home_g"]

ev_home = ev_home.rename(columns={"home_league": "League", "home_team": "Team"})

pf = pd.merge(ev_away, ev_home, on=["League", "Team"])
league_counts = pf['League'].value_counts().reset_index()
league_counts.columns = ['League', 'League_Count']
pf = pd.merge(pf, league_counts, on="League", how="left")

#ev_compare["pf"] = ev_compare["home_hr_event"]/(ev_compare["home_hr_event"] * ev_compare["away/home"] + ev_compare["away_hr_event"] * (1 - ev_compare["away/home"]))
pf["PA"] = pf["home_pa"] + pf["away_pa"]
pf["ba_pf"] = pf["home_ba"]/((pf["away_ba"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_ba"] * 1/pf["League_Count"]))
pf["woba_pf"] = pf["home_woba"]/((pf["away_woba"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_woba"] * 1/pf["League_Count"]))
pf["hr_pf"] = pf["home_hr/g"]/((pf["away_hr/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_hr/g"] * 1/pf["League_Count"]))
pf["1b_pf"] = pf["home_1b/g"]/((pf["away_1b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_1b/g"] * 1/pf["League_Count"]))
pf["2b_pf"] = pf["home_2b/g"]/((pf["away_2b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_2b/g"] * 1/pf["League_Count"]))
pf["3b_pf"] = pf["home_3b/g"]/((pf["away_3b/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_3b/g"] * 1/pf["League_Count"]))
pf["h_pf"] = pf["home_h/g"]/((pf["away_h/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_h/g"] * 1/pf["League_Count"]))
pf["bb_pf"] = pf["home_bb/g"]/((pf["away_bb/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_bb/g"] * 1/pf["League_Count"]))
pf["k_pf"] = pf["home_k/g"]/((pf["away_k/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_k/g"] * 1/pf["League_Count"]))
pf["runs_pf"] = pf["home_score/g"]/((pf["away_score/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_score/g"] * 1/pf["League_Count"]))
pf["BA_PF"] = my_round(pf["ba_pf"],2)
pf["wOBA_PF"] = my_round(pf["woba_pf"],2)
pf["HR_PF"] = my_round(pf["hr_pf"],2)
pf["1B_PF"] = my_round(pf["1b_pf"],2)
pf["2B_PF"] = my_round(pf["2b_pf"],2)
pf["3B_PF"] = my_round(pf["3b_pf"],2)
pf["H_PF"] = my_round(pf["h_pf"],2)
pf["K_PF"] = my_round(pf["k_pf"],2)
pf["BB_PF"] = my_round(pf["bb_pf"],2)
if league == "1軍":
    pf["gb_pf"] = pf["home_gb/g"]/((pf["away_gb/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_gb/g"] * 1/pf["League_Count"]))
    pf["fb_pf"] = pf["home_fb/g"]/((pf["away_fb/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_fb/g"] * 1/pf["League_Count"]))
    pf["ld_pf"] = pf["home_ld/g"]/((pf["away_ld/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_ld/g"] * 1/pf["League_Count"]))
    pf["iffb_pf"] = pf["home_iffb/g"]/((pf["away_iffb/g"] * (pf["League_Count"]-1)/pf["League_Count"]) + (pf["home_iffb/g"] * 1/pf["League_Count"]))
    pf["GB_PF"] = my_round(pf["gb_pf"],2)
    pf["FB_PF"] = my_round(pf["fb_pf"],2)
    pf["LD_PF"] = my_round(pf["ld_pf"],2)
    pf["IFFB_PF"] = my_round(pf["iffb_pf"],2)
else:
    pf["GB_PF"] = np.nan
    pf["FB_PF"] = np.nan
    pf["LD_PF"] = np.nan
    pf["IFFB_PF"] = np.nan
pf["RUNS_PF"] = my_round(pf["runs_pf"],2)
pf["bpf/100"] = pf["runs_pf"] * pf["home_g"]/(pf["home_g"] + pf["away_g"]) + (pf["League_Count"]-pf["runs_pf"])/(pf["League_Count"] - 1) * pf["away_g"]/(pf["home_g"] + pf["away_g"])
pf["Park Factor"] = my_round(pf["bpf/100"],2)
pf = pf[["League", "Team", "Park Factor", "wOBA_PF", "BA_PF", "RUNS_PF", "HR_PF", "H_PF", 
         "1B_PF", "2B_PF", "3B_PF", "K_PF", "BB_PF", "GB_PF", "FB_PF", "LD_PF", "IFFB_PF", "PA"]]
pf = pf.sort_values("Park Factor", ascending=False)
pf = pf.set_axis(["League", "Team", "Park Factor", "wOBAcon", "BAcon", "R", "HR", "H", "1B", "2B", "3B", "SO", "BB", "GB", "FB", "LD", "IFFB", "PA"], axis=1)
if league == "1軍":
    cl_pf = pf[pf["League"] == "セ・リーグ"]
    pl_pf = pf[pf["League"] == "パ・リーグ"]
    cl_pf = cl_pf.drop(columns="League").reset_index(drop=True)
    pl_pf = pl_pf.drop(columns="League").reset_index(drop=True)
    pl_style = pl_pf.style.format({
        'Park Factor': '{:.2f}',
        'wOBAcon': '{:.2f}',
        'BAcon': '{:.2f}',
        'R': '{:.2f}',
        'HR': '{:.2f}',
        'H': '{:.2f}',
        '1B': '{:.2f}',
        '2B': '{:.2f}',
        '3B': '{:.2f}',
        'SO': '{:.2f}',
        'BB': '{:.2f}',
        'GB': '{:.2f}',
        'FB': '{:.2f}',
        'LD': '{:.2f}',
        'IFFB': '{:.2f}',
    })

    cl_style = cl_pf.style.format({
        'Park Factor': '{:.2f}',
        'wOBAcon': '{:.2f}',
        'BAcon': '{:.2f}',
        'R': '{:.2f}',
        'HR': '{:.2f}',
        'H': '{:.2f}',
        '1B': '{:.2f}',
        '2B': '{:.2f}',
        '3B': '{:.2f}',
        'SO': '{:.2f}',
        'BB': '{:.2f}',
        'GB': '{:.2f}',
        'FB': '{:.2f}',
        'LD': '{:.2f}',
        'IFFB': '{:.2f}',
    })
    st.markdown(f"{latest_date_str} 終了時点")

    st.markdown("セ・リーグ")
    st.dataframe(cl_style, use_container_width=True)
    st.markdown("パ・リーグ")
    st.dataframe(pl_style, use_container_width=True)
elif league == "2軍":
    el_pf = pf[pf["League"] == "イースタン"]
    wl_pf = pf[pf["League"] == "ウエスタン"]
    el_pf = el_pf.drop(columns="League").reset_index(drop=True)
    wl_pf = wl_pf.drop(columns="League").reset_index(drop=True)
    el_style = el_pf.style.format({
        'Park Factor': '{:.2f}',
        'wOBAcon': '{:.2f}',
        'BAcon': '{:.2f}',
        'R': '{:.2f}',
        'HR': '{:.2f}',
        'H': '{:.2f}',
        '1B': '{:.2f}',
        '2B': '{:.2f}',
        '3B': '{:.2f}',
        'SO': '{:.2f}',
        'BB': '{:.2f}',
        'GB': '{:.2f}',
        'FB': '{:.2f}',
        'LD': '{:.2f}',
        'IFFB': '{:.2f}',
    })

    wl_style = wl_pf.style.format({
        'Park Factor': '{:.2f}',
        'wOBAcon': '{:.2f}',
        'BAcon': '{:.2f}',
        'R': '{:.2f}',
        'HR': '{:.2f}',
        'H': '{:.2f}',
        '1B': '{:.2f}',
        '2B': '{:.2f}',
        '3B': '{:.2f}',
        'SO': '{:.2f}',
        'BB': '{:.2f}',
        'GB': '{:.2f}',
        'FB': '{:.2f}',
        'LD': '{:.2f}',
        'IFFB': '{:.2f}',
    })
    st.markdown(f"{latest_date_str} 終了時点")

    st.markdown("イースタン")
    st.dataframe(el_style, use_container_width=True)
    st.markdown("ウエスタン")
    st.dataframe(wl_style, use_container_width=True)
    