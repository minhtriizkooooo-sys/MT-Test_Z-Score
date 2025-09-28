from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from scipy import stats
import io
import plotly.express as px
import plotly.io as pio

app = Flask(__name__)

# Lưu anomalies tạm thời để export
temp_anomalies = pd.DataFrame()

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    global temp_anomalies

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    df = pd.read_csv(file)

    # Kiểm tra cột cần thiết
    if 'MaHS' not in df.columns or 'Lop' not in df.columns:
        return jsonify({'error': 'CSV thiếu cột MaHS hoặc Lop'}), 400

    # Chọn cột điểm số
    score_cols = [col for col in df.columns if col not in ['MaHS', 'Lop']]
    if len(score_cols) == 0:
        return jsonify({'error': 'CSV không có cột điểm số'}), 400

    # Tính z-score
    z_scores = np.abs(stats.zscore(df[score_cols], nan_policy='omit'))
    anomalies_mask = (z_scores > 3)  # z > 3 là bất thường
    anomalies = df.loc[anomalies_mask.any(axis=1), ['MaHS', 'Lop'] + score_cols]

    temp_anomalies = anomalies.copy()

    # Filter theo lớp và môn (frontend sẽ request lọc sau)
    anomalies_json = anomalies.to_dict(orient='records')

    # Biểu đồ Plotly
    bar_fig = px.bar(anomalies, x='MaHS', y=score_cols,
                     title='Điểm bất thường theo học sinh', barmode='group')
    scatter_fig = px.scatter(df, x=score_cols[0], y=score_cols[1] if len(score_cols) >1 else score_cols[0],
                             color='Lop', title='Scatter plot theo lớp')
    hist_fig = px.histogram(df, x=score_cols[0], color='Lop', barmode='overlay', title='Histogram')

    # Convert plotly figs -> HTML div
    bar_html = pio.to_html(bar_fig, include_plotlyjs=False, full_html=False)
    scatter_html = pio.to_html(scatter_fig, include_plotlyjs=False, full_html=False)
    hist_html = pio.to_html(hist_fig, include_plotlyjs=False, full_html=False)

    return jsonify({
        'anomalies': anomalies_json,
        'bar_chart': bar_html,
        'scatter_chart': scatter_html,
        'hist_chart': hist_html
    })

@app.route('/export')
def export():
    global temp_anomalies
    if temp_anomalies.empty:
        return "No anomalies to export", 400

    output = io.StringIO()
    temp_anomalies.to_csv(output, index=False)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), 
                     mimetype='text/csv',
                     download_name='anomalies.csv',
                     as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
