/**
 * dashboard.js: draws every chart on the Insights page with Plotly.
 *
 * Data comes from two <script type="application/json"> blocks rendered by
 * Django (results-data and activity-data), so no extra requests are made.
 * Colors follow a colorblind-validated palette: blue is the primary series,
 * orange the comparison series, and heatmaps use a single-hue blue ramp.
 */
(() => {
  const results = JSON.parse(document.getElementById("results-data")?.textContent || "null");
  const activity = JSON.parse(document.getElementById("activity-data")?.textContent || "null");
  if (!results || typeof Plotly === "undefined") return;

  const C = {
    blue: "#2a78d6", orange: "#eb6834", grey: "#a8a69e",
    ink: "#0b0b0b", ink2: "#52514e", muted: "#898781", grid: "#ecebe6", axis: "#c3c2b7",
    ramp: [[0, "#eef5fd"], [0.15, "#cde2fb"], [0.35, "#86b6ef"], [0.55, "#3987e5"], [0.75, "#256abf"], [1, "#0d366b"]],
  };
  const gbp = v => "£" + Math.round(v).toLocaleString("en-GB");
  const pct = (v, d = 0) => (100 * v).toFixed(d) + "%";

  const baseLayout = {
    font: { family: "Inter, system-ui, sans-serif", size: 12, color: C.ink2 },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: 16, t: 8, b: 40 },
    xaxis: { gridcolor: C.grid, linecolor: C.axis, zeroline: false, tickfont: { color: C.muted } },
    yaxis: { gridcolor: C.grid, linecolor: C.axis, zeroline: false, tickfont: { color: C.muted } },
    hoverlabel: { bgcolor: "#fff", bordercolor: C.axis, font: { color: C.ink } },
    showlegend: false,
    legend: { orientation: "h", y: 1.12, x: 0, font: { color: C.ink2 } },
  };
  const config = { displayModeBar: false, responsive: true };

  /** Merge nested layout options onto the shared base. */
  function layout(extra = {}) {
    return {
      ...baseLayout, ...extra,
      xaxis: { ...baseLayout.xaxis, ...(extra.xaxis || {}) },
      yaxis: { ...baseLayout.yaxis, ...(extra.yaxis || {}) },
      margin: { ...baseLayout.margin, ...(extra.margin || {}) },
    };
  }
  function draw(id, traces, extra) {
    const node = document.getElementById(id);
    if (node) Plotly.newPlot(node, traces, layout(extra), config);
  }

  // ── 1. Overview ────────────────────────────────────────────────────────────
  const ov = results.overview;
  const months = ov.monthly.map(m => m.month + "-01");
  draw("chart-monthly", [{
    x: months, y: ov.monthly.map(m => m.revenue), type: "scatter", mode: "lines+markers",
    line: { color: C.blue, width: 2 }, marker: { size: 5, color: C.blue },
    customdata: ov.monthly.map(m => [m.orders, m.customers, m.partial ? " (partial month)" : ""]),
    hovertemplate: "%{x|%b %Y}%{customdata[2]}<br>Revenue £%{y:,.0f}<br>%{customdata[0]:,} orders · %{customdata[1]:,} customers<extra></extra>",
  }], { yaxis: { tickprefix: "£", tickformat: "~s" }, xaxis: { tickformat: "%b %Y" } });

  const wk = ov.weekly_pattern;
  draw("chart-weekly", [{
    z: wk.orders, x: wk.hours.map(h => `${h}:00`), y: wk.days, type: "heatmap",
    colorscale: C.ramp, xgap: 2, ygap: 2, colorbar: { thickness: 10, outlinewidth: 0, tickfont: { color: C.muted } },
    hovertemplate: "%{y} %{x}<br>%{z:,} orders<extra></extra>",
  }], { yaxis: { autorange: "reversed", gridcolor: "rgba(0,0,0,0)" }, xaxis: { gridcolor: "rgba(0,0,0,0)" }, margin: { l: 40 } });

  const countries = [...ov.countries].reverse();
  draw("chart-countries", [{
    x: countries.map(c => c.revenue), y: countries.map(c => c.country), type: "bar", orientation: "h",
    marker: { color: C.blue }, text: countries.map(c => pct(c.share, 1)), textposition: "outside", cliponaxis: false,
    customdata: countries.map(c => c.customers),
    hovertemplate: "%{y}<br>£%{x:,.0f}<br>%{customdata:,} customers<extra></extra>",
  }], { xaxis: { type: "log", tickprefix: "£", tickformat: "~s", title: { text: "Revenue (log scale)", font: { size: 11 } } },
        margin: { l: 110, r: 48 } });

  const products = [...ov.top_products].reverse();
  draw("chart-products", [{
    x: products.map(p => p.revenue), y: products.map(p => p.name), type: "bar", orientation: "h",
    marker: { color: C.blue }, customdata: products.map(p => p.customers),
    hovertemplate: "%{y}<br>£%{x:,.0f} · %{customdata:,} customers<extra></extra>",
  }], { xaxis: { tickprefix: "£", tickformat: "~s" }, margin: { l: 230 } });

  // ── 2. Customers ───────────────────────────────────────────────────────────
  const segs = results.segments.segments;
  draw("chart-segments", [
    { name: "Share of customers", x: segs.map(s => s.segment), y: segs.map(s => s.customer_share), type: "bar",
      marker: { color: C.blue }, text: segs.map(s => pct(s.customer_share)), textposition: "outside",
      hovertemplate: "%{x}<br>%{y:.1%} of customers<extra></extra>" },
    { name: "Share of revenue", x: segs.map(s => s.segment), y: segs.map(s => s.revenue_share), type: "bar",
      marker: { color: C.orange }, text: segs.map(s => pct(s.revenue_share)), textposition: "outside",
      hovertemplate: "%{x}<br>%{y:.1%} of revenue<extra></extra>" },
  ], { barmode: "group", bargap: 0.25, bargroupgap: 0.08, showlegend: true, yaxis: { tickformat: ".0%", range: [0, 0.9] } });

  // Month 0 is 100% by definition, so the grid starts at month 1. Both axes are
  // categories, otherwise Plotly reads "2010-01" as a date and "1" as a number.
  const co = results.cohorts;
  const later = co.offsets.map((k, i) => [k, i]).filter(([k]) => k > 0);
  const cohortLabel = c => new Date(c + "-01T00:00").toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  draw("chart-cohorts", [{
    z: co.retention.map(row => later.map(([, i]) => row[i])),
    x: later.map(([k]) => `Month ${k}`), y: co.cohorts.map(cohortLabel), type: "heatmap",
    colorscale: C.ramp, zmin: 0, zmax: 0.5, xgap: 2, ygap: 2,
    text: co.retention.map(row => later.map(([, i]) => (row[i] === null ? "" : pct(row[i])))),
    texttemplate: "%{text}", textfont: { size: 10 },
    customdata: co.cohorts.map((_, r) => later.map(() => co.sizes[r])),
    colorbar: { thickness: 10, outlinewidth: 0, tickformat: ".0%", tickfont: { color: C.muted } },
    hovertemplate: "Customers who first ordered in %{y} (%{customdata:,})<br>%{x}: %{z:.1%} ordered again<extra></extra>",
  }], { yaxis: { type: "category", autorange: "reversed", gridcolor: "rgba(0,0,0,0)", dtick: 1 },
        xaxis: { type: "category", gridcolor: "rgba(0,0,0,0)", side: "top" }, margin: { l: 70, t: 30 } });

  // ── 3. Prediction ──────────────────────────────────────────────────────────
  const pr = results.prediction;
  const models = [...pr.comparison].reverse();
  draw("chart-models", [{
    x: models.map(m => m.roc_auc), y: models.map(m => m.model), type: "bar", orientation: "h",
    marker: { color: models.map(m => (m.model.includes("baseline") ? C.grey : C.blue)) },
    error_x: { type: "data", symmetric: false, color: C.ink2, thickness: 1.5, width: 5,
               array: models.map(m => m.auc_ci_high - m.roc_auc), arrayminus: models.map(m => m.roc_auc - m.auc_ci_low) },
    customdata: models.map(m => [m.auc_ci_low, m.auc_ci_high, m.pr_auc]),
    hovertemplate: "%{y}<br>ROC AUC %{x:.3f} (95% CI %{customdata[0]:.3f}–%{customdata[1]:.3f})<br>PR AUC %{customdata[2]:.3f}<extra></extra>",
  }], { xaxis: { range: [0.5, 0.85], title: { text: "ROC AUC (0.5 = random)", font: { size: 11 } } }, margin: { l: 170 } });

  draw("chart-roc", [
    { x: [0, 1], y: [0, 1], mode: "lines", line: { color: C.axis, width: 1 }, hoverinfo: "skip", name: "Random" },
    { name: "Recency rule (baseline)", x: pr.roc.baseline_fpr, y: pr.roc.baseline_tpr, mode: "lines",
      line: { color: C.orange, width: 2 }, hovertemplate: "False positive rate %{x:.2f}<br>True positive rate %{y:.2f}<extra>Baseline</extra>" },
    { name: pr.best_model, x: pr.roc.fpr, y: pr.roc.tpr, mode: "lines", line: { color: C.blue, width: 2 },
      hovertemplate: "False positive rate %{x:.2f}<br>True positive rate %{y:.2f}<extra>" + pr.best_model + "</extra>" },
  ], { showlegend: true, xaxis: { title: { text: "False positive rate", font: { size: 11 } }, range: [0, 1] },
       yaxis: { title: { text: "True positive rate", font: { size: 11 } }, range: [0, 1] } });

  draw("chart-lift", [{
    x: pr.lift.map(d => `D${d.decile}`), y: pr.lift.map(d => d.rate), type: "bar", marker: { color: C.blue },
    text: pr.lift.map(d => pct(d.rate)), textposition: "outside", cliponaxis: false,
    hovertemplate: "Decile %{x}<br>%{y:.1%} bought again<extra></extra>",
  }], { yaxis: { tickformat: ".0%", range: [0, 1.08] },
        shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: pr.base_rate_test, y1: pr.base_rate_test, line: { color: C.ink2, width: 1.5 } }],
        annotations: [{ xref: "paper", x: 1, y: pr.base_rate_test, yanchor: "bottom", xanchor: "right", showarrow: false,
                        text: `Overall: ${pct(pr.base_rate_test)}`, font: { size: 11, color: C.ink2 } }] });

  draw("chart-calibration", [
    { x: [0, 1], y: [0, 1], mode: "lines", line: { color: C.axis, width: 1 }, hoverinfo: "skip" },
    { x: pr.calibration.map(c => c.predicted), y: pr.calibration.map(c => c.observed), mode: "lines+markers",
      line: { color: C.blue, width: 2 }, marker: { size: 8, color: C.blue, line: { color: "#fff", width: 2 } },
      customdata: pr.calibration.map(c => c.n),
      hovertemplate: "Predicted %{x:.0%}<br>Actual %{y:.0%}<br>%{customdata} customers<extra></extra>" },
  ], { xaxis: { tickformat: ".0%", range: [0, 1], title: { text: "Predicted probability", font: { size: 11 } } },
       yaxis: { tickformat: ".0%", range: [0, 1], title: { text: "Actual repurchase rate", font: { size: 11 } } } });

  const imp = pr.importance.filter(f => f.drop_in_auc > 0.0005).reverse();
  draw("chart-importance", [{
    x: imp.map(f => f.drop_in_auc), y: imp.map(f => f.feature), type: "bar", orientation: "h", marker: { color: C.blue },
    hovertemplate: "%{y}<br>AUC drops by %{x:.4f} when shuffled<extra></extra>",
  }], { xaxis: { title: { text: "Drop in ROC AUC", font: { size: 11 } } }, margin: { l: 200 } });

  // ── 4. Baskets: out-of-time test of the recommendations ─────────────────────
  const ev = results.baskets.evaluation;
  if (ev) {
    const ks = ev.by_k.map(r => `Top ${r.k}`);
    const series = (key, name, color) => ({
      name, x: ks, y: ev.by_k.map(r => r[key]), type: "bar", marker: { color },
      error_y: { type: "data", symmetric: false, color: C.ink2, thickness: 1.5, width: 5,
                 array: ev.by_k.map(r => r[key + "_ci"][1] - r[key]), arrayminus: ev.by_k.map(r => r[key] - r[key + "_ci"][0]) },
      text: ev.by_k.map(r => pct(r[key])), textposition: "inside", insidetextanchor: "middle",
      textfont: { color: "#fff", size: 13 },
      hovertemplate: `${name}<br>%{x}: %{y:.1%} hit rate<extra></extra>`,
    });
    draw("chart-rec-eval", [series("popular", "Best-sellers", C.grey), series("rules", "Basket rules", C.blue)],
         { barmode: "group", showlegend: true, yaxis: { tickformat: ".0%", range: [0, 0.7] } });
  }

  // ── 5. Method ──────────────────────────────────────────────────────────────
  const f = results.funnel;
  const steps = [["Raw rows", f.raw_rows], ["Duplicates removed", f.after_removing_duplicates],
                 ["Cancellations set aside", f.after_setting_aside_cancellations],
                 ["Reversed sales removed", f.after_removing_reversed_sales],
                 ["Products only", f.after_keeping_products_only], ["Positive qty & price", f.clean_rows],
                 ["…with a customer ID", f.rows_with_customer_id]].reverse();
  draw("chart-funnel", [{
    x: steps.map(s => s[1]), y: steps.map(s => s[0]), type: "bar", orientation: "h", marker: { color: C.blue },
    text: steps.map(s => s[1].toLocaleString("en-GB")), textposition: "outside", cliponaxis: false,
    hovertemplate: "%{y}<br>%{x:,} rows<extra></extra>",
  }], { xaxis: { range: [0, f.raw_rows * 1.18], tickformat: "~s" }, margin: { l: 170, r: 30 } });

  // ── 6. This store (live) ───────────────────────────────────────────────────
  if (activity && activity.by_month.length) {
    draw("chart-store-months", [{
      x: activity.by_month.map(m => m.month + "-01"), y: activity.by_month.map(m => m.orders), type: "bar",
      marker: { color: C.blue }, customdata: activity.by_month.map(m => m.revenue),
      hovertemplate: "%{x|%b %Y}<br>%{y} orders · £%{customdata:.2f}<extra></extra>",
    }], { xaxis: { tickformat: "%b %Y", type: "date" }, yaxis: { dtick: 1 } });
    const sp = [...activity.by_product].reverse();
    draw("chart-store-products", [{
      x: sp.map(p => p.revenue), y: sp.map(p => p.name), type: "bar", orientation: "h", marker: { color: C.blue },
      customdata: sp.map(p => p.units), hovertemplate: "%{y}<br>£%{x:.2f} · %{customdata} units<extra></extra>",
    }], { xaxis: { tickprefix: "£" }, margin: { l: 220 } });
  }
})();
