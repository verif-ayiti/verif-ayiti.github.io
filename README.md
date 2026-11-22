# Haïti Vérif

Blog statique en français (fr-CA) de vérification des faits sur la Force de répression des gangs (FRG/GSF) et les rumeurs liées aux opérations en Haïti.

Le contenu est tiré uniquement de la page de référence à jour au 15 novembre 2026. Aucun fait n’y est ajouté.

## Dossier

`/workspace/blog-haiti`

- `data/` — fichiers JSON (articles, faits, chronologie, guide, sources)
- `scripts/build.py` — générateur HTML/CSS
- `assets/` — feuille de style et script de filtre
- `public/` — site généré, prêt à être publié sur GitHub Pages ou Netlify

## Reconstruire le site

```bash
cd /workspace/blog-haiti
python3 scripts/build.py
```

Pour une mise à jour quotidienne : modifier ou ajouter une fiche dans `data/posts.json` (puis, au besoin, `chronologie.json`, `faits.json` ou `sources.json`), puis relancer la commande ci-dessus.

## Prévisualiser en local

```bash
python3 -m http.server 8080 --directory public
```

Puis ouvrir <http://127.0.0.1:8080/>.

## Publication

Le site est publié sur GitHub Pages : <https://verif-ayiti.github.io/>

Le dépôt est [verif-ayiti/verif-ayiti.github.io](https://github.com/verif-ayiti/verif-ayiti.github.io). Chaque poussée sur `main` lance le flux `.github/workflows/pages.yml`, qui régénère le site (`python3 scripts/build.py`) et le déploie. L’URL de base est définie dans `data/site.json` (`site_url`). Le site est publié à la racine du domaine (`base_path` est vide). Les liens internes restent relatifs ; le fil RSS, le plan du site et `robots.txt` utilisent des URL absolues. L’ancienne adresse <https://lund2026.github.io/verif-haiti/> redirige vers ce site.

- **Netlify** (solution de rechange) : pointer le dépôt sur ce dossier et laisser `netlify.toml` publier le répertoire `public`.

## Structure des pages

- Accueil : liste des articles, du plus récemment mis à jour au plus ancien
- Une page par affirmation vérifiée (verdict, affirmation, circulation, faits, sources, date)
- Faits de référence
- Chronologie
- Comment vérifier
- À propos (indépendance, méthode, sources, corrections)
- Fil RSS : `public/feed.xml`
