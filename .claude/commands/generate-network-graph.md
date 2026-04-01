---
name: Generate Network Graph
description: Create an interactive network visualization showing connections between dioceses, facilities, and individuals.
user-invocable: true
---

# Generate Network Graph

You are creating an interactive force-directed network graph as a standalone HTML file. The graph shows connections between entities — dioceses connected by shared clergy transfers, facilities connected to the dioceses that sent clergy to them, or clergy connected by shared institutions.

## Process

### Step 1: Determine the network type
Parse the user's request:
- **Transfer network**: Dioceses as nodes, transfers as edges. Use `transfer_network`.
- **Facility network**: A facility at center, diocese nodes around it. Use `facility_clergy`.
- **Diocese network**: One diocese at center, connected facilities and transfer partners. Use `search_clergy`, `facility_cross_state`, `transfer_network`.

### Step 2: Gather the data
Pull all relevant connections. For each edge, note the weight (number of clergy involved).

### Step 3: Generate the HTML

Create a standalone HTML file using D3.js force simulation:

```html
<!DOCTYPE html>
<html>
<head>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body { background: #1a1a2e; color: #e0e0e0; font-family: Arial, sans-serif; margin: 0; overflow: hidden; }
  .header { padding: 16px 24px; }
  h1 { color: #fff; margin: 0; font-size: 1.3rem; } .subtitle { color: #999; font-size: 0.85rem; }
  svg { width: 100vw; height: calc(100vh - 80px); }
  .link { stroke: #42b883; stroke-opacity: 0.4; }
  .node circle { stroke: #fff; stroke-width: 1.5px; cursor: pointer; }
  .node text { fill: #e0e0e0; font-size: 10px; pointer-events: none; }
  .tooltip { position: absolute; background: rgba(0,0,0,0.85); color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 0.8rem; pointer-events: none; display: none; }
</style>
</head>
<body>
<div class="header"><h1>[TITLE]</h1><p class="subtitle">[SUBTITLE]</p></div>
<svg id="graph"></svg>
<div class="tooltip" id="tooltip"></div>
<script>
const nodes = [NODES_ARRAY];  // {id, label, type, size}
const links = [LINKS_ARRAY];  // {source, target, weight}
// ... D3 force simulation code
</script>
</body>
</html>
```

Node types and colors:
- **Diocese**: blue (#2B579A), size proportional to accused count
- **Facility**: green (#42b883), size proportional to referral count
- **Individual**: grey (#666), small fixed size

Edge width proportional to weight (number of transfers/referrals).

Include D3 force simulation with:
- `d3.forceLink()` with distance proportional to inverse weight
- `d3.forceManyBody()` for repulsion
- `d3.forceCenter()` for centering
- Drag interaction on nodes
- Hover tooltips showing node details and connection count

### Step 4: Write and report
Save to `data/exports/network_[subject_slug].html`
Tell the user where it is.

$ARGUMENTS
