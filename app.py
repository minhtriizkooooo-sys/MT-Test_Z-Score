from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
import numpy as np
from scipy import stats
import io
import plotly.express as px
import plotly
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # cần cho session

# ===== Route intro video =====
@app.route("/intro")
def intro():
    # Nếu intro đã xem, redirect thẳng index
    if session.get("intro_played"):
        return redirect(url_for("index"))
    return render_template("intro.html")

# ===== Route chính =====
@app.route("/", methods=["GET", "POST"])
def index():
    # đánh dấu intro đã xem
    session["intro_played"] = True

    anomalies = None
    summary_json = None
    scatter_plots = []
    hist_plots = []
    filename = None
    error = None
    tables = None

    if request.method == "POST":
        z_threshold = float(request.form.get("z_threshold", 2.0))
        file = request.files.get("file")

        if file:
            # Đọc CSV
            try:
                df = pd.read_csv(file, encoding="utf-8")
            except:
                file.seek(0)
                df = pd.read_csv(file, encoding="latin1")

            # Chuẩn hóa tên cột
            df.columns = df.columns.str.strip().str.replace(" ","").str.capitalize()

            # Kiểm tra cột Lop
            if "Lop" not in df.columns:
                error = "Không tìm thấy cột 'Lop'"
                return render_template("index.html", error=error)

            # Kiểm tra cột MaHS
            student_col = [c for c in df.columns if c.lower() in ["mahs","id","studentid"]]
            if not student_col:
                error = "Không tìm thấy cột 'MaHS'"
                return render_template("index.html", error=error)
            df["MaHS"] = df[student_col[0]]

            # Các cột môn học
            subject_cols = [c for c in df.columns if c not in ["MaHS","Lop"]]
            if not subject_cols:
                error = "Không tìm thấy cột điểm môn học"
                return render_template("index.html", error=error)

            # Tính Z-score
            for subj in subject_cols:
                df[f"Z_{subj}"] = stats.zscore(df[subj].fillna(0))
                df[f"Highlight_{subj}"] = df[f"Z_{subj}"].abs() > z_threshold

            # Lọc anomalies
            anomalies = df[df[[f"Highlight_{s}" for s in subject_cols]].any(axis=1)]

            # Tạo summary
            class_summary = df.groupby("Lop").size().reset_index(name="Tổng học sinh")
            anomaly_count = anomalies.groupby("Lop").size().reset_index(name="Học sinh bất thường")
            summary = pd.merge(class_summary, anomaly_count, on="Lop", how="left").fillna(0)

            # Bar chart
            fig_col = px.bar(summary, x="Lop", y=["Tổng học sinh","Học sinh bất thường"],
                             barmode="group",
                             color_discrete_map={"Tổng học sinh":"#4CAF50","Học sinh bất thường":"#FF5252"},
                             labels={"value":"Số học sinh","Lop":"Lớp"},
                             title="Tổng học sinh & Học sinh bất thường theo lớp")
            summary_json = json.dumps(fig_col, cls=plotly.utils.PlotlyJSONEncoder)

            # Scatter & histogram từng môn
            for subj in subject_cols:
                fig_scat = px.scatter(df, x="MaHS", y=subj, color=f"Z_{subj}",
                                      color_continuous_scale="RdYlGn_r",
                                      size=df[f"Z_{subj}"].abs(),
                                      size_max=20,
                                      hover_data={"MaHS":True, subj:True, f"Z_{subj}":True})
                scatter_plots.append((subj, json.dumps(fig_scat, cls=plotly.utils.PlotlyJSONEncoder)))

                fig_hist = px.histogram(df, x=subj, nbins=20, color=f"Highlight_{subj}",
                                        color_discrete_map={True:"#FF0000", False:"#4CAF50"},
                                        labels={"count":"Số học sinh"})
                hist_plots.append((subj, json.dumps(fig_hist, cls=plotly.utils.PlotlyJSONEncoder)))

            # Lưu CSV anomalies
            filename = "Students_Anomalies.csv"
            anomalies.to_csv(filename, index=False, encoding="utf-8")

            tables = [df.to_html(classes="table table-striped", index=False)]
            anomalies_table = [anomalies.to_html(classes="table table-bordered", index=False)]

            return render_template("index.html",
                                   tables=tables,
                                   anomalies=anomalies_table,
                                   summary_json=summary_json,
                                   scatter_plots=scatter_plots,
                                   hist_plots=hist_plots,
                                   filename=filename)

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
