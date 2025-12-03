from flask import Flask, render_template, request, session, url_for, Response
import csv
import random
import os
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")  # 使用非互動後端
import matplotlib.pyplot as plt

# ✅ 讓 matplotlib 支援中文（Windows 建議用微軟正黑體）
from matplotlib import rcParams
rcParams['font.sans-serif'] = ['Microsoft JhengHei']  # 如果跑不動可改成 'SimHei'
rcParams['axes.unicode_minus'] = False  # 避免負號變成方塊


app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# --- 核心計算邏輯 ---

def get_health_advice(blood_pressure_in, blood_pressure_out, blood_sugar, height, weight):
    # 四個字典：鍵名固定用英文，避免 KeyError
    fontLargestStrong = {'blood_pressure': [], 'blood_sugar': [], 'bmi': []}
    fontSecondStrong  = {'blood_pressure': [], 'blood_sugar': [], 'bmi': []}
    fontNormalStrong  = {'blood_pressure': [], 'blood_sugar': [], 'bmi': []}
    fontNormal        = {'blood_pressure': [], 'blood_sugar': [], 'bmi': []}

    # ---------------- 血壓判斷 ----------------
    if isinstance(blood_pressure_in, float) and isinstance(blood_pressure_out, float):

        # 高血壓
        if blood_pressure_in > 120 or blood_pressure_out > 80:
            fontLargestStrong['blood_pressure'].append("血壓太高 > 120/80 mmHg")
            fontSecondStrong['blood_pressure'].append("！注意！建議與醫師討論血壓控制。")
            fontNormalStrong['blood_pressure'].extend([
                "一般建議血壓落在約 90–120 / 60–80 mmHg。",
                "可以從減少外食、降低鹽分、避免含糖飲料開始調整。",
                "每週至少 150 分鐘的中強度有氧運動（快走、慢跑、騎腳踏車），有助於降血壓與減脂。"
            ])
            fontNormal['blood_pressure'].append("減脂時避免極端斷食，以免頭暈或血壓劇烈波動。")

        # 低血壓
        elif blood_pressure_in < 90 or blood_pressure_out < 60:
            fontLargestStrong['blood_pressure'].append("血壓偏低 < 90/60 mmHg")
            fontSecondStrong['blood_pressure'].append("！注意！若常頭暈、眼前發黑，建議就醫評估。")
            fontNormalStrong['blood_pressure'].extend([
                "正常血壓範圍約為 90–120 / 60–80 mmHg。",
                "每天喝足夠的水，避免長時間站立或待在悶熱環境。",
                "減脂期間仍需保留一定的主食（澱粉），避免因熱量過低導致低血壓不適。"
            ])
            fontNormal['blood_pressure'].append("可準備少量含電解質飲品或點心，當作偶發低血壓時的緊急補充。")

        # 正常血壓 → 也給維持 / 減脂建議
        else:
            fontLargestStrong['blood_pressure'].append("血壓在理想範圍內，狀態不錯！")
            fontSecondStrong['blood_pressure'].append("穩定的血壓對減脂、運動表現與心血管健康都很重要。")
            fontNormalStrong['blood_pressure'].extend([
                "正常血壓範圍約為 90–120 / 60–80 mmHg。",
                "可以維持每週 3–5 次、每次 30 分鐘以上的有氧運動。",
                "搭配 2–3 次重量訓練，幫助增加肌肉量與基礎代謝率。"
            ])
            fontNormal['blood_pressure'].append("建議每 3–6 個月量一次血壓，持續追蹤自己的變化。")

    else:
        fontLargestStrong['blood_pressure'].append("尚未輸入收縮壓與舒張壓，無法提供血壓相關建議。")

    # ---------------- 血糖判斷 ----------------
    if isinstance(blood_sugar, float):

        # 高血糖
        if blood_sugar > 140:
            fontLargestStrong['blood_sugar'].append("血糖偏高 > 140 mg/dL")
            fontSecondStrong['blood_sugar'].append("！注意！建議與醫師或營養師討論飲食控制。")
            fontNormalStrong['blood_sugar'].extend([
                "一般來說，空腹血糖建議 70–100 mg/dL，飯後兩小時 70–140 mg/dL。",
                "減脂時可以多選擇低 GI 的澱粉來源，例如：糙米、地瓜、燕麥。",
                "盡量避免含糖飲料、甜點與精緻澱粉（白麵包、蛋糕等），同時有利於穩定血糖與減脂。"
            ])
            fontNormal['blood_sugar'].append("搭配規律運動，可以提升胰島素敏感度，對血糖與體重控制都有幫助。")

        # 低血糖
        elif blood_sugar < 70:
            fontLargestStrong['blood_sugar'].append("血糖偏低 < 70 mg/dL")
            fontSecondStrong['blood_sugar'].append("！注意！若常出現手抖、冒冷汗或心悸，請盡快就醫。")
            fontNormalStrong['blood_sugar'].extend([
                "空腹正常血糖約為 70–100 mg/dL，飯後兩小時約 70–140 mg/dL。",
                "減脂不能完全不吃澱粉，建議分散在一天中少量多餐，避免血糖大起大落。"
            ])
            fontNormal['blood_sugar'].append("可準備一點水果、牛奶或無糖優格，作為血糖過低時的應急小點心。")

        # 正常血糖 → 一樣給飲食 / 減脂建議
        else:
            fontLargestStrong['blood_sugar'].append("血糖目前在安全範圍內 👍")
            fontSecondStrong['blood_sugar'].append("穩定血糖有助於控制食慾與維持專注力。")
            fontNormalStrong['blood_sugar'].extend([
                "空腹正常血糖約為 70–100 mg/dL，飯後兩小時約 70–140 mg/dL。",
                "減脂方向建議：以『少油、少糖、多纖維』為原則，而不是完全不吃。",
                "主食可以優先選擇原型澱粉（糙米、地瓜、燕麥）搭配足量蔬菜與蛋白質。"
            ])
            fontNormal['blood_sugar'].append("避免含糖飲料與宵夜，是長期瘦身非常關鍵的一步。")
    else:
        fontLargestStrong['blood_sugar'].append("尚未輸入血糖，無法提供血糖相關建議。")

    # ---------------- BMI 判斷 ----------------
    if isinstance(weight, float) and isinstance(height, float) and height > 0:
        bmi = round(weight / (height / 100) ** 2, 2)

        # 肥胖
        if bmi >= 27:
            fontLargestStrong['bmi'].append(f"你的 BMI 為 {bmi} → 肥胖範圍")
            fontSecondStrong['bmi'].append("建議以『健康減脂』為長期目標，而不是速成瘦身。")
            fontNormalStrong['bmi'].extend([
                "正常BMI範圍為18.5-24。",
                "每週可先設定減重 0.5–1.0 公斤為目標，避免減太快造成肌肉流失。",
                "飲食：控制總熱量、優先確保蛋白質，減少含糖飲料與油炸食物。",
                "運動：每週 3–5 次有氧 + 2–3 次重量訓練，循序漸進即可。"
            ])
            fontNormal['bmi'].append("若有三高或心血管疾病家族史，建議與醫療專業討論個人化減重計畫。")

        # 過重
        elif 24 <= bmi < 27:
            fontLargestStrong['bmi'].append(f"你的 BMI 為 {bmi} → 過重")
            fontSecondStrong['bmi'].append("再調整一些生活習慣，就有機會回到理想範圍！")
            fontNormalStrong['bmi'].extend([
                "正常BMI範圍為18.5-24。",
                "可以從『每天少一杯含糖飲料』或『晚餐少半碗飯』開始建立熱量赤字。",
                "若有計算 TDEE，可將每日攝取略微壓在 TDEE 以下，讓體脂慢慢下降。"
            ])
            fontNormal['bmi'].append("建議每 2–4 週量一次體重與腰圍，重視趨勢比單次數字更重要。")

        # 正常體重
        elif 18.5 <= bmi < 24:
            fontLargestStrong['bmi'].append(f"你的 BMI 為 {bmi} → 體重在正常範圍 🙂")
            fontSecondStrong['bmi'].append("如果目標是『體態更精實』或『線條更明顯』，仍可透過飲食與運動微調。")
            fontNormalStrong['bmi'].extend([
                "正常BMI範圍為18.5-24。",
                "可以參考 TDEE，把每日熱量稍微壓在 TDEE 以下一點點，讓體脂慢慢下降。",
                "持續規律重量訓練，有助於增加肌肉量與改善體態比例。",
                "避免過度節食，否則容易掉肌肉、代謝降低，反而不利於體態維持。"
            ])
            fontNormal['bmi'].append("你已經有不錯的基礎，可以把重點放在『體脂、肌肉量與精神狀態』，而不是只看體重。")

        # 過輕
        else:
            fontLargestStrong['bmi'].append(f"你的 BMI 為 {bmi} → 過輕")
            fontSecondStrong['bmi'].append("若常感到疲倦、容易感冒或有月經異常（女性），建議與醫師討論。")
            fontNormalStrong['bmi'].extend([
                "建議以增肌與健康為優先目標，而不是再繼續減重。",
                "可增加優質澱粉（全穀根莖）、蛋白質與健康脂肪（堅果、酪梨、橄欖油）。"
            ])
            fontNormal['bmi'].append("搭配重量訓練與足夠睡眠，有助於增加肌肉、提升體力與代謝。")

    else:
        fontLargestStrong['bmi'].append("尚未輸入身高或體重，無法計算 BMI 與體態建議。")

    return fontLargestStrong, fontSecondStrong, fontNormalStrong, fontNormal


def calculate_tdee_advice(weight, height, age, gender, activity_level, goal):
    """計算 BMR, TDEE 並根據 '增肌' 或 '減脂' 提供建議"""
    if not (weight and height and age and gender and activity_level):
        return None

    # 1. 計算 BMR (Mifflin-St Jeor 公式)
    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    bmr = int(round(bmr, 0))

    # 2. 計算 TDEE
    tdee = int(round(bmr * activity_level, 0))

    # 3. 根據目標 (goal) 提供建議
    advice = {}
    
    if goal == 'bulk':  # 增肌
        min_cal = tdee + 200
        max_cal = tdee + 300
        advice['title'] = "增肌建議 (Muscle Gain)"
        advice['cal_range'] = f"每日建議熱量：{min_cal} ~ {max_cal} 大卡"
        advice['desc'] = [
            f"建議攝取超過 TDEE ({tdee}) 約 200～300 卡。",
            "飲食重點：蛋白質與碳水化合物需相互配合。",
            "蛋白質能形成肌肉，碳水化合物可以防止肌肉流失。",
            "建議分配：蛋白質應佔總熱量的 30～40％、碳水化合物應佔 35～40％。"
        ]
    elif goal == 'cut':  # 減脂
        max_cal = int(tdee * 0.9)  # -10%
        min_cal = int(tdee * 0.8)  # -20%
        advice['title'] = "減脂建議 (Fat Loss)"
        advice['cal_range'] = f"每日建議熱量：{min_cal} ~ {max_cal} 大卡"
        advice['desc'] = [
            f"建議每日減少攝取約 {int(tdee * 0.1)} ~ {int(tdee * 0.2)} 大卡 (約 10~20%)。",
            f"只要整天熱量攝取低於 TDEE ({tdee})，就有瘦身效果。",
            "建議：高纖維、高蛋白、控制精緻澱粉攝取。",
            "搭配適度重量訓練可避免肌肉流失。"
        ]
    else:  # 維持
        advice['title'] = "維持體重"
        advice['cal_range'] = f"每日建議熱量：{tdee} 大卡"
        advice['desc'] = ["攝取與消耗熱量平衡，即可維持目前體重。"]

    return {
        'bmr': bmr,
        'tdee': tdee,
        'advice': advice,
        'goal': goal
    }

# ========= 取得某暱稱的體重歷史 =========

def get_weight_history_for_nickname(nickname):
    dates = []
    weights = []
    if not nickname:
        return dates, weights

    try:
        if os.path.exists('health_records.csv'):
            with open('health_records.csv', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    # 結構：0 日期, 1 暱稱, 6 體重
                    if len(row) >= 7:
                        dt = row[0]
                        nick = row[1]
                        w = row[6]
                        if nick == nickname and w not in (None, "", "None"):
                            try:
                                w_val = float(w)
                                dates.append(dt)
                                weights.append(w_val)
                            except ValueError:
                                continue
    except Exception as e:
        print(f"Error reading weight history: {e}")

    return dates, weights


# ========= 新增：取得某暱稱在 bulk 模式的「肌力指標」歷史 =========

def get_strength_history_for_nickname(nickname):
    dates = []
    scores = []
    if not nickname:
        return dates, scores

    try:
        if os.path.exists('health_records.csv'):
            with open('health_records.csv', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    # 結構（新）：最後一欄是 strength_score，倒數第二欄是 goal
                    if len(row) >= 18:
                        dt = row[0]
                        nick = row[1]
                        goal = row[16]
                        strength = row[17]
                        if nick == nickname and goal == 'bulk' and strength not in (None, "", "None"):
                            try:
                                s_val = float(strength)
                                dates.append(dt)
                                scores.append(s_val)
                            except ValueError:
                                continue
    except Exception as e:
        print(f"Error reading strength history: {e}")

    return dates, scores


# --- 路由 ---

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/result', methods=['POST'])
def result():
    nickname = request.form.get('nickname') or ""
    session['nickname'] = nickname

    # 基礎數據
    blood_pressure_in = float(request.form.get('blood_pressure_in')) if request.form.get('blood_pressure_in') else None
    blood_pressure_out = float(request.form.get('blood_pressure_out')) if request.form.get('blood_pressure_out') else None
    blood_sugar = float(request.form.get('blood_sugar')) if request.form.get('blood_sugar') else None
    height = float(request.form.get('height')) if request.form.get('height') else None
    weight = float(request.form.get('weight')) if request.form.get('weight') else None
    mood = request.form.get('mood') or ""
    hide_nickname = "yes" if request.form.get('hide_nickname') == "yes" else "no"

    # TDEE 相關輸入
    age = int(request.form.get('age')) if request.form.get('age') else None
    gender = request.form.get('gender')   # 'male' or 'female'
    activity_level = float(request.form.get('activity_level')) if request.form.get('activity_level') else None
    goal = request.form.get('goal')       # 'bulk' or 'cut'
    session['goal'] = goal  # 之後如果要用也可以

    # 今日肌力指標（可空白）
    strength_score = float(request.form.get('strength_score')) if request.form.get('strength_score') else None

    # BMI 計算
    bmi_value = None
    if height and weight:
        bmi_value = round(weight / ((height / 100) ** 2), 2)

    # 心情小語
    encouragement_phrases = {
        '開心': ["快樂是一種能力，繼續保持這份美好！", "今天的成功是因為昨天的積累，明天的成功依靠今天的努力。"],
        '難過': ["當你感到難過時，記得這只是暫時的，陽光總會照進來。", "再長的路，一步步也能走完。"],
        '焦慮': ["勇氣不是沒有恐懼，而是克服恐懼。", "只要努力，你就能成為你想成為的人。"],
        '生氣': ["學會掌控自己的情緒，就是掌控了自己的生活。", "不要被憤怒支配，冷靜是你最強的武器。"],
        '挫折': ["沒有絕望的處境，只有對處境絕望的人。", "失敗只是成功的墊腳石，再試一次吧！"]
    }
    encouragement_phrase = None
    if mood in encouragement_phrases:
        encouragement_phrase = random.choice(encouragement_phrases[mood])

    # 呼叫健康建議
    fontLargestStrong, fontSecondStrong, fontNormalStrong, fontNormal = get_health_advice(
        blood_pressure_in, blood_pressure_out, blood_sugar, height, weight
    )

    # 呼叫 TDEE 計算
    tdee_data = calculate_tdee_advice(weight, height, age, gender, activity_level, goal)
    
    # 準備寫入 CSV 的字串
    tdee_val = tdee_data['tdee'] if tdee_data else ""
    bmr_val = tdee_data['bmr'] if tdee_data else ""
    goal_val = goal if goal else ""

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CSV 寫入
    # 結構：0日期,1暱稱,2收縮,3舒張,4血糖,5身高,6體重,7BMI,8心情,9鼓勵語,10hide,
    #      11Age,12Gender,13Activity,14BMR,15TDEE,16Goal,17StrengthScore
    with open('health_records.csv', mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            current_date, nickname, blood_pressure_in, blood_pressure_out, blood_sugar, 
            height, weight, bmi_value, mood, encouragement_phrase, hide_nickname,
            age, gender, activity_level, bmr_val, tdee_val, goal_val, strength_score
        ])

    return render_template(
        'result.html',
        fontLargestStrong=fontLargestStrong,
        fontSecondStrong=fontSecondStrong,
        fontNormalStrong=fontNormalStrong,
        fontNormal=fontNormal,
        encouragement_phrase=encouragement_phrase,
        tdee_data=tdee_data,
        bmi_value=bmi_value
    )


@app.route('/GI')
def GI():
    return render_template('GI.html')

@app.route('/info')
def info():
    return render_template('info.html')


# ========= 體重折線圖 =========

@app.route('/weight_plot.png')
@app.route('/weight_plot.png')
@app.route('/weight_plot.png')
def weight_plot():
    nickname = session.get('nickname')
    dates, weights = get_weight_history_for_nickname(nickname)

    fig, ax = plt.subplots()

    if weights:
        x = np.arange(len(weights))
        ax.plot(x, weights, marker='o')

        # 英文 Y 軸 / X 軸（保持不變）
        ax.set_ylabel("Weight (kg)")
        ax.set_xlabel("Record Order (Old → New)")

        # ★ 標題改成中文暱稱
        if nickname:
            ax.set_title(f"{nickname} 的體重變化")
        else:
            ax.set_title("體重變化")

        # X 軸標籤（保持英文）
        if len(weights) >= 2:
            ax.set_xticks([0, len(weights) - 1])
            ax.set_xticklabels(["First", "Latest"])
        else:
            ax.set_xticks([0])
            ax.set_xticklabels(["First"])

        ax.margins(x=0.05, y=0.1)

    else:
        # 無資料時英文提示
        ax.text(
            0.5, 0.5,
            "Not enough weight records.\nRecord a few more times!",
            ha='center', va='center',
            transform=ax.transAxes, fontsize=11
        )
        ax.set_axis_off()

    from io import BytesIO
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')


# ========= ⭐ bulk 模式肌力提升趨勢圖 =========

@app.route('/strength_plot.png')
@app.route('/strength_plot.png')
@app.route('/strength_plot.png')
def strength_plot():
    nickname = session.get('nickname')
    dates, scores = get_strength_history_for_nickname(nickname)

    fig, ax = plt.subplots()

    if scores:
        x = np.arange(len(scores))
        ax.plot(x, scores, marker='o')

        # 保持英文座標軸
        ax.set_ylabel("Strength Score (e.g., Squat kg)")
        ax.set_xlabel("Record Order (Bulk Mode Only)")

        # ★ 只有標題改成「中文暱稱＋肌力趨勢」
        if nickname:
            ax.set_title(f"{nickname} 的肌力趨勢（Bulk 模式）")
        else:
            ax.set_title("肌力趨勢（Bulk 模式）")

        # X 軸標籤維持 First / Latest
        if len(scores) >= 2:
            ax.set_xticks([0, len(scores) - 1])
            ax.set_xticklabels(["First", "Latest"])
        else:
            ax.set_xticks([0])
            ax.set_xticklabels(["First"])

        ax.margins(x=0.05, y=0.1)

    else:
        ax.text(
            0.5, 0.5,
            "No 'bulk' strength records.\nSelect bulk mode and enter today's strength score.",
            ha='center', va='center',
            transform=ax.transAxes, fontsize=10
        )
        ax.set_axis_off()

    from io import BytesIO
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png')


@app.route('/history')
def history():
    my_nickname = session.get('nickname')
    all_records = []
    try:
        if os.path.exists('health_records.csv'):
            with open('health_records.csv', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    # 簡易防呆，避免讀取錯誤格式
                    if len(row) < 9:
                        continue
                    
                    dt = row[0]
                    nick = row[1] if len(row) > 1 else ""
                    bmi = row[7] if len(row) > 7 else ""
                    mood = row[8] if len(row) > 8 else ""
                    hide = row[10] if len(row) > 10 else "no"
                    tdee_v = row[15] if len(row) > 15 else ""
                    goal = row[16] if len(row) > 16 else ""
                    strength = row[17] if len(row) > 17 else ""

                    h = row[5] if len(row) > 5 else ""
                    w = row[6] if len(row) > 6 else ""
                    bp_in = row[2] if len(row) > 2 else ""
                    bp_out = row[3] if len(row) > 3 else ""
                    bs = row[4] if len(row) > 4 else ""

                    all_records.append({
                        'datetime': dt, 'nickname': nick,
                        'height': h, 'weight': w, 'bp_in': bp_in, 'bp_out': bp_out, 'blood_sugar': bs,
                        'bmi': bmi, 'mood': mood, 'hide': hide, 'tdee': tdee_v,
                        'goal': goal, 'strength': strength
                    })
    except Exception as e:
        print(f"Error reading history: {e}")
        all_records = []

    public_records = []
    for r in all_records:
        display_name = "匿名用戶" if r['hide'] == "yes" else r['nickname']
        public_records.append({**r, 'display_name': display_name})

    if my_nickname:
        my_records = [r for r in all_records if r['nickname'] == my_nickname]
    else:
        my_records = []

    return render_template(
        'history.html',
        public_records=public_records,
        my_records=my_records,
        my_nickname=my_nickname
    )


if __name__ == '__main__':
    app.run(debug=True)
