#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate data.js and icons/ from the Valheim wiki.

    python3 scripts/scrape.py

Fetches wikitext through the Fandom MediaWiki API, parses the stats table on
/wiki/Food, patches the handful of gaps that table has, resolves every item icon
to a real file, downloads them at 64px, and writes data.js.

Standard library only. API responses are cached under scripts/.cache so re-runs
are cheap; delete that directory to force a fresh fetch.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'scripts', '.cache')
ICONS = os.path.join(ROOT, 'icons')
API   = 'https://valheim.fandom.com/api.php'
UA    = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
         '(KHTML, like Gecko) Chrome/120 Safari/537.36')

BIOME_ORDER = ['Meadows', 'Black Forest', 'Swamp', 'Ocean', 'Mountain',
               'Plains', 'Mistlands', 'Ashlands']

# Debuff items — not something you cook.
SKIP = {'Bukeperries', 'Rotten meat'}

# The Food page files every feast under "Swamp" as a sort artefact; the Feast
# page has the real biomes.
FEAST_BIOME = {
    'Whole roasted Meadow boar': 'Meadows',
    'Black Forest buffet platter': 'Black Forest',
    "Swamp dweller's delight": 'Swamp',
    "Sailor's bounty": 'Ocean',
    "Hearty Mountain logger's stew": 'Mountain',
    'Plains pie picnic': 'Plains',
    'Mushrooms galore á la Mistlands': 'Mistlands',
    'Ashlands gourmet bowl': 'Ashlands',
}

# Recipes the Food table leaves blank (sourced from /wiki/Cooking_station).
MAT_FIX = {'Cooked bear meat': [['Bear meat', 1]]}

# Intermediates other recipes consume directly. Sourced from /wiki/Bread,
# /wiki/Frosted_sweetbread and /wiki/Barley_flour.
INTERMEDIATE = [
    dict(name='Barley flour', station='Windmill', biome='Plains', qty=1,
         mats=[['Barley', 1]]),
    dict(name='Bread dough', station='Food preparation table', biome='Plains', qty=2,
         mats=[['Barley flour', 10]]),
    dict(name='Unbaked sweetbread', station='Food preparation table', biome='Plains', qty=2,
         mats=[['Cloudberries', 2], ['Egg', 1], ['Barley flour', 1], ['Honey', 1]]),
]

# Base ingredients: biome, where you get it, category.
BASE = {
    'Raspberries':      ('Meadows', 'Bushes in Meadows', 'forage'),
    'Mushroom':         ('Meadows', 'Meadows & Black Forest floor', 'forage'),
    'Honey':            ('Meadows', 'Beehive (tame) or wild beehives', 'farm'),
    'Dandelion':        ('Meadows', 'Meadows floor', 'forage'),
    'Neck tail':        ('Meadows', 'Neck', 'drop'),
    'Boar meat':        ('Meadows', 'Boar (tameable)', 'drop'),
    'Deer meat':        ('Meadows', 'Deer', 'drop'),
    'Raw fish':         ('Meadows', 'Fishing rod', 'drop'),
    'Blueberries':      ('Black Forest', 'Bushes in Black Forest', 'forage'),
    'Yellow mushroom':  ('Black Forest', 'Burial Chambers / caves', 'forage'),
    'Carrot':           ('Black Forest', 'Plant carrot seeds', 'farm'),
    'Thistle':          ('Black Forest', 'Black Forest & Swamp floor', 'forage'),
    'Bear meat':        ('Black Forest', 'Bear, Vile', 'drop'),
    'Greydwarf eye':    ('Black Forest', 'Greydwarfs', 'drop'),
    'Turnip':           ('Swamp', 'Plant turnip seeds (found in Swamp)', 'farm'),
    'Entrails':         ('Swamp', 'Draugr, meat piles', 'drop'),
    'Bloodbag':         ('Swamp', 'Leeches', 'drop'),
    'Ooze':             ('Swamp', 'Blobs, Oozers', 'drop'),
    'Serpent meat':     ('Ocean', 'Serpent', 'drop'),
    'Onion':            ('Mountain', 'Plant onion seeds (found in Mountain caves)', 'farm'),
    'Wolf meat':        ('Mountain', 'Wolf (tameable)', 'drop'),
    'Freeze gland':     ('Mountain', 'Drake', 'drop'),
    'Cloudberries':     ('Plains', 'Bushes in Plains', 'forage'),
    'Barley':           ('Plains', 'Fuling Villages; then farmable', 'farm'),
    'Lox meat':         ('Plains', 'Lox (tameable)', 'drop'),
    'Chicken meat':     ('Plains', 'Chicken / Hen', 'farm'),
    'Egg':              ('Plains', 'Hen, or buy from Haldor', 'farm'),
    'Magecap':          ('Mistlands', 'Mistlands floor', 'forage'),
    'Jotun puffs':      ('Mistlands', 'Mistlands floor', 'forage'),
    'Sap':              ('Mistlands', 'Tap Yggdrasil roots with a sap extractor', 'farm'),
    'Royal jelly':      ('Mistlands', 'Seeker Broods, Infested Mine piles', 'drop'),
    'Blood clot':       ('Mistlands', 'Ticks', 'drop'),
    'Seeker meat':      ('Mistlands', 'Seeker, Seeker Soldier', 'drop'),
    'Hare meat':        ('Mistlands', 'Hare', 'drop'),
    'Anglerfish':       ('Mistlands', 'Fishing in Mistlands (Mistlands bait)', 'drop'),
    'Smoke puff':       ('Ashlands', 'Ashlands floor', 'forage'),
    'Fiddlehead':       ('Ashlands', 'Ashlands floor', 'forage'),
    'Vineberry cluster':('Ashlands', 'Ashlands; plant vineberry seeds', 'forage'),
    'Asksvin tail':     ('Ashlands', 'Asksvin, Asksvin Hatchling', 'drop'),
    'Volture meat':     ('Ashlands', 'Volture', 'drop'),
    'Volture egg':      ('Ashlands', 'Volture nests', 'drop'),
    'Bonemaw meat':     ('Ashlands', 'Bonemaw', 'drop'),
    'Woodland herb blend':          ('Black Forest', 'Buy from The Bog Witch — 120 coins / 5 (after The Elder)', 'vendor'),
    "Seafarer's herbs":             ('Ocean', 'Buy from The Bog Witch — 130 coins / 5 (after killing a Serpent)', 'vendor'),
    'Mountain peak pepper powder':  ('Mountain', 'Buy from The Bog Witch — 140 coins / 5 (after Moder)', 'vendor'),
    'Grasslands herbalist harvest': ('Plains', 'Buy from The Bog Witch — 160 coins / 5 (after Yagluth)', 'vendor'),
    'Herbs of the hidden hills':    ('Mistlands', 'Buy from The Bog Witch — 180 coins / 5 (after The Queen)', 'vendor'),
    'Fiery spice powder':           ('Ashlands', 'Buy from The Bog Witch — 200 coins / 5 (after Fader)', 'vendor'),
}

# Icons whose filename doesn't match "<Name>.png" (tabbed infoboxes mostly).
# Each list is tried in order against the API; the first that exists wins.
ICON_HINTS = {
    'Neck tail':    ['Necktail.png', 'Neck tail.png'],
    'Royal jelly':  ['Royal_jelly.png', 'Royal jelly.png'],
    'Volture egg':  ['Volture Egg.png', 'Volture egg.png'],
    'Piquant pie':  ['Piquant pie.png', 'Piquant Pie.png'],
    'Asksvin tail': ['Asksvin tail.png', 'Asksvin Tail.png'],
    'Bonemaw meat': ['Bonemaw meat.png', 'Bonemaw Meat.png'],
    'Volture meat': ['Volture meat.png', 'Volture Meat.png'],
}


# ───────────────────────────── fetching ─────────────────────────────
def http(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def api(params, cache_key=None):
    path = None
    if cache_key:
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9._-]', '_', cache_key)[:180] + '.json')
        if os.path.exists(path):
            return json.load(open(path, encoding='utf-8'))
    data = json.loads(http(API + '?' + urllib.parse.urlencode(params)))
    if path:
        json.dump(data, open(path, 'w', encoding='utf-8'))
    time.sleep(0.2)
    return data


def wikitext(page):
    d = api({'action': 'parse', 'page': page, 'prop': 'wikitext',
             'format': 'json', 'formatversion': '2'}, 'page-' + page)
    return d['parse']['wikitext']


# ───────────────────────── Food table parsing ─────────────────────────
def clean(s):
    s = re.sub(r'<!--.*?-->', '', s.strip(), flags=re.S)
    s = re.sub(r'data-sort-(value|type)="[^"]*"\s*\|', '', s)
    s = re.sub(r'\{\{Duration\|(\d+)[^}]*\}\}', r'\1', s)
    s = re.sub(r'\[\[File:([^|\]]+)[^\]]*\]\]', r'\1', s)
    s = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'<br\s*/?>', ' / ', s)
    s = s.replace("'''", '').replace('<small>', '').replace('</small>', '')
    return re.sub(r'\s+', ' ', s).strip()


def split_cells(row):
    """Wiki rows mix inline '||' separators with one-cell-per-line '|'."""
    cells = []
    for line in row.strip().split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            if cells:
                cells[-1] += '\n' + line      # continuation of a bulleted cell
            continue
        for part in line[1:].split('||'):
            cells.append(part)
    return cells


def num(s):
    m = re.match(r'^\s*(\d+)', s or '')
    return int(m.group(1)) if m else 0


def parse_food_table(text):
    tbl = text[text.index('== List of foods =='):text.index('==Ranked foods==')]
    body = tbl[tbl.index('|-'):]
    rows = re.split(r'\n\|-\s*(?:<!--.*?-->)?\s*\n', body)
    out = []
    for row in rows:
        if row.strip().startswith('!') or row.strip().startswith('|}'):
            continue
        cells = split_cells(row)
        if len(cells) < 14:
            continue
        name = clean(cells[0])
        if not name:
            continue
        mats = [[m.group(1).strip(), int(m.group(2))] for m in
                re.finditer(r'\*\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*x\s*(\d+)', cells[6])]
        out.append(dict(
            name=name, icon=clean(cells[1]),
            hp=clean(cells[2]), stam=clean(cells[3]), eitr=clean(cells[4]),
            mats=mats,
            fork=clean(cells[7]).replace('N/A', '').strip().lstrip('|').strip(),
            heal=clean(cells[8]), dur=clean(cells[9]), weight=clean(cells[10]),
            stack=clean(cells[11]), biome=clean(cells[12]), station=clean(cells[13]),
            mult=clean(cells[14]) if len(cells) > 14 else '',
        ))
    return out


def parse_station(stn):
    stn = stn.strip()
    if stn.startswith('Cauldron'):
        m = re.search(r'\((\d+)\)', stn)
        return 'Cauldron', int(m.group(1)) if m else 1
    if 'Stone Oven' in stn or 'Stone oven' in stn:
        return 'Food prep table + Stone oven', 0
    for s in ('Food preparation table', 'Iron cooking station', 'Cooking station'):
        if stn.startswith(s):
            return s, 0
    return '', 0            # parenthesised = gathered, not cooked


# ─────────────────────────── icon resolution ───────────────────────────
def resolve_icons(names, table_icons):
    cands = {}
    for n in names:
        c = []
        if table_icons.get(n):
            c.append(table_icons[n])
        for h in ICON_HINTS.get(n, []):
            if h not in c:
                c.append(h)
        guess = n[0].upper() + n[1:] + '.png'
        if guess not in c:
            c.append(guess)
        cands[n] = c

    files = sorted({f for v in cands.values() for f in v})
    found = {}
    for i in range(0, len(files), 40):
        chunk = files[i:i + 40]
        d = api({'action': 'query', 'titles': '|'.join('File:' + c for c in chunk),
                 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': '64',
                 'format': 'json', 'formatversion': '2'}, 'img-%d-%s' % (i, chunk[0]))
        renamed = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        for p in d['query']['pages']:
            if 'imageinfo' in p:
                key = renamed.get(p['title'], p['title'])[5:]
                found[key] = p['imageinfo'][0].get('thumburl') or p['imageinfo'][0]['url']

    resolved, missing = {}, []
    os.makedirs(ICONS, exist_ok=True)
    for name, cs in cands.items():
        hit = next((c for c in cs if c in found), None)
        if not hit:
            missing.append(name)
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + '.webp'
        path = os.path.join(ICONS, slug)
        if not os.path.exists(path):
            with open(path, 'wb') as fh:
                fh.write(http(found[hit]))
            time.sleep(0.1)
        resolved[name] = slug
    return resolved, missing


# ───────────────────────────────  main  ───────────────────────────────
def main():
    print('fetching wiki pages…')
    foods = parse_food_table(wikitext('Food'))
    print('  parsed %d rows from /wiki/Food' % len(foods))

    recipes, gathered = [], {}
    for f in foods:
        if f['name'] in SKIP:
            continue
        station, level = parse_station(f['station'])
        biome = FEAST_BIOME.get(f['name'], f['biome'])
        if biome not in BIOME_ORDER:
            sys.exit('unexpected biome %r on %s' % (biome, f['name']))
        e = dict(
            name=f['name'], icon='',
            hp=num(f['hp']), stam=num(f['stam']), eitr=num(f['eitr']),
            heal=num(f['heal']), duration=num(f['dur']),
            weight=float(f['weight']) if re.match(r'^[\d.]+$', f['weight']) else None,
            stack=num(f['stack']), fork=f['fork'], biome=biome,
            tier=BIOME_ORDER.index(biome) + 1, station=station, level=level,
            mats=MAT_FIX.get(f['name'], f['mats']),
        )
        if station:
            m = re.match(r'^\s*(\d+)\s*$', f['mult'])
            e['yield'] = int(m.group(1)) if m else 1
            e['feast'] = '10 uses' in f['mult']
            recipes.append(e)
        else:
            gathered[f['name']] = e     # edible but not cooked

    for it in INTERMEDIATE:
        recipes.append(dict(
            name=it['name'], icon='', hp=0, stam=0, eitr=0, heal=0, duration=0,
            weight=None, stack=0, fork='', biome=it['biome'],
            tier=BIOME_ORDER.index(it['biome']) + 1, station=it['station'], level=0,
            mats=it['mats'], intermediate=True, feast=False, **{'yield': it['qty']},
        ))

    items = []
    for name, (biome, source, cat) in BASE.items():
        g = gathered.get(name)
        items.append(dict(
            name=name, icon='', biome=biome, tier=BIOME_ORDER.index(biome) + 1,
            source=source, cat=cat,
            hp=g['hp'] if g else 0, stam=g['stam'] if g else 0,
            eitr=g['eitr'] if g else 0, heal=g['heal'] if g else 0,
            duration=g['duration'] if g else 0, edible=bool(g),
        ))

    # Every material must resolve to a base item or another recipe.
    known = {i['name'] for i in items} | {r['name'] for r in recipes}
    bad = [(r['name'], m) for r in recipes for m, _ in r['mats'] if m not in known]
    orphan = sorted(set(gathered) - {i['name'] for i in items})
    if bad:
        sys.exit('unresolved ingredients: %r' % bad)
    if orphan:
        sys.exit('edible items missing from BASE: %r' % orphan)

    print('resolving icons…')
    table_icons = {f['name']: f['icon'] for f in foods}
    slugs, missing = resolve_icons([r['name'] for r in recipes] + [i['name'] for i in items],
                                   table_icons)
    if missing:
        sys.exit('no icon found for: %r' % missing)
    for e in recipes + items:
        e['icon'] = slugs[e['name']]

    data = dict(biomeOrder=BIOME_ORDER, items=items, recipes=recipes)
    dest = os.path.join(ROOT, 'data.js')
    with open(dest, 'w', encoding='utf-8') as fh:
        fh.write('// Valheim food data, scraped from valheim.fandom.com\n')
        fh.write('// Regenerate with: python3 scripts/scrape.py\n')
        fh.write('// Sources: /wiki/Food, /wiki/Cauldron, /wiki/Food_preparation_table,\n')
        fh.write('//          /wiki/Feast, /wiki/Stone_oven, /wiki/Cooking_station.\n')
        fh.write('window.VALHEIM = ')
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write(';\n')

    print('wrote %s — %d recipes, %d base items, %d icons'
          % (os.path.relpath(dest, ROOT), len(recipes), len(items), len(slugs)))


if __name__ == '__main__':
    main()
