"""Validasi input form sederhana. Setiap fungsi return (data, errors)."""
import re
from datetime import date

from app.models import Customers, Services

PHONE_RE = re.compile(r'^[0-9+()\-\s]{6,20}$')


class Form:
    def __init__(self, source):
        self.source = source
        self.data = {}
        self.errors = {}

    def text(self, name, label, required=True, max_length=255):
        value = (self.source.get(name) or '').strip()
        if required and not value:
            self.errors[name] = f'{label} wajib diisi.'
        elif len(value) > max_length:
            self.errors[name] = f'{label} maksimal {max_length} karakter.'
        self.data[name] = value or None
        return value

    def phone(self, name, label, required=True):
        value = self.text(name, label, required=required, max_length=20)
        if value and name not in self.errors and not PHONE_RE.match(value):
            self.errors[name] = f'{label} tidak valid.'
        return value

    def date(self, name, label, required=True):
        raw = (self.source.get(name) or '').strip()
        value = None
        if raw:
            try:
                value = date.fromisoformat(raw)
            except ValueError:
                self.errors[name] = f'{label} tidak valid.'
        elif required:
            self.errors[name] = f'{label} wajib diisi.'
        self.data[name] = value
        return value

    def choice(self, name, label, choices, required=True):
        value = (self.source.get(name) or '').strip()
        if value not in choices:
            if required or value:
                self.errors[name] = f'{label} tidak valid.'
            value = None
        self.data[name] = value
        return value

    def integer(self, name, label, required=True):
        raw = (self.source.get(name) or '').strip()
        value = int(raw) if raw.isdigit() else None
        if value is None and (required or raw):
            self.errors[name] = f'{label} wajib dipilih.'
        self.data[name] = value
        return value

    def result(self):
        return self.data, self.errors


def customer_form(source):
    f = Form(source)
    f.text('no_spk', 'No. SPK', max_length=50)
    f.date('tgl_spk', 'Tanggal SPK')
    f.text('nama', 'Nama customer')
    f.phone('no_tlpn', 'No. telepon')
    f.text('alamat', 'Alamat')
    f.text('sn_indoor', 'SN indoor', max_length=100)
    f.text('model_indoor', 'Model indoor', max_length=100)
    f.text('sn_outdoor', 'SN outdoor', max_length=100)
    f.text('model_outdoor', 'Model outdoor', max_length=100)
    f.text('kerusakan', 'Kerusakan')
    f.choice('garansi', 'Garansi', Customers.GARANSI)
    return f.result()


def service_form(source, tgl_spk=None, with_status=False):
    f = Form(source)
    f.integer('teknisi_id', 'Teknisi')
    kunjungan = f.date('tanggal_kunjungan', 'Tanggal kunjungan')
    selesai = f.date('tanggal_selesai', 'Tanggal selesai')
    f.text('remark_unit', 'Remark unit', required=False)
    if with_status:
        f.choice('status_pekerjaan', 'Status pekerjaan', Services.STATUS)
        f.text('keterangan_service', 'Keterangan service', required=False)

    if kunjungan and selesai and selesai < kunjungan:
        f.errors['tanggal_selesai'] = 'Tanggal selesai tidak boleh sebelum tanggal kunjungan.'
    if kunjungan and tgl_spk and kunjungan < tgl_spk:
        f.errors['tanggal_kunjungan'] = 'Tanggal kunjungan tidak boleh sebelum tanggal SPK.'
    return f.result()


def karyawan_form(source):
    f = Form(source)
    f.text('nama', 'Nama', max_length=100)
    f.phone('no_tlpn', 'No. telepon')
    return f.result()


def password_form(source):
    # Password tidak di-strip: spasi adalah bagian dari password
    f = Form(source)
    current = source.get('password') or ''
    new = source.get('new_password') or ''
    confirm = source.get('confirm_password') or ''
    f.data = {'password': current, 'new_password': new}
    if not current:
        f.errors['password'] = 'Password saat ini wajib diisi.'
    if not new:
        f.errors['new_password'] = 'Password baru wajib diisi.'
    elif len(new) > 128:
        f.errors['new_password'] = 'Password baru maksimal 128 karakter.'
    elif len(new) < 8:
        f.errors['new_password'] = 'Password baru minimal 8 karakter.'
    elif new and new != confirm:
        f.errors['confirm_password'] = 'Konfirmasi password tidak sama.'
    return f.result()
