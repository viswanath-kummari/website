/**
 * Fresh Cut Meat Shop - Chart.js Business Analytics Visualizations
 */

function initDashboardCharts(chartData) {
  if (!chartData) return;

  const colorCharcoal = '#202522';
  const colorOrange = '#D97745';
  const colorSage = '#81917B';
  const colorIvoryDark = '#c2baa6';

  // 1. Daily Sales & Profit Overview (Bar + Line)
  const dailyCanvas = document.getElementById('chartDailySales');
  if (dailyCanvas && chartData.daily_sales) {
    const labels = chartData.daily_sales.map(d => d.date_label);
    const revenueData = chartData.daily_sales.map(d => parseFloat(d.revenue));
    const profitData = chartData.daily_sales.map(d => parseFloat(d.profit));

    new Chart(dailyCanvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Sales Revenue (₹)',
            data: revenueData,
            backgroundColor: colorOrange,
            borderRadius: 6
          },
          {
            label: 'Gross Profit (₹)',
            data: profitData,
            backgroundColor: colorSage,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString('en-IN', {minimumFractionDigits: 2})}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => '₹' + val
            }
          }
        }
      }
    });
  }

  // 2. Category-wise Sales Distribution (Doughnut)
  const catCanvas = document.getElementById('chartCategorySales');
  if (catCanvas && chartData.category_sales) {
    const labels = chartData.category_sales.map(c => c.category);
    const revData = chartData.category_sales.map(c => parseFloat(c.revenue));

    new Chart(catCanvas, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: revData,
          backgroundColor: [colorOrange, colorCharcoal, colorSage, colorIvoryDark],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ₹${ctx.parsed.toLocaleString('en-IN', {minimumFractionDigits: 2})}`
            }
          }
        }
      }
    });
  }

  // 3. Top Selling Products (Horizontal Bar)
  const prodCanvas = document.getElementById('chartTopProducts');
  if (prodCanvas && chartData.product_sales) {
    const labels = chartData.product_sales.map(p => p.product_name);
    const data = chartData.product_sales.map(p => parseFloat(p.revenue));

    new Chart(prodCanvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue (₹)',
          data: data,
          backgroundColor: colorCharcoal,
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: { callback: (val) => '₹' + val }
          }
        }
      }
    });
  }

  // 4. Expenses Breakdown (Pie)
  const expCanvas = document.getElementById('chartExpenses');
  if (expCanvas && chartData.expense_breakdown) {
    const labels = chartData.expense_breakdown.map(e => e.category);
    const data = chartData.expense_breakdown.map(e => parseFloat(e.total_amount));

    new Chart(expCanvas, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: [
            '#D97745', '#81917B', '#202522', '#6b806d', '#b0653f', '#445147', '#a38f78'
          ],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  }
}
