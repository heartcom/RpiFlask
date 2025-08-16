let historyChart = null;

async function fetchHistory(n=200) {
  try {
    const res = await fetch(`/api/dht-history?n=${n}`);
    const json = await res.json();
    if (!json.ok) return {labels: [], temps: [], humis: []};

    // 오래된 -> 최신 순으로 정렬되어 온다고 가정
    const labels = json.rows.map(d => d.ts);
    const temps  = json.rows.map(d => d.temp_c);
    const humis  = json.rows.map(d => d.humidity);
    return {labels, temps, humis};
  } catch (e) {
    console.error(e);
    return {labels: [], temps: [], humis: []};
  }
}

async function renderChart() {
  const {labels, temps, humis} = await fetchHistory(200);
  const ctx = document.getElementById('history-chart');

  if (historyChart) historyChart.destroy();
  historyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: '온도(°C)', data: temps, borderColor: 'red',  fill: false, tension: 0.2 },
        { label: '습도(%)',  data: humis, borderColor: 'blue', fill: false, tension: 0.2 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { autoSkip: true, maxRotation: 0 } },
        y: { beginAtZero: false }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', renderChart);
