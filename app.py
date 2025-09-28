from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from scipy import stats
import io

app = Flask(__name__)

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Lấy file CSV từ request
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Lấy filter params
    selected_class = request.form.get('class', None)
    selected_subject = request.form.get('subject', None)
    z_thresh = float(request.form.get('zscore', 3.0))

    # Đọc CSV
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()

    # Lọc theo class và subject nếu có
    if selected_class:
        df = df[df['Lop'] == selected_class]
    if selected_subject:
        df = df[['StudentID', 'Lop', selected_subject]]

    # Tính điểm trung bình nếu nhiều môn
    subjects = [col for col in df.columns if col not in ['StudentID', 'Lop']]
    df['Average'] = df[subjects].mean(axis=1)

    # Tính z-score
    df['zscore'] = np.abs(stats.zscore(df['Average'], nan_policy='omit'))

    # HS bất thường
    anomalies = df[df['zscore'] > z_thresh]

    # Chuẩn bị dữ liệu trả về cho JS
    result = {
        'columns': list(anomalies.columns),
        'data': anomalies.to_dict(orient='records')
    }
    return jsonify(result)

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='anomalies.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
