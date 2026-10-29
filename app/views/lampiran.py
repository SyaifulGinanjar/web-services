from flask import Blueprint, abort, current_app, flash, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from app import storage
from app.models import Lampiran, Services, ServiceTambahan, Teknisi

bp = Blueprint('lampiran', __name__, url_prefix='/lampiran')

# owner_type -> (model pemilik, endpoint halaman ubah)
OWNERS = {
    'teknisi': (Teknisi, 'karyawan.edit'),
    'service': (Services, 'service.edit'),
    'service_tambahan': (ServiceTambahan, 'service_tambahan.edit'),
}


def _owner_page(owner_type, owner_id):
    if owner_type not in OWNERS:
        abort(404)
    model, endpoint = OWNERS[owner_type]
    model().get(owner_id) or abort(404)
    return url_for(endpoint, id=owner_id)


@bp.route('/<owner_type>/<int:owner_id>', methods=['POST'])
def upload(owner_type, owner_id):
    back = _owner_page(owner_type, owner_id)
    file = request.files.get('file')
    if not file or not file.filename:
        flash('Pilih file terlebih dahulu.', 'danger')
        return redirect(back)

    data = file.read()
    if not data:
        flash('File kosong.', 'danger')
        return redirect(back)
    # Cek ekstensi DAN isi file (magic bytes), bukan hanya nama file
    detected = storage.detect_type(file.filename, data[:16])
    if not detected:
        flash('File harus PDF, JPG, atau PNG yang valid.', 'danger')
        return redirect(back)

    ext, content_type = detected
    nama_file = secure_filename(file.filename) or f'lampiran.{ext}'
    try:
        key = storage.save(data, ext, content_type)
    except Exception:
        current_app.logger.exception('Gagal menyimpan lampiran')
        flash('File gagal disimpan. Coba lagi beberapa saat.', 'danger')
        return redirect(back)

    Lampiran().create({
        'owner_type': owner_type, 'owner_id': owner_id, 'nama_file': nama_file[:255],
        'storage_key': key, 'content_type': content_type, 'ukuran': len(data),
        'keterangan': (request.form.get('keterangan') or '').strip()[:100] or None,
        'uploaded_by': session.get('username', '-'),
    })
    flash(f'File "{nama_file}" berhasil diupload.', 'success')
    return redirect(back)


@bp.route('/<int:id>')
def show(id):
    row = Lampiran().get(id) or abort(404)
    response = storage.serve(row['storage_key'], row['nama_file'], as_attachment=bool(request.args.get('download')))
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@bp.route('/<int:id>/hapus', methods=['POST'])
def delete(id):
    lampiran = Lampiran()
    row = lampiran.get(id) or abort(404)
    lampiran.delete(id)
    flash(f'File "{row["nama_file"]}" berhasil dihapus.', 'success')
    model, endpoint = OWNERS.get(row['owner_type'], (None, None))
    if endpoint and model().get(row['owner_id']):
        return redirect(url_for(endpoint, id=row['owner_id']))
    return redirect(request.referrer or url_for('dashboard.index'))
