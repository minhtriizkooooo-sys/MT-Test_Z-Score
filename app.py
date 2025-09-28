from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Tạo folder upload nếu chưa tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route("/")
def intro():
    return render_template("intro.html")

@app.route("/index", methods=['GET','POST'])
def index():
    tables = anomalies = scatter_plots = hist_plots = summary_json = None
    error = None
    filename = None

    if request.method == 'POST':
        try:
            file = request.files['file']
            df = pd.read_csv(file)

            # Kiểm tra cột bắt buộc
            if 'MaHS' not in df.columns or 'Lop' not in df.columns:
                raise ValueError("CSV phải có cột MaHS và Lop")

            # Chọn các cột numeric để tính z-score
            df_numeric = df.select_dtypes(include=np.number)
            z_scores = np.abs((df_numeric - df_numeric.mean()) / df_numeric.std(ddof=0))
            anomalies_df = df[(z_scores > 4).any(axis=1)]

            # Lưu anomalies
            filename = "anomalies.csv"
            anomalies_df.to_csv(os.path.join("static", filename), index=False)

            tables = df.to_html(classes='table table-striped', index=False)
            anomalies = anomalies_df.to_html(classes='table table-danger', index=False)

        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        tables=tables,
        anomalies=anomalies,
        filename=filename,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
