// Scatter Plot: Price vs Score (Cost-Performance Analysis)

let currentChartData = [];
let activeMetric = "score_tone";

const metricLabels = {
  score_tone: "Tone (Olive Preference Score)",
  score_tone_sub: "Tone w/SUB (サブウーファー追加)",
  score_tone_eq: "Tone w/EQ (イコライザー適用)",
  score_tone_sub_eq: "Tone w/Both (SUB + EQ)"
};

function initScatterPlot(speakers) {
  currentChartData = speakers;
  renderScatterPlot();
}

function renderScatterPlot() {
  const chartEl = document.getElementById("scatterPlot");
  if (!chartEl || !window.Plotly) return;

  const validItems = currentChartData.filter(s => {
    const price = s.effective_price_jpy || s.price_jpy;
    const score = s[activeMetric];
    return price && price > 0 && score !== null && !isNaN(score);
  });

  if (validItems.length === 0) {
    Plotly.purge(chartEl);
    return;
  }

  // Separate by availability
  const domesticItems = validItems.filter(s => s.availability === 'domestic_in_stock' || s.availability === 'domestic_backorder');
  const importItems = validItems.filter(s => s.availability === 'import_only');
  const otherItems = validItems.filter(s => s.availability !== 'domestic_in_stock' && s.availability !== 'domestic_backorder' && s.availability !== 'import_only');

  function makeTrace(items, name, color, symbol = 'circle') {
    return {
      x: items.map(s => s.effective_price_jpy || s.price_jpy),
      y: items.map(s => s[activeMetric]),
      text: items.map(s => `<b>${s.brand} ${s.model}</b><br>価格: ¥${(s.effective_price_jpy || s.price_jpy).toLocaleString()}<br>${metricLabels[activeMetric]}: ${s[activeMetric]}<br>残差コスパ: ${s.cp_tone !== null ? s.cp_tone : '--'}`),
      hoverinfo: 'text',
      mode: 'markers',
      type: 'scatter',
      name: name,
      customdata: items.map(s => s.id),
      marker: {
        size: 9,
        color: color,
        symbol: symbol,
        opacity: 0.85,
        line: { color: '#ffffff', width: 1 }
      }
    };
  }

  const traces = [
    makeTrace(domesticItems, '国内正規品', '#10b981'),
    makeTrace(importItems, '並行輸入 / 海外のみ', '#3b82f6'),
    makeTrace(otherItems, 'ディスコン / その他', '#94a3b8', 'triangle-up')
  ];

  // Compute Regression Line for Log10(Price)
  const logPrices = validItems.map(s => Math.log10(s.effective_price_jpy || s.price_jpy));
  const scores = validItems.map(s => s[activeMetric]);

  const n = logPrices.length;
  let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
  for (let i = 0; i < n; i++) {
    sumX += logPrices[i];
    sumY += scores[i];
    sumXY += logPrices[i] * scores[i];
    sumXX += logPrices[i] * logPrices[i];
  }
  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  const minP = Math.min(...validItems.map(s => s.effective_price_jpy || s.price_jpy));
  const maxP = Math.max(...validItems.map(s => s.effective_price_jpy || s.price_jpy));

  const regX = [minP, maxP];
  const regY = [
    slope * Math.log10(minP) + intercept,
    slope * Math.log10(maxP) + intercept
  ];

  traces.push({
    x: regX,
    y: regY,
    mode: 'lines',
    type: 'scatter',
    name: '平均期待値ライン (回帰直線)',
    line: {
      color: '#f59e0b',
      dash: 'dash',
      width: 2.5
    },
    hoverinfo: 'none'
  });

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: isDark ? '#1e293b' : '#f8fafc',
    margin: { t: 20, r: 30, b: 50, l: 50 },
    xaxis: {
      type: 'log',
      title: { text: '実勢価格 (円・対数軸)', font: { color: isDark ? '#94a3b8' : '#475569', size: 12 } },
      gridcolor: isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(203, 213, 225, 0.6)',
      tickfont: { color: isDark ? '#94a3b8' : '#475569' },
      tickformat: ',d'
    },
    yaxis: {
      title: { text: metricLabels[activeMetric], font: { color: isDark ? '#94a3b8' : '#475569', size: 12 } },
      gridcolor: isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(203, 213, 225, 0.6)',
      tickfont: { color: isDark ? '#94a3b8' : '#475569' }
    },
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.15,
      font: { color: isDark ? '#cbd5e1' : '#334155', size: 11 }
    },
    hovermode: 'closest'
  };

  const config = {
    responsive: true,
    displayModeBar: false
  };

  Plotly.react(chartEl, traces, layout, config);

  chartEl.on('plotly_click', (data) => {
    if (data.points && data.points.length > 0) {
      const speakerId = data.points[0].customdata;
      if (speakerId) {
        const found = currentChartData.find(s => s.id === speakerId);
        if (found && window.openEditModal) {
          window.openEditModal(found);
        }
      }
    }
  });
}

document.getElementById("chartMetricSelect")?.addEventListener("change", (e) => {
  activeMetric = e.target.value;
  renderScatterPlot();
});

window.initScatterPlot = initScatterPlot;
window.renderScatterPlot = renderScatterPlot;
