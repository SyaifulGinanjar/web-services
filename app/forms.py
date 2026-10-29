"""Validasi input form sederhana. Setiap fungsi return (data, errors)."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.models import Customers, Services, ServiceTambahan

PHONE_RE = re.compile(r'^[0-9+()\-\s]{6,20}$')
MAX_MONEY = Decimal('10000000000000')  # batas DECIMAL(15,2)
OUT_OF_WARRANTY = 'Out Of Warranty'


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

    def money(self, name, label, required=True):
        """Nominal Rupiah: menerima '1250000', '1.250.000', 'Rp 1.250.000,50'."""
        raw = (self.source.get(name) or '').strip()
        value = None
        if raw:
            cleaned = raw.lower().replace('rp', '').replace(' ', '').replace('.', '').replace(',', '.')
            try:
                value = Decimal(cleaned)
            except InvalidOperation:
                self.errors[name] = f'{label} harus berupa angka.'
            else:
                if not value.is_finite() or value < 0:
                    self.errors[name] = f'{label} tidak boleh negatif.'
                elif value >= MAX_MONEY:
                    self.errors[name] = f'{label} terlalu besar.'
                value = value.quantize(Decimal('0.01')) if name not in self.errors else None
        elif required:
            self.errors[name] = f'{label} wajib diisi.'
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


def _biaya(f, garansi, status):
    """Biaya hanya untuk Out of Warranty; wajib saat pekerjaan selesai."""
    if garansi == OUT_OF_WARRANTY:
        f.money('biaya', 'Biaya', required=status == 'completed')
    else:
        f.data['biaya'] = None


def service_form(source, tgl_spk=None, with_status=False, garansi=None):
    f = Form(source)
    f.integer('teknisi_id', 'Teknisi')
    kunjungan = f.date('tanggal_kunjungan', 'Tanggal kunjungan')
    selesai = f.date('tanggal_selesai', 'Tanggal selesai')
    f.text('remark_unit', 'Remark unit', required=False)
    status = None
    if with_status:
        status = f.choice('status_pekerjaan', 'Status pekerjaan', Services.STATUS)
        f.text('keterangan_service', 'Keterangan service', required=False)
    _biaya(f, garansi, status)

    if kunjungan and selesai and selesai < kunjungan:
        f.errors['tanggal_selesai'] = 'Tanggal selesai tidak boleh sebelum tanggal kunjungan.'
    if kunjungan and tgl_spk and kunjungan < tgl_spk:
        f.errors['tanggal_kunjungan'] = 'Tanggal kunjungan tidak boleh sebelum tanggal SPK.'
    return f.result()


def service_tambahan_form(source, tgl_spk_lama=None, garansi=None):
    f = Form(source)
    f.text('no_spk_baru', 'No. SPK Baru', max_length=50)
    tgl_spk = f.date('tgl_spk', 'Tanggal SPK')
    status = f.choice('status_pekerjaan', 'Status', ServiceTambahan.STATUS)
    dijadwalkan = status in ('in progress', 'completed')

    f.integer('teknisi_id', 'Teknisi', required=dijadwalkan)
    kunjungan = f.date('tanggal_kunjungan', 'Tanggal kunjungan', required=dijadwalkan)
    selesai = f.date('tanggal_selesai', 'Tanggal selesai', required=status == 'completed')
    f.text('remark_unit', 'Remark unit', required=False)
    f.text('keterangan', 'Keterangan', required=False, max_length=1000)
    _biaya(f, garansi, status)

    if tgl_spk and tgl_spk_lama and tgl_spk < tgl_spk_lama:
        f.errors['tgl_spk'] = 'Tanggal SPK baru tidak boleh sebelum tanggal SPK lama.'
    if kunjungan and tgl_spk and kunjungan < tgl_spk:
        f.errors['tanggal_kunjungan'] = 'Tanggal kunjungan tidak boleh sebelum tanggal SPK.'
    if selesai and kunjungan and selesai < kunjungan:
        f.errors['tanggal_selesai'] = 'Tanggal selesai tidak boleh sebelum tanggal kunjungan.'
    if selesai and not kunjungan and 'tanggal_kunjungan' not in f.errors:
        f.errors['tanggal_kunjungan'] = 'Isi tanggal kunjungan terlebih dahulu.'

    # 'belum' disimpan sebagai NULL di database
    if status == 'belum':
        f.data['status_pekerjaan'] = None
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
