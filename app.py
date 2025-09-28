# app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
import base64

app = Flask(__name__)

# Lưu dữ liệu CSV và anomalies tạm thời
data_storage = {"df": None, "anomalies": None}

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    df = pd.read_csv(file)
    # Chuẩn hóa tên cột (StudentID, Class, Subject, Score)
    df.columns = [c.strip() for c in df.columns]
    for col in ['StudentID', 'Class', 'Subject', 'Score']:
        if col not in df.columns:
            return jsonify({"error": f"Missing column: {col}"}), 400

    # Tính z-score theo Subject
    df['zscore'] = df.groupby('Subject')['Score'].transform(lambda x: (x - x.mean())/x.std(ddof=0))
    df['Anomaly'] = df['zscore'].abs() > 3  # threshold có thể thay đổi

    # Lưu dữ liệu tạm
    data_storage["df"] = df
    data_storage["anomalies"] = df[df['Anomaly']]

    # Lọc theo lớp nếu được gửi từ request
    class_filter = request.form.get('class')
    subject_filter = request.form.get('subject')
    filtered_df = df.copy()
    if class_filter:
        filtered_df = filtered_df[filtered_df['Class'] == class_filter]
    if subject_filter:
        filtered_df = filtered_df[filtered_df['Subject'] == subject_filter]

    # Biểu đồ scatter
    scatter_fig = px.scatter(filtered_df, x='StudentID', y='Score', color='Anomaly', 
                             hover_data=['Class', 'Subject', 'zscore'])
    scatter_fig.update_layout(margin=dict(l=20,r=20,t=20,b=20))
    scatter_json = scatter_fig.to_json()

    # Histogram
    hist_fig = px.histogram(filtered_df, x='Score', nbins=20, color='Anomaly')
    hist_fig.update_layout(margin=dict(l=20,r=20,t=20,b=20))
    hist_json = hist_fig.to_json()

    # Trả về dữ liệu anomalies và biểu đồ
    anomalies_list = filtered_df[filtered_df['Anomaly']].to_dict(orient='records')
    return jsonify({"anomalies": anomalies_list, "scatter": scatter_json, "hist": hist_json})

@app.route('/export')
def export_csv():
    if data_storage["anomalies"] is None:
        return "No data to export", 400

    output = BytesIO()
    data_storage["anomalies"].to_csv(output, index=False)
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True,
                     download_name="anomalies.csv")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
