document.addEventListener("DOMContentLoaded", function () {
  const uploadForm = document.getElementById("uploadForm");
  const fileInput = document.getElementById("fileInput");
  const lopSelect = document.getElementById("lopSelect");
  const monSelect = document.getElementById("monSelect");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const zInput = document.getElementById("zscore");
  const resultDiv = document.getElementById("result");

  // Upload file
  uploadForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      alert("Hãy chọn file CSV!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    fetch("/upload", {
      method: "POST",
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          alert("Lỗi upload: " + data.error);
          console.error("Upload error:", data.error);
          return;
        }
        // Render danh sách Lop và Mon
        lopSelect.innerHTML = `<option value="All">All</option>`;
        data.lops.forEach(lop => {
          lopSelect.innerHTML += `<option value="${lop}">${lop}</option>`;
        });

        monSelect.innerHTML = `<option value="All">All</option>`;
        data.mons.forEach(mon => {
          monSelect.innerHTML += `<option value="${mon}">${mon}</option>`;
        });

        alert("Upload thành công, chọn bộ lọc rồi bấm Phân tích!");
      })
      .catch(err => {
        console.error("Fetch error:", err);
        alert("Không kết nối được server!");
      });
  });

  // Phân tích
  analyzeBtn.addEventListener("click", function () {
    const lop = lopSelect.value;
    const mon = monSelect.value;
    const zscore = zInput.value || 3.0;

    fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lop, mon, zscore })
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          alert("Lỗi phân tích: " + data.error);
          console.error("Analyze error:", data.error);
          return;
        }
        console.log("Phân tích thành công:", data);
        resultDiv.innerHTML = `
          <h3>Kết quả</h3>
          <p>Số anomalies: ${data.anomalies.length}</p>
          <pre>${JSON.stringify(data.anomalies, null, 2)}</pre>
        `;
        // TODO: gọi hàm vẽ chart tại đây
      })
      .catch(err => {
        console.error("Fetch error:", err);
        alert("Không kết nối được server!");
      });
  });
});
