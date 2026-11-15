"""SQLite storage for property listings and their photographs."""
import sqlite3

import click
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS properties (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    title                 TEXT    NOT NULL,
    property_type         TEXT    NOT NULL CHECK (property_type IN ('Flat', 'Plot')),
    price                 REAL    NOT NULL CHECK (price > 0),
    carpet_area_sqft      REAL    NOT NULL CHECK (carpet_area_sqft > 0),
    bhk                   INTEGER,
    floor                 INTEGER,
    total_floors          INTEGER,
    facing                TEXT,
    locality              TEXT    NOT NULL,
    city                  TEXT    NOT NULL,
    address               TEXT,
    ready_to_move         INTEGER NOT NULL DEFAULT 0,
    possession_date       TEXT,
    developer             TEXT,
    railway_station_name  TEXT,
    railway_station_km    REAL,
    bus_stand_name        TEXT,
    bus_stand_km          REAL,
    highway_name          TEXT,
    highway_km            REAL,
    connectivity_notes    TEXT,
    amenities             TEXT,
    notes                 TEXT,
    created_at            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TEXT
);

CREATE TABLE IF NOT EXISTS photos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id    INTEGER NOT NULL REFERENCES properties (id) ON DELETE CASCADE,
    filename       TEXT    NOT NULL UNIQUE,
    original_name  TEXT,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_photos_property ON photos (property_id);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties (property_type);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties (price);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript(SCHEMA)


@click.command("init-db")
def init_db_command():
    """Create the tables if they do not exist."""
    init_db()
    click.echo("Database ready.")


@click.command("seed")
def seed_command():
    """Insert a few sample listings (no photos) for trying the app out."""
    from .models import insert_property

    samples = [
        dict(title="2 BHK in Skyline Residency", property_type="Flat", price=6_850_000,
             carpet_area_sqft=780, bhk=2, floor=7, total_floors=14, facing="East",
             locality="Wakad", city="Pune", ready_to_move=1, developer="Skyline Developers",
             railway_station_name="Chinchwad", railway_station_km=4.5,
             bus_stand_name="Wakad Chowk", bus_stand_km=0.8,
             highway_name="Mumbai-Bengaluru Highway (NH 48)", highway_km=1.2,
             connectivity_notes="Metro line under construction 2 km away",
             amenities="Gym, pool, covered parking"),
        dict(title="3 BHK Lakeview Towers", property_type="Flat", price=11_200_000,
             carpet_area_sqft=1150, bhk=3, floor=11, total_floors=22, facing="North",
             locality="Baner", city="Pune", ready_to_move=0, possession_date="2027-12-31",
             developer="Lakeview Infra", railway_station_name="Shivajinagar",
             railway_station_km=9.0, bus_stand_name="Baner Gaon", bus_stand_km=1.5,
             highway_name="NH 48", highway_km=2.4, amenities="Clubhouse, garden"),
        dict(title="Corner plot, Green Acres layout", property_type="Plot", price=4_500_000,
             carpet_area_sqft=1500, facing="North-East", locality="Talegaon",
             city="Pune", ready_to_move=1, railway_station_name="Talegaon",
             railway_station_km=2.2, bus_stand_name="Talegaon ST Stand", bus_stand_km=2.8,
             highway_name="Mumbai-Pune Expressway", highway_km=3.5,
             connectivity_notes="NA plot, clear title, 30 ft road"),
        dict(title="Residential plot near ring road", property_type="Plot", price=3_200_000,
             carpet_area_sqft=1200, facing="West", locality="Hinjewadi Phase 3",
             city="Pune", ready_to_move=1, bus_stand_name="Maan Phata", bus_stand_km=1.1,
             highway_name="Proposed Ring Road", highway_km=0.6, railway_station_name="Pimpri",
             railway_station_km=16.0),
    ]
    for s in samples:
        insert_property(s)
    click.echo(f"Inserted {len(samples)} sample properties.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
