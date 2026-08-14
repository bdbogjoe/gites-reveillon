"""Assemble la page publiée depuis le gabarit.

gites.tpl.html a la forme :
    <title>…</title>
    [<link …>]*  <style>…</style>          -> vont dans le <head>
    …contenu…    [<script>…</script>]*     -> vont dans le <body>

Les polices woff2 sous-ensemblées sont injectées en base64 à la place des
marqueurs __SERIF__ / __SANS__ / __MONO__.
"""
import base64, pathlib, re, sys, unicodedata, collections, json, shutil, subprocess, tempfile

RACINE = pathlib.Path(__file__).parent
SORTIE = pathlib.Path("/home/eric/gites/index.html")
POLICES = (("__SERIF__", "serif.woff2"), ("__SANS__", "sans.woff2"), ("__MONO__", "mono.woff2"))
DESC = ("Un gîte de groupe pour 15 personnes du 26 décembre au 2 janvier, à moins de 2 h de Toulouse : "
        "carte, tarifs, distances supermarché et gare, et points à vérifier avant d'appeler.")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%94%EF%B8%8F%3C/text%3E%3C/svg%3E")


def _entrees(doc, sid):
    """(nom normalisé, commune normalisée) des entrées de premier niveau d'une section."""
    bloc = re.search(r'<section id="%s">.*?</section>' % sid, doc, re.S)
    if not bloc:
        return set()
    out = set()
    motif = r'\n        <li[^>]*>\s*(?:<div class="ruban[^>]*>.*?</div>\s*)?<h3>(.*?)</h3>(.*?)</li>'
    for m in re.finditer(motif, bloc.group(0), re.S):
        titre = re.sub(r'<span class="cap">.*?</span>', '', m.group(1), flags=re.S)
        titre = re.sub(r'<[^>]+>', '', titre)
        loc = re.search(r'<p class="loc">([^<]+)</p>', m.group(2))
        bouts = re.split(r'[\u2014\u00b7]', titre)
        nom = bouts[0]
        com = loc.group(1) if loc else (bouts[1] if len(bouts) > 1 else "")
        out.add((_cle(nom), _cle(com)))
    return out


def _cle(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\d+\s*pl\.?", "", s)
    for mot in ("gite de sejour ", "gite de ", "gite ", "hameau des ", "chalet des ", "chalets du ",
                "domaine de ", "domaine ", "le ", "la ", "les ", "l'"):
        s = s.replace(mot, "")
    return re.sub(r"[^a-z0-9]", "", s)


def construire():
    src = (RACINE / "gites.tpl.html").read_text(encoding="utf-8")
    for marqueur, fichier in POLICES:
        if marqueur not in src:
            raise SystemExit(f"marqueur de police absent : {marqueur}")
        src = src.replace(marqueur, base64.b64encode((RACINE / fichier).read_bytes()).decode("ascii"))

    m = re.match(r"\s*<title>(.*?)</title>\s*", src, re.S)
    if not m:
        raise SystemExit("<title> introuvable en tête de gabarit")
    titre, reste = m.group(1).strip(), src[m.end():].strip()

    # tout ce qui précède la fin de la dernière balise <style> appartient au <head>
    fin_style = reste.rindex("</style>") + len("</style>")
    tete, corps = reste[:fin_style].strip(), reste[fin_style:].strip()

    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<meta name="description" content="{DESC}">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{FAVICON}">
<meta property="og:title" content="{titre}">
<meta property="og:description" content="{DESC}">
<meta property="og:type" content="article">
{tete}
</head>
<body>
{corps}
</body>
</html>
"""
    SORTIE.write_text(doc, encoding="utf-8")
    return doc, titre


STUB = """
var ajoutes = new Set(), BOUTONS = {};
function Faux(){}
Faux.prototype.addTo = function(){ ajoutes.add(this); return this; };
['bindPopup','bindTooltip','on','setStyle','openPopup'].forEach(function(m){ Faux.prototype[m] = function(){ return this; }; });
function f(){ return new Faux(); }
var map = { hasLayer:function(o){return ajoutes.has(o)}, removeLayer:function(o){ajoutes.delete(o)},
  fitBounds:function(){}, once:function(){}, scrollWheelZoom:{disable:function(){},enable:function(){}},
  addLayer:function(){}, on:function(){}, setView:function(){return map} };
var L = { map:function(){return map}, tileLayer:f, circleMarker:f, marker:f, circle:f, polyline:f,
  layerGroup:f, divIcon:f, latLngBounds:function(){return{}}, control:{layers:f}, Browser:{} };
function faux(k){ return { getAttribute:function(a){ return a === 'data-stat' ? k : null; },
  setAttribute:function(){}, addEventListener:function(_, h){ BOUTONS[k] = h; },
  classList:{add:function(){},remove:function(){}}, style:{} }; }
var TOUS = ['confirme','libre','contacte','vu','inconnu','pris','__etoile'].map(faux);
var document = { getElementById:function(){ return faux('x'); },
  querySelectorAll:function(s){ return /stat-btn/.test(s) ? TOUS : []; },
  querySelector:function(){ return null; }, addEventListener:function(){},
  documentElement:{setAttribute:function(){}, getAttribute:function(){return null}} };
var window = { matchMedia:function(){return{matches:false, addEventListener:function(){}}},
  localStorage:{getItem:function(){return null}, setItem:function(){}} };
var localStorage = window.localStorage;
"""

VERIF = """
function att(q, eu, veut){ if (eu !== veut) console.log("ECHEC " + q + " : " + eu + " au lieu de " + veut); }
var N0 = ajoutes.size, TOT = %d, ET = %d, n = %s, ne = %s;
if (Object.keys(BOUTONS).length !== 7) console.log("ECHEC boutons cables : " + Object.keys(BOUTONS).length + " au lieu de 7");
function b(k){ BOUTONS[k](); }
b('pris');     att("masquer les pris", N0 - ajoutes.size, n.pris + ne.pris);
b('inconnu');  att("masquer aussi les a-appeler", N0 - ajoutes.size, n.pris + ne.pris + n.inconnu + ne.inconnu);
b('pris'); b('inconnu');
               att("tout retabli", ajoutes.size, N0);
b('__etoile'); att("etoiles seules", N0 - ajoutes.size, TOT - ET);
b('confirme'); att("etoiles hors confirmes", N0 - ajoutes.size, (TOT - ET) + ne.confirme * 2);
b('confirme'); b('__etoile');
               att("etat final identique a l'initial", ajoutes.size, N0);
"""


def _carte_tourne(doc):
    """Exécute le script de la carte sous Node avec un Leaflet bouchonné.

    Attrape la classe de bug qu'aucune vérification de texte ne voit : du code
    placé hors de la portée où vivent `map` et `COUCHES`. Le premier filtre par
    statut avait atterri après la fermeture de l'IIFE de la carte — page valide,
    boutons morts. On clique donc ici chaque bouton et on compte les points.
    """
    if not shutil.which("node"):
        return True  # pas de Node : on ne bloque pas la construction
    sc = re.findall(r"<script[^>]*>(.*?)</script>", doc, re.S)[-1]
    G = json.loads(re.search(r"var G = (\[.*?\]);\n", sc, re.S).group(1))
    n = collections.Counter(g["d"] for g in G)
    ne = collections.Counter(g["d"] for g in G if g.get("i"))
    essai = STUB + sc + VERIF % (len(G), sum(ne.values()),
                                 json.dumps(dict(n)), json.dumps({k: ne.get(k, 0) for k in n}))
    f = pathlib.Path(tempfile.gettempdir()) / "carte_smoke.js"
    f.write_text(essai, encoding="utf-8")
    r = subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=60)
    if r.returncode or "ECHEC" in r.stdout:
        print((r.stdout + r.stderr).strip()[-900:])
        return False
    return True


def _renvois_morts(doc):
    """Aucun lien du gisement ne doit pointer vers une fiche rangée ailleurs.

    Quand un gîte passe en hors budget ou aux écartés, sa fiche part mais les
    listes récapitulatives du gisement gardent parfois leur entrée — c'est arrivé
    à Ventaujols puis au Grand Brugeron. Le contrôle des doublons ne le voyait
    pas : il ne compare que les fiches entre elles, pas les liens.
    """
    ranges = set()
    for sid in ("horsbudget", "pris", "ecartes"):
        m = re.search(r'<section id="%s">.*?</section>' % sid, doc, re.S)
        if m:
            ranges |= set(re.findall(r'<li id="([^"]+)"', m.group(0)))
    m = re.search(r'<section id="gisement">.*?</section>', doc, re.S)
    if not m:
        return True
    gis = m.group(0)
    vises = set(re.findall(r'href="#([^"]+)"', gis))
    propres = set(re.findall(r'<li id="([^"]+)"', gis))
    morts = (vises & ranges) - propres
    if morts:
        print("      liens du gisement vers des fiches rangées ailleurs : " + ", ".join(sorted(morts)))
    return not morts


def _tels_en_double(doc):
    """Aucun numéro ne doit s'afficher deux fois dans la même fiche.

    Trois fois le même défaut : La Ferme des Pierres, le Grand Brugeron, puis Le
    Clos des Pommiers. À chaque fois j'ajoute un numéro relevé sur une source sans
    voir qu'il était déjà dans la ligne de sources de la fiche.

    On ne compte que ce qui est visible : les blocs <details> reproduisent
    l'annonce mot pour mot et un numéro y figure légitimement, même s'il est aussi
    dans la ligne de sources. Les sections d'analyse, où je commente sciemment
    quel numéro appeler, sont écartées aussi.
    """
    hors = ("pieges", "sources", "mail")
    zones = {}
    for sid in re.findall(r'<section id="([^"]+)"', doc):
        m = re.search(r'<section id="%s">.*?</section>' % sid, doc, re.S)
        if m and sid not in hors:
            zones[sid] = m.group(0)
    fautives = []
    for sid, sec in zones.items():
        bornes = [m.start() for m in re.finditer(r'<li id="[^"]+"', sec)] + [len(sec)]
        for i in range(len(bornes) - 1):
            bloc = sec[bornes[i]:bornes[i + 1]]
            a = re.match(r'<li id="([^"]+)"', bloc).group(1)
            # on écarte les citations verbatim et mes propres paragraphes d'analyse,
            # où nommer un numéro déjà listé est délibéré (« appelez celui-ci, pas la centrale »)
            visible = re.sub(r"<details.*?</details>", " ", bloc, flags=re.S)
            visible = re.sub(r'<p class="(?:flag|cite)">.*?</p>', " ", visible, flags=re.S)
            tels = [re.sub(r"\D", "", t) for t in re.findall(r"0[1-9](?:[ .]?\d{2}){4}", visible)]
            for t in set(tels):
                if tels.count(t) > 1:
                    fautives.append("%s (%s × %d)" % (a, t, tels.count(t)))
    if fautives:
        print("      numéros affichés deux fois dans une même fiche : " + ", ".join(sorted(set(fautives))[:8]))
    return not fautives


def verifier(doc):
    svg_pts = doc.count('class="pt-')
    ctrl = {
        "doctype": doc.startswith("<!doctype html>"),
        "head fermé une fois": doc.count("</head>") == 1,
        "body ouvert et fermé": doc.count("<body>") == 1 and doc.count("</body>") == 1,
        "style dans le head": doc.index("<style>") < doc.index("</head>"),
        "leaflet.css dans le head": 0 < doc.index('href="leaflet.css"') < doc.index("</head>"),
        "leaflet.js dans le body": doc.index('src="leaflet.js"') > doc.index("<body>"),
        "conteneur de carte": 'id="map"' in doc,
        "polices embarquées": doc.count("data:font/woff2;base64,") == 3,
        "aucun marqueur résiduel": not any(k in doc for k, _ in POLICES),
        "ancres uniques": len(set(re.findall(r'<li id="([a-z]+)"', doc))) == len(re.findall(r'<li id="[a-z]+"', doc)),
        "carte : un point par fiche listée": len(re.findall(r'"a"\s*:', doc))
            == len(set(re.findall(r'"a"\s*:\s*"([a-z0-9]+)"', doc))),
        "chaque point renvoie à une ancre existante": all(
            ('id="%s"' % a) in doc for a in re.findall(r'"a"\s*:\s*"([a-z0-9]+)"', doc)),
        "chaque fiche a un site ou l'absence documentée": all(
            any(d in m for d in (".fr", ".com", "pas de site officiel", "site hors ligne", "n'a pas de site"))
            for m in re.findall(r'<p class="meta">(.*?)</p>', doc, re.S)),
        "chaque fiche a un lien hors carte": all(
            any("google.com/maps" not in u for u in re.findall(r'href="([^"]+)"', m))
            for m in re.findall(r'<p class="meta">(.*?)</p>', doc, re.S)),
        "aucun gîte listé deux fois": not (
            _entrees(doc, "gisement")
            & (_entrees(doc, "horsbudget") | _entrees(doc, "pris") | _entrees(doc, "ecartes"))),
        "filtres de carte : les boutons masquent et rétablissent": _carte_tourne(doc),
        "aucun renvoi du gisement vers une fiche rangée ailleurs": _renvois_morts(doc),
        "aucun téléphone répété dans une même fiche": _tels_en_double(doc),
        "attribution OpenStreetMap": "OpenStreetMap" in doc,
        "repli sans JavaScript": "<noscript>" in doc,
    }
    for libelle, ok in ctrl.items():
        print(("  OK  " if ok else " ÉCHEC ") + libelle)
    return all(ctrl.values())


if __name__ == "__main__":
    doc, titre = construire()
    ok = verifier(doc)
    print(f"\n{SORTIE} — {len(doc.encode())/1024:.0f} Ko — « {titre} »")
    sys.exit(0 if ok else 1)
