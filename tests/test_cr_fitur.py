"""Test fitur CR: service tambahan, biaya Out of Warranty, lampiran, dashboard, logo.
Model di-monkeypatch supaya test tidak butuh database."""
import io
from datetime import date, datetime
from decimal import Decimal

import pytest

from app import models, storage
from app.forms import service_form, service_tambahan_form
from app.pagination import Page

OOW, UW = 'Out Of Warranty', 'Under Warranty'

CUSTOMER = {'id': 7, 'no_spk': 'SPK-001', 'tgl_spk': date(2026, 1, 10), 'nama': 'Budi', 'alamat': 'Jl. Merdeka',
            'no_tlpn': '0812345678', 'garansi': OOW}
TAMBAHAN = {'id': 3, 'customer_id': 7, 'no_spk_baru': 'SPK-001-B', 'tgl_spk': date(2026, 2, 1), 'teknisi_id': 1,
            'tanggal_kunjungan': date(2026, 2, 2), 'tanggal_selesai': date(2026, 2, 3), 'remark_unit': 'Bocor',
            'status_pekerjaan': 'completed', 'keterangan': 'Ganti pipa', 'biaya': Decimal('1250000.00'),
            'no_spk_lama': 'SPK-001', 'nama': 'Budi', 'alamat': 'Jl. Merdeka', 'no_tlpn': '0812345678',
            'garansi': OOW, 'teknisi_nama': 'Arman', 'waktu_service': 3, 'jumlah_lampiran': 2}
LAMPIRAN = [
    {'id': 1, 'nama_file': 'foto.jpg', 'content_type': 'image/jpeg', 'ukuran': 2048, 'keterangan': 'Foto unit',
     'uploaded_by': 'admin', 'created_at': datetime(2026, 2, 3, 10, 0), 'storage_key': 'a.jpg'},
    {'id': 2, 'nama_file': 'ba.pdf', 'content_type': 'application/pdf', 'ukuran': 3 * 1024 * 1024,
     'keterangan': None, 'uploaded_by': 'admin', 'created_at': datetime(2026, 2, 3, 11, 0), 'storage_key': 'b.pdf'},
]

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
PDF = b'%PDF-1.7\n' + b'\x00' * 32


def tambahan_form(**overrides):
    form = {'no_spk_baru': 'SPK-002', 'tgl_spk': '2026-02-01', 'status_pekerjaan': 'completed',
            'teknisi_id': '1', 'tanggal_kunjungan': '2026-02-02', 'tanggal_selesai': '2026-02-03',
            'remark_unit': '', 'keterangan': '', 'biaya': '1.250.000'}
    form.update(overrides)
    return form


# ------------------------------------------------------------------ Forms
def test_service_tambahan_form_valid_out_of_warranty():
    data, errors = service_tambahan_form(tambahan_form(), tgl_spk_lama=date(2026, 1, 10), garansi=OOW)
    assert errors == {}
    assert data['biaya'] == Decimal('1250000.00')
    assert data['status_pekerjaan'] == 'completed'


def test_service_tambahan_belum_dijadwalkan_boleh_tanpa_teknisi_dan_tanggal():
    form = tambahan_form(status_pekerjaan='belum', teknisi_id='', tanggal_kunjungan='', tanggal_selesai='', biaya='')
    data, errors = service_tambahan_form(form, garansi=OOW)
    assert errors == {}
    assert data['status_pekerjaan'] is None  # disimpan sebagai NULL


def test_service_tambahan_completed_wajib_lengkap():
    form = tambahan_form(teknisi_id='', tanggal_kunjungan='', tanggal_selesai='', biaya='')
    _, errors = service_tambahan_form(form, garansi=OOW)
    assert {'teknisi_id', 'tanggal_kunjungan', 'tanggal_selesai', 'biaya'} <= set(errors)


def test_service_tambahan_urutan_tanggal():
    form = tambahan_form(tgl_spk='2026-01-05', tanggal_kunjungan='2026-01-04', tanggal_selesai='2026-01-03')
    _, errors = service_tambahan_form(form, tgl_spk_lama=date(2026, 1, 10), garansi=UW)
    assert {'tgl_spk', 'tanggal_kunjungan', 'tanggal_selesai'} <= set(errors)


@pytest.mark.parametrize('raw, expected', [
    ('1250000', Decimal('1250000.00')),
    ('Rp 1.250.000', Decimal('1250000.00')),
    ('1.250.000,50', Decimal('1250000.50')),
    ('0', Decimal('0.00')),
])
def test_biaya_format_diterima(raw, expected):
    data, errors = service_tambahan_form(tambahan_form(biaya=raw), garansi=OOW)
    assert errors == {}
    assert data['biaya'] == expected


@pytest.mark.parametrize('raw', ['abc', '-5', 'NaN', '99999999999999'])
def test_biaya_tidak_valid(raw):
    _, errors = service_tambahan_form(tambahan_form(biaya=raw), garansi=OOW)
    assert 'biaya' in errors


def test_biaya_diabaikan_untuk_under_warranty():
    data, errors = service_tambahan_form(tambahan_form(biaya='500000'), garansi=UW)
    assert errors == {}
    assert data['biaya'] is None


def test_service_form_biaya_wajib_saat_completed_oow():
    form = {'teknisi_id': '1', 'tanggal_kunjungan': '2026-01-12', 'tanggal_selesai': '2026-01-12',
            'status_pekerjaan': 'completed'}
    assert 'biaya' in service_form(form, with_status=True, garansi=OOW)[1]
    assert 'biaya' not in service_form({**form, 'status_pekerjaan': 'in progress'}, with_status=True,
                                       garansi=OOW)[1]
    assert service_form(form, with_status=True, garansi=UW)[0]['biaya'] is None


# --------------------------------------------------------------- Filters
def test_rupiah_filter(app):
    rupiah = app.jinja_env.filters['rupiah']
    assert rupiah(Decimal('1250000.00')) == 'Rp 1.250.000'
    assert rupiah(Decimal('1250000.50')) == 'Rp 1.250.000,50'
    assert rupiah(0) == 'Rp 0'
    assert rupiah(None) == '-'


# --------------------------------------------------------------- Storage
def test_detect_type_cek_isi_file():
    assert storage.detect_type('foto.PNG', PNG) == ('png', 'image/png')
    assert storage.detect_type('ba.pdf', PDF) == ('pdf', 'application/pdf')
    assert storage.detect_type('palsu.pdf', PNG) is None  # ekstensi benar, isi salah
    assert storage.detect_type('script.exe', b'MZ') is None
    assert storage.detect_type('tanpa-ekstensi', PDF) is None


def test_local_storage_save_serve_delete(app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.test_request_context():
        key = storage.save(PDF, 'pdf', 'application/pdf')
        assert (tmp_path / 'lampiran' / key).read_bytes() == PDF
        response = storage.serve(key, 'ba.pdf', as_attachment=True)
        assert 'attachment' in response.headers['Content-Disposition']
        response.close()
        storage.delete(key)
        assert not (tmp_path / 'lampiran' / key).exists()


# ------------------------------------------------------- Halaman (render)
@pytest.fixture
def fake_db(monkeypatch):
    page = Page([TAMBAHAN], total=1, page=1, per_page=10)
    stubs = {
        (models.ServiceTambahan, 'paginate'): lambda self, params: page,
        (models.ServiceTambahan, 'get'): lambda self, id: TAMBAHAN if id == 3 else None,
        (models.ServiceTambahan, 'by_customer'): lambda self, customer_id: [TAMBAHAN],
        (models.ServiceTambahan, 'spk_exists'): lambda self, no, exclude_id=None: no == 'DIPAKAI',
        (models.Customers, 'get'): lambda self, id: CUSTOMER if id == 7 else None,
        (models.Customers, 'search'): lambda self, q, limit=10: [CUSTOMER],
        (models.Teknisi, 'all'): lambda self: [{'id': 1, 'nama': 'Arman'}],
        (models.Teknisi, 'get'): lambda self, id: {'id': 1, 'nama': 'Arman', 'no_tlpn': '0812'} if id == 1 else None,
        (models.Lampiran, 'list'): lambda self, owner_type, owner_id: LAMPIRAN,
        (models.Services, 'get'): lambda self, id: {
            'id': 5, 'customer_id': 7, 'teknisi_id': 1, 'tanggal_kunjungan': date(2026, 1, 11),
            'tanggal_selesai': date(2026, 1, 12), 'remark_unit': '', 'status_pekerjaan': 'completed',
            'keterangan_service': '', 'biaya': Decimal('300000'), 'nama': 'Budi', 'no_spk': 'SPK-001',
            'tgl_spk': date(2026, 1, 10), 'garansi': OOW} if id == 5 else None,
    }
    calls = {}
    for (cls, name), fn in stubs.items():
        monkeypatch.setattr(cls, name, fn)

    def record(name):
        def fn(self, *args):
            calls.setdefault(name, []).append(args)
            return 99
        return fn

    monkeypatch.setattr(models.ServiceTambahan, 'create', record('tambahan.create'))
    monkeypatch.setattr(models.Lampiran, 'create', record('lampiran.create'))
    return calls


def test_halaman_service_tambahan_render(auth_client, fake_db):
    html = auth_client.get('/service-tambahan/').get_data(as_text=True)
    for text in ('SPK-001-B', 'SPK-001', 'Budi', 'Arman', '3 hari', 'Completed', 'Rp 1.250.000', 'Service Tambahan'):
        assert text in html

    assert 'SPK-001' in auth_client.get('/service-tambahan/tambah?q=SPK').get_data(as_text=True)
    form_html = auth_client.get('/service-tambahan/tambah/7').get_data(as_text=True)
    assert 'name="biaya"' in form_html  # customer Out of Warranty
    edit = auth_client.get('/service-tambahan/3/ubah')
    assert edit.status_code == 200
    assert 'foto.jpg' in edit.get_data(as_text=True) and 'Lampiran' in edit.get_data(as_text=True)
    assert auth_client.get('/service-tambahan/tambah/999').status_code == 404


def test_tambah_service_tambahan(auth_client, fake_db):
    response = auth_client.post('/service-tambahan/tambah/7', data=tambahan_form())
    assert response.status_code == 302
    customer_id, data = fake_db['tambahan.create'][0]
    assert customer_id == 7 and data['no_spk_baru'] == 'SPK-002'

    dobel = auth_client.post('/service-tambahan/tambah/7', data=tambahan_form(no_spk_baru='DIPAKAI'))
    assert dobel.status_code == 422 and 'sudah dipakai' in dobel.get_data(as_text=True)
    sama = auth_client.post('/service-tambahan/tambah/7', data=tambahan_form(no_spk_baru='SPK-001'))
    assert 'tidak boleh sama' in sama.get_data(as_text=True)


def test_halaman_lain_render(auth_client, fake_db):
    assert 'Lampiran' in auth_client.get('/karyawan/1/ubah').get_data(as_text=True)
    service_html = auth_client.get('/service/5/ubah').get_data(as_text=True)
    assert 'name="biaya"' in service_html and 'value="300.000"' in service_html


def test_upload_lampiran(app, auth_client, fake_db, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = auth_client.post('/lampiran/teknisi/1', data={'file': (io.BytesIO(PNG), 'ktp.png'),
                                                             'keterangan': 'KTP'},
                                content_type='multipart/form-data')
    assert response.status_code == 302 and response.headers['Location'].endswith('/karyawan/1/ubah')
    (saved,) = fake_db['lampiran.create'][0]
    assert saved['nama_file'] == 'ktp.png' and saved['keterangan'] == 'KTP' and saved['uploaded_by'] == 'admin'
    assert (tmp_path / 'lampiran' / saved['storage_key']).exists()


def test_upload_lampiran_ditolak(app, auth_client, fake_db, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    auth_client.post('/lampiran/teknisi/1', data={'file': (io.BytesIO(PNG), 'virus.exe')},
                     content_type='multipart/form-data')
    auth_client.post('/lampiran/teknisi/1', data={'file': (io.BytesIO(b'bukan pdf'), 'palsu.pdf')},
                     content_type='multipart/form-data')
    assert 'lampiran.create' not in fake_db
    assert auth_client.post('/lampiran/bukan_owner/1').status_code == 404
    assert auth_client.post('/lampiran/teknisi/999', data={}).status_code == 404


def test_lampiran_wajib_login(client):
    assert client.get('/lampiran/1').status_code == 302
    assert client.post('/lampiran/teknisi/1').status_code in (302, 400)


def test_dashboard_render_rekap_tambahan(auth_client, monkeypatch):
    summary = {
        'totals': {'total_customer': 10, 'total_pekerjaan': 8, 'selesai': 5, 'proses': 3, 'belum_dijadwalkan': 2},
        'kpi': {'kunjungan_ok': 1, 'kunjungan_gagal': 0, 'selesai_ok': 1, 'selesai_gagal': 0},
        'garansi': [], 'teknisi': [], 'unit': [], 'batas': {'kunjungan': 1, 'selesai': 3},
        'tambahan': {'total_customer': 4, 'total_pekerjaan': 6, 'selesai': 2, 'proses': 3, 'belum_dijadwalkan': 1},
        'biaya_oow': {'service': 300000, 'tambahan': 1250000, 'total': 1550000, 'jumlah': 2},
        'biaya_teknisi': [{'id': 1, 'nama': 'Arman', 'jumlah': 3, 'service': 300000, 'tambahan': 1250000,
                           'total': 1550000},
                          {'id': 2, 'nama': 'Dedi', 'jumlah': 1, 'service': 0, 'tambahan': 400000, 'total': 400000}],
    }
    monkeypatch.setattr(models.Dashboard, 'years', lambda self: [2026])
    monkeypatch.setattr(models.Dashboard, 'summary', lambda self, tahun=None, bulan=None: summary)
    html = auth_client.get('/').get_data(as_text=True)
    assert 'Service Tambahan' in html and 'Rp 1.550.000' in html
    assert '/service-tambahan/?status=belum' in html
    assert 'per Karyawan' in html and 'Arman' in html
    assert 'Rp 1.950.000' in html and 'Rp 1.650.000' in html  # total gabungan & total service tambahan

    summary['biaya_teknisi'] = []
    assert 'Belum ada data untuk periode ini' in auth_client.get('/').get_data(as_text=True)


def test_logo_tampil_di_login(client):
    html = client.get('/login').get_data(as_text=True)
    assert 'class="login-logo' in html and '/static/img/logo.jpg' in html
