# Phys.io Mission site

Open `index.html` through a local web server (videos and textures will not load from file://):

    cd frontend
    python -m http.server 8000

Then visit http://localhost:8000

## Files
- `index.html` the whole site (three.js r128 and Lenis load from CDN)
- `tex/` Earth textures from the three.js examples
- `logo-loop.webm`, `logo-loop.mp4` logo animation
- `data/baselines.json` measured baselines: 20 seeds, budget 400, target 50 W/m2 (benchmark.json contract format)
- `data/baselines_full.json` every run, with provenance

## Adding the agent lab result
Put the final `benchmark.json` at `results/benchmark.json` next to `index.html` (needs 5+ seeds),
or use the "Load benchmark.json" button in the Faster section.
