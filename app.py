import copy
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from PIL import Image, ImageOps

import settings as cfg
from storage import LocalStorage, get_storage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["affiches", "logos", "flyers", "brochures", "maquettes", "ia", "autres"]
MAX_SIDE = 2400
THUMB_SIDE = 900

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

storage = get_storage(BASE_DIR)
_lock = threading.Lock()


def load_items():
    return storage.load_items()


def save_items(items):
    storage.save_items(items)


def jpeg_bytes(img, quality):
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


app.jinja_env.globals["image_url"] = storage.url


_settings_cache = {"at": 0.0, "data": None}
SETTINGS_TTL = 15


def load_settings(fresh=False):
    now = time.monotonic()
    if fresh or _settings_cache["data"] is None or now - _settings_cache["at"] > SETTINGS_TTL:
        _settings_cache["data"] = storage.load_doc(cfg.SETTINGS_NAME, {})
        _settings_cache["at"] = now
    return cfg.merge(copy.deepcopy(_settings_cache["data"]))


def save_settings(data):
    storage.save_doc(cfg.SETTINGS_NAME, data)
    _settings_cache["data"] = copy.deepcopy(data)
    _settings_cache["at"] = time.monotonic()


@app.context_processor
def inject_site():
    if request.endpoint in ("static", "uploaded") or request.path.startswith("/api/"):
        return {}
    site = load_settings()
    prof = site["profile"]
    return {
        "site": site,
        "profile": prof,
        "show": site["sections"],
        "photo_url": storage.url(prof["photo"]) if prof["photo"] else url_for("static", filename="img/christian.jpg"),
        "theme_css": cfg.theme_css(site["theme"]),
        "fonts_url": cfg.fonts_url(site["theme"]),
        "brand_initials": cfg.initials(prof["name"]),
        "tel_href": "tel:" + "".join(c for c in prof["phone"] if c.isdigit() or c == "+"),
    }


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


def check_csrf():
    sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(400)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def process_jpeg(raw):
    if not raw.startswith(b"\xff\xd8\xff"):
        raise ValueError("not a jpeg")
    Image.open(BytesIO(raw)).verify()
    img = ImageOps.exif_transpose(Image.open(BytesIO(raw))).convert("RGB")
    full = img.copy()
    full.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    thumb = img.copy()
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
    return full, thumb


@app.route("/")
def index():
    return render_template("index.html", page="home")


@app.route("/realisations")
def realisations():
    items = load_items()
    used = [c for c in CATEGORIES if any(i["category"] == c for i in items)]
    return render_template("realisations.html", page="work", items=items, categories=used)


@app.route("/uploads/<path:name>")
def uploaded(name):
    if not isinstance(storage, LocalStorage):
        abort(404)
    return send_from_directory(storage.upload_dir, name, max_age=60 * 60 * 24 * 30)


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        check_csrf()
        pwd = request.form.get("password", "")
        if ADMIN_PASSWORD and secrets.compare_digest(pwd, ADMIN_PASSWORD):
            session.clear()
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Mot de passe incorrect.")
    return render_template("login.html", configured=bool(ADMIN_PASSWORD))


@app.route("/admin/logout", methods=["POST"])
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html", items=load_items(), categories=CATEGORIES)


@app.route("/admin/upload", methods=["POST"])
@login_required
def upload():
    check_csrf()
    category = request.form.get("category", "autres")
    if category not in CATEGORIES:
        category = "autres"
    title = request.form.get("title", "").strip()[:120]
    files = request.files.getlist("images")
    added, rejected = 0, []
    new_items = []
    for f in files:
        if not f or not f.filename:
            continue
        try:
            full, thumb = process_jpeg(f.read())
        except Exception:
            rejected.append(f.filename)
            continue
        uid = uuid.uuid4().hex
        storage.put_image(f"{uid}.jpg", jpeg_bytes(full, 88))
        storage.put_image(f"{uid}_t.jpg", jpeg_bytes(thumb, 82))
        new_items.append({
            "id": uid,
            "file": f"{uid}.jpg",
            "thumb": f"{uid}_t.jpg",
            "title": title,
            "category": category,
            "width": full.width,
            "height": full.height,
            "created": datetime.now(timezone.utc).isoformat(),
        })
        added += 1
    if new_items:
        with _lock:
            items = load_items()
            save_items(new_items + items)
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(added=added, rejected=rejected)
    if added:
        flash(f"{added} image(s) ajoutée(s).")
    if rejected:
        flash("Fichiers refusés (JPEG uniquement) : " + ", ".join(rejected))
    return redirect(url_for("admin"))


@app.route("/admin/update/<item_id>", methods=["POST"])
@login_required
def update(item_id):
    check_csrf()
    with _lock:
        items = load_items()
        for it in items:
            if it["id"] == item_id:
                it["title"] = request.form.get("title", "").strip()[:120]
                cat = request.form.get("category", it["category"])
                it["category"] = cat if cat in CATEGORIES else it["category"]
                break
        save_items(items)
    flash("Réalisation mise à jour.")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<item_id>", methods=["POST"])
@login_required
def delete(item_id):
    check_csrf()
    with _lock:
        items = load_items()
        keep = []
        for it in items:
            if it["id"] == item_id:
                for key in ("file", "thumb"):
                    storage.delete_image(it[key])
            else:
                keep.append(it)
        save_items(keep)
    flash("Réalisation supprimée.")
    return redirect(url_for("admin"))


@app.route("/admin/profil", methods=["GET", "POST"])
@login_required
def profile_settings():
    if request.method == "POST":
        check_csrf()
        f = request.form
        with _lock:
            data = load_settings(fresh=True)
            for key in ("name", "phone", "email", "address", "location", "since", "ai_tools"):
                value = f.get(key, "").strip()[:200]
                data["profile"][key] = value or cfg.DEFAULTS["profile"][key]
            for lang in cfg.LANGS:
                data["texts"][lang] = {}
                for key, _, _ in cfg.TEXT_FIELDS:
                    value = f.get(f"text_{lang}_{key}", "").strip()[:2000]
                    if value:
                        data["texts"][lang][key] = value
            th = data["theme"]
            for key in ("primary", "secondary", "accent", "background"):
                th[key] = cfg.clean_color(f.get(key), cfg.DEFAULTS["theme"][key])
            for key in ("font_head", "font_body"):
                th[key] = f.get(key) if f.get(key) in cfg.FONTS else cfg.DEFAULTS["theme"][key]
            data["sections"] = {key: bool(f.get(f"section_{key}")) for key, _ in cfg.SECTIONS}
            save_settings(data)
        flash("Profil et apparence enregistrés.")
        return redirect(url_for("profile_settings"))
    return render_template("profile.html", fonts=cfg.FONTS, langs=cfg.LANGS,
                           text_fields=cfg.TEXT_FIELDS, sections=cfg.SECTIONS)


@app.route("/admin/profil/apparence-defaut", methods=["POST"])
@login_required
def reset_theme():
    check_csrf()
    with _lock:
        data = load_settings(fresh=True)
        data["theme"] = dict(cfg.DEFAULTS["theme"])
        save_settings(data)
    flash("Apparence d'origine restaurée.")
    return redirect(url_for("profile_settings"))


@app.route("/admin/photo", methods=["POST"])
@login_required
def upload_photo():
    check_csrf()
    f = request.files.get("photo")
    try:
        img, _ = process_jpeg(f.read() if f else b"")
    except Exception:
        flash("Photo refusée (JPEG uniquement).")
        return redirect(url_for("profile_settings"))
    img = ImageOps.fit(img, (900, 900), Image.LANCZOS)
    name = f"profile_{uuid.uuid4().hex}.jpg"
    storage.put_image(name, jpeg_bytes(img, 88))
    with _lock:
        data = load_settings(fresh=True)
        old = data["profile"].get("photo")
        data["profile"]["photo"] = name
        save_settings(data)
    if old:
        storage.delete_image(old)
    flash("Photo de profil mise à jour.")
    return redirect(url_for("profile_settings"))


@app.route("/admin/photo/defaut", methods=["POST"])
@login_required
def reset_photo():
    check_csrf()
    with _lock:
        data = load_settings(fresh=True)
        old = data["profile"].get("photo")
        data["profile"]["photo"] = ""
        save_settings(data)
    if old:
        storage.delete_image(old)
    flash("Photo d'origine restaurée.")
    return redirect(url_for("profile_settings"))


@app.route("/api/realisations")
def api_realisations():
    items = load_items()
    return jsonify([dict(it, url=storage.url(it["file"]), thumb_url=storage.url(it["thumb"])) for it in items])


@app.errorhandler(413)
def too_large(_):
    flash("Envoi trop volumineux (60 Mo maximum par envoi).")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
