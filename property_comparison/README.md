# Property Compare

A small web app for shortlisting residential property: record flats and plots,
filter them, compare them side by side, and export comparison reports as PDF and
Excel.

## Features

- **Listings** for flats and plots: price, carpet / plot area, BHK, floor, facing,
  developer, possession date and ready-to-move status.
- **Price per sq ft**, calculated automatically (live in the form, on every card,
  in comparisons and as a formula in the Excel export).
- **Locality and connectivity**: locality, city, address, nearest railway station,
  bus stand and highway with distances in km, plus free-text notes (metro,
  schools, airport…).
- **Photographs**: upload several per property. Images are checked, auto-rotated
  from EXIF data, resized to 1600 px max and stored as JPEG.
- **Filters**: budget (min / max ₹), property type, location (matches locality,
  city or address) and ready-to-move / under-construction, plus sorting by price,
  price per sq ft, area or distance to railway station / highway.
- **Flats vs plots summary**: count, average price, average and lowest price per
  sq ft for whatever is currently filtered.
- **Comparison**: tick two or more listings and compare them in one table. The
  best value in each row is highlighted (lowest price, price per sq ft and
  distances; largest area; ready to move).
- **Reports**
  - **PDF** (landscape A4): flats vs plots summary and the side-by-side table with
    a photo of each property and the best values highlighted.
  - **Excel** with three sheets: *Comparison* (side by side with photos and
    highlighting), *Listings* (one row per property, auto-filter, price per sq ft as
    a live formula) and *Flats vs Plots* (summary formulas over *Listings*, so edits
    flow through).
  - Export the properties you're comparing, a single property, or all listings
    that match the current filters.

Amounts are shown in Indian format (₹68,50,000, ₹68.50 L, ₹1.12 Cr). The PDF
writes `Rs.` because the built-in PDF fonts have no ₹ glyph.

## Running it

Requires Python 3.10+.

```bash
cd property_comparison
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..
flask --app property_comparison seed     # optional: 4 sample listings
flask --app property_comparison run      # http://127.0.0.1:5000
```

Data lives in `property_comparison/instance/` (`properties.sqlite3` and
`uploads/`); set `PROPERTY_COMPARE_DATA=/some/folder` to keep it elsewhere.
Copy that folder to back everything up. Set `SECRET_KEY` in the
environment if you run it anywhere other than your own machine.

## Tests

```bash
pip install pytest
python -m pytest property_comparison/tests
```

## Layout

| File | Purpose |
| --- | --- |
| `__init__.py` | App factory and template filters |
| `db.py` | SQLite schema, `init-db` and `seed` commands |
| `models.py` | Form validation, filters, queries, photo storage |
| `reports.py` | Comparison rows with best-value logic, PDF and Excel builders |
| `views.py` | Routes |
| `formatting.py` | Indian currency grouping and unit helpers |
| `templates/`, `static/` | Pages and styling |

## Notes and limits

- It's a single-user tool with no login. Don't expose it on a public network as is.
- "Carpet area" holds the plot area for plots; price per sq ft uses that value.
- Distances are typed in by you, not looked up from a map service.
