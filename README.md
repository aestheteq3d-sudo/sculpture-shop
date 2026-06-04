# AESTHETEQ — Design & Form Collection

> Algorithmic 3D-printed lamps. Parametric form, FDM fabrication. Minneapolis, MN.

## Deploy to GitHub Pages + Custom Domain

1. Create repo on GitHub → upload all files → Settings → Pages → Source: `main /root`
2. Add DNS records (see DNS section in conversation)
3. Enforce HTTPS → done

## File Structure

```
aestheteq/
├── index.html          Landing page — hero, featured forms, why section
├── collection.html     Store — 17 forms × 6+6 filament colors, interactive configurator
├── lab.html            Design Lab — 61 Blender renders, 17 filter groups
├── about.html          Studio story, materials, process
├── contact.html        Custom order inquiry form
├── css/
│   └── aestheteq.css   Complete design system
├── js/
│   ├── nav.js          Shared nav, footer, ticker, scroll reveal
│   ├── products.js     Product catalog + filament color definitions
│   ├── configurator.js Object-only canvas colorization engine (BFS masks)
│   └── lab-data.js     61 design lab renders (base64)
├── assets/
│   ├── products/       {key}-src.jpg + {key}-mask.png per product
│   └── favicon.ico etc
└── tools/
    └── add_lamp.py     Script to add new lamps
```

## Adding New Lamps

When you export a new Blender render:

```bash
python tools/add_lamp.py --image path/to/new_render.png --key my_new_lamp
```

The script outputs the exact JSON entry to paste into `js/products.js`.

## Color System

- **Shade**: Translucent PETG — Frost, Amber, Smoke, Crimson, Ice, Sage
- **Base**: PA-CF / Matte PLA — PA-CF Black, Matte White, Olive, Silk Copper, Silk Silver, Gloss Crimson
- Canvas colorization uses stored BFS flood-fill masks — **background pixels are never altered**

## Update Etsy Link

In `js/nav.js`, replace:
```
https://www.etsy.com/shop/aestheteq
```
with your real Etsy shop URL (appears in nav, footer, and product modals).
