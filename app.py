from flask import Flask, render_template, request, send_file, jsonify, session, redirect, url_for
import pandas as pd
import numpy as np
from scipy import stats
import os

app = Flask(__name__)
app.secret_key = "replace_with_a_strong_secret_key"

# Biến toàn cục để lưu dữ liệu tạm
DATAFRAME = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    global DATAFRAME
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Không có file"}), 400

    try:
        df = pd.read_csv(file, encoding="utf-8")
    except:
        file.seek(0)
        df = pd.read_csv(file, encoding="latin1")

    # Chuẩn hóa tên cột
    df.columns = df.columns.str.strip().str.replace(" ", "").str.capitalize()

    # Kiểm tra cột Lop
    if "Lop" not in df.columns:
        return jsonify({"error": "Không tìm thấy cột Lop"}), 400

    # Kiểm tra cột MaHS
    student_col = [c for c in df.columns if c.lower() in ["mahs", "id", "studentid"]]
    if not student_col:
        return jsonify({"error": "Không tìm thấy cột MaHS"}), 400

    df["MaHS"] = df[student_col[0]]
    DATAFRAME = df  # Lưu lại để phân tích sau

    lops = df["Lop"].unique().tolist()
    mons = [c for c in df.columns if c not in ["MaHS", "Lop"]]

    return jsonify({"lops": lops, "mons": mons})

@app.route("/analyze", methods=["POST"])
def analyze():
    global DATAFRAME
    if DATAFRAME is None:
        return jsonify({"error": "Chưa upload file"}), 400

    data = request.get_json()
    lop = data.get("lop")
    mon = data.get("mon")
    z_threshold = float(data.get("zscore", 2.0))

    df = DATAFRAME.copy()

    # Lọc theo lớp
    if lop and lop != "All":
        df = df[df["Lop"] == lop]

    # Xác định môn học
    mons = [c for c in df.columns if c not in ["MaHS", "Lop"]]
    if mon and mon != "All" and mon in mons:
        mons = [mon]

    # Tính z-score và bất thường
    chart_data = []
    scatter_data = []
    hist_data = []

    for m in mons:
        df[f"Z_{m}"] = stats.zscore(df[m].fillna(0))
        df[f"Highlight_{m}"] = df[f"Z_{m}"].abs() > z_threshold

        chart_data.append({
            "Lop": lop if lop != "All" else "Tất cả",
            "Diem": round(df[m].mean(), 2)
        })

        scatter_data += [
            {"Lop": row["Lop"], "Diem": row[m]} for _, row in df.iterrows()
        ]

        hist_data = df[m].dropna().tolist()

    return jsonify({
        "chart_data": chart_data,
        "scatter_data": scatter_data,
        "hist_data": hist_data
    })

@app.route("/download")
def download():
    global DATAFRAME
    if DATAFRAME is None:
        return "Chưa có dữ liệu để tải", 400

    anomalies = DATAFRAME[DATAFRAME.filter(like="Highlight_").any(axis=1)]
    filename = "Students_Anomalies.csv"
    anomalies.to_csv(filename, index=False, encoding="utf-8")
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
