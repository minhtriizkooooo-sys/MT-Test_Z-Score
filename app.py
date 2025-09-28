import os
from flask import Flask, render_template, request
import pandas as pd
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Tạo folder upload nếu chưa tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route("/")
def intro():
    # Hiển thị video test.mp4 trước khi vào index
    return render_template("intro.html")

@app.route("/index", methods=['GET', 'POST'])
def index():
    tables = anomalies = filename = None
    error = None

    if request.method == 'POST':
        try:
            file = request.files['file']
            df = pd.read_csv(file)

            # Kiểm tra cột bắt buộc
            if 'MaHS' not in df.columns or 'Lop' not in df.columns:
                raise ValueError("CSV phải có cột MaHS và Lop")

            # Chọn cột số và tính z-score
            df_numeric = df.select_dtypes(include=np.number)
            z_scores = np.abs((df_numeric - df_numeric.mean()) / df_numeric.std(ddof=0))
            anomalies_df = df[(z_scores > 4).any(axis=1)]

            # Lưu file anomalies
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
    # Bind vào 0.0.0.0 và port Render cung cấp
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
