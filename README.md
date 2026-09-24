# Valheim Cookbook

A single-page recipe search for Valheim food and mead, meant to sit open on a second monitor while you play.

**Open `index.html` in a browser.** No install, no build step, no internet needed (icons are stored locally; only the two webfonts come from the network and degrade to system fonts without it).

Live at **https://valheim-cookbook.vercel.app**

## Hosting

Plain static files — `index.html` at the root plus `data.js` and `icons/`. Any static host serves it as-is, with no build step.

`vercel.json` declares exactly that: no framework, no build command, output directory `.`. Icons get a one-year immutable cache header since their filenames never change.

## SEO and social

The canonical URL is hardcoded in five places, because scrapers don't reliably resolve relative URLs. **On a custom domain, update:** the `canonical`, `og:url`, `og:image` and `twitter:image` tags plus the JSON-LD `url`/`screenshot` in `index.html`, the `Sitemap:` line in `robots.txt`, and `<loc>` in `sitemap.xml`. Icon and manifest links are deliberately *relative* so opening `index.html` straight off disk still works.

| File | |
|---|---|
| `og-image.jpg` | 1200×800, 158KB — the social card, derived from `valheim-og-image.png` |
| `valheim-og-image.png` | 1536×1024 source art (2MB; only kept for re-exporting) |
| `favicon.svg` / `.ico` / `-96x96.png` | favicons |
| `apple-touch-icon.png` | 180×180 for iOS home screen |
| `web-app-manifest-{192,512}.png` | manifest icons |
| `manifest.json` | installable as a standalone window — handy on a second monitor |
| `robots.txt`, `sitemap.xml` | crawler basics |

Two deliberate choices:

- The source art is 1.5:1, but social cards are ~1.91:1. Cropping to 1.91 would clip either the Valheim logo or the mockup panel, so the card ships at the source ratio and lets each platform crop as it sees fit. Slack, Discord and iMessage show it whole; Facebook and X centre-crop it.
- Manifest icons declare `purpose: "any"`, not `"maskable"`. The medallion fills 506×501 of its 512 canvas, so Android's 80% maskable safe zone would crop the rim.

Recipe content is rendered by JavaScript, so it isn't in the HTML source. Googlebot renders JS and will index it, but if search traffic ever matters, the robust fix is to have `scripts/scrape.py` also emit a static recipe list into the page.

## What it does

- **Food / Mead tabs** at the top of the list. They're two different crafting worlds — different stations, different stats, no shared recipes — so they're separate views rather than one more filter. The inventory underneath them is *shared*, which is the point: the Honey you're carrying counts towards both a Boar jerky and a Tasty mead. Sort, station and effect filters are per-tab; the tab lives in the URL (`#mead`), so a link opens where you left it.
- **My inventory** — type in what you're carrying. The list narrows to recipes that use those ingredients, and every card shows `have/need` per ingredient with a `✓ cook now ×N` badge for how many you can make. The ingredient picker is scoped to the tab you're on, so browsing pies doesn't offer you Powdered dragon eggshells.
- **Sub-recipe chains are always on.** Ingredients count even when they need an intermediate step: hold raw Deer meat and *Deer stew* still appears, marked `✓ cook the parts first`, with its Cooked deer meat row flagged `can cook ↻`. Same for Barley → Barley flour → pies. Shared ingredients are pooled correctly, so a feast needing Deer stew ×3 *and* Queen's jam ×4 reports one combined Blueberries figure.
- **Stations** — tick what you've built and set your cauldron level. This *is* the station filter: untick Stone oven and its fourteen recipes disappear; drop the cauldron to level 2 and the 28 higher-level recipes go with it. The Mead ketill appears here too, because Oat milk is brewed in it — it's the same tick as on the Mead tab. Each row shows how many recipes that station makes.
- **Biome** — filter to one or more biomes. Every card also carries a colour-coded biome tag and its station, so a flat list stays scannable without grouping.
- **Search** — matches recipe names and the whole ingredient tree, so "barley" finds every pie made with its flour. On the Mead tab it also matches effect text, so "carry" finds Mead of Troll endurance and "poison" finds its mead.
- **Show** — recipes using my ingredients (default), can cook, missing only 1–2 things, or everything.
- **Sort** — total buff, health, stamina, eitr, healing/tick, duration, biome tier, how many you can cook, or name. Meads sort by effect type (the default, which clusters them health → stamina → eitr → resistance → utility), biome tier, duration, cooldown, how many you can brew, or name.

On the Mead tab specifically:

- **Every mead card spells out both stages** — brew a base at the Mead ketill, then ferment it — because that two-step craft is the thing people actually forget. The card names the base, shows its icon, and states the yield and the fermenter cycle.
- **Effect** filter pills replace nothing; they're an extra axis meads have and food doesn't. The footer of each card names its **cooldown group**, so it's obvious that drinking a Minor healing mead locks out the Major one.
- **Stations** becomes Mead ketill + Fermenter, with build costs in the hint — both are required, and unticking either explains itself rather than showing an empty grid.
- **A− / A+** in the toolbar scales the whole UI from 14px to 24px. All sizes are `rem` off a single `--ui` variable, so everything scales together.

Everything persists in `localStorage`.

Two behaviours worth knowing:

- With an empty inventory, "recipes using my ingredients" shows everything rather than an empty screen.
- Flour, dough and unbaked parts aren't food, so they're kept out of the list — but they're still used for chain resolution and appear if you search for them by name.

## Files

| File | |
|---|---|
| `index.html` | the whole app — markup, styles, logic |
| `data.js` | generated: 77 cooked foods + 4 intermediates + 20 meads + 69 base ingredients |
| `icons/` | 190 item icons, 64px, from the wiki (meads and mead bases included) — WebP for the older ones fetched from Fandom, PNG for those added since |
| `scripts/scrape.py` | regenerates `data.js` and `icons/` |

## Data

Scraped from the official Valheim wiki at [valheim.weirdgloop.org](https://valheim.weirdgloop.org) via its MediaWiki API:
[Food](https://valheim.weirdgloop.org/w/Food) (the stats table),
[Cauldron](https://valheim.weirdgloop.org/w/Cauldron) (station levels),
[Food Preparation Table](https://valheim.weirdgloop.org/w/Food_Preparation_Table),
[Feast](https://valheim.weirdgloop.org/w/Feast),
[Stone Oven](https://valheim.weirdgloop.org/w/Stone_Oven),
[Cooking Station](https://valheim.weirdgloop.org/w/Cooking_Station),
[Mead](https://valheim.weirdgloop.org/w/Mead) (the mead table and its cooldown groups),
[Mead Ketill](https://valheim.weirdgloop.org/w/Mead_Ketill),
[Fermenter](https://valheim.weirdgloop.org/w/Fermenter),
plus individual item pages for the spice blends, doughs, flours and the mead-only reagents.
Stats, cauldron levels, yields and ingredients were then checked against the 1.0.15 game files as read out by [Physgun's item database](https://physgun.com/tools/valheim/items/), and the handful of rows where the wiki is wrong are overridden in the scraper.

The data came from Fandom until the Deep North update (1.0). The community wiki moved to Weird Gloop, and Fandom's Food table only has half the Deep North rows, with blank ingredients and stations. Weird Gloop titles items in Title Case (`Cooked Boar Meat`); the scraper converts them back to the game's sentence case (`Cooked boar meat`), keeping biome names and a few proper nouns capitalised. The names have to stay the same because saved inventories are keyed by them. After the switch every pre-existing food, item and mead came out identical.

Notes on the dataset:

- Recipes for oven foods are stored as the **prep-table step's ingredients** (what you actually gather), with the station shown as `Food prep table + Stone oven`. `Bread dough`, `Unbaked sweetbread` and `Barley flour` are modelled as real intermediates because other recipes consume them directly.
- Feast biomes come from the Feast page. The Food page files every feast under "Swamp" as a sort artefact.
- `Bukeperries` and `Rotten meat` are excluded — they're −100% regen debuffs, not something you cook.
- `Cooked bear meat` had no recipe listed on the wiki table; it's filled in from the Cooking station page (Bear meat ×1).
- The Iron cooking station is treated as a superset of the Cooking station, so owning only the iron one still unlocks the basic grilled meats.
- Deep North brings two new oven shapes. `Cooked seal blubber` goes into the Stone oven raw (`Stone oven`). `Baked poteitr` and `Oven pancake` are batters mixed in a cauldron and then baked (`Cauldron + Stone oven`, gated by both the cauldron level and the oven). As with the pies, the recipe stores the cauldron step's ingredients.
- `Kale chips` is listed on the Food table as a straight oven bake of Kale ×12. Its [Raw Kale Chips](https://valheim.weirdgloop.org/w/Raw_Kale_Chips) page says the Kale goes into a level 6 cauldron and comes out as four raw chips, so `RECIPE_FIX` models it that way (`Cauldron + Stone oven`, level 6, makes 4). The game files confirm it (`KaleChipsUncooked`: Cauldron level 6, Kale ×12, makes 4).
- `Oat milk` is brewed in the Mead ketill and is eaten as food, not fermented. It's also an ingredient in Pancakes and Oatmeal.
- `Oat flour` is a Windmill intermediate, like Barley flour.
- Where the wiki disagrees with the game files, the game files win. Neither wiki source is reliable on its own: the Deep North item pages are still marked work in progress, and the Food table has errors in both old and new rows. The fixes live in `MAT_FIX`, `STAT_FIX` and `INTERMEDIATE` in the scraper:
  - `Cooked moose meat`: regen 7, not 5.
  - `Oven pancake`: lasts 30 min, not 25, and the batter takes Poteitr ×2, not ×1.
  - `Luminous larva`: lasts 10 min, not 15.
  - `Lingonberry juice`: cauldron level 6, not 7.
  - `Frosted sweetbread`: regen 4, not 2.
  - `Cooked lox meat`: weighs 2.0, not 1.0.
  - `Unbaked sweetbread`: one per craft, not two.
- `Seasoning of the gourd` is bought from the Bog Witch at 220 coins for 5, after Kall Fimbulbringer. The item's infobox says 200, but its own text and the [Bog Witch](https://valheim.weirdgloop.org/w/The_Bog_Witch) trade table both say 220. Physgun has no trader prices to settle it.
- Cauldron level 7 needs a Smoker. Saved settings from before 1.0 that were on level 6, then the maximum, are moved to 7 on load; otherwise every level 7 recipe would be hidden for returning users.

And on the meads:

- A mead is stored as its **Mead ketill ingredients** — what you gather — with the base carried alongside for display, the same way oven foods store the prep-table step. Mead bases aren't modelled as real intermediates because nothing else consumes them.
- **Biome and tier are derived, not scraped.** The wiki files no biome against a mead, so each one takes the biome of its highest-tier ingredient — the thing that actually gates it. Berserkir mead lands in Mountain because Toadstool is sold only after Moder; Anti-sting concoction lands in Plains because Grouper needs a Fuling trophy for its bait.
- **Effect categories** come from the cooldown groups on the Mead page where they exist (healing / stamina / eitr), then from the effect text (anything reading "resistance"), then utility. `Tasty mead` is the one hand-placed exception: it's in no group and its effect reads as a health *penalty*, so the text rule would file it under utility rather than stamina.
- `Love potion` is excluded — it's bought ready-made from The Bog Witch for 110 coins and has no ketill recipe, which is why the Mead ketill page doesn't list it either.
- The 12 mead-only ingredients (Coal, Feathers, the three fish, Scale hide, Toadstool and the four Bog Witch reagents) never appear in the Food table, so they live in a `MEAD_ONLY` dict next to `BASE`.

## Refreshing the data

```sh
python3 scripts/scrape.py
```

Standard library only, no dependencies. It re-parses the wiki, downloads any new icons, and rewrites `data.js`. Responses are cached in `scripts/.cache` — delete it to force a fresh fetch.

The script **fails loudly** rather than silently producing a broken dataset: if an ingredient doesn't resolve to a known item, an edible food isn't listed in `BASE`, or an icon can't be found, it exits with the offending names. The mead half adds one more check — the recipe list on the Mead Ketill page must match the bases parsed out of the Mead table, so a mead added to one page and not the other is an error rather than a silent omission. When the game adds foods, that's your to-do list — new base ingredients go in the `BASE` dict, new intermediates in `INTERMEDIATE`, new mead-only reagents in `MEAD_ONLY`, and icons whose file isn't at the obvious name in `ICON_HINTS`.

Four wiki and cache quirks the script handles, all of which cost an afternoon to find:

- Filenames in the tables are often **redirects** to a re-capitalised upload, and a redirect page answers with no `imageinfo` at all. Some chain twice (`Black soup.png` → `BlackSoup.png` → `Black Soup.png`), so icon lookups pass `redirects=1` and walk the answer back to the name that was asked for.
- `action=parse` does **not** follow redirects by default — without `redirects=1` it hands back the `#REDIRECT` stub.
- The icon lookup is batched 40 files at a time, and each batch is cached keyed on its full list of filenames. A key built from the first filename alone breaks when a new name shifts every later batch: an old answer without the new file comes back and the icon reads as missing.
- Cache filenames carry a hash suffix. macOS filesystems are case-insensitive, so `Mead ketill` and `Mead Ketill` would otherwise share one cache entry and the second page would quietly serve the first one's wikitext.

## Reminders baked into the footer

Buffs decay as `bonus × (time left / duration)^0.3`, so re-eat at roughly 50% remaining. Feasts must be placed with a Serving tray and give 10 servings. Spice blends are bought from The Bog Witch and gate the feast recipes.

The Mead tab's footer carries its own: a fermenter needs a roof and 70% cover, holds one base at a time and takes two in-game days per cycle, and destroying it mid-cycle loses the base.
