#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerate data.js and icons/ from the Valheim wiki.

    python3 scripts/scrape.py

Fetches wikitext through the Fandom MediaWiki API, parses the stats table on
/wiki/Food and the mead table on /wiki/Mead, patches the handful of gaps those
tables have, resolves every item icon to a real file, downloads them at 64px,
and writes data.js.

Standard library only. API responses are cached under scripts/.cache so re-runs
are cheap; delete that directory to force a fresh fetch.
"""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request

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

# Ingredients only meads use — none of these are food, so they'd never appear in
# the Food table. Biome is where the ingredient gates you, matching how BASE
# files the vendor spices under the biome of the boss that unlocks them.
MEAD_ONLY = {
    'Coal':          ('Meadows', 'Charcoal kiln, overcooking meat, Surtlings', 'craft'),
    'Feathers':      ('Meadows', 'Gulls, crows, hens; chests; felled beech & fir', 'drop'),
    'Perch':         ('Meadows', 'Fishing offshore Meadows & Black Forest (Fishing bait)', 'fish'),
    'Trollfish':     ('Black Forest', 'Fishing offshore Black Forest (Mossy fishing bait)', 'fish'),
    'Fresh seaweed':             ('Swamp', 'Buy from The Bog Witch — 75 coins / 5', 'vendor'),
    'Cured squirrel hamstring':  ('Swamp', 'Buy from The Bog Witch — 80 coins / 5', 'vendor'),
    'Powdered dragon eggshells': ('Swamp', 'Buy from The Bog Witch — 120 coins / 5', 'vendor'),
    'Pungent pebbles':           ('Swamp', 'Buy from The Bog Witch — 125 coins / 5', 'vendor'),
    'Toadstool':       ('Mountain', 'Buy from The Bog Witch — 85 coins (after Moder)', 'vendor'),
    'Fragrant bundle': ('Mountain', 'Buy from The Bog Witch — 140 coins / 5 (after Moder)', 'vendor'),
    'Grouper':         ('Plains', 'Fishing offshore Plains (Stingy fishing bait)', 'fish'),
    'Scale hide':      ('Mistlands', 'Hare', 'drop'),
}

# Bought from The Bog Witch for 110 coins — it has no Mead ketill recipe, so it
# isn't a brewing recipe and the Mead ketill page doesn't list it.
MEAD_SKIP = {'Love potion'}

# The cooldown groups on /wiki/Mead map cleanly onto the effect a mead gives.
# Tasty mead is in no group and its effect reads as a health *penalty* for a
# stamina gain, so the text rule below would file it under utility.
GROUP_KIND = {'healing': 'health', 'stamina': 'stamina', 'eitr': 'eitr'}
MEAD_KIND_FIX = {'Tasty mead': 'stamina'}

# A fermenter cycle, per /wiki/Fermenter. Kept as wiki-sourced game-time rather
# than converted to real minutes, which depends on the server's day length.
FERMENT_TIME = '2 in-game days'

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
def http(url, tries=4):
    # Fandom's CDN throws the odd 502/504 under a burst of icon downloads.
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, 'code', None)
            if attempt == tries - 1 or (code is not None and code < 500):
                raise
            print('  %s on %s — retrying' % (code or type(e).__name__, url[-48:]))
            time.sleep(2 * (attempt + 1))


def api(params, cache_key=None):
    path = None
    if cache_key:
        os.makedirs(CACHE, exist_ok=True)
        # The hash suffix matters: filenames are case-insensitive on macOS, so
        # 'Mead ketill' and 'Mead Ketill' would otherwise share a cache entry
        # and the second page would silently serve the first one's wikitext.
        stem = re.sub(r'[^A-Za-z0-9._-]', '_', cache_key)[:120]
        digest = hashlib.sha1(cache_key.encode('utf-8')).hexdigest()[:8]
        path = os.path.join(CACHE, '%s-%s.json' % (stem, digest))
        if os.path.exists(path):
            return json.load(open(path, encoding='utf-8'))
    data = json.loads(http(API + '?' + urllib.parse.urlencode(params)))
    if path:
        json.dump(data, open(path, 'w', encoding='utf-8'))
    time.sleep(0.2)
    return data


def wikitext(page):
    # redirects=1 because action=parse otherwise hands back the '#REDIRECT'
    # stub rather than the target page.
    d = api({'action': 'parse', 'page': page, 'prop': 'wikitext', 'redirects': '1',
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


def table_rows(tbl):
    """Yield a wiki table's rows, header and separator lines dropped.

    The body starts *at* a '|-', so the first chunk carries that separator with
    it; left in place split_cells reads it as a stray '-' cell and shifts every
    column of the first row by one.
    """
    body = tbl[tbl.index('|-'):]
    for row in re.split(r'\n\|-\s*(?:<!--.*?-->)?\s*\n', body):
        row = re.sub(r'^\|-[^\n]*\n?', '', row.strip('\n'))
        if row.strip().startswith('!') or row.strip().startswith('|}'):
            continue
        yield row


def parse_food_table(text):
    tbl = text[text.index('== List of foods =='):text.index('==Ranked foods==')]
    out = []
    for row in table_rows(tbl):
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


# ───────────────────────── Mead table parsing ─────────────────────────
# Both '{{Item Link|Honey|10}}' and '{{item link| Mushroom|10}}' occur.
ITEM_LINK = re.compile(r'\{\{\s*[Ii]tem\s+[Ll]ink\s*\|\s*([^|}]+?)\s*\|\s*(\d+)\s*\}\}')
ITEM_LINK_BARE = re.compile(r'\{\{\s*[Ii]tem\s+[Ll]ink\s*\|\s*([^|}]+?)\s*\}\}')


def parse_mead_groups(text):
    """The ==Cooldown== section lists which meads share an exclusion group."""
    sec = text[text.index('==Cooldown=='):text.index('== List of meads ==')]
    groups, cur = {}, None
    for line in sec.split('\n'):
        line = line.strip()
        m = re.match(r'^\*\s*(\w+) meads group:', line)
        if m:
            cur = m.group(1).lower()
            continue
        m = ITEM_LINK_BARE.match(line.lstrip('*').strip()) if line.startswith('**') else None
        if m and cur:
            groups[m.group(1)] = cur
    return groups


def parse_mead_table(text):
    tbl = text[text.index('== List of meads =='):text.index('==Trivia==')]
    out = []
    for row in table_rows(tbl):
        cells = split_cells(row)
        if len(cells) < 8:
            continue
        name = clean(cells[0])
        if not name:
            continue
        # Column 2 is the base's icon; its link= target is the base item name.
        m = re.search(r'link=([^|\]]+)', cells[2]) or re.search(r'File:(.+?)\.png', cells[2])
        out.append(dict(
            name=name, icon=clean(cells[1]),
            base=m.group(1).strip() if m else '',
            base_icon=(re.search(r'File:([^|\]]+)', cells[2]).group(1).strip()
                       if 'File:' in cells[2] else ''),
            mats=[[a, int(b)] for a, b in ITEM_LINK.findall(cells[3])],
            qty=num(clean(cells[4])),
            effect=clean(cells[5]), dur=clean(cells[6]), cd=clean(cells[7]),
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
        # redirects=1 is load-bearing: plenty of the filenames the wiki tables
        # cite are now redirects to a re-capitalised upload, and a redirect page
        # answers with no imageinfo at all. Several chain twice, e.g.
        # 'Black soup.png' → 'BlackSoup.png' → 'Black Soup.png'.
        d = api({'action': 'query', 'titles': '|'.join('File:' + c for c in chunk),
                 'redirects': '1', 'prop': 'imageinfo', 'iiprop': 'url',
                 'iiurlwidth': '64', 'format': 'json', 'formatversion': '2'},
                'img-%d-%s' % (i, chunk[0]))
        # Walk each answer back to the title we actually asked for.
        back = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        back.update({r['to']: r['from'] for r in d['query'].get('redirects', [])})
        for p in d['query']['pages']:
            if 'imageinfo' not in p:
                continue
            title = p['title']
            for _ in range(8):
                if title not in back:
                    break
                title = back[title]
            found[title[5:]] = p['imageinfo'][0].get('thumburl') or p['imageinfo'][0]['url']

    resolved, missing = {}, []
    os.makedirs(ICONS, exist_ok=True)
    for name, cs in cands.items():
        hit = next((c for c in cs if c in found), None)
        if not hit:
            missing.append(name)
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + '.webp'
        path = os.path.join(ICONS, slug)
        # Fetch fully before opening the file. Writing straight from http() left
        # a 0-byte icon behind whenever a download failed, and the exists() check
        # then skipped it on every later run.
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            blob = http(found[hit])
            with open(path, 'wb') as fh:
                fh.write(blob)
            time.sleep(0.1)
        resolved[name] = slug
    return resolved, missing


# ────────────────────────────  mead recipes  ────────────────────────────
def build_meads(biome_of):
    """Every mead brewed at the Mead ketill, checked against that page's list."""
    text = wikitext('Mead')
    groups = parse_mead_groups(text)
    rows = [m for m in parse_mead_table(text) if m['name'] not in MEAD_SKIP]
    print('  parsed %d meads from /wiki/Mead' % len(rows))

    # The ketill page is the authority on what's actually brewable. Any drift
    # between the two lists is a wiki edit we want to hear about, not paper over.
    listed = set(ITEM_LINK_BARE.findall(
        wikitext('Mead Ketill').split('== Recipes ==')[1].split('==Trivia==')[0]))
    parsed = {m['base'] for m in rows}
    if parsed != listed:
        sys.exit('Mead ketill recipe list disagrees with the mead table:\n'
                 '  only on the ketill page: %r\n  only in the mead table: %r'
                 % (sorted(listed - parsed), sorted(parsed - listed)))

    meads = []
    for m in rows:
        bad = [n for n, _ in m['mats'] if n not in biome_of]
        if bad:
            sys.exit('%s uses unknown ingredients %r — add them to MEAD_ONLY'
                     % (m['name'], bad))
        if not m['mats']:
            sys.exit('no ingredients parsed for %s' % m['name'])

        # A mead is gated by its rarest ingredient, so that ingredient's biome is
        # the one worth tagging and sorting by. The wiki lists no biome itself.
        tier = max(BIOME_ORDER.index(biome_of[n]) for n, _ in m['mats'])
        group = groups.get(m['name'], '')
        kind = (MEAD_KIND_FIX.get(m['name']) or GROUP_KIND.get(group)
                or ('resistance' if 'resistance' in m['effect'].lower() else 'utility'))
        meads.append(dict(
            name=m['name'], icon='', base=m['base'], baseIcon='',
            effect=m['effect'], kind=kind, group=group,
            duration=num(m['dur']), cooldown=num(m['cd']),
            biome=BIOME_ORDER[tier], tier=tier + 1, mats=m['mats'],
            _icon=m['icon'], _base_icon=m['base_icon'], **{'yield': m['qty'] or 1},
        ))
    return meads


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
    for name, (biome, source, cat) in {**BASE, **MEAD_ONLY}.items():
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

    meads = build_meads({e['name']: e['biome'] for e in items + recipes})

    print('resolving icons…')
    table_icons = {f['name']: f['icon'] for f in foods}
    for m in meads:
        table_icons[m['name']] = m.pop('_icon')
        table_icons[m['base']] = m.pop('_base_icon')
    slugs, missing = resolve_icons(
        [r['name'] for r in recipes] + [i['name'] for i in items]
        + [m['name'] for m in meads] + [m['base'] for m in meads],
        table_icons)
    if missing:
        sys.exit('no icon found for: %r' % missing)
    for e in recipes + items:
        e['icon'] = slugs[e['name']]
    for m in meads:
        m['icon'] = slugs[m['name']]
        m['baseIcon'] = slugs[m['base']]

    data = dict(biomeOrder=BIOME_ORDER, fermentTime=FERMENT_TIME,
                items=items, recipes=recipes, meads=meads)
    dest = os.path.join(ROOT, 'data.js')
    with open(dest, 'w', encoding='utf-8') as fh:
        fh.write('// Valheim food data, scraped from valheim.fandom.com\n')
        fh.write('// Regenerate with: python3 scripts/scrape.py\n')
        fh.write('// Sources: /wiki/Food, /wiki/Cauldron, /wiki/Food_preparation_table,\n')
        fh.write('//          /wiki/Feast, /wiki/Stone_oven, /wiki/Cooking_station,\n')
        fh.write('//          /wiki/Mead, /wiki/Mead_Ketill, /wiki/Fermenter.\n')
        fh.write('window.VALHEIM = ')
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write(';\n')

    print('wrote %s — %d recipes, %d meads, %d base items, %d icons'
          % (os.path.relpath(dest, ROOT), len(recipes), len(meads), len(items), len(slugs)))


if __name__ == '__main__':
    main()
