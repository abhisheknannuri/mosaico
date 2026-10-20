# UI guide

How pages are built. Rationale: ADR-0017.

## Layout

```text
+---------------------------------------------------------------+
| [≡] mosaico | Dashboard                       ● mosaicod 0.8   |  topbar (fixed)
|============== brand gradient line ============================|
| [▦] Overview     |  page_header                                |
| [⛁] Recordings   |  stats (optional)                           |
|                  |  cards / table                              |  content (scrolls)
|                  |                                             |
| [📖] API docs    |                                             |
+------------------+---------------------------------------------+
  sidebar (fixed; collapses to an icon rail, choice remembered)
```

- Sidebar links only for pages that exist; current page has `aria-current="page"`.
- Sidebar collapse: `toggleNav()` in `static/js/app.js`, state in `localStorage`, applied by an
  inline script in `<head>` before the page draws.
- Icons: Lucide 1.49.0 SVGs in `templates/icons/` (ISC licence alongside), included with
  `{% include "icons/<name>.svg" %}`; they inherit the text colour.

## Page anatomy

Every page template:

```jinja
{% extends "base.html" %}
{% import "components.html" as ui %}

{% block content %}
{{ ui.page_header("Title", "One line of context.", back_href="/recordings", back_label="Recordings") }}
{% include "partials/<page>.html" %}   {# the part htmx can swap #}
{% endblock %}
```

Inside the partial, in this order when present: `.stats` row → `.cards` grid → tables / cards.

## Components (`templates/components.html`)

| Macro | Use for | Example |
|---|---|---|
| `page_header(title, subtitle, back_href, back_label)` | Top of every page | `ui.page_header("Recordings", "Newest first.")` |
| `stat(label, value, hint, title)` | A single number; `hint` says what it means, `title` is the hover text (exact value); group in `<div class="stats">` | `ui.stat("Stored", t \| bytes, "compressed, in mosaicod", t \| bytes_exact)` |
| `card(title, id, link_href, link_label)` | A panel around any content; group in `<div class="cards">` for a 2-column grid | `{% call ui.card("Latest") %}…{% endcall %}` |
| `chips(items)` | Short labels (ontology tags); a single chip with class `chip ok` marks a positive state | `ui.chips(summary.ontology_tags)`, "in Mosaico" on the Ingest page |
| `share_bar(share, title)` | A bar filled to `share` (0–1), e.g. in a table cell | storage by ontology type |
| `bar(label, value, share, title)` | One row of a `<ul class="bar-list">`: label, bar, value, percentage; share 0–1 | — |
| `key_values(mapping)` | Properties of one item | selected file on the Ingest page |
| `text_field(label, name, value, hint)` | Labelled single-line input with optional hint | recording name |
| `key_value_rows(label, name, id, rows)` | Pairs of inputs `{name}_key` / `{name}_value`; "Add" copies the last row (`addRow` in `app.js`) | metadata |
| `empty_state(title)` | Nothing to show yet; body via `{% call %}` | no recordings |

Plain `<table>` is styled globally; add `class="num"` to numeric `th`/`td` (right-aligned, tabular
digits, never wrapped), `class="name"` to the identifying column and `class="nowrap"` to short
text that must stay on one line (dates, durations).
Links in a `name` cell look like the name (underlined on hover); a selected row has
`aria-selected="true"`. Long names wrap instead of widening the table.

## Formatting

Use the Jinja filters, never format in templates by hand: `| bytes` (3 significant digits:
1.98 GB, 366 MB), `| bytes_exact` (hover text: 1,979,880,035 bytes), `| percent` (99.7%, <0.1%),
`| duration`, `| datetime`. Every size shown has its exact value as `title`.

## CSS rules (`static/css/app.css`)

- Sections in order: tokens → base → layout → components. One block per component, named like
  its macro.
- Use tokens (`var(--space-4)`, `var(--border)`, …); no raw colours or pixel spacing outside
  `:root`.
- No page-specific CSS. A new visual need becomes a component (macro + CSS block + row in the
  table above).
- Dark only, Mosaico brand colours (`docs/py/docs/stylesheets/extra.css`).

## Review

After any UI change: headless Chrome screenshots at 1440 px, expanded and collapsed sidebar; check
alignment of left edges, sizes, empty states.
