from datetime import datetime

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template,
                   request, send_from_directory, url_for)

from . import models, reports
from .formatting import num

bp = Blueprint("main", __name__)


def _ids_from_request():
    ids = []
    for raw in request.args.getlist("ids"):
        for part in raw.split(","):
            if part.strip().isdigit():
                ids.append(int(part))
    return ids


def _filter_args(filters):
    """Query-string args that reproduce the active filters (for export links)."""
    out = {}
    for k in ("min_price", "max_price"):
        if filters[k] is not None:
            out[k] = num(filters[k])
    for k in ("type", "location", "ready"):
        if filters[k]:
            out[k] = filters[k]
    if filters["sort"] != "newest":
        out["sort"] = filters["sort"]
    return out


@bp.route("/")
def index():
    filters = models.parse_filters(request.args)
    props = models.list_properties(filters)
    return render_template(
        "index.html", props=props, filters=filters, sorts=models.SORTS,
        summary=models.type_summary(props), locations=models.distinct_locations(),
        export_args=_filter_args(filters), filtered=bool(_filter_args(filters)))


@bp.route("/property/new", methods=["GET", "POST"])
def new_property():
    if request.method == "POST":
        data, errors = models.parse_property_form(request.form)
        if not errors:
            pid = models.insert_property(data)
            saved, photo_errors = models.save_photos(pid, request.files.getlist("photos"))
            for e in photo_errors:
                flash(e, "error")
            flash("Property added" + (f" with {saved} photo(s)." if saved else "."), "success")
            return redirect(url_for("main.detail", pid=pid))
        for e in errors:
            flash(e, "error")
        return render_template("form.html", prop=data, mode="new", **_form_ctx()), 400
    return render_template("form.html", prop={"property_type": request.args.get("type", "Flat")},
                           mode="new", **_form_ctx())


@bp.route("/property/<int:pid>")
def detail(pid):
    prop = models.get_property(pid) or abort(404)
    return render_template("detail.html", p=prop)


@bp.route("/property/<int:pid>/edit", methods=["GET", "POST"])
def edit_property(pid):
    prop = models.get_property(pid) or abort(404)
    if request.method == "POST":
        data, errors = models.parse_property_form(request.form)
        if not errors:
            models.update_property(pid, data)
            saved, photo_errors = models.save_photos(pid, request.files.getlist("photos"))
            for e in photo_errors:
                flash(e, "error")
            flash("Property updated" + (f"; {saved} photo(s) added." if saved else "."), "success")
            return redirect(url_for("main.detail", pid=pid))
        for e in errors:
            flash(e, "error")
        data["id"], data["photos"] = pid, prop["photos"]
        return render_template("form.html", prop=data, mode="edit", **_form_ctx()), 400
    return render_template("form.html", prop=prop, mode="edit", **_form_ctx())


def _form_ctx():
    return {"types": models.PROPERTY_TYPES, "facings": models.FACINGS}


@bp.route("/property/<int:pid>/delete", methods=["POST"])
def delete_property(pid):
    models.get_property(pid) or abort(404)
    models.delete_property(pid)
    flash("Property deleted.", "success")
    return redirect(url_for("main.index"))


@bp.route("/property/<int:pid>/photos", methods=["POST"])
def upload_photos(pid):
    models.get_property(pid) or abort(404)
    saved, errors = models.save_photos(pid, request.files.getlist("photos"))
    for e in errors:
        flash(e, "error")
    if saved:
        flash(f"Uploaded {saved} photo(s).", "success")
    elif not errors:
        flash("Choose at least one photo to upload.", "error")
    return redirect(url_for("main.detail", pid=pid) + "#photos")


@bp.route("/photo/<int:photo_id>/delete", methods=["POST"])
def delete_photo(photo_id):
    photo = models.delete_photo(photo_id) or abort(404)
    flash("Photo removed.", "success")
    return redirect(url_for("main.detail", pid=photo["property_id"]) + "#photos")


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/compare")
def compare():
    ids = _ids_from_request()
    props = models.get_properties(ids)
    if len(props) < 2:
        flash("Select at least two properties to compare.", "error")
        return redirect(url_for("main.index"))
    return render_template("compare.html", props=props, rows=reports.comparison_rows(props),
                           summary=models.type_summary(props),
                           ids=",".join(str(p["id"]) for p in props))


def _report_selection():
    """Properties for a report: explicit ?ids=… or else the active filters."""
    ids = _ids_from_request()
    if ids:
        props = models.get_properties(ids)
        return props, f"Selected properties: {len(props)}"
    filters = models.parse_filters(request.args)
    return models.list_properties(filters), models.filters_summary(filters)


def _download(data, mimetype, ext):
    name = f"property-comparison-{datetime.now():%Y%m%d-%H%M}.{ext}"
    return Response(data, mimetype=mimetype,
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@bp.route("/report.pdf")
def report_pdf():
    props, subtitle = _report_selection()
    return _download(reports.build_pdf(props, subtitle), "application/pdf", "pdf")


@bp.route("/report.xlsx")
def report_excel():
    props, subtitle = _report_selection()
    return _download(
        reports.build_excel(props, subtitle),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")
