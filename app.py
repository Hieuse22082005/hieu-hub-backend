from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import random
import os
import time
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# --- CẤU HÌNH HỆ THỐNG & AI ---
SYSTEM_PASSWORD = os.environ.get("APP_PASSWORD", "hieu123")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

DATA_CACHE = {}
CACHE_TTL = 600

def load_data(sheet_url):
    if not sheet_url: 
        print("❌ Lỗi: Link Google Sheets đang để trống!")
        return pd.DataFrame()
    
    current_time = time.time()
    if sheet_url in DATA_CACHE:
        cached_data, timestamp = DATA_CACHE[sheet_url]
        if current_time - timestamp < CACHE_TTL:
            return cached_data

    try:
        csv_url = sheet_url.strip()
        if "docs.google.com/spreadsheets" in csv_url:
            if "/edit" in csv_url:
                base_url = csv_url.split("/edit")[0]
                csv_url = base_url + "/export?format=csv"
                if "gid=" in sheet_url:
                    try:
                        gid = sheet_url.split("gid=")[1].split("&")[0]
                        csv_url += f"&gid={gid}"
                    except:
                        pass
            elif not csv_url.endswith("/export?format=csv"):
                if not csv_url.endswith("/"):
                    csv_url += "/"
                csv_url += "export?format=csv"

        df = pd.read_csv(csv_url)
        df = df.fillna("")
        df.columns = [str(c).strip() for c in df.columns]
        
        for col in ['Từ', 'Nghĩa', 'Loại', 'Phát âm', 'Giới từ', 'Đồng nghĩa', 'Trái nghĩa']:
            if col not in df.columns: df[col] = ""
            else: df[col] = df[col].astype(str).str.strip()
                
        DATA_CACHE[sheet_url] = (df, current_time)
        return df
    except Exception as e:
        return pd.DataFrame()

def generate_distractors(df, current_val, col_name, num=3):
    others = df[df[col_name] != current_val][col_name].unique().tolist()
    others = [x for x in others if x != ""]
    if len(others) < num: num = len(others)
    if num <= 0: return [current_val]
    opts = [current_val] + random.sample(others, num)
    random.shuffle(opts)
    return opts

# --- API ENDPOINTS ---
@app.route('/api/login', methods=['POST'])
def login():
    return jsonify({"success": True})

@app.route('/api/get-data', methods=['POST'])
def get_data():
    url = request.json.get('sheet_url')
    df = load_data(url)
    return jsonify({"success": True, "data": df.to_dict('records')})

@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    prompt = request.json.get('prompt')
    if not GEMINI_API_KEY:
        return jsonify({"success": False, "reply": "Lỗi: Máy chủ Render chưa được cấu hình GEMINI_API_KEY!"})
    
    try:
        response = model.generate_content(f"Bạn là trợ lý học tiếng Anh thông minh Hieu's Hub. Hãy giải thích ngắn gọn, dễ hiểu và cho ví dụ TOEIC.\n\nUser: {prompt}")
        return jsonify({"success": True, "reply": response.text})
    except Exception as e: 
        return jsonify({"success": False, "reply": f"Lỗi AI: {str(e)}"})

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    sheet_url = data.get('sheet_url')
    mode = data.get('mode')
    num_questions = int(data.get('num', 10))
    
    df = load_data(sheet_url)
    if df.empty: 
        return jsonify({"success": False, "msg": "Không đọc được dữ liệu."})

    quiz_list = []
    if mode == "Dạng 7 (Đồng nghĩa)": df = df[df['Đồng nghĩa'] != ""]
    elif mode == "Dạng 8 (Trái nghĩa)": df = df[df['Trái nghĩa'] != ""]
        
    num_to_sample = min(num_questions, len(df))
    if num_to_sample <= 0:
        return jsonify({"success": False, "msg": "File không đủ dữ liệu để tạo đề!"})
        
    df_sample = df.sample(frac=1).head(num_to_sample).reset_index()

    for idx, row in df_sample.iterrows():
        tu = row.get('Từ', '').strip()
        nghia = row.get('Nghĩa', '').strip()
        loai = row.get('Loại', '').strip()
        ipa = row.get('Phát âm', '').strip()
        prep = row.get('Giới từ', '').strip()
        dong_nghia = row.get('Đồng nghĩa', '').strip()
        trai_nghia = row.get('Trái nghĩa', '').strip()
        
        # GOM TẤT CẢ THÔNG TIN TỪ VỰNG VÀO MỘT CHUỖI (TRỪ NGHĨA)
        details = []
        if ipa: details.append(f"🗣️ {ipa}")
        if loai: details.append(f"🏷️ {loai}")
        if prep: details.append(f"🔗 + {prep}")
        if dong_nghia: details.append(f"✨ Đồng nghĩa: {dong_nghia}")
        if trai_nghia: details.append(f"⚡ Trái nghĩa: {trai_nghia}")
        subtitle_str = "  |  ".join(details)
        
        q_obj = {"id": idx, "word": tu, "meaning": nghia, "type": "multiple_choice", "color": "#58a6ff"}

        if mode == "Dạng 1 (Trắc nghiệm)":
            q_obj["title"] = f"Câu {idx+1}: {tu}"
            q_obj["subtitle"] = subtitle_str # Truyền dải thông tin xuống giao diện
            q_obj["options"] = generate_distractors(df, nghia, 'Nghĩa')
            q_obj["answer"] = nghia
        elif mode == "Dạng 2 (Làm đâu biết đó)":
            q_obj["color"] = "#fffd75"
            q_obj["title"] = f"Từ vựng: {tu}"
            q_obj["subtitle"] = subtitle_str
            q_obj["options"] = generate_distractors(df, nghia, 'Nghĩa')
            q_obj["answer"] = nghia
        elif mode == "Dạng 3 (Viết từ)":
            q_obj["type"] = "typing"
            q_obj["color"] = "#00ffcc"
            q_obj["title"] = nghia
            # THÊM GỢI Ý IPA CHO DẠNG 3
            q_obj["subtitle"] = f"🗣️ Gợi ý IPA: {ipa}" if ipa else "Không có gợi ý IPA"
            q_obj["answer"] = tu
        elif mode == "Dạng 4 (Loại từ)":
            q_obj["color"] = "#ffa500"
            q_obj["title"] = f"Từ vựng: {tu}"
            q_obj["options"] = ["n", "v", "adj", "adv", "phr"]
            q_obj["answer"] = loai
        elif mode == "Dạng 5 (Giới từ)":
            q_obj["color"] = "#ff7b72"
            q_obj["title"] = f"Cấu trúc của từ: {tu}"
            ans_prep = prep.lower() if prep else "none"
            opts = ["none", "to", "from", "of", "with", "in", "on", "at", "for", "about", "be"]
            if ans_prep not in opts: opts.append(ans_prep)
            q_obj["options"] = opts
            q_obj["answer"] = ans_prep
        elif mode == "Dạng 6 (Chọn từ)":
            q_obj["title"] = f"Nghĩa: {nghia}"
            q_obj["options"] = generate_distractors(df, tu, 'Từ')
            q_obj["answer"] = tu
        elif mode == "Dạng 7 (Đồng nghĩa)":
            q_obj["color"] = "#bd93f9"
            q_obj["title"] = f"Tìm từ ĐỒNG NGHĨA với: {tu}"
            dong_nghia = row.get('Đồng nghĩa').strip()
            q_obj["options"] = generate_distractors(df, dong_nghia, 'Đồng nghĩa')
            q_obj["answer"] = dong_nghia
        elif mode == "Dạng 8 (Trái nghĩa)":
            q_obj["color"] = "#ff5555"
            q_obj["title"] = f"Tìm từ TRÁI NGHĨA với: {tu}"
            trai_nghia = row.get('Trái nghĩa').strip()
            q_obj["options"] = generate_distractors(df, trai_nghia, 'Trái nghĩa')
            q_obj["answer"] = trai_nghia

        quiz_list.append(q_obj)
    return jsonify({"success": True, "data": quiz_list})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
