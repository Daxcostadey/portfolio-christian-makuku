import json
import os

import requests

BUCKET = os.environ.get("SUPABASE_BUCKET", "realisations")
INDEX_NAME = "data/realisations.json"


class LocalStorage:
    def __init__(self, upload_dir, data_file):
        self.upload_dir = upload_dir
        self.data_file = data_file
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(os.path.dirname(data_file), exist_ok=True)

    def load_items(self):
        if not os.path.exists(self.data_file):
            return []
        with open(self.data_file, encoding="utf-8") as f:
            return json.load(f)

    def save_items(self, items):
        tmp = self.data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.data_file)

    def put_image(self, name, data):
        with open(os.path.join(self.upload_dir, name), "wb") as f:
            f.write(data)

    def delete_image(self, name):
        path = os.path.join(self.upload_dir, name)
        if os.path.exists(path):
            os.remove(path)

    def url(self, name):
        return "/uploads/" + name


class SupabaseStorage:
    def __init__(self, base_url, service_key):
        self.base = base_url.rstrip("/") + "/storage/v1"
        self.public_base = f"{self.base}/object/public/{BUCKET}/"
        self.s = requests.Session()
        self.s.headers.update({"apikey": service_key})
        if not service_key.startswith("sb_"):
            self.s.headers["Authorization"] = f"Bearer {service_key}"
        self._ensure_bucket()

    def _ensure_bucket(self):
        r = self.s.get(f"{self.base}/bucket/{BUCKET}", timeout=20)
        if r.status_code == 200:
            return
        r = self.s.post(f"{self.base}/bucket", json={
            "id": BUCKET, "name": BUCKET, "public": True,
            "allowed_mime_types": ["image/jpeg", "application/json"],
        }, timeout=20)
        if r.status_code not in (200, 201) and "already exists" not in r.text.lower():
            r.raise_for_status()

    def _put(self, name, data, content_type, cache="31536000"):
        r = self.s.post(f"{self.base}/object/{BUCKET}/{name}", data=data, headers={
            "Content-Type": content_type, "x-upsert": "true", "cache-control": cache,
        }, timeout=60)
        r.raise_for_status()

    def load_items(self):
        r = self.s.get(f"{self.base}/object/authenticated/{BUCKET}/{INDEX_NAME}", timeout=20)
        if r.status_code in (400, 404):
            return []
        r.raise_for_status()
        return r.json()

    def save_items(self, items):
        self._put(INDEX_NAME, json.dumps(items, ensure_ascii=False).encode("utf-8"), "application/json", cache="0")

    def put_image(self, name, data):
        self._put(name, data, "image/jpeg")

    def delete_image(self, name):
        self.s.delete(f"{self.base}/object/{BUCKET}", json={"prefixes": [name]}, timeout=20)

    def url(self, name):
        return self.public_base + name


def supabase_url(value):
    value = (value or "").strip().rstrip("/")
    if value and "://" not in value and "." not in value:
        value = f"https://{value}.supabase.co"
    elif value and "://" not in value:
        value = "https://" + value
    return value


def get_storage(base_dir):
    url = supabase_url(os.environ.get("SUPABASE_URL"))
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseStorage(url, key)
    return LocalStorage(
        os.environ.get("UPLOAD_DIR", os.path.join(base_dir, "uploads")),
        os.environ.get("DATA_FILE", os.path.join(base_dir, "data", "realisations.json")),
    )
