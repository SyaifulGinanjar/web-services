"""Penyimpanan file lampiran.

- local: file disimpan di UPLOAD_FOLDER/lampiran (untuk development).
- blob : Vercel Blob. Filesystem Vercel tidak permanen, jadi production wajib memakai ini.

`save()` mengembalikan storage_key yang disimpan di tabel lampiran:
nama file untuk local, URL blob untuk blob.
"""
import json
import os
import uuid
from urllib.request import Request, urlopen

from flask import current_app, redirect, send_from_directory

BLOB_API = 'https://blob.vercel-storage.com'
BLOB_API_VERSION = '7'

# Ekstensi -> (content type, magic bytes di awal file)
FILE_TYPES = {
    'pdf': ('application/pdf', (b'%PDF-',)),
    'png': ('image/png', (b'\x89PNG\r\n\x1a\n',)),
    'jpg': ('image/jpeg', (b'\xff\xd8\xff',)),
    'jpeg': ('image/jpeg', (b'\xff\xd8\xff',)),
}


def detect_type(filename, head):
    """Return (ext, content_type) jika ekstensi DAN isi file cocok, selain itu None."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in FILE_TYPES:
        return None
    content_type, signatures = FILE_TYPES[ext]
    if not head.startswith(signatures):
        return None
    return ext, content_type


def _local_dir():
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'lampiran')
    os.makedirs(folder, exist_ok=True)
    return folder


def _blob_request(url, method, data=None, headers=None):
    request = Request(url, data=data, method=method, headers={
        'authorization': f'Bearer {current_app.config["BLOB_READ_WRITE_TOKEN"]}',
        'x-api-version': BLOB_API_VERSION,
        **(headers or {}),
    })
    with urlopen(request, timeout=30) as response:
        body = response.read()
    return json.loads(body) if body else {}


def save(data, ext, content_type):
    name = f'{uuid.uuid4().hex}.{ext}'
    if current_app.config['STORAGE_BACKEND'] == 'blob':
        result = _blob_request(f'{BLOB_API}/lampiran/{name}', 'PUT', data=data,
                               headers={'x-content-type': content_type})
        return result['url']
    with open(os.path.join(_local_dir(), name), 'wb') as file:
        file.write(data)
    return name


def delete(key):
    if current_app.config['STORAGE_BACKEND'] == 'blob':
        _blob_request(f'{BLOB_API}/delete', 'POST', data=json.dumps({'urls': [key]}).encode(),
                      headers={'content-type': 'application/json'})
        return
    path = os.path.join(_local_dir(), os.path.basename(key))
    if os.path.exists(path):
        os.remove(path)


def serve(key, download_name, as_attachment):
    """Response untuk mengirim file ke user (route pemanggil sudah memastikan user login)."""
    if current_app.config['STORAGE_BACKEND'] == 'blob':
        return redirect(f'{key}?download=1' if as_attachment else key)
    return send_from_directory(_local_dir(), os.path.basename(key), as_attachment=as_attachment,
                               download_name=download_name)
