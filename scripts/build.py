#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère le site statique Haïti Vérif à partir des fichiers JSON de data/."""

from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
OUTPUT = Path(__file__).resolve().parents[1] / "public"

VERDICT_SLUG = {
    "Faux": "faux",
    "Trompeur": "trompeur",
    "Non vérifié": "non-verifie",
    "Vrai": "vrai",
}

NAV = [
    ("index.html", "Accueil", "accueil"),
    ("index.html#verifications", "Vérifications", "verifications"),
    ("elections/index.html", "Élections", "elections"),
    ("faits.html", "Faits de référence", "faits"),
    ("chronologie.html", "Chronologie", "chrono"),
    ("comment-verifier.html", "Comment vérifier", "guide"),
    ("a-propos.html", "À propos", "apropos"),
]

MONTHS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

# Fuseau de l'utilisateur (America/Toronto, UTC−5 à cette date).
TZ_EASTERN = timezone(timedelta(hours=-5))


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def typo(text: str) -> str:
    """Apostrophes typographiques et espaces insécables avant : ; ! ?"""
    if not text:
        return text
    text = text.replace("'", "’")
    text = re.sub(r"[ \u00a0\u202f]*([;:!?])", "\u202f\\1", text)
    return text


def esc(text: str) -> str:
    return html.escape(typo(text), quote=True)


def href(from_depth: int, target: str, base_path: str = "") -> str:
    """Chemin relatif, compatible GitHub Pages (y compris sous-dossier de projet)."""
    prefix = "../" * from_depth if from_depth else ""
    if base_path:
        base = base_path.strip("/")
        if target.startswith("#"):
            return prefix + "index.html" + target if from_depth else target
        return f"/{base}/{target}" if not from_depth else prefix + target
    return prefix + target


def site_root(site: dict) -> str:
    """URL absolue du site, sans barre finale."""
    url = (site.get("site_url") or "").strip().rstrip("/")
    if url:
        return url
    base = (site.get("base_path") or "").strip("/")
    if base:
        return f"https://verif-ayiti.github.io/{base}"
    return ""


def abs_url(site: dict, target: str = "") -> str:
    """URL absolue d'une page (cible relative au site)."""
    root = site_root(site)
    target = (target or "").lstrip("/")
    if not root:
        return target
    return f"{root}/{target}" if target else f"{root}/"


def format_iso_date_display(iso: str) -> str:
    y, m, d = [int(x) for x in iso.split("-")]
    return f"{d} {MONTHS_FR[m]} {y}".replace("1 ", "1er ", 1) if d == 1 else f"{d} {MONTHS_FR[m]} {y}"


def sort_key(post: dict) -> tuple:
    """Plus récent d'abord : date de mise à jour, puis date, puis ordre du fichier."""
    updated = post.get("updated") or post.get("sort_date") or post.get("date") or "0000-01-01"
    published = post.get("sort_date") or post.get("date") or "0000-01-01"
    return (updated, published)


def rss_datetime(iso_date: str) -> str:
    y, m, d = [int(x) for x in iso_date.split("-")[:3]]
    dt = datetime(y, m, d, 8, 0, 0, tzinfo=TZ_EASTERN)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def badge(verdict: str, large: bool = False) -> str:
    slug = VERDICT_SLUG[verdict]
    cls = f"badge badge-{slug}" + (" badge-lg" if large else "")
    return f'<span class="{cls}">{esc(verdict)}</span>'


def layout(
    *,
    site: dict,
    title: str,
    description: str,
    depth: int,
    active: str,
    body: str,
    canonical: str | None = None,
    extra_head: str = "",
    page_path: str = "",
) -> str:
    home = href(depth, "index.html")
    css = href(depth, "css/style.css")
    rss = href(depth, "feed.xml")
    page_title = title if title == site["title"] else f"{title} — {site['title']}"
    canon = canonical or (abs_url(site, page_path) if page_path and site_root(site) else "")

    nav_items = []
    # Sur mobile, le menu est dans un <details>.
    for target, label, key in NAV:
        url = href(depth, target)
        current = ' aria-current="page"' if key == active and not target.endswith("#verifications") else ""
        nav_items.append(f'<li><a href="{url}"{current}>{esc(label)}</a></li>')
    nav_html = "<ul>\n" + "\n".join(nav_items) + "\n</ul>"

    return f"""<!DOCTYPE html>
<html lang="fr-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="author" content="{esc(site['title'])}">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="{esc(page_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="fr_CA">
  <link rel="stylesheet" href="{css}">
  <link rel="alternate" type="application/rss+xml" title="{esc(site['full_title'])}" href="{rss}">
  {f'<link rel="canonical" href="{html.escape(canon, quote=True)}">' if canon else ''}
  {f'<meta property="og:url" content="{html.escape(canon, quote=True)}">' if canon else ''}
  {extra_head}
</head>
<body>
  <a class="skip-link" href="#contenu">Aller au contenu</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{home}">
        <span class="brand-name">{esc(site['title'])}</span>
        <span class="brand-tagline">{esc(site['tagline'])}</span>
      </a>
      <details class="nav-toggle">
        <summary>Menu</summary>
        <nav class="site-nav" aria-label="Navigation principale">{nav_html}</nav>
      </details>
      <nav class="site-nav" aria-label="Navigation principale">{nav_html}</nav>
    </div>
  </header>
  <main id="contenu">
    <div class="wrap">
{body}
    </div>
  </main>
  <footer class="site-footer">
    <div class="footer-inner">
      <p>{esc(site['title'])} — vérification indépendante des faits, à jour le {esc(site['updated_display'])}.</p>
      <p>
        <a href="{href(depth, 'a-propos.html')}">À propos et méthode</a>
        · <a class="rss-link" href="{rss}">Fil RSS</a>
      </p>
    </div>
  </footer>
<script data-goatcounter="https://verif-haiti.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""


def section_tag(post: dict) -> str:
    if post.get("section") == "elections":
        return '<span class="section-tag">Élections</span>'
    return ""


def render_home(site, posts, retenir) -> str:
    counts = {k: 0 for k in VERDICT_SLUG}
    for p in posts:
        counts[p["verdict"]] += 1

    filters = [
        ("tous", "Tous", len(posts)),
        ("Faux", "Faux", counts["Faux"]),
        ("Trompeur", "Trompeur", counts["Trompeur"]),
        ("Non vérifié", "Non vérifié", counts["Non vérifié"]),
        ("Vrai", "Vrai", counts["Vrai"]),
    ]
    btns = []
    for value, label, n in filters:
        pressed = "true" if value == "tous" else "false"
        btns.append(
            f'<button type="button" class="filter-btn" data-filter="{html.escape(value)}" aria-pressed="{pressed}">{esc(label)} <span class="count">({n})</span></button>'
        )

    cards = []
    for p in posts:
        url = href(0, f"articles/{p['slug']}.html")
        updated_label = p.get("date_display") or format_iso_date_display(p["date"])
        if p.get("updated_display") and p.get("updated") and p["updated"] != p.get("date"):
            updated_label = f"Mis à jour le {p['updated_display']}"
        elif p.get("updated") and p.get("date") and p["updated"] != p["date"] and p.get("updated_display"):
            updated_label = f"Mis à jour le {p['updated_display']}"
        cards.append(
            f"""<li class="card" data-verdict="{html.escape(p['verdict'])}">
  <div class="card-top">{badge(p['verdict'])}{section_tag(p)}<time class="date" datetime="{html.escape(p.get('updated') or p['date'])}">{esc(updated_label)}</time></div>
  <h2><a href="{url}">{esc(p['title'])}</a></h2>
  <p class="card-circ">Où ça circule&nbsp;: {esc(p['circulated'])}</p>
  <a class="card-more" href="{url}">Lire la vérification</a>
</li>"""
        )

    warning = (
        f'<p class="warning-note">{esc(site["frg_warning"])} '
        f'<a href="{html.escape(site["frg_warning_url"])}" rel="noopener noreferrer">Source&nbsp;: Amitié FM</a></p>'
    )

    body = f"""
      <header class="page-header">
        <h1>{esc(site['full_title'])}</h1>
        <p class="lede">{esc(site['description'])}</p>
        <p class="meta-line">À jour le {esc(site['updated_display'])} · {len(posts)} vérifications</p>
      </header>

      <section id="verifications" aria-labelledby="verif-titre">
        <header class="page-header">
          <h2 id="verif-titre" style="font-family:var(--font-serif);font-size:1.5rem;margin:0 0 0.4rem;">Rumeurs vérifiées</h2>
          <p class="lede">Verdicts&nbsp;: Faux, Trompeur, Non vérifié, Vrai. Bilan au {esc(site['updated_display'])}. Les articles les plus récemment mis à jour apparaissent en premier.</p>
        </header>
        <div class="toolbar" role="toolbar" aria-label="Filtrer par verdict">
          <span class="toolbar-label">Filtrer&nbsp;:</span>
          {''.join(btns)}
        </div>
        <p id="filter-empty">Aucune vérification pour ce filtre.</p>
        <ul class="card-list" id="article-list">
          {''.join(cards)}
        </ul>
        {warning}
      </section>
      <script src="{href(0, 'js/filters.js')}" defer></script>
"""
    return layout(
        site=site,
        title=site["title"],
        description=site["description"],
        depth=0,
        active="accueil",
        body=body,
        page_path="/",
    )


def source_items(sources: list, depth: int) -> str:
    items = []
    for s in sources:
        title = s.get("title") or s["href"]
        meta_parts = [p for p in (s.get("site"), s.get("date")) if p]
        meta = f'<span class="source-meta">{esc(" · ".join(meta_parts))}</span>' if meta_parts else ""
        items.append(
            f'<li><a href="{html.escape(s["href"])}" rel="noopener noreferrer">{esc(title)}</a>{meta}</li>'
        )
    return "<ul class=\"source-list\">\n" + "\n".join(items) + "\n</ul>"


def render_article(site, post, prev_post, next_post) -> str:
    date_label = post.get("date_display") or format_iso_date_display(post["date"])
    time_attr = post.get("date") or site["updated"]
    updated_html = ""
    if post.get("updated") and post.get("updated_display") and post["updated"] != post.get("date"):
        updated_html = (
            f' · Mis à jour le <time datetime="{html.escape(post["updated"])}">{esc(post["updated_display"])}</time>'
        )
    date_note = ""
    if post.get("date_note"):
        date_note = f'<p class="date-note">{esc(post["date_note"])}</p>'

    pager_parts = []
    if prev_post:
        pager_parts.append(
            f'<a class="prev" href="{href(1, "articles/" + prev_post["slug"] + ".html")}">← {esc(prev_post["title"])}</a>'
        )
    if next_post:
        pager_parts.append(
            f'<a class="next" href="{href(1, "articles/" + next_post["slug"] + ".html")}">{esc(next_post["title"])} →</a>'
        )
    pager = f'<nav class="pager" aria-label="Articles voisins">{"".join(pager_parts)}</nav>' if pager_parts else ""
    elections_back = ""
    if post.get("section") == "elections":
        elections_back = (
            f'<p class="warning-note">Cette fiche fait partie de la section <a href="{href(1, "elections/index.html")}">Élections</a>. '
            f'Voir aussi le <a href="{href(1, "elections/calendrier.html")}">calendrier officiel</a> et les '
            f'<a href="{href(1, "elections/candidats.html")}">inscriptions publiées par le CEP</a>.</p>'
        )

    body = f"""
      <article class="article-page">
        <div class="article-kicker">
          {badge(post['verdict'], large=True)}{section_tag(post)}
          <p class="meta-line" style="margin:0;">
            <time datetime="{html.escape(time_attr)}">{esc(date_label)}</time>{updated_html}
          </p>
        </div>
        <h1>{esc(post['title'])}</h1>
        {date_note}

        <section class="fact-block">
          <h2>Affirmation</h2>
          <p>{esc(post['claim'])}</p>
        </section>

        <section class="fact-block">
          <h2>Où elle circule</h2>
          <p>{esc(post['circulated'])}</p>
        </section>

        <section class="fact-block">
          <h2>Faits vérifiés</h2>
          <p>{esc(post['facts'])}</p>
        </section>

        <section class="fact-block">
          <h2>Sources</h2>
          {source_items(post['sources'], 1)}
        </section>

        {elections_back}
        {pager}
      </article>
"""
    desc = f"Verdict : {post['verdict']}. {post['claim']}"
    return layout(
        site=site,
        title=post["title"],
        description=desc[:220],
        depth=1,
        active="elections" if post.get("section") == "elections" else "verifications",
        body=body,
        page_path=f"articles/{post['slug']}.html",
    )


def render_faits(site, faits) -> str:
    props = []
    for item in faits["items"]:
        props.append(
            f"<div class=\"prop\"><dt>{esc(item['label'])}</dt><dd>{esc(item['value'])}</dd></div>"
        )
    body = f"""
      <header class="page-header">
        <h1>Faits de référence</h1>
        <p class="lede">{esc(faits['intro'])}</p>
      </header>
      <dl class="props">
        {''.join(props)}
      </dl>
      <p class="warning-note">{esc(site['effectifs_note'])}</p>
"""
    return layout(
        site=site,
        title="Faits de référence",
        description=faits["intro"],
        depth=0,
        active="faits",
        body=body,
        page_path="faits.html",
    )


def render_chrono(site, chrono) -> str:
    items = []
    for ev in chrono["events"]:
        items.append(
            f'<li><span class="t-date">{esc(ev["date"])}</span><p>{esc(ev["event"])}</p></li>'
        )
    body = f"""
      <header class="page-header">
        <h1>Chronologie</h1>
        <p class="lede">{esc(chrono['intro'])}</p>
      </header>
      <ol class="timeline">
        {''.join(items)}
      </ol>
"""
    return layout(
        site=site,
        title="Chronologie",
        description=chrono["intro"],
        depth=0,
        active="chrono",
        body=body,
        page_path="chronologie.html",
    )


def render_guide(site, guide) -> str:
    steps = []
    for s in guide["steps"]:
        steps.append(f"<li><h2>{esc(s['title'])}</h2><p>{esc(s['detail'])}</p></li>")
    body = f"""
      <header class="page-header">
        <h1>Comment vérifier soi-même</h1>
        <p class="lede">{esc(guide['intro'])}</p>
      </header>
      <ol class="steps">
        {''.join(steps)}
      </ol>
"""
    return layout(
        site=site,
        title="Comment vérifier soi-même",
        description=guide["intro"],
        depth=0,
        active="guide",
        body=body,
        page_path="comment-verifier.html",
    )


def render_apropos(site, sources, n_posts: int) -> str:
    # Textes de méthode rédigés à partir des pratiques déjà décrites dans la page source
    # (verdicts, « Non vérifié n’est pas faux », distinction FRG / forces bilatérales,
    # citation des sources, mise en garde sur les effectifs). Aucun fait nouveau sur les opérations.
    catalog = []
    for s in sources["links"]:
        meta_parts = [p for p in (s.get("site"), s.get("date")) if p]
        meta = f'<span class="source-meta">{esc(" · ".join(meta_parts))}</span>' if meta_parts else ""
        catalog.append(
            f'<li><a href="{html.escape(s["href"])}" rel="noopener noreferrer">{esc(s["title"])}</a>{meta}</li>'
        )

    body = f"""
      <article class="prose">
        <header class="page-header">
          <h1>À propos</h1>
          <p class="lede">{esc(site['full_title'])}. Site à jour le {esc(site['updated_display'])}.</p>
        </header>

        <h2>Indépendance</h2>
        <p>Ce blog rassemble des vérifications de faits sur les rumeurs qui circulent au sujet de la Force de répression des gangs (FRG, en anglais Gang Suppression Force, GSF), de l’ex-mission MSS dirigée par le Kenya, et des déploiements étrangers connexes en Haïti, notamment le déploiement salvadorien de la fin octobre 2026.</p>
        <p>Il n’est affilié ni à la FRG, ni à l’Organisation des Nations Unies, ni au gouvernement haïtien, ni au gouvernement salvadorien, ni à un parti politique. Son objet est de documenter les affirmations en circulation et de les comparer aux sources officielles et aux médias fiables déjà cités.</p>

        <p>Depuis le 15 novembre 2026, une section <a href="{href(0, 'elections/index.html')}">Élections</a> applique la même méthode aux rumeurs sur les élections prévues en 2027. Elle s’appuie d’abord sur les publications officielles du Conseil électoral provisoire (CEP) et ne prend parti pour aucun candidat ni aucune structure politique.</p>

        <h2>Méthode</h2>
        <p>Chaque fiche porte sur une affirmation précise. La méthode est la suivante&nbsp;:</p>
        <ul>
          <li>relever l’affirmation et le lieu où elle circule (réseaux sociaux, sites, déclarations)&nbsp;;</li>
          <li>la comparer aux communiqués officiels (FRG, ONU, Police nationale d’Haïti, gouvernements concernés) et à des médias fiables (notamment AFP Factuel, Reuters, AP, Le Nouvelliste)&nbsp;;</li>
          <li>attribuer un verdict, daté, et citer les sources pour que chacun puisse vérifier&nbsp;;</li>
          <li>n’ajouter aucun fait qui ne figure pas dans les sources utilisées.</li>
        </ul>
        <p>Comme le rappelle le <a href="{href(0, 'comment-verifier.html')}">guide de vérification</a>, une vidéo choc sans date ni lieu est le format le plus souvent détourné. Il faut aussi distinguer la FRG des forces déployées dans un cadre bilatéral&nbsp;: tout soldat étranger en Haïti n’est pas forcément sous mandat de l’ONU. Les chiffres d’effectifs changent vite&nbsp;; il faut vérifier la date de chaque source avant de les citer.</p>
        <p>Le présent site compte {n_posts} fiches, correspondant chacune à une affirmation déjà examinée dans la page de référence à jour au {esc(site['updated_display'])}.</p>

        <h2>Signification des verdicts</h2>
        <ul>
          <li><strong>Vrai</strong>&nbsp;: l’affirmation est confirmée par les autorités officielles compétentes.</li>
          <li><strong>Faux</strong>&nbsp;: l’affirmation est contredite par des faits vérifiés (par exemple une vidéo tournée dans un autre pays, ou une assertion infirmée par des sources officielles).</li>
          <li><strong>Trompeur</strong>&nbsp;: l’affirmation contient un élément de vrai, mais elle induit en erreur (mauvaise attribution, chiffres confondus, cadrage incomplet).</li>
          <li><strong>Non vérifié</strong>&nbsp;: l’affirmation n’est confirmée, à la date indiquée, ni par une source officielle ni par un média fiable. «&nbsp;Non vérifié&nbsp;» n’est pas «&nbsp;faux&nbsp;»&nbsp;: c’est une invitation à attendre.</li>
        </ul>

        <h2>Sources</h2>
        <p>{esc(sources['intro'])} Les liens ci-dessous sont ceux de la page de référence. Chaque article cite aussi la ou les sources qui concernent précisément l’affirmation examinée.</p>
        <ul class="catalog">
          {''.join(catalog)}
        </ul>

        <h2>Politique de correction</h2>
        <p>Les erreurs matérielles sont corrigées dès qu’elles sont constatées, avec une mention datée dans l’article concerné. Les changements de verdict (par exemple de «&nbsp;Non vérifié&nbsp;» à «&nbsp;Trompeur&nbsp;») et les compléments d’information sont datés, comme les mentions «&nbsp;Ajout&nbsp;» et «&nbsp;Mise à jour&nbsp;» des fiches d’origine. Une affirmation reste «&nbsp;Non vérifié&nbsp;» tant qu’aucune source officielle ou média fiable ne la confirme ou ne l’infirme.</p>
        <p>{esc(site['frg_warning'])} <a href="{html.escape(site['frg_warning_url'])}" rel="noopener noreferrer">Source&nbsp;: Amitié FM</a></p>
      </article>
"""
    return layout(
        site=site,
        title="À propos",
        description="Indépendance, méthode, sources et politique de correction de Haïti Vérif.",
        depth=0,
        active="apropos",
        body=body,
        page_path="a-propos.html",
    )


# ---------------------------------------------------------------------------
# Section Élections
# ---------------------------------------------------------------------------

def elections_subnav(active: str) -> str:
    items = [
        ("elections/index.html", "Vue d'ensemble", "home"),
        ("elections/candidats.html", "Inscriptions à la présidence", "candidats"),
        ("elections/calendrier.html", "Calendrier officiel", "calendrier"),
    ]
    links = []
    for target, label, key in items:
        cur = ' aria-current="page"' if key == active else ""
        links.append(f'<a href="{href(1, target)}"{cur}>{esc(label)}</a>')
    return '<nav class="subnav" aria-label="Section Élections">' + " ".join(links) + "</nav>"


def elections_notice(faits, cand) -> str:
    return f"""<section class="callout callout-alert" aria-labelledby="avis-cep">
        <p class="callout-lead" id="avis-cep">{esc(faits['avertissement_titre'])}</p>
        <p>{esc(faits['avertissement'])}</p>
        <p class="meta-line" style="margin-top:0.6rem;">Relevé du tableau du CEP&nbsp;: {esc(cand['snapshot_display'])}. {esc(cand['snapshot_note'])}</p>
      </section>"""


def elections_verifier_box(faits) -> str:
    items = []
    for v in faits["verifier"]:
        items.append(
            f'<li><a href="{html.escape(v["href"])}" rel="noopener noreferrer">{esc(v["label"])}</a>'
            f'<span class="source-meta">{esc(v["detail"])}</span></li>'
        )
    tips = "".join(f"<li>{esc(t)}</li>" for t in faits["conseils"])
    return f"""<section class="fact-block" aria-labelledby="verifier-elec">
        <h2 id="verifier-elec">{esc(faits['verifier_titre'])}</h2>
        <ul class="source-list">{''.join(items)}</ul>
        <ul class="tips">{tips}</ul>
      </section>"""


def render_elections_home(site, faits, cal, cand, posts) -> str:
    milestones = []
    for m in cal["prochaines"]:
        milestones.append(
            f'<li><span class="t-date">{esc(format_iso_date_display(m["date"]))}</span><p>{esc(m["label"])}</p></li>'
        )
    rows = []
    for x in cand["postes"]:
        rows.append(
            f'<tr><td>{esc(x["poste"])}</td><td class="num">{x["inscrits"]:,}</td></tr>'.replace(",", "\u202f")
        )
    total = f"{cand['total_tableau']:,}".replace(",", "\u202f")
    cards = []
    for p in posts:
        url = href(1, f"articles/{p['slug']}.html")
        cards.append(
            f"""<li class="card" data-verdict="{html.escape(p['verdict'])}">
  <div class="card-top">{badge(p['verdict'])}<time class="date" datetime="{html.escape(p.get('updated') or p['date'])}">{esc(p.get('date_display') or format_iso_date_display(p['date']))}</time></div>
  <h2><a href="{url}">{esc(p['title'])}</a></h2>
  <p class="card-circ">Où ça circule&nbsp;: {esc(p['circulated'])}</p>
  <a class="card-more" href="{url}">Lire la vérification</a>
</li>"""
        )
    body = f"""
      <header class="page-header">
        <h1>Élections en Haïti 2026-2027</h1>
        <p class="lede">{esc(faits['intro'])}</p>
        {elections_subnav('home')}
      </header>

      {elections_notice(faits, cand)}

      <section class="fact-block" aria-labelledby="dates-cles">
        <h2 id="dates-cles">Dates clés du calendrier officiel</h2>
        <p>Selon le <a href="{html.escape(cal['source_pdf'])}" rel="noopener noreferrer">calendrier électoral actualisé</a> publié par le CEP le 28 octobre 2026&nbsp;:</p>
        <ol class="timeline">{''.join(milestones)}</ol>
        <p><a href="{href(1, 'elections/calendrier.html')}">Voir le calendrier complet et les reports successifs</a></p>
      </section>

      <section class="fact-block" aria-labelledby="inscrits">
        <h2 id="inscrits">Inscriptions en ligne par poste</h2>
        <p>Chiffres du <a href="{html.escape(cand['source_tableau'])}" rel="noopener noreferrer">tableau public du CEP</a>, relevés le {esc(cand['snapshot_display'])}. Ce sont des inscriptions en ligne, pas des candidatures acceptées.</p>
        <table class="data-table">
          <thead><tr><th scope="col">Poste</th><th scope="col" class="num">Inscriptions en ligne</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
          <tfoot><tr><th scope="row">Total</th><td class="num">{total}</td></tr></tfoot>
        </table>
        <p class="meta-line">Pour les postes de maire, CASEC et ASEC (collectivités territoriales), l'inscription en ligne se poursuit jusqu'au 30 novembre 2026. <a href="{href(1, 'elections/candidats.html')}">Voir les inscriptions à la présidence</a></p>
      </section>

      <section aria-labelledby="verif-elec">
        <h2 id="verif-elec" style="font-family:var(--font-serif);font-size:1.5rem;margin:1.5rem 0 0.6rem;">Rumeurs électorales vérifiées</h2>
        <ul class="card-list">
          {''.join(cards)}
        </ul>
      </section>

      {elections_verifier_box(faits)}
"""
    return layout(
        site=site,
        title="Élections",
        description="Calendrier officiel, inscriptions publiées par le CEP et rumeurs vérifiées sur les élections en Haïti 2026-2027.",
        depth=1,
        active="elections",
        body=body,
        page_path="elections/index.html",
    )


def render_elections_candidats(site, faits, cand) -> str:
    rows = []
    for i, c in enumerate(cand["president"], 1):
        rows.append(
            f"<tr><td class=\"num\">{i}</td><td>{html.escape(c['nom'])}</td><td>{html.escape(c['prenom'])}</td>"
            f"<td>{html.escape(c['structure'])}</td><td>{esc(cand['statut_affiche'])}</td></tr>"
        )
    pres = next((x for x in cand["postes"] if x["poste"] == "Président"), None)
    count = pres["inscrits"] if pres else len(cand["president"])
    body = f"""
      <header class="page-header">
        <h1>Inscriptions en ligne à la présidence</h1>
        <p class="lede">Liste des {len(cand['president'])} inscriptions en ligne au poste de président, telle que publiée par le Conseil électoral provisoire (CEP), classée par ordre alphabétique. Les noms et les sigles des structures politiques sont reproduits tels que le CEP les publie.</p>
        {elections_subnav('candidats')}
      </header>

      {elections_notice(faits, cand)}

      <div class="table-wrap">
        <table class="data-table">
          <caption>Inscriptions en ligne au poste de président (tableau du CEP, relevé du {esc(cand['snapshot_display'])}, {count} inscriptions)</caption>
          <thead><tr><th scope="col" class="num">#</th><th scope="col">Nom</th><th scope="col">Prénom(s)</th><th scope="col">Structure (sigle publié par le CEP)</th><th scope="col">Statut</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>

      <section class="fact-block">
        <h2>Source</h2>
        <ul class="source-list">
          <li><a href="{html.escape(cand['source_tableau'])}" rel="noopener noreferrer">Tableau public des inscriptions en ligne du CEP</a><span class="source-meta">tableau.cephaiti.ht · relevé du {esc(cand['snapshot_display'])}</span></li>
          <li><a href="{html.escape(cand['source_api'])}" rel="noopener noreferrer">Données brutes du tableau (poste&nbsp;: Président)</a><span class="source-meta">tableau.cephaiti.ht</span></li>
        </ul>
        <p>Avis du CEP sur ce tableau&nbsp;: «&nbsp;{esc(cand['avis_cep'])}&nbsp;»</p>
        <p>Ce blog ne publie pas de biographie ni de commentaire sur les personnes inscrites. Il mettra cette page à jour après la publication de la liste préliminaire (prévue le 15 décembre 2026) et de la liste définitive (prévue le 11 janvier 2027).</p>
      </section>
"""
    return layout(
        site=site,
        title="Inscriptions en ligne à la présidence",
        description="Liste des inscriptions en ligne au poste de président publiée par le CEP, strictement préliminaire et non validée.",
        depth=1,
        active="elections",
        body=body,
        page_path="elections/candidats.html",
    )


def render_elections_calendrier(site, faits, cal) -> str:
    rows = []
    for e in cal["echeances"]:
        if e["debut"] == e["fin"]:
            when = format_iso_date_display(e["debut"])
        else:
            when = f"Du {format_iso_date_display(e['debut'])} au {format_iso_date_display(e['fin'])}"
        rows.append(
            f'<tr><td class="num">{esc(e["ref"])}</td><td>{esc(e["activite"])}</td><td>{esc(when)}</td></tr>'
        )
    reps = []
    for r in cal["reports"]:
        reps.append(
            f'<li><span class="t-date">{esc(format_iso_date_display(r["date_publication"]))} · {esc(r["statut"])}</span>'
            f'<p><a href="{html.escape(r["href"])}" rel="noopener noreferrer">{esc(r["titre"])}</a>&nbsp;: {esc(r["resume"])}</p></li>'
        )
    body = f"""
      <header class="page-header">
        <h1>Calendrier électoral officiel 2026-2027</h1>
        <p class="lede">{esc(cal['intro'])}</p>
        {elections_subnav('calendrier')}
      </header>

      <div class="table-wrap">
        <table class="data-table">
          <caption>Échéances principales du calendrier actualisé (CEP, 28 octobre 2026), par ordre chronologique</caption>
          <thead><tr><th scope="col" class="num">Étape</th><th scope="col">Activité</th><th scope="col">Date</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      <p class="meta-line">Sources&nbsp;: <a href="{html.escape(cal['source_pdf'])}" rel="noopener noreferrer">calendrier actualisé 2026-2027 (PDF)</a> · <a href="{html.escape(cal['source_annonce'])}" rel="noopener noreferrer">annonce du CEP</a> · <a href="{html.escape(cal['source_note'])}" rel="noopener noreferrer">note de presse CEP/DC/081-2526 (PDF)</a>. Le calendrier prévoit aussi des étapes pour le vote des Haïtiens vivant à l'étranger (étape 21) : consulter le PDF.</p>

      <section class="callout" aria-labelledby="reports">
        <p class="callout-lead" id="reports">Reports successifs</p>
        <p>{esc(cal['reports_intro'])}</p>
        <ol class="timeline" style="margin-top:0.8rem;">{''.join(reps)}</ol>
      </section>

      {elections_verifier_box(faits)}
"""
    return layout(
        site=site,
        title="Calendrier électoral officiel",
        description="Calendrier électoral actualisé 2026-2027 du CEP et reports successifs des élections en Haïti.",
        depth=1,
        active="elections",
        body=body,
        page_path="elections/calendrier.html",
    )


def render_404(site) -> str:
    body = f"""
      <header class="page-header center-msg">
        <h1>Page introuvable</h1>
        <p class="lede">Cette adresse ne correspond à aucune page du site. Retourner à <a href="{href(0, 'index.html')}">l’accueil</a> ou consulter les <a href="{href(0, 'index.html#verifications')}">vérifications</a>.</p>
      </header>
"""
    return layout(
        site=site,
        title="Page introuvable",
        description="Cette page n’existe pas.",
        depth=0,
        active="",
        body=body,
        page_path="404.html",
    )


def render_rss(site, posts) -> str:
    items = []
    root = site_root(site)
    home = abs_url(site, "") if root else "index.html"
    feed = abs_url(site, "feed.xml") if root else "feed.xml"
    for p in posts:
        link_path = f"articles/{p['slug']}.html"
        link = abs_url(site, link_path) if root else link_path
        pub = rss_datetime(p.get("updated") or p["date"])
        facts = typo(p["facts"])
        claim = typo(p["claim"])
        desc = (
            f"<p><strong>Verdict : {xml_escape(p['verdict'])}</strong></p>"
            f"<p><strong>Affirmation :</strong> {xml_escape(claim)}</p>"
            f"<p><strong>Où elle circule :</strong> {xml_escape(typo(p['circulated']))}</p>"
            f"<p><strong>Faits vérifiés :</strong> {xml_escape(facts)}</p>"
        )
        guid_perm = "true" if root else "false"
        guid = link if root else p["slug"]
        items.append(
            f"""    <item>
      <title>{xml_escape(typo(p['title']))}</title>
      <link>{xml_escape(link)}</link>
      <guid isPermaLink="{guid_perm}">{xml_escape(guid)}</guid>
      <pubDate>{pub}</pubDate>
      <category>{xml_escape(p['verdict'])}</category>{"<category>Élections</category>" if p.get("section") == "elections" else ""}
      <description><![CDATA[{desc}]]></description>
    </item>"""
        )
    built = datetime.now(TZ_EASTERN).strftime("%a, %d %b %Y %H:%M:%S %z")
    atom = (
        f'\n    <atom:link href="{xml_escape(feed)}" rel="self" type="application/rss+xml" />'
        if root
        else ""
    )
    ns = ' xmlns:atom="http://www.w3.org/2005/Atom"' if root else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"{ns}>
  <channel>
    <title>{xml_escape(typo(site['full_title']))}</title>
    <link>{xml_escape(home)}</link>{atom}
    <description>{xml_escape(typo(site['description']))}</description>
    <language>fr-ca</language>
    <lastBuildDate>{built}</lastBuildDate>
    <ttl>1440</ttl>
{chr(10).join(items)}
  </channel>
</rss>
"""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    site = load("site.json")
    posts = load("posts.json")["posts"]
    el_posts = load("elections/posts.json")["posts"]
    for ep in el_posts:
        ep["section"] = "elections"
    posts = posts + el_posts
    el_cand = load("elections/candidats.json")
    el_cal = load("elections/calendrier.json")
    el_faits = load("elections/faits_elections.json")
    faits = load("faits.json")
    chrono = load("chronologie.json")
    guide = load("guide.json")
    sources = load("sources.json")
    retenir = load("retenir.json")

    posts_sorted = sorted(
        posts,
        key=lambda p: (sort_key(p)[0], sort_key(p)[1], -int(p.get("order", 0))),
        reverse=True,
    )

    write(OUTPUT / "index.html", render_home(site, posts_sorted, retenir))
    write(OUTPUT / "faits.html", render_faits(site, faits))
    write(OUTPUT / "chronologie.html", render_chrono(site, chrono))
    write(OUTPUT / "comment-verifier.html", render_guide(site, guide))
    write(OUTPUT / "a-propos.html", render_apropos(site, sources, len(posts)))
    write(OUTPUT / "404.html", render_404(site))
    write(OUTPUT / "feed.xml", render_rss(site, posts_sorted))

    el_sorted = [p for p in posts_sorted if p.get("section") == "elections"]
    write(OUTPUT / "elections" / "index.html", render_elections_home(site, el_faits, el_cal, el_cand, el_sorted))
    write(OUTPUT / "elections" / "candidats.html", render_elections_candidats(site, el_faits, el_cand))
    write(OUTPUT / "elections" / "calendrier.html", render_elections_calendrier(site, el_faits, el_cal))

    (OUTPUT / "articles").mkdir(parents=True, exist_ok=True)
    for i, post in enumerate(posts_sorted):
        prev_post = posts_sorted[i - 1] if i > 0 else None
        next_post = posts_sorted[i + 1] if i + 1 < len(posts_sorted) else None
        # pager: previous = plus récent, next = plus ancien? Usually prev = older or next in list.
        # "voisin" : précédent dans la liste (plus récent) / suivant (plus ancien).
        write(
            OUTPUT / "articles" / f"{post['slug']}.html",
            render_article(site, post, prev_post, next_post),
        )

    css_dir = OUTPUT / "css"
    js_dir = OUTPUT / "js"
    css_dir.mkdir()
    js_dir.mkdir()
    shutil.copyfile(ASSETS / "style.css", css_dir / "style.css")
    shutil.copyfile(ASSETS / "filters.js", js_dir / "filters.js")

    # GitHub Pages : ne pas faire traiter le site par Jekyll.
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")

    # robots.txt
    sitemap_ref = abs_url(site, "sitemap.xml") if site_root(site) else "sitemap.xml"
    (OUTPUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {sitemap_ref}\n",
        encoding="utf-8",
    )

    pages = [
        "index.html",
        "faits.html",
        "chronologie.html",
        "comment-verifier.html",
        "a-propos.html",
        "feed.xml",
        "elections/index.html",
        "elections/candidats.html",
        "elections/calendrier.html",
    ] + [f"articles/{p['slug']}.html" for p in posts_sorted]
    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    for p in pages:
        loc = abs_url(site, p) if site_root(site) else p
        sitemap += f"  <url><loc>{xml_escape(loc)}</loc><lastmod>{site['updated']}</lastmod></url>\n"
    sitemap += "</urlset>\n"
    (OUTPUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"Site généré dans {OUTPUT}")
    print(f"{len(posts_sorted)} articles, {len(pages)} URL dans le plan du site.")


if __name__ == "__main__":
    build()
