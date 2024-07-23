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
from collections import defaultdict

st.set_page_config(layout='wide')

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

cols = st.columns(2)
with cols[0]:
    st.title("Basis")

with cols[1]:
    cols_2 = st.columns(3)
    with cols_2[2]:
        league = st.selectbox(
            "League Type",
            ["1軍", "2軍"],
            index=0
        )

if league == "1軍":
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/1軍/all2024.csv")
else:
    data = pd.read_csv("~/Python/baseball/NPB/スポナビ/2軍/farm2024.csv")

data['game_date'] = pd.to_datetime(data['game_date'], format='%Y-%m-%d')
latest_date = data["game_date"].max()
latest_date_str = latest_date.strftime("%Y/%m/%d")
year_list = list(data['game_date'].dt.year.unique())
year_list.sort(reverse=True)

data["runner_id"] = data["runner_id"].astype(str).str.zfill(3)
data["post_runner_id"] = data["post_runner_id"].astype(str).str.zfill(3)
data["B-S"] = data["balls"].astype(str).str.cat(data["strikes"].astype(str), sep="-")

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
if league == "1軍":
    gb_run = df2024[df2024["GB"] == 1]["run_value"].mean()
    ld_run = df2024[df2024["LD"] == 1]["run_value"].mean()
    iffb_run = df2024[df2024["IFFB"] == 1]["run_value"].mean()
    offb_run = df2024[df2024["OFFB"] == 1]["run_value"].mean()
    fb_run = df2024[df2024["FB"] == 1]["run_value"].mean()

    hr_out = df2024[df2024["events"] == "home_run"]["event_out"].mean()
    walk_out = df2024[(df2024["events"] == "walk")|(df2024["events"] == "intentional_walk")]["event_out"].mean()
    hbp_out = df2024[df2024["events"] == "hit_by_pitch"]["event_out"].mean()
    k_out = df2024[(df2024["events"] == "strike_out")|(df2024["events"] == "uncaught_third_strike")]["event_out"].mean()
    gb_out = df2024[df2024["GB"] == 1]["event_out"].mean()
    iffb_out = df2024[df2024["IFFB"] == 1]["event_out"].mean()
    offb_out = df2024[df2024["OFFB"] == 1]["event_out"].mean()
    ld_out = df2024[df2024["LD"] == 1]["event_out"].mean()

    run_list = ["Run Value", hr_run, walk_run, hbp_run, k_run, gb_run, iffb_run, offb_run, ld_run]
    out_list = ["Out Value", hr_out, walk_out, hbp_out, k_out, gb_out, iffb_out, offb_out, ld_out]
    ro_cols = ["Expectancy", "HR", "BB", "HBP", "SO", "GB", "FB(IF)", "FB(OF)", "LD"]

    ro_df = pd.DataFrame([run_list, out_list]).set_axis(ro_cols, axis=1)
    ro_style = ro_df.style.format({
            'HR': '{:.3f}',
            'BB': '{:.3f}',
            'SO': '{:.3f}',
            'HBP': '{:.3f}',
            'GB': '{:.3f}',
            'FB(IF)': '{:.3f}',
            'FB(OF)': '{:.3f}',
            'LD': '{:.3f}',
        })
else:
    gb_run = np.nan
    ld_run = np.nan
    fb_run = np.nan
    iffb_run = np.nan
    offb_run = np.nan

value_list = [single_run, double_run, triple_run, hr_run, out_value, 
              k_run, bb_run, walk_run, hbp_run, gb_run, fb_run, iffb_run, offb_run, ld_run, sb_run, cs_run]
value_columns = ["1B", "2B", "3B", "HR", "Out", "SO", "BB", "BB-IBB", "HBP", 
                 "GB", "FB", "FB(IF)", "FB(OF)", "LD", "SB", "CS"]

rv_df = pd.DataFrame([value_list]).set_axis(value_columns, axis=1)
formatted_rv = rv_df.applymap(lambda x: '{:.3f}'.format(x))

bb_value = bb_run - out_value
hbp_value = hbp_run - out_value
single_value = single_run - out_value
double_value = double_run - out_value
triple_value = triple_run - out_value
hr_value = hr_run - out_value
if league == "1軍":
    gb_value = gb_run - out_value
    fb_value = fb_run - out_value
    ld_value = ld_run - out_value
    iffb_value = iffb_run - out_value
    offb_value = offb_run - out_value
else:
    gb_value = np.nan
    fb_value = np.nan
    ld_value = np.nan
    iffb_value = np.nan
    offb_value = np.nan

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

woba_list = [mean_woba * wOBA_scale, wOBA_scale, bb_value*wOBA_scale, hbp_value*wOBA_scale, 
             single_value*wOBA_scale, double_value*wOBA_scale, triple_value*wOBA_scale, hr_value*wOBA_scale]
woba_columns = ["wOBA", "wOBA scale", "wBB", "wHBP", "w1B", "w2B", "w3B", "wHR"]
woba_df = pd.DataFrame([woba_list]).set_axis(woba_columns, axis=1)
formatted_woba = woba_df.applymap(lambda x: '{:.3f}'.format(x))

runner_int = {
    "000": "000", "100": "100", "010": "020", "001": "003",
    "110": "120", "101": "103", "011": "023", "111": "123"
}

run_expectancy = RUNS
run_expectancy["Mean"] = my_round(run_expectancy["Mean"], 3)
run_expectancy["Runner"] = run_expectancy["RUNNER"].replace(runner_int)
run_expectancy = run_expectancy.pivot_table(index="Outs", columns="Runner", values="Mean")
# インデックスを並べ替えたい順序を指定
desired_order = ["000", "100", "020", "003", "120", "103", "023", "123"]
run_expectancy = run_expectancy[desired_order]
# アウトカウントのカラム名を変更
run_expectancy.index = ["0 Outs", "1 Out", "2 Outs"]
formatted_run_expectancy = run_expectancy.applymap(lambda x: '{:.3f}'.format(x))

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
count_bat_stats["vStrike"] = my_round(count_bat_stats["v_strike"], 3)
count_bat_stats["vBall"] = my_round(count_bat_stats["v_ball"], 3)
count_bat_stats["v_single"] = (single_value*wOBA_scale - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_double"] = (double_value*wOBA_scale - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_triple"] = (triple_value*wOBA_scale - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_home_run"] = (hr_value*wOBA_scale- count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_gb"] = (gb_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_fb"] = (fb_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_iffb"] = (iffb_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_offb"] = (offb_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_ld"] = (ld_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_hbp"] = (hbp_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v_out"] = (out_value - count_bat_stats["woba"])/wOBA_scale
count_bat_stats["v1B"] = my_round(count_bat_stats["v_single"], 3)
count_bat_stats["v2B"] = my_round(count_bat_stats["v_double"], 3)
count_bat_stats["v3B"] = my_round(count_bat_stats["v_triple"], 3)
count_bat_stats["vHR"] = my_round(count_bat_stats["v_home_run"], 3)
count_bat_stats["vHBP"] = my_round(count_bat_stats["v_hbp"], 3)
count_bat_stats["vGB"] = my_round(count_bat_stats["v_gb"], 3)
count_bat_stats["vFB"] = my_round(count_bat_stats["v_fb"], 3)
count_bat_stats["vIFFB"] = my_round(count_bat_stats["v_iffb"], 3)
count_bat_stats["vOFFB"] = my_round(count_bat_stats["v_offb"], 3)
count_bat_stats["vLD"] = my_round(count_bat_stats["v_ld"], 3)
count_bat_stats["vOut"] = my_round(count_bat_stats["v_out"], 3)
pitch_df = data.dropna(subset="pitch_number")
p_num = pitch_df.groupby("B-S").agg(
    P=("B-S", "size")
)
count_bat_stats = pd.merge(count_bat_stats, p_num, on="B-S")
count_bat_stats = count_bat_stats[["B-S", "P", "wOBA", "Run Value", "vBall", "vStrike", "v1B", "v2B", "v3B", "vHR", "vHBP", "vGB", "vFB", "vIFFB", "vOFFB", "vLD", "vOut"]]
bs_style = count_bat_stats.style.format({
            'Run Value': '{:.3f}',
            'wOBA': '{:.3f}',
            'vBall': '{:.3f}',
            'vStrike': '{:.3f}',
            'v1B': '{:.3f}',
            'v2B': '{:.3f}',
            'v3B': '{:.3f}',
            'vHR': '{:.3f}',
            'vHBP': '{:.3f}',
            'vGB': '{:.3f}',
            'vFB': '{:.3f}',
            'vIFFB': '{:.3f}',
            'vOFFB': '{:.3f}',
            'vLD': '{:.3f}',
            'vOut': '{:.3f}',
        })

st.markdown(f"{latest_date_str} 終了時点")

st.header("RE24")
st.table(formatted_run_expectancy)

st.header("Run Value(B-S)")
st.table(bs_style)

st.header("Run Value")
st.table(formatted_rv)

st.header("wOBA")
st.table(formatted_woba)

if league == "1軍":
    st.header("tRA")
    st.table(ro_style)