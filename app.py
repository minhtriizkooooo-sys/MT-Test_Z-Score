from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import io
import numpy as np

app = Flask(__name__)

# Lưu DataFrame toàn bộ upload tạm thời trong memory
df_global = None

@app.route('/')
def home():
    return render_template('intro.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    global df_global
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    try:
        df = pd.read_csv(file)
        df_global = df
        # Tạo danh sách Lop và Mon
        lops = sorted(df['Lop'].dropna().unique())
        mons = sorted(df['Mon'].dropna().unique())
        return jsonify({'lops': lops, 'mons': mons})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/analyze', methods=['POST'])
def analyze():
    global df_global
    if df_global is None:
        return jsonify({'error': 'No data uploaded'}), 400
    data = request.get_json()
    lop_filter = data.get('lop')
    mon_filter = data.get('mon')
    z_threshold = float(data.get('zscore', 3.0))

    df = df_global.copy()

    if lop_filter != 'All':
        df = df[df['Lop'] == lop_filter]
    if mon_filter != 'All':
        df = df[df['Mon'] == mon_filter]

    # Tính z-score
    df['zscore'] = np.abs((df['Diem'] - df['Diem'].mean()) / df['Diem'].std(ddof=0))
    df_anomaly = df[df['zscore'] > z_threshold]

    # Chuẩn bị dữ liệu chart theo lop
    chart_data = df.groupby('Lop')['Diem'].mean().reset_index().to_dict(orient='records')
    scatter_data = df.to_dict(orient='records')
    hist_data = df['Diem'].tolist()

    # Chuẩn bị dữ liệu anomalies để xuất file
    anomalies_csv = df_anomaly.to_csv(index=False)
    anomalies_bytes = io.BytesIO()
    anomalies_bytes.write(anomalies_csv.encode('utf-8'))
    anomalies_bytes.seek(0)

    return jsonify({
        'chart_data': chart_data,
        'scatter_data': scatter_data,
        'hist_data': hist_data,
        'anomalies': df_anomaly.to_dict(orient='records')
    })

@app.route('/download')
def download():
    global df_global
    if df_global is None:
        return "No data uploaded", 400
    anomalies = df_global[df_global['zscore'] > 3.0] if 'zscore' in df_global else pd.DataFrame()
    if anomalies.empty:
        return "No anomalies found", 400
    output = io.BytesIO()
    anomalies.to_csv(output, index=False)
    output.seek(0)
    return send_file(output, download_name="anomalies.csv", as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
