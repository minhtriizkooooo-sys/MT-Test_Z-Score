from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
import pandas as pd
import numpy as np
import io
import os

app = Flask(__name__)
app.secret_key = "replace_with_a_strong_secret_key"

# Global storage (simple, in-memory)
DATAFRAME = None
ANOMALIES_DF = None
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------- Intro (fullscreen) ----------
@app.route("/", methods=["GET"])
def intro():
    # Root shows intro video fullscreen; intro.html should redirect to /index after video ends
    return render_template("intro.html")


# ---------- Index (main UI) ----------
@app.route("/index", methods=["GET"])
def index():
    return render_template("index.html")


# ---------- Upload endpoint (used by script.js) ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    """
    POST: accept multipart/form-data with 'file'
    Returns JSON with list of classes (lops) and subjects (mons).
    GET: returns a simple JSON message (so visiting /upload in browser won't give Method Not Allowed).
    """
    global DATAFRAME, ANOMALIES_DF

    if request.method == "GET":
        return jsonify({"message": "Send a POST with form-data 'file' to upload CSV."})

    # POST
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded (field 'file' missing)."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    try:
        # Try utf-8 then fallback to latin1
        try:
            df = pd.read_csv(file, encoding="utf-8")
        except Exception:
            file.seek(0)
            df = pd.read_csv(file, encoding="latin1")
    except Exception as e:
        return jsonify({"error": f"Cannot read CSV: {e}"}), 400

    # Normalize column names
    df.columns = df.columns.str.strip()
    # Try to detect common column names:
    # Ensure 'Lop' column exists (class). Allow variants 'lop','class' etc.
    colmap = {c.lower(): c for c in df.columns}
    # map 'lop' variants to 'Lop'
    lop_col = None
    for candidate in ("lop", "class"):
        if candidate in colmap:
            lop_col = colmap[candidate]
            break
    if lop_col is None:
        return jsonify({"error": "Không tìm thấy cột 'Lop' (lớp) trong CSV."}), 400
    # rename to 'Lop'
    if lop_col != "Lop":
        df = df.rename(columns={lop_col: "Lop"})

    # detect student id column -> map to 'MaHS'
    student_col = None
    for c in df.columns:
        low = c.lower()
        if "mahs" in low or low == "id" or "student" in low:
            student_col = c
            break
    if student_col is None:
        # if none found, we still allow if there's an index column, but prefer to error
        return jsonify({"error": "Không tìm thấy cột 'MaHS' / id học sinh trong CSV."}), 400
    if student_col != "MaHS":
        df = df.rename(columns={student_col: "MaHS"})

    # Identify candidate subject/score columns: any column except 'MaHS' and 'Lop'
    candidate_subjects = [c for c in df.columns if c not in ("MaHS", "Lop")]
    if not candidate_subjects:
        return jsonify({"error": "Không tìm thấy cột điểm môn học trong CSV."}), 400

    # Try to coerce those columns to numeric (safe)
    for c in candidate_subjects:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Remove columns that are completely NaN after coercion
    numeric_subjects = [c for c in candidate_subjects if not df[c].isna().all()]
    if not numeric_subjects:
        return jsonify({"error": "Các cột môn học không chứa dữ liệu số hợp lệ."}), 400

    # Keep only relevant columns: MaHS, Lop, numeric_subjects
    cols_keep = ["MaHS", "Lop"] + numeric_subjects
    df = df[cols_keep].copy()

    # Save dataframe into memory
    DATAFRAME = df
    ANOMALIES_DF = None

    # Build lists to return to frontend
    lops = sorted(df["Lop"].dropna().astype(str).unique().tolist())
    mons = sorted(numeric_subjects)

    return jsonify({"lops": lops, "mons": mons})


# ---------- Analyze endpoint (used by script.js) ----------
@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """
    POST (JSON): { lop: 'All' or specific, mon: 'All' or specific subject, zscore: float }
    Returns JSON with chart_data, scatter_data, hist_data, anomalies.
    GET: returns instructions (prevents Method Not Allowed if someone opens the route)
    """
    global DATAFRAME, ANOMALIES_DF

    if request.method == "GET":
        return jsonify({"message": "POST JSON {lop, mon, zscore} to analyze."})

    if DATAFRAME is None:
        return jsonify({"error": "Chưa upload file CSV. Gửi file tới /upload trước."}), 400

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Yêu cầu phải là JSON với fields: lop, mon, zscore"}), 400

    lop = payload.get("lop", "All")
    mon = payload.get("mon", "All")
    try:
        z_threshold = float(payload.get("zscore", 3.0))
    except Exception:
        z_threshold = 3.0

    df = DATAFRAME.copy()

    # Filter class
    if lop and lop != "All":
        df = df[df["Lop"].astype(str) == str(lop)]

    # Subjects to analyze
    subjects = [c for c in df.columns if c not in ("MaHS", "Lop")]
    if mon and mon != "All":
        if mon in subjects:
            subjects = [mon]
        else:
            return jsonify({"error": f"Môn '{mon}' không tồn tại trong dữ liệu."}), 400

    # Calculate z-scores per subject and highlight
    z_abs = pd.DataFrame(index=df.index)
    for s in subjects:
        col = df[s].astype(float)
        # if all NaN or zero variance, produce zeros
        if col.dropna().shape[0] <= 1 or np.nanstd(col) == 0:
            z = pd.Series(0.0, index=col.index)
        else:
            z = (col - col.mean()) / col.std(ddof=0)
        z_abs[f"Z_{s}"] = np.abs(z)

    # Build anomalies mask
    anomaly_mask = (z_abs > z_threshold).any(axis=1)
    anomalies = df[anomaly_mask].copy()
    # Attach z values for returned anomalies (for clarity)
    for s in subjects:
        anomalies[f"Z_{s}"] = z_abs.loc[anomalies.index, f"Z_{s}"].values

    # Save anomalies for download
    ANOMALIES_DF = anomalies.copy()
    anomalies_csv_path = os.path.join(UPLOAD_DIR, "anomalies.csv")
    ANOMALIES_DF.to_csv(anomalies_csv_path, index=False, encoding="utf-8")

    # Chart data: total students and anomaly count per class (from original df)
    class_total = df.groupby("Lop").size().reset_index(name="Total")
    class_anom = anomalies.groupby("Lop").size().reset_index(name="Anomalies")
    summary = pd.merge(class_total, class_anom, on="Lop", how="left").fillna(0).astype({"Total": int, "Anomalies": int})
    chart_data = summary.to_dict(orient="records")  # list of {Lop, Total, Anomalies}

    # Scatter/hist data per subject
    scatter = {}
    hist = {}
    for s in subjects:
        scatter[s] = df[["MaHS", "Lop", s]].dropna().to_dict(orient="records")
        hist[s] = df[s].dropna().tolist()

    # Response
    resp = {
        "chart_data": chart_data,
        "scatter": scatter,
        "hist": hist,
        "anomalies": anomalies.to_dict(orient="records"),
        "anomalies_csv": os.path.basename(anomalies_csv_path)
    }
    return jsonify(resp)


# ---------- Download anomalies ----------
@app.route("/download", methods=["GET"])
def download():
    global ANOMALIES_DF
    if ANOMALIES_DF is None or ANOMALIES_DF.empty:
        return "Không có dữ liệu bất thường để tải", 400
    path = os.path.join(UPLOAD_DIR, "anomalies.csv")
    if not os.path.exists(path):
        # fallback: write and send
        ANOMALIES_DF.to_csv(path, index=False, encoding="utf-8")
    return send_file(path, as_attachment=True)


# ---------- Helpful route (optional) ----------
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "has_dataframe": DATAFRAME is not None,
        "num_rows": int(DATAFRAME.shape[0]) if DATAFRAME is not None else 0,
        "has_anomalies": ANOMALIES_DF is not None and not ANOMALIES_DF.empty
    })


if __name__ == "__main__":
    # Bind to 0.0.0.0 so hosting providers detect the port; use env PORT if present.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
