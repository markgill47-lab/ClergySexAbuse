---
name: Generate Choropleth Map
description: Generate an interactive US choropleth map visualization for any clergy abuse metric. Produces a standalone HTML file.
user-invocable: true
---

# Generate US Choropleth Map

You are generating an interactive choropleth map of the United States, shaded by a clergy abuse statistic. The output is a **single standalone HTML file** that can be opened in any browser — no build step, no server needed.

## What you're building

A map of the US where each state is colored by the intensity of a statistical measure (total accused, conviction rate, per-capita rate, etc.). The map includes:
- Hover tooltips showing state name + value
- Click to select/deselect states
- Color gradient legend
- Title and description

## Step 1: Determine the metric

The user will specify what they want to visualize. If unclear, ask. Common metrics:
- Total accused clergy per state
- Accused per 100k population
- Accused per 100k Catholic population
- Conviction rate (%)
- Treatment referral rate (%)
- No-accountability rate (%)

## Step 2: Pull the data

Use the MCP tools to get the data. For state-level metrics, use `stats_by_state`. For custom metrics, you may need multiple tool calls and computation.

Example: For "conviction rate by state," call `stats_by_state` and extract `conviction_rate` per state.

## Step 3: Generate the HTML

Create a standalone HTML file using this template structure. The file must be COMPLETELY self-contained — inline all CSS, JavaScript, and data. The only external dependency is the TopoJSON CDN for US state boundaries.

**Template:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>[MAP TITLE]</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .container { max-width: 960px; margin: 0 auto; padding: 24px; }
  h1 { font-size: 1.5rem; margin-bottom: 8px; color: #ffffff; }
  .subtitle { font-size: 0.9rem; color: #999; margin-bottom: 24px; }
  .map-container { position: relative; background: #16213e; border-radius: 8px; padding: 16px; }
  svg { width: 100%; height: auto; }
  .state { stroke: rgba(255,255,255,0.15); stroke-width: 0.5px; cursor: pointer; transition: filter 0.15s; }
  .state:hover { filter: brightness(1.3); stroke: rgba(255,255,255,0.4); stroke-width: 1px; }
  .tooltip { position: absolute; background: rgba(0,0,0,0.85); color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; pointer-events: none; display: none; z-index: 10; }
  .tooltip .value { font-weight: bold; color: #42b883; }
  .legend { display: flex; align-items: center; gap: 8px; margin-top: 16px; font-size: 0.8rem; }
  .legend-bar { width: 200px; height: 12px; border-radius: 3px; }
  .source { font-size: 0.75rem; color: #666; margin-top: 16px; }
</style>
</head>
<body>
<div class="container">
  <h1>[TITLE]</h1>
  <p class="subtitle">[DESCRIPTION]</p>
  <div class="map-container">
    <svg id="map" viewBox="0 0 960 600"></svg>
    <div class="tooltip" id="tooltip"></div>
    <div class="legend">
      <span>[LOW LABEL]</span>
      <div class="legend-bar" id="legend-bar"></div>
      <span>[HIGH LABEL]</span>
    </div>
  </div>
  <p class="source">Source: Clergy Abuse Data Platform — BishopAccountability.org + Anderson Advocates. [RECORD COUNT] records.</p>
</div>
<script>
// DATA — inline the state values here
const stateData = {
  // "AL": { name: "Alabama", value: 123, label: "123 accused" },
  // ... all 50 states
  [INLINE STATE DATA HERE]
};

// FIPS to state abbr mapping
const fipsToState = {
  "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT",
  "10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL",
  "18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD",
  "25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE",
  "32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND",
  "39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD",
  "47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV",
  "55":"WI","56":"WY"
};

// Color scale
const values = Object.values(stateData).map(d => d.value).filter(v => v > 0);
const minVal = Math.min(...values);
const maxVal = Math.max(...values);

function getColor(value) {
  if (!value || value === 0) return '#2a2a3a';
  const t = (value - minVal) / (maxVal - minVal || 1);
  const r = Math.round(26 + t * (66 - 26));
  const g = Math.round(58 + t * (184 - 58));
  const b = Math.round(58 + t * (131 - 58));
  return `rgb(${r},${g},${b})`;
}

// Legend gradient
document.getElementById('legend-bar').style.background =
  'linear-gradient(to right, rgb(26,58,58), rgb(66,184,131))';

// Load TopoJSON and render
const svg = d3.select('#map');
const projection = d3.geoAlbersUsa().scale(1280).translate([480, 300]);
const path = d3.geoPath().projection(projection);
const tooltip = document.getElementById('tooltip');

d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json').then(us => {
  const states = topojson.feature(us, us.objects.states).features;

  svg.selectAll('path')
    .data(states)
    .join('path')
    .attr('class', 'state')
    .attr('d', path)
    .attr('fill', d => {
      const abbr = fipsToState[d.id.toString().padStart(2, '0')];
      const data = stateData[abbr];
      return data ? getColor(data.value) : '#2a2a3a';
    })
    .on('mousemove', (event, d) => {
      const abbr = fipsToState[d.id.toString().padStart(2, '0')];
      const data = stateData[abbr];
      if (data) {
        tooltip.style.display = 'block';
        tooltip.style.left = (event.offsetX + 12) + 'px';
        tooltip.style.top = (event.offsetY - 12) + 'px';
        tooltip.innerHTML = `${data.name}<br><span class="value">${data.label}</span>`;
      }
    })
    .on('mouseleave', () => { tooltip.style.display = 'none'; });
});
</script>
</body>
</html>
```

## Step 4: Fill in the data

Replace the placeholder sections:
- `[TITLE]` — descriptive title
- `[DESCRIPTION]` — one-line explanation of what the map shows
- `[LOW LABEL]` / `[HIGH LABEL]` — legend endpoints (e.g., "0%" / "15%")
- `[INLINE STATE DATA HERE]` — the actual data object, one entry per state
- `[RECORD COUNT]` — total records in the analysis

Format each state entry as:
```javascript
"CA": { name: "California", value: 45.6, label: "45.6 per 100k" },
```

The `value` drives the color. The `label` is what shows in the tooltip.

## Step 5: Write the file

Write the completed HTML to a file in the project. Suggested path: `data/exports/map_[metric_name].html`

Tell the user where the file is and that they can open it directly in a browser.

## Formatting numbers

- Raw counts: no decimal, with commas (1,234)
- Rates/percentages: one decimal (12.3%)
- Per-capita: one decimal (45.6 per 100k)

## Color scheme

Default: dark teal (#1a3a3a) → bright green (#42b883) on dark background (#1a1a2e).
This matches the existing VueTest dashboard aesthetic. If the user requests a different scheme, adjust the RGB values in `getColor()` and the legend gradient.

$ARGUMENTS
