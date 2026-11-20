"""Validation, queries and photo storage for property listings."""
import os
import uuid
from datetime import date

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from .db import get_db

PROPERTY_TYPES = ("Flat", "Plot")
FACINGS = ("", "North", "South", "East", "West",
           "North-East", "North-West", "South-East", "South-West")
ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "bmp"}
MAX_PHOTO_EDGE = 1600

# Fields that only make sense for flats; cleared when a plot is saved.
FLAT_ONLY_FIELDS = ("bhk", "floor", "total_floors")

TEXT_FIELDS = ("title", "property_type", "facing", "locality", "city", "address",
               "possession_date", "developer", "railway_station_name", "bus_stand_name",
               "highway_name", "connectivity_notes", "amenities", "notes")
REQUIRED_TEXT = {"title": "Title", "locality": "Locality", "city": "City"}
FLOAT_FIELDS = {"price": "Price", "carpet_area_sqft": "Carpet / plot area",
                "railway_station_km": "Railway station distance",
                "bus_stand_km": "Bus stand distance", "highway_km": "Highway distance"}
INT_FIELDS = {"bhk": "BHK", "floor": "Floor", "total_floors": "Total floors"}
COLUMNS = TEXT_FIELDS + tuple(FLOAT_FIELDS) + tuple(INT_FIELDS) + ("ready_to_move",)

PPSF_SQL = "(p.price / p.carpet_area_sqft)"

SORTS = {
    "newest": ("Newest first", "p.created_at DESC, p.id DESC"),
    "price_asc": ("Price: low to high", "p.price ASC"),
    "price_desc": ("Price: high to low", "p.price DESC"),
    "ppsf_asc": ("Price/sq ft: low to high", f"{PPSF_SQL} ASC"),
    "ppsf_desc": ("Price/sq ft: high to low", f"{PPSF_SQL} DESC"),
    "area_desc": ("Area: largest first", "p.carpet_area_sqft DESC"),
    "rail_asc": ("Nearest railway station", "p.railway_station_km IS NULL, p.railway_station_km ASC"),
    "highway_asc": ("Nearest highway", "p.highway_km IS NULL, p.highway_km ASC"),
}


# --------------------------------------------------------------------------- validation

def _num(raw, cast, label, errors, minimum=0, required=False, strictly_positive=False):
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        value = cast(float(raw)) if cast is int else cast(raw)
    except ValueError:
        errors.append(f"{label} must be a number.")
        return None
    if strictly_positive and value <= 0:
        errors.append(f"{label} must be greater than zero.")
    elif value < minimum:
        errors.append(f"{label} cannot be negative.")
    return value


def parse_property_form(form):
    """Return (data, errors) from a submitted add/edit form."""
    errors = []
    data = {f: (form.get(f) or "").strip() or None for f in TEXT_FIELDS}

    for field, label in REQUIRED_TEXT.items():
        if not data[field]:
            errors.append(f"{label} is required.")

    if data["property_type"] not in PROPERTY_TYPES:
        errors.append("Property type must be Flat or Plot.")
    if data["facing"] and data["facing"] not in FACINGS:
        errors.append("Facing is not a recognised direction.")

    for field, label in FLOAT_FIELDS.items():
        required = field in ("price", "carpet_area_sqft")
        data[field] = _num(form.get(field), float, label, errors,
                           required=required, strictly_positive=required)
    for field, label in INT_FIELDS.items():
        data[field] = _num(form.get(field), int, label, errors)

    data["ready_to_move"] = 1 if form.get("ready_to_move") in ("1", "on", "yes", "true") else 0

    if data["property_type"] == "Plot":
        for f in FLAT_ONLY_FIELDS:
            data[f] = None
    elif data["floor"] is not None and data["total_floors"] is not None \
            and data["floor"] > data["total_floors"]:
        errors.append("Floor cannot be higher than total floors.")

    if data["possession_date"]:
        try:
            date.fromisoformat(data["possession_date"])
        except ValueError:
            errors.append("Possession date must be a valid date (YYYY-MM-DD).")

    return data, errors


# --------------------------------------------------------------------------- filters

def parse_filters(args):
    """Normalise query-string filters. Invalid numbers are ignored."""
    def money(key):
        raw = (args.get(key) or "").strip().replace(",", "")
        try:
            v = float(raw)
            return v if v >= 0 else None
        except ValueError:
            return None

    ptype = args.get("type") or ""
    ready = args.get("ready") or ""
    sort = args.get("sort") or "newest"
    return {
        "min_price": money("min_price"),
        "max_price": money("max_price"),
        "type": ptype if ptype in PROPERTY_TYPES else "",
        "location": (args.get("location") or "").strip(),
        "ready": ready if ready in ("yes", "no") else "",
        "sort": sort if sort in SORTS else "newest",
    }


def filters_summary(f):
    from .formatting import inr
    parts = []
    if f["min_price"] is not None or f["max_price"] is not None:
        lo = inr(f["min_price"], "Rs. ") if f["min_price"] is not None else "any"
        hi = inr(f["max_price"], "Rs. ") if f["max_price"] is not None else "any"
        parts.append(f"Budget {lo} to {hi}")
    if f["type"]:
        parts.append(f"Type: {f['type']}")
    if f["location"]:
        parts.append(f"Location contains '{f['location']}'")
    if f["ready"]:
        parts.append("Ready to move" if f["ready"] == "yes" else "Under construction")
    return "; ".join(parts) or "No filters (all listings)"


# --------------------------------------------------------------------------- queries

def _enrich(row, photos=None):
    d = dict(row)
    d["price_per_sqft"] = d["price"] / d["carpet_area_sqft"] if d["carpet_area_sqft"] else None
    d["photos"] = photos if photos is not None else []
    if d["property_type"] == "Flat" and d["floor"] is not None:
        d["floor_display"] = f"{d['floor']}" + (f" of {d['total_floors']}" if d["total_floors"] else "")
    else:
        d["floor_display"] = None
    return d


def _photos_by_property(ids):
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = get_db().execute(
        f"SELECT * FROM photos WHERE property_id IN ({marks}) ORDER BY id", list(ids)).fetchall()
    out = {i: [] for i in ids}
    for r in rows:
        out[r["property_id"]].append(dict(r))
    return out


def list_properties(filters):
    where, params = [], []
    if filters["min_price"] is not None:
        where.append("p.price >= ?")
        params.append(filters["min_price"])
    if filters["max_price"] is not None:
        where.append("p.price <= ?")
        params.append(filters["max_price"])
    if filters["type"]:
        where.append("p.property_type = ?")
        params.append(filters["type"])
    if filters["location"]:
        like = f"%{filters['location']}%"
        where.append("(p.locality LIKE ? OR p.city LIKE ? OR p.address LIKE ?)")
        params += [like, like, like]
    if filters["ready"]:
        where.append("p.ready_to_move = ?")
        params.append(1 if filters["ready"] == "yes" else 0)

    sql = "SELECT p.* FROM properties p"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + SORTS[filters["sort"]][1]
    rows = get_db().execute(sql, params).fetchall()
    photos = _photos_by_property([r["id"] for r in rows])
    return [_enrich(r, photos[r["id"]]) for r in rows]


def get_property(pid):
    row = get_db().execute("SELECT * FROM properties WHERE id = ?", (pid,)).fetchone()
    if row is None:
        return None
    return _enrich(row, _photos_by_property([pid])[pid])


def get_properties(ids):
    """Fetch properties keeping the order of ``ids``; unknown ids are skipped."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in get_db().execute(
        f"SELECT * FROM properties WHERE id IN ({marks})", ids)}
    photos = _photos_by_property(list(rows))
    return [_enrich(rows[i], photos[i]) for i in ids if i in rows]


def distinct_locations():
    rows = get_db().execute(
        "SELECT DISTINCT locality FROM properties UNION SELECT DISTINCT city FROM properties "
        "ORDER BY 1").fetchall()
    return [r[0] for r in rows]


def insert_property(data):
    cols = [c for c in COLUMNS if c in data]
    db = get_db()
    cur = db.execute(
        f"INSERT INTO properties ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        [data[c] for c in cols])
    db.commit()
    return cur.lastrowid


def update_property(pid, data):
    cols = [c for c in COLUMNS if c in data]
    db = get_db()
    db.execute(
        f"UPDATE properties SET {', '.join(c + ' = ?' for c in cols)}, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [data[c] for c in cols] + [pid])
    db.commit()


def delete_property(pid):
    db = get_db()
    files = [r["filename"] for r in
             db.execute("SELECT filename FROM photos WHERE property_id = ?", (pid,))]
    db.execute("DELETE FROM properties WHERE id = ?", (pid,))
    db.commit()
    for f in files:
        _remove_file(f)


def type_summary(props):
    """Flats vs plots: count, average price, average and best price per sq ft."""
    out = []
    for t in PROPERTY_TYPES:
        group = [p for p in props if p["property_type"] == t]
        if not group:
            continue
        ppsf = [p["price_per_sqft"] for p in group]
        out.append({
            "type": t,
            "count": len(group),
            "avg_price": sum(p["price"] for p in group) / len(group),
            "avg_area": sum(p["carpet_area_sqft"] for p in group) / len(group),
            "avg_ppsf": sum(ppsf) / len(ppsf),
            "min_ppsf": min(ppsf),
        })
    return out


# --------------------------------------------------------------------------- photos

def photo_path(filename):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], filename)


def _remove_file(filename):
    try:
        os.remove(photo_path(filename))
    except FileNotFoundError:
        pass


def save_photos(pid, files):
    """Validate, normalise (rotate, shrink, JPEG) and store uploaded photos.

    Returns (saved_count, errors).
    """
    saved, errors = 0, []
    db = get_db()
    for f in files:
        if not f or not f.filename:
            continue
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_PHOTO_EXTENSIONS:
            errors.append(f"{f.filename}: unsupported file type.")
            continue
        try:
            img = Image.open(f.stream)
            img.load()
        except (UnidentifiedImageError, OSError):
            errors.append(f"{f.filename}: not a valid image.")
            continue
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_PHOTO_EDGE, MAX_PHOTO_EDGE))
        name = f"{uuid.uuid4().hex}.jpg"
        img.save(photo_path(name), "JPEG", quality=85, optimize=True)
        db.execute("INSERT INTO photos (property_id, filename, original_name) VALUES (?, ?, ?)",
                   (pid, name, f.filename[:200]))
        saved += 1
    db.commit()
    return saved, errors


def get_photo(photo_id):
    row = get_db().execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
    return dict(row) if row else None


def delete_photo(photo_id):
    photo = get_photo(photo_id)
    if photo:
        db = get_db()
        db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        db.commit()
        _remove_file(photo["filename"])
    return photo
