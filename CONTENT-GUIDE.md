# Content Guide

This is a static GitHub Pages site. HTML defines page structure, `assets/css/site.css` defines presentation, `assets/js/site.js` loads content, and editable text/data lives in `content/*.json`.

## One-Click Website Update

The normal local maintenance workflow is:

1. Add or remove Photography photos if needed.
2. Add or remove Aviation Photography photos if needed.
3. Add or edit publication metadata and publication assets if needed.
4. Add new actual flights inside the Flight Log project if needed.
5. Double-click:

```text
Update Website.command
```

The updater synchronizes Photography, synchronizes Aviation Photography, validates Publications, exports Flight Log data, and validates structured content.

It does not publish the website. It does not run `git add`, `git commit`, `git push`, merge branches, or deploy GitHub Pages.

## Homepage Text

Edit `content/site.json`.

- `profile.heroName` controls the large English name.
- `profile.chineseName` controls the homepage Chinese name. Keep the Traditional Chinese spelling: `楊翥成`.
- `profile.subtitle` controls the line below the name.
- `profile.intro` controls the short hero introduction.
- `homeCards` controls the five homepage entry cards.

## Homepage Portrait

Put the portrait image in `assets/images/Myself/` and update:

```json
"portrait": {
  "src": "assets/images/Myself/DSC08674.jpg",
  "alt": "Portrait of Zhucheng Yang"
}
```

The portrait is shown uncropped with natural proportional sizing and original source color. CSS should use `filter: none;`; do not permanently edit the source image.

## Update Google Scholar Metrics

Metrics are manually maintained in `content/site.json`:

```json
"scholarMetrics": {
  "citations": 522,
  "hIndex": 8,
  "updated": "2026-07-31",
  "url": "https://scholar.google.com/citations?user=mU3KsEEAAAAJ&hl=en"
}
```

Do not add automatic Google Scholar scraping.

## Add A Publication

The Academic / Publications page is data-driven from `content/publications.json`. Do not hard-code publication metadata into HTML.

1. Put the publication first-page screenshot or cover image in the active publication asset directory:

```text
assets/images/publications/
```

2. Open `content/publications.json`.
3. Copy an existing publication object and paste it at the desired position, normally newest first.
4. Add verified metadata only: `title`, `authors`, `journal`, `year`, `doi`, `url` or `link`, `image`, and optional verified fields such as `volume`, `issue`, `articleNumber`, `pages`, or `note`.
5. Double-click `Update Website.command`, or run:

```bash
python3 scripts/sync-publications.py
```

6. Preview the Academic page.

No HTML editing is required.

Example PaperXX image assignment:

```json
"image": "assets/images/publications/Paper20.png"
```

Use an author list:

```json
"authors": [
  "First Author",
  "Zhucheng Yang",
  "Corresponding Author*"
]
```

Visible numbering is automatic from array position. `Zhucheng Yang` is highlighted automatically. Scholar metrics remain separate in `content/site.json`; `scripts/sync-publications.py` does not scrape Google Scholar or publisher sites.

If a publication image is present but no publication record references it, the validator reports:

```text
EDITORIAL METADATA REQUIRED
```

Do not guess title, authors, journal, year, DOI, or URL from an image filename.

## Edit Existing Publication

Correcting publication metadata should require editing only `content/publications.json`.

Common editable fields are `title`, `authors`, `journal`, `year`, `volume`, `issue`, `articleNumber`, `pages`, `doi`, `url`, `link`, `image`, and verified labels such as `note`.

No HTML editing is normally required.

## Add News

Open `content/news.json` and add one object. Keep newest items anywhere you like; the site sorts by date automatically.

Use the standard categories:

- `PUBLICATION`
- `CONFERENCE`
- `AWARD`
- `MILESTONE`
- `RESEARCH`

Every item should include concise English and Simplified Chinese:

```json
{
  "date": "2026-05-14",
  "displayDate": "MAY 14",
  "category": "PUBLICATION",
  "title": "Short Title",
  "text": "One factual English sentence.",
  "textZh": "一句简洁、事实对应的中文描述。"
}
```

For conferences, add optional fields such as `event`, `location`, and `format`. Use `category: "CONFERENCE"` even when the format is `Poster`, `Talk`, or `Invited Talk`.

For awards, add optional `organization`. Keep wording factual and restrained.

For month-level dates, use:

```json
"date": "2026-04",
"datePrecision": "month",
"displayDate": "APR 2026"
```

## Chinese News Style

News Chinese uses Simplified Chinese and the system sans-serif stack, not Kai-style type. Keep it concise, natural, and equivalent to the English sentence. Use recurring terms consistently:

- metal nanoclusters: 金属纳米团簇
- atomically precise: 原子精确
- atomically resolved: 原子分辨
- smart synthesis: 智能合成
- protein nanocages: 蛋白纳米笼
- biomimetic catalysis: 仿生催化

## How To Edit A Photography Chapter

Edit `content/travel.json`. Photography copy should not require HTML editing.

Fields:

- `folder`: physical asset folder under `assets/images/photography/`.
- `title`: public artistic chapter title.
- `meta`: visible location/time metadata.
- `introEn`: visible English introduction.
- `introZh`: visible Chinese introduction.
- `order`: explicit page position.
- `featured`: opening image filename for the chapter.
- `photos`: complete source filename inventory and display order.

The physical folder controls chapter membership. The title controls what visitors see. The featured filename must also remain inside `photos`; the page renders it as the large opening image and excludes it from the supporting gallery.

To change the opening image, edit only:

```json
"featured": "another-photo.jpg"
```

## Add Photo To An Existing Photography Chapter

1. Copy the photo into the existing physical chapter folder, for example:

```text
assets/images/photography/Andalus May 2026/
```

2. Run:

```bash
python3 scripts/sync-photography.py
```

3. Optionally reposition the appended filename inside that chapter's `photos` array.

No HTML editing is required.

## Add A New Photography Chapter

1. Create a folder under the active photography asset tree:

```text
assets/images/photography/Japan Apr 2027/
```

2. Place the journey photographs inside that folder.
3. Run:

```bash
python3 scripts/sync-photography.py
```

4. Edit the generated draft in `content/travel.json`: `title`, `meta`, `introEn`, `introZh`, `order`, and `featured`.

No HTML editing is required.

Example:

```json
{
  "folder": "Japan Apr 2027",
  "title": "Japan Apr 2027",
  "meta": "",
  "introEn": "",
  "introZh": "",
  "order": 17,
  "featured": "first-image.jpg",
  "photos": [
    "first-image.jpg",
    "second-image.jpg"
  ]
}
```

The sync script preserves existing photo order, appends new physical files to the end, removes stale references, and creates draft chapters for new folders. It does not rewrite titles, copy, metadata, order, or featured choices for existing chapters.

## Add Aviation Photography

Put images in the active Flying photography directory:

```text
assets/images/flying/
```

Then run:

```bash
python3 scripts/sync-flying.py
```

The script updates `content/flying.json` under `aviationPhotography.photos`, preserves existing order, appends new files to the end, and never edits Planespotting or `content/flight-data.json`.

Optionally move the appended filename in `aviationPhotography.photos` to change the gallery sequence.

To change the Aviation Photography opening image, edit:

```json
"featured": "filename.jpg"
```

The featured filename must also remain inside `aviationPhotography.photos`; it is rendered once as the large opening aviation image.

## How To Add A Planespotting Airport

Open `content/flying.json` and add an object to `planespotting`. Use the IATA code as the unique identifier:

```json
{
  "iata": "SIN",
  "airport": "Singapore Changi Airport",
  "city": "Singapore",
  "country": "Singapore"
}
```

Coordinates are reused from `content/flight-data.json` when available; do not duplicate coordinate data in `content/flying.json`. If the IATA code exists in `content/flight-data.json`, the map marks it with a ring. No HTML editing is required.

Current planespotting list:

- `SIN`
- `LHR`
- `LAX`
- `CAN`
- `MNL`
- `EWR`
- `EDI`
- `MAN`
- `PEK`
- `SFO`
- `TPE`
- `TSA`
- `DOH`
- `SHA`
- `XMN`
- `SZX`

Planespotting is separate from flight history. Do not manually duplicate flight records or invent routes for a planespotting airport.

## Update Flight History

GENERATED FILE — DO NOT MANUALLY MAINTAIN NORMAL FLIGHT RECORDS HERE.

`content/flight-data.json` is generated output for the website. The authoritative flight history remains in:

```text
/Users/yangzhucheng/Documents/Flight log 2/data/flightlog.sqlite
```

The website wrapper calls the existing Flight Log exporter:

```text
/Users/yangzhucheng/Documents/Flight log 2/flightlog/export_web.py
```

The public export intentionally avoids raw per-flight chronology. The website uses aggregate statistics, airport coordinates, route summaries, and the privacy-preserving `specialLiveries` list.

## Special Liveries Flown

The Flying page's `SPECIAL LIVERIES FLOWN` section is generated from the authoritative Flight Log data. Do not hard-code special aircraft in `flying.html`, `assets/js/site.js`, or `content/flight-data.json`.

Current source fields are:

- `registration`
- `aircraft_model`
- `airline_en`
- `note`

Only notes that explicitly contain the word `livery` are exported. The exporter deduplicates by aircraft registration and omits flight dates, routes, flight numbers, and recent-flight ordering. If a future Flight Log version adds a dedicated livery field, update `/Users/yangzhucheng/Documents/Flight log 2/flightlog/export_web.py` to use that field as the primary source.

To add a special livery:

1. Open the Flight Log project.
2. Add or edit the aircraft's normal authoritative flight record.
3. Put the verified livery name in the note field, for example:

```text
Star Alliance Livery
```

4. Double-click `Update Website.command`, or run:

```bash
python3 scripts/update-flight-data.py
```

5. Preview the Flying page.

## Add A New Flight

Do not edit `content/flight-data.json` manually.

For a new actual flight record:

1. Open the Flight Log project.
2. Add or import the flight using the Flight Log project's normal authoritative workflow.
3. Double-click `Update Website.command`, or return to the website repo and run:

```bash
python3 scripts/update-flight-data.py
```

4. The Flight Log exporter regenerates `content/flight-data.json`.
5. Preview the Flying page.
6. Commit later when satisfied.

Do not manually type new flights into `content/flight-data.json`. Do not add flown flights to `content/flying.json`.

## Optional Full Update Workflow

```bash
cd "/Users/yangzhucheng/Documents/GitHub/K2Mount.github.io"
python3 scripts/update-all.py
```

Then preview locally. `scripts/update-all.py` orchestrates existing sync and validation scripts; it does not duplicate their internal logic and it does not publish the website.

## Preview Locally

Use a local HTTP server because JSON fetches do not work reliably from `file://`.

```bash
cd "/Users/yangzhucheng/Documents/GitHub/K2Mount.github.io"
python3 -m http.server 8022
```

Open:

```text
http://127.0.0.1:8022/index.html
```

## Publish Later

Keep redesign work on `Redesign-V2` until reviewed. Later, create a pull request from `Redesign-V2` to `main`, merge after approval, and let GitHub Pages deploy from the production branch.
