import io
import os
import zipfile

import pytest
from openpyxl import load_workbook
from PIL import Image

from property_comparison import create_app
from property_comparison.formatting import indian_group, inr_short


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


@pytest.fixture
def client(app):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    return app.test_client()


def png_bytes(color=(200, 50, 50), size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


FLAT = dict(title="2 BHK Skyline", property_type="Flat", price="6800000", carpet_area_sqft="800",
            bhk="2", floor="5", total_floors="12", locality="Wakad", city="Pune",
            ready_to_move="1", railway_station_name="Chinchwad", railway_station_km="4.5",
            bus_stand_name="Wakad Chowk", bus_stand_km="0.8", highway_name="NH 48", highway_km="1.2")
PLOT = dict(title="Corner plot", property_type="Plot", price="4500000", carpet_area_sqft="1500",
            bhk="3", locality="Talegaon", city="Pune", railway_station_km="2.2", highway_km="3.5")


def add(client, data, photos=None):
    payload = dict(data)
    if photos:
        payload["photos"] = photos
    resp = client.post("/property/new", data=payload, content_type="multipart/form-data")
    assert resp.status_code == 302, resp.data
    return int(resp.headers["Location"].rsplit("/", 1)[-1])


def test_formatting():
    assert indian_group(12345678) == "1,23,45,678"
    assert indian_group(999) == "999"
    assert indian_group(100000) == "1,00,000"
    assert inr_short(6_850_000) == "₹68.50 L"
    assert inr_short(11_200_000) == "₹1.12 Cr"


def test_pages_render(client):
    assert client.get("/").status_code == 200
    assert client.get("/property/new").status_code == 200
    assert client.get("/property/new?type=Plot").status_code == 200
    pid = add(client, FLAT)
    page = client.get(f"/property/{pid}/edit").get_data(as_text=True)
    assert 'value="6800000"' in page and 'value="4.5"' in page and 'value="2"' in page
    assert client.get("/?min_price=100&max_price=99999999").status_code == 200
    assert client.get("/property/999").status_code == 404


def test_add_and_price_per_sqft(client):
    pid = add(client, FLAT)
    page = client.get(f"/property/{pid}").get_data(as_text=True)
    assert "2 BHK Skyline" in page
    assert "₹8,500" in page  # 68,00,000 / 800
    assert "Chinchwad" in page and "4.5 km" in page


def test_plot_drops_flat_only_fields(client, app):
    pid = add(client, PLOT)
    with app.app_context():
        from property_comparison.models import get_property
        p = get_property(pid)
    assert p["bhk"] is None
    assert p["price_per_sqft"] == pytest.approx(3000)


@pytest.mark.parametrize("override, message", [
    ({"price": ""}, "Price is required"),
    ({"price": "-5"}, "Price must be greater than zero"),
    ({"carpet_area_sqft": "abc"}, "Carpet / plot area must be a number"),
    ({"title": ""}, "Title is required"),
    ({"floor": "20"}, "Floor cannot be higher"),
    ({"railway_station_km": "-1"}, "cannot be negative"),
    ({"property_type": "Villa"}, "Flat or Plot"),
])
def test_validation(client, override, message):
    resp = client.post("/property/new", data={**FLAT, **override})
    assert resp.status_code == 400
    assert message in resp.get_data(as_text=True)


def test_filters(client):
    add(client, FLAT)
    add(client, PLOT)
    add(client, {**FLAT, "title": "Pricey penthouse", "price": "25000000", "locality": "Baner",
                 "ready_to_move": ""})

    def titles(qs):
        return client.get("/?" + qs).get_data(as_text=True)

    page = titles("max_price=7000000")
    assert "2 BHK Skyline" in page and "Corner plot" in page and "Pricey penthouse" not in page
    page = titles("min_price=5000000&max_price=10000000")
    assert "2 BHK Skyline" in page and "Corner plot" not in page
    page = titles("type=Plot")
    assert "Corner plot" in page and "2 BHK Skyline" not in page
    page = titles("location=baner")
    assert "Pricey penthouse" in page and "Corner plot" not in page
    page = titles("ready=yes")
    assert "2 BHK Skyline" in page and "Pricey penthouse" not in page and "Corner plot" not in page
    page = titles("ready=no")
    assert "Pricey penthouse" in page and "2 BHK Skyline" not in page
    page = titles("sort=ppsf_asc")
    assert page.index("Corner plot") < page.index("2 BHK Skyline") < page.index("Pricey penthouse")


def test_photo_upload_and_delete(client, app):
    pid = add(client, FLAT, photos=[(png_bytes(), "front.png")])
    resp = client.post(f"/property/{pid}/photos", content_type="multipart/form-data",
                       data={"photos": [(png_bytes((0, 0, 255)), "side.png"),
                                        (io.BytesIO(b"not an image"), "fake.jpg"),
                                        (io.BytesIO(b"x"), "doc.pdf")]},
                       follow_redirects=True)
    text = resp.get_data(as_text=True)
    assert "Uploaded 1 photo" in text
    assert "fake.jpg: not a valid image" in text
    assert "doc.pdf: unsupported file type" in text

    with app.app_context():
        from property_comparison.models import get_property
        photos = get_property(pid)["photos"]
    assert len(photos) == 2
    path = os.path.join(app.config["UPLOAD_FOLDER"], photos[0]["filename"])
    assert os.path.exists(path) and path.endswith(".jpg")
    assert client.get(f"/uploads/{photos[0]['filename']}").status_code == 200

    client.post(f"/photo/{photos[0]['id']}/delete")
    assert not os.path.exists(path)

    client.post(f"/property/{pid}/delete")
    assert os.listdir(app.config["UPLOAD_FOLDER"]) == []
    assert client.get(f"/property/{pid}").status_code == 404


def test_compare_highlights_best(client):
    a = add(client, FLAT, photos=[(png_bytes(), "a.png")])
    b = add(client, PLOT)
    page = client.get(f"/compare?ids={a}&ids={b}").get_data(as_text=True)
    assert "Comparing 2 properties" in page
    # plot is cheaper and has cheaper price/sq ft and larger area
    assert '<td class="best">₹45,00,000</td>' in page
    assert '<td class="best">₹3,000</td>' in page
    assert '<td class="best">1,500 sq ft</td>' in page
    # flat is ready to move and nearer the highway
    assert '<td class="best">Yes</td>' in page
    assert '<td class="best">1.2 km</td>' in page


def test_compare_needs_two(client):
    a = add(client, FLAT)
    resp = client.get(f"/compare?ids={a}", follow_redirects=True)
    assert "Select at least two" in resp.get_data(as_text=True)


def test_pdf_report(client):
    a = add(client, FLAT, photos=[(png_bytes(), "a.png")])
    b = add(client, PLOT)
    resp = client.get(f"/report.pdf?ids={a},{b}")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")
    assert "attachment" in resp.headers["Content-Disposition"]
    # filtered (no ids) and empty results still produce a valid PDF
    assert client.get("/report.pdf?type=Plot").data.startswith(b"%PDF")
    assert client.get("/report.pdf?min_price=999999999").data.startswith(b"%PDF")


def test_many_properties_pdf(client):
    ids = [add(client, {**FLAT, "title": f"Flat {i}"}) for i in range(9)]
    resp = client.get("/report.pdf?ids=" + ",".join(map(str, ids)))
    assert resp.data.startswith(b"%PDF")


def test_excel_report(client):
    a = add(client, FLAT, photos=[(png_bytes(), "a.png")])
    b = add(client, PLOT)
    resp = client.get(f"/report.xlsx?ids={a}&ids={b}")
    assert resp.status_code == 200
    wb = load_workbook(io.BytesIO(resp.data))
    assert wb.sheetnames == ["Comparison", "Listings", "Flats vs Plots"]

    comp = wb["Comparison"]
    labels = {comp.cell(r, 1).value: r for r in range(1, comp.max_row + 1)}
    row = labels["Price per sq ft"]
    assert comp.cell(row, 2).value == pytest.approx(8500)
    assert comp.cell(row, 3).value == pytest.approx(3000)
    assert comp.cell(row, 3).fill.fgColor.rgb.endswith("D6F5DF")  # plot is best
    assert len(comp._images) == 1

    listings = wb["Listings"]
    assert listings["B2"].value == "2 BHK Skyline"
    assert listings["H2"].value == "=IFERROR(F2/G2,\"\")"
    assert listings["U3"].value == 3.5

    summary = wb["Flats vs Plots"]
    assert summary["A2"].value == "Flat" and summary["B2"].value.startswith("=COUNTIF")

    with zipfile.ZipFile(io.BytesIO(resp.data)) as z:
        assert any(n.startswith("xl/media/") for n in z.namelist())


def test_edit_property(client, app):
    pid = add(client, FLAT)
    resp = client.post(f"/property/{pid}/edit", data={**FLAT, "price": "7200000"},
                       content_type="multipart/form-data")
    assert resp.status_code == 302
    with app.app_context():
        from property_comparison.models import get_property
        assert get_property(pid)["price"] == 7_200_000


def test_export_links_keep_filters(client):
    add(client, FLAT)
    page = client.get("/?max_price=10000000&type=Flat").get_data(as_text=True)
    assert "/report.pdf?max_price=10000000&amp;type=Flat" in page
    assert "/report.xlsx?max_price=10000000&amp;type=Flat" in page
