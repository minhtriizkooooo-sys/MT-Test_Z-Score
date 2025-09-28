from flask import Flask, render_template, request, send_file, session, redirect, url_for
import pandas as pd
import numpy as np
from scipy import stats
import json
import plotly.express as px

app = Flask(__name__)
app.secret_key = "replace_with_a_strong_secret_key"

@app.route("/intro")
def intro():
    # Chỉ hiện 1 lần
    if session.get("intro_done"):
        return redirect(url_for("index"))
    session["intro_done"] = True
    return render_template("intro.html")

@app.route("/", methods=["GET", "POST"])
def index():
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
            try:
                df = pd.read_csv(file, encoding="utf-8")
            except:
                file.seek(0)
                df = pd.read_csv(file, encoding="latin1")

            df.columns = df.columns.str.strip().str.replace(" ", "").str.capitalize()

            if "Lop" not in df.columns:
                error = "Không tìm thấy cột 'Lop'"
            else:
                student_col = [c for c in df.columns if c.lower() in ["mahs","id","studentid"]]
                if not student_col:
                    error = "Không tìm thấy cột 'MaHS'"
                else:
                    df["MaHS"] = df[student_col[0]]
                    subject_cols = [c for c in df.columns if c not in ["MaHS","Lop"]]
                    if not subject_cols:
                        error = "Không tìm thấy cột điểm môn học"
                    else:
                        # Z-score
                        for subj in subject_cols:
                            df[f"Z_{subj}"] = stats.zscore(df[subj].fillna(0))
                            df[f"Highlight_{subj}"] = df[f"Z_{subj}"].abs() > z_threshold

                        anomalies = df[df[[f"Highlight_{s}" for s in subject_cols]].any(axis=1)]

                        # Summary
                        class_summary = df.groupby("Lop").size().reset_index(name="Tổng học sinh")
                        anomaly_count = anomalies.groupby("Lop").size().reset_index(name="Học sinh bất thường")
                        summary = pd.merge(class_summary, anomaly_count, on="Lop", how="left").fillna(0)

                        fig_col = px.bar(summary, x="Lop", y=["Tổng học sinh","Học sinh bất thường"],
                                         barmode="group",
                                         color_discrete_map={"Tổng học sinh":"#4CAF50","Học sinh bất thường":"#FF5252"},
                                         labels={"value":"Số học sinh","Lop":"Lớp"},
                                         title="Tổng học sinh & Học sinh bất thường theo lớp")
                        summary_json = json.dumps(fig_col, cls=plotly.utils.PlotlyJSONEncoder)

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

                        filename = "Students_Anomalies.csv"
                        anomalies.to_csv(filename, index=False, encoding="utf-8")

                        tables = [df.to_html(classes="table table-striped", index=False)]

    return render_template("index.html",
                           tables=tables,
                           anomalies=[anomalies.to_html(classes="table table-bordered", index=False)] if anomalies is not None else None,
                           summary_json=summary_json,
                           scatter_plots=scatter_plots,
                           hist_plots=hist_plots,
                           filename=filename,
                           error=error)

@app.route("/download/<filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
