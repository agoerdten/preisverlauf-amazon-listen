const priceFormatter = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

function formatDateLabel(isoDate) {
  const [, month, day] = isoDate.split("-");
  return `${day}.${month}.`;
}

function computeStats(history) {
  const prices = history.map((entry) => entry.price);
  const average = prices.reduce((sum, price) => sum + price, 0) / prices.length;
  const min = Math.min(...prices);
  const current = prices[prices.length - 1];
  return { current, average, min };
}

function readChartColors() {
  const styles = getComputedStyle(document.documentElement);
  const read = (name) => styles.getPropertyValue(name).trim();
  return {
    series: read("--series-1"),
    gridline: read("--gridline"),
    baseline: read("--baseline"),
    muted: read("--text-muted"),
  };
}

function renderChart(canvas, history) {
  const colors = readChartColors();
  const labels = history.map((entry) => formatDateLabel(entry.date));
  const prices = history.map((entry) => entry.price);
  const lastIndex = prices.length - 1;

  return new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data: prices,
          borderColor: colors.series,
          backgroundColor: colors.series,
          borderWidth: 2,
          borderCapStyle: "round",
          borderJoinStyle: "round",
          tension: 0,
          pointRadius: (ctx) => (ctx.dataIndex === lastIndex ? 4 : 0),
          pointHoverRadius: 5,
          pointBackgroundColor: colors.series,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => priceFormatter.format(ctx.parsed.y),
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: colors.muted, maxTicksLimit: 6 },
        },
        y: {
          grid: { color: colors.gridline },
          border: { color: colors.baseline },
          ticks: {
            color: colors.muted,
            callback: (value) => priceFormatter.format(value),
          },
        },
      },
    },
  });
}

function renderProductCard(product, history) {
  const template = document.getElementById("product-card-template");
  const card = template.content.firstElementChild.cloneNode(true);
  const stats = computeStats(history);

  const titleLink = card.querySelector(".product-title");
  titleLink.textContent = product.title;
  titleLink.href = product.url;

  card.querySelector(".stat-value").textContent = priceFormatter.format(stats.current);

  const delta = card.querySelector(".stat-delta");
  const isBelowAverage = stats.current <= stats.average;
  delta.classList.add(isBelowAverage ? "is-good" : "is-critical");
  delta.textContent = isBelowAverage ? "unter Durchschnitt" : "über Durchschnitt";

  card.querySelector(".stat-min").textContent = `Tiefstpreis: ${priceFormatter.format(stats.min)}`;

  const canvas = card.querySelector(".product-chart");

  return { card, canvas, history };
}

async function loadDashboard() {
  const grid = document.getElementById("product-grid");

  let index;
  try {
    index = await fetch("./data/index.json").then((response) => response.json());
  } catch (error) {
    grid.innerHTML = `<p class="empty-state">Konnte data/index.json nicht laden.</p>`;
    return;
  }

  if (!index.products || index.products.length === 0) {
    grid.innerHTML = `<p class="empty-state">Noch keine Produkte getrackt.</p>`;
    return;
  }

  grid.innerHTML = "";
  const pending = [];

  for (const product of index.products) {
    try {
      const entry = await fetch(`./data/products/${product.productId}.json`).then((response) => response.json());
      if (!entry.history || entry.history.length === 0) continue;
      const { card, canvas, history } = renderProductCard(product, entry.history);
      grid.appendChild(card);
      pending.push(() => renderChart(canvas, history));
    } catch (error) {
      console.error(`Konnte Produkt ${product.productId} nicht laden`, error);
    }
  }

  pending.forEach((draw) => draw());
}

loadDashboard();
