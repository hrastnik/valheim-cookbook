# Valheim Cookbook

A single-page recipe search for Valheim food, meant to sit open on a second monitor while you play.

**Open `index.html` in a browser.** No install, no build step, no internet needed (icons are stored locally; only the two webfonts come from the network and degrade to system fonts without it).

## What it does

- **My inventory** — type in what you're carrying. The list narrows to recipes that use those ingredients, and every card shows `have/need` per ingredient with a `✓ cook now ×N` badge for how many you can make.
- **Sub-recipe chains are always on.** Ingredients count even when they need an intermediate step: hold raw Deer meat and *Deer stew* still appears, marked `✓ cook the parts first`, with its Cooked deer meat row flagged `can cook ↻`. Same for Barley → Barley flour → pies. Shared ingredients are pooled correctly, so a feast needing Deer stew ×3 *and* Queen's jam ×4 reports one combined Blueberries figure.
- **Stations** — tick what you've built and set your cauldron level. This *is* the station filter: untick Stone oven and its ten recipes disappear; drop the cauldron to level 2 and the 16 higher-level recipes go with it. Each row shows how many recipes that station makes.
- **Biome** — filter to one or more biomes. Every card also carries a colour-coded biome tag and its station, so a flat list stays scannable without grouping.
- **Search** — matches recipe names and the whole ingredient tree, so "barley" finds every pie made with its flour.
- **Show** — recipes using my ingredients (default), can cook, missing only 1–2 things, or everything.
- **Sort** — total buff, health, stamina, eitr, healing/tick, duration, biome tier, how many you can cook, or name.
- **A− / A+** in the toolbar scales the whole UI from 14px to 24px. All sizes are `rem` off a single `--ui` variable, so everything scales together.

Everything persists in `localStorage`.

Two behaviours worth knowing:

- With an empty inventory, "recipes using my ingredients" shows everything rather than an empty screen.
- Flour, dough and unbaked parts aren't food, so they're kept out of the list — but they're still used for chain resolution and appear if you search for them by name.

## Files

| File | |
|---|---|
| `index.html` | the whole app — markup, styles, logic |
| `data.js` | generated: 60 cooked foods + 3 intermediates + 48 base ingredients |
| `icons/` | 111 item icons, 64px, from the wiki |
| `scripts/scrape.py` | regenerates `data.js` and `icons/` |

## Data

Scraped from the Valheim wiki via its MediaWiki API:
[Food](https://valheim.fandom.com/wiki/Food) (the stats table),
[Cauldron](https://valheim.fandom.com/wiki/Cauldron) (station levels),
[Food preparation table](https://valheim.fandom.com/wiki/Food_preparation_table),
[Feast](https://valheim.fandom.com/wiki/Feast),
[Stone oven](https://valheim.fandom.com/wiki/Stone_oven),
[Cooking station](https://valheim.fandom.com/wiki/Cooking_station),
plus individual item pages for the spice blends, doughs and flour.

Notes on the dataset:

- Recipes for oven foods are stored as the **prep-table step's ingredients** (what you actually gather), with the station shown as `Food prep table + Stone oven`. `Bread dough`, `Unbaked sweetbread` and `Barley flour` are modelled as real intermediates because other recipes consume them directly.
- Feast biomes come from the Feast page. The Food page files every feast under "Swamp" as a sort artefact.
- `Bukeperries` and `Rotten meat` are excluded — they're −100% regen debuffs, not something you cook.
- `Cooked bear meat` had no recipe listed on the wiki table; it's filled in from the Cooking station page (Bear meat ×1).
- The Iron cooking station is treated as a superset of the Cooking station, so owning only the iron one still unlocks the basic grilled meats.

## Refreshing the data

```sh
python3 scripts/scrape.py
```

Standard library only, no dependencies. It re-parses the wiki, downloads any new icons, and rewrites `data.js`. Responses are cached in `scripts/.cache` — delete it to force a fresh fetch.

The script **fails loudly** rather than silently producing a broken dataset: if an ingredient doesn't resolve to a known item, an edible food isn't listed in `BASE`, or an icon can't be found, it exits with the offending names. When the game adds foods, that's your to-do list — new base ingredients go in the `BASE` dict, new intermediates in `INTERMEDIATE`.

## Reminders baked into the footer

Buffs decay as `bonus × (time left / duration)^0.3`, so re-eat at roughly 50% remaining. Feasts must be placed with a Serving tray and give 10 servings. Spice blends are bought from The Bog Witch and gate the feast recipes.
