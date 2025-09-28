let barChart, scatterChart, histChart;

// Upload CSV
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('fileInput');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const res = await fetch('/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if(data.error){
        alert(data.error);
        return;
    }
    // Show filters
    document.getElementById('filters').style.display = 'block';
    const lopSelect = document.getElementById('lopFilter');
    const monSelect = document.getElementById('monFilter');

    lopSelect.innerHTML = '<option>All</option>' + data.lops.map(l=>`<option>${l}</option>`).join('');
    monSelect.innerHTML = '<option>All</option>' + data.mons.map(m=>`<option>${m}</option>`).join('');
});

// Analyze button
document.getElementById('analyzeBtn').addEventListener('click', async () => {
    const lop = document.getElementById('lopFilter').value;
    const mon = document.getElementById('monFilter').value;
    const zscore = document.getElementById('zscoreFilter').value;

    const res = await fetch('/analyze', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({lop, mon, zscore})
    });
    const data = await res.json();
    if(data.error){
        alert(data.error);
        return;
    }

    // Bar chart
    if(barChart) barChart.destroy();
    const ctxBar = document.getElementById('barChart').getContext('2d');
    barChart = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: data.chart_data.map(d=>d.Lop),
            datasets: [{
                label: 'Điểm trung bình',
                data: data.chart_data.map(d=>d.Diem),
                backgroundColor: '#4caf50'
            }]
        }
    });

    // Scatter chart
    if(scatterChart) scatterChart.destroy();
    const ctxScatter = document.getElementById('scatterChart').getContext('2d');
    scatterChart = new Chart(ctxScatter, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Điểm',
                data: data.scatter_data.map(d=>({x:d.Lop, y:d.Diem})),
                backgroundColor:'#2e7d32'
            }]
        }
    });

    // Histogram
    if(histChart) histChart.destroy();
    const ctxHist = document.getElementById('histChart').getContext('2d');
    histChart = new Chart(ctxHist, {
        type: 'bar',
        data: {
            labels: data.hist_data.map((_,i)=>i+1),
            datasets:[{
                label:'Điểm',
                data:data.hist_data,
                backgroundColor:'#81c784'
            }]
        }
    });
});

// Download anomalies
document.getElementById('downloadBtn').addEventListener('click', () => {
    window.location.href = '/download';
});
