# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
import numpy as np
from scipy.stats import zscore
import io
import plotly.express as px
import plotly.io as pio
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ===== Route intro video =====
@app.route('/')
def intro():
    return render_template('intro.html')

# ===== Route index =====
@app.route('/index')
def index():
    return render_template('index.html')

# ===== Route upload file CSV =====
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "Không có file được gửi", 400
    file = request.files['file']
    if file.filename == '':
        return "Chưa chọn file", 400
    if file:
        # Lưu file tạm thời
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Phân tích học sinh bất thường
        anomalies, bar_chart_html, scatter_html, hist_html = analyze_file(file_path)

        # Lưu anomalies CSV
        anomalies_csv_path = os.path.join(UPLOAD_FOLDER, 'anomalies.csv')
        anomalies.to_csv(anomalies_csv_path, index=False)

        return render_template('result.html',
                               anomalies=anomalies.to_dict(orient='records'),
                               bar_chart=bar_chart_html,
                               scatter_chart=scatter_html,
                               hist_chart=hist_html,
                               csv_file='anomalies.csv')

# ===== Route download anomalies CSV =====
@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename),
                     as_attachment=True)

# ===== Function analyze CSV =====
def analyze_file(file_path):
    df = pd.read_csv(file_path)
    
    # Chuẩn hóa cột
    df.columns = df.columns.str.strip()
    
    # Lọc cột điểm số (cột có 'Diem' hoặc 'diem')
    score_cols = [col for col in df.columns if 'Diem' in col or 'diem' in col]
    
    if not score_cols:
        raise ValueError("File CSV không có cột điểm hợp lệ")

    # Chuyển các cột điểm về numeric
    df[score_cols] = df[score_cols].apply(pd.to_numeric, errors='coerce')

    # Tính z-score cho mỗi cột điểm
    df_z = df.copy()
    df_z['max_z'] = df_z[score_cols].apply(lambda x: np.max(np.abs(zscore(x, nan_policy='omit'))), axis=1)

    # Lọc học sinh bất thường: max z > 4
    anomalies = df_z[df_z['max_z'] > 4]

    # ===== Vẽ biểu đồ =====
    # 1. Biểu đồ cột số học sinh bất thường theo lớp
    if 'Lop' in df.columns:
        bar_df = anomalies.groupby('Lop').size().reset_index(name='SoHocSinhBatThuong')
        bar_fig = px.bar(bar_df, x='Lop', y='SoHocSinhBatThuong',
                         title='Số học sinh bất thường theo lớp',
                         color='SoHocSinhBatThuong', color_continuous_scale='Greens')
        bar_chart_html = pio.to_html(bar_fig, full_html=False)
    else:
        bar_chart_html = "<p>Không có cột 'Lop' trong file CSV</p>"

    # 2. Scatter plot điểm vs z-score (lấy điểm đầu tiên)
    first_score = score_cols[0]
    scatter_fig = px.scatter(df_z, x=first_score, y='max_z', color='Lop' if 'Lop' in df.columns else None,
                             title=f'Scatter {first_score} vs z-score')
    scatter_html = pio.to_html(scatter_fig, full_html=False)

    # 3. Histogram điểm
    hist_fig = px.histogram(df_z, x=first_score, nbins=20, color='Lop' if 'Lop' in df.columns else None,
                            title=f'Phân bố {first_score}')
    hist_html = pio.to_html(hist_fig, full_html=False)

    return anomalies, bar_chart_html, scatter_html, hist_html

if __name__ == '__main__':
    # Render yêu cầu bind port 0.0.0.0 cho hosting như Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
