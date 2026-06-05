import streamlit as st
from datetime import date
import json
import os
import math

# =================【功能 1：資料永久存檔機制】=================
DB_FILE = "exams_data.json"

def load_data():
    """從檔案讀取資料"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    """將目前的最新資料儲存進檔案"""
    serializable_data = {}
    for exam, data in st.session_state.exams.items():
        serializable_data[exam] = {
            "date": data["date"].isoformat() if isinstance(data["date"], date) else data["date"],
            "chapters": data["chapters"]
        }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=4)

# =================【核心修正：舊資料結構自動升級防呆】=================
if 'exams' not in st.session_state:
    raw_data = load_data()
    st.session_state.exams = {}
    
    for exam, data in raw_data.items():
        migrated_chapters = []
        for ch in data.get("chapters", []):
            # 情況 A：如果偵測到使用者地上的舊資料是純字串（舊版本）
            if isinstance(ch, str):
                migrated_chapters.append({
                    "name": ch,
                    "hours": 1.0,         # 自動補上預設 1 小時
                    "difficulty": "🟢 簡單" # 自動補上預設簡單標籤
                })
            # 情況 B：如果是新版的字典結構
            elif isinstance(ch, dict):
                migrated_chapters.append({
                    "name": ch.get("name", "未命名章節"),
                    "hours": ch.get("hours", 1.0),
                    "difficulty": ch.get("difficulty", "🟢 簡單")
                })
        
        # 處理日期字串轉回物件
        exam_date = data["date"]
        if isinstance(exam_date, str):
            exam_date = date.fromisoformat(exam_date)
            
        st.session_state.exams[exam] = {
            "date": exam_date,
            "chapters": migrated_chapters
        }
    # 修復完成後立刻重寫檔案，確保地上檔案結構也是最新的
    save_data()

# 網頁頂部基本設定
st.set_page_config(page_title="智能讀書計畫與時間分配系統", page_icon="⏱️", layout="wide")
st.title("📚 智能讀書計畫與時間分配系統")
st.write("精準管理考試倒數，自動規劃每日讀書配速！")
st.markdown("---")

# =================【功能 2：頂部今日讀書大盤點儀表板】=================
today = date.today()
total_today_hours = 0.0
active_exams_count = 0

# 計算今天各科加總總共要讀多少小時
for exam_name, data in st.session_state.exams.items():
    days_left = (data["date"] - today).days
    if days_left > 0:
        active_exams_count += 1
        # 排除掉網頁上已經打勾複習完的章節時數
        uncompleted_hours = sum(ch["hours"] for ch in data["chapters"] if not st.session_state.get(f"cb_{exam_name}_{ch['name']}", False))
        total_today_hours += (uncompleted_hours / days_left)

# 顯示最上方的番茄鐘大看板
if active_exams_count > 0 and total_today_hours > 0:
    with st.container(border=True):
        st.markdown("### 📅 今日讀書排程與配速建議")
        t_hours = int(total_today_hours)
        t_minutes = int(round((total_today_hours - t_hours) * 60))
        
        col_t1, col_t2 = st.columns([1, 2])
        with col_t1:
            st.metric(label="今日需讀書總時數", value=f"{t_hours} 小時 {t_minutes} 分鐘")
        with col_t2:
            pomodoro = math.ceil(total_today_hours * 2)
            st.info(f"💡 **無痛達標建議（區塊時間法）：**\n"
                    f"今天建議將讀書時間拆成 **{pomodoro} 個番茄鐘**（讀 25 分鐘、休息 5 分鐘）。\n"
                    f"利用空檔把規定數量的番茄鐘分配完，就能輕鬆跟上進度囉！")

# =================【側邊欄：新增考試科目】=================
with st.sidebar:
    st.header("➕ 新增考試科目")
    new_exam_name = st.text_input("請輸入新科目名稱（如：微積分）：", key="new_exam")
    new_exam_date = st.date_input("請選擇考試日期：", value=date.today(), key="new_date")
    
    if st.button("確認新增科目", use_container_width=True):
        if new_exam_name.strip() == "":
            st.error("科目名稱不能留空！")
        elif new_exam_name in st.session_state.exams:
            st.sidebar.warning("這個科目已經存在囉！")
        else:
            st.session_state.exams[new_exam_name] = {"date": new_exam_date, "chapters": []}
            save_data()
            st.rerun()

# =================【主畫面：各科進度與時間分配】=================
if not st.session_state.exams:
    st.info("💡 目前沒有任何考試科目。請使用左側邊欄輸入你的第一個考試科目吧！")
else:
    for exam_name, data in list(st.session_state.exams.items()):
        exam_date = data["date"]
        chapters = data["chapters"]
        days_left = (exam_date - today).days
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"🎯 科目：{exam_name}")
                st.caption(f"📅 考試日期：{exam_date}")
            with col2:
                if days_left > 0:
                    st.metric(label="倒數天數", value=f"{days_left} 天")
                elif days_left == 0:
                    st.metric(label="倒數天數", value="💥 今天考試！")
                else:
                    st.metric(label="倒數天數", value=f"已過 {abs(days_left)} 天")

            # --- 功能 3：章節進度條與困難度顯示 ---
            st.write("📖 **章節複習進度：** (勾選代表已讀完)")
            remaining_hours = 0.0
            total_hours = 0.0
            completed_chapters = 0
            
            if chapters:
                cols = st.columns(min(len(chapters), 4)) # 一行最多並排 4 個章節
                for idx, ch in enumerate(chapters):
                    total_hours += ch["hours"]
                    diff_tag = ch.get("difficulty", "🟢 簡單")
                    
                    with cols[idx % 4]:
                        # 格式化顯示：把困難度標籤擺在最前面，視覺排版更整齊
                        display_label = f"{diff_tag} | {ch['name']} ({ch['hours']}hr)"
                        is_done = st.checkbox(display_label, key=f"cb_{exam_name}_{ch['name']}", on_change=save_data)
                        if not is_done:
                            remaining_hours += ch["hours"]
                        else:
                            completed_chapters += 1
                
                # 渲染進度條
                progress_percent = int((completed_chapters / len(chapters)) * 100)
                st.progress(completed_chapters / len(chapters))
                st.caption(f"📊 目前複習進度：{progress_percent}% (已完成 {completed_chapters}/{len(chapters)} 個章節)")
            else:
                st.caption("⚠️ 目前尚未新增任何章節。")

            # --- 功能 4：動態平攤並換算單科每日配速時間 ---
            if chapters and days_left > 0:
                if remaining_hours == 0:
                    st.success("🎉 太強了！這一科的所有章節都已經複習完畢囉！")
                else:
                    daily_hours_float = remaining_hours / days_left
                    d_hours = int(daily_hours_float)
                    d_minutes = int(round((daily_hours_float - d_hours) * 60))
                    time_text = f"{d_hours} 小時 {d_minutes} 分鐘" if d_hours > 0 else f"{d_minutes} 分鐘"
                    st.warning(f"📈 這一科平均每天需要分配：**{time_text}** 的讀書時間")

            st.markdown("---")
            
            # --- 新增章節輸入區塊 ---
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                new_ch_name = st.text_input(f"為「{exam_name}」新增章節名稱：", placeholder="例如：CH1 導論", key=f"input_ch_{exam_name}")
            with c2:
                new_ch_hours = st.number_input("預估時間 (小時)", min_value=0.5, value=1.0, step=0.5, key=f"input_hr_{exam_name}")
            with c3:
                new_ch_diff = st.selectbox("設定困難度", ["🟢 簡單", "🟡 中等", "🔴 困難"], key=f"input_df_{exam_name}")
            with c4:
                st.write(""); st.write("")
                if st.button("➕ 新增章節", key=f"btn_ch_{exam_name}", use_container_width=True):
                    if new_ch_name.strip() != "":
                        existing_names = [c.get("name") for c in st.session_state.exams[exam_name]["chapters"]]
                        if new_ch_name not in existing_names:
                            st.session_state.exams[exam_name]["chapters"].append({
                                "name": new_ch_name,
                                "hours": new_ch_hours,
                                "difficulty": new_ch_diff
                            })
                            save_data()
                            st.rerun()
                        else:
                            st.warning("該章節名稱已存在！")
                    else:
                        st.error("⚠️ 欄位不能留空，請先輸入章節名稱喔！")
            
            # 刪除整科科目按鈕
            if st.button(f"🗑️ 刪除 {exam_name} 科目", key=f"del_{exam_name}"):
                del st.session_state.exams[exam_name]
                save_data()
                st.rerun()