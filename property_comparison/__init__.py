"""Property comparison web app: list, filter and compare flats and plots."""
import os

from flask import Flask

from . import db, formatting


def create_app(test_config=None):
    data_dir = os.environ.get("PROPERTY_COMPARE_DATA") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "instance")
    app = Flask(__name__, instance_path=os.path.abspath(data_dir))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.path.join(app.instance_path, "properties.sqlite3"),
        UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads"),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # total upload size per request
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.init_db()

    app.jinja_env.filters.update(
        inr=formatting.inr, inr_short=formatting.inr_short, sqft=formatting.sqft,
        km=formatting.km, yes_no=formatting.yes_no, num=formatting.num)

    from .reports import format_value
    app.jinja_env.globals["format_value"] = format_value

    @app.errorhandler(413)
    def too_large(_e):
        from flask import flash, redirect, request
        flash("Upload too large (limit 50 MB per submission).", "error")
        return redirect(request.referrer or "/")

    from . import views
    app.register_blueprint(views.bp)
    return app
