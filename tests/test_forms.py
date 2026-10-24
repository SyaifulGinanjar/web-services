from datetime import date

from app.forms import customer_form, karyawan_form, password_form, service_form

VALID_CUSTOMER = {
    'no_spk': 'SPK-001', 'tgl_spk': '2026-01-10', 'nama': 'Budi', 'no_tlpn': '0812-3456-789',
    'alamat': 'Jl. Merdeka', 'sn_indoor': 'A1', 'model_indoor': 'FTKQ', 'sn_outdoor': 'B1',
    'model_outdoor': 'RKQ', 'kerusakan': 'Tidak dingin', 'garansi': 'Under Warranty',
}


def test_customer_form_valid():
    data, errors = customer_form(VALID_CUSTOMER)
    assert errors == {}
    assert data['tgl_spk'] == date(2026, 1, 10)


def test_customer_form_rejects_bad_input():
    _, errors = customer_form({**VALID_CUSTOMER, 'nama': '  ', 'tgl_spk': '10/01/2026',
                               'no_tlpn': 'abc', 'garansi': 'Lifetime'})
    assert set(errors) == {'nama', 'tgl_spk', 'no_tlpn', 'garansi'}


def test_service_form_date_order():
    form = {'teknisi_id': '1', 'tanggal_kunjungan': '2026-01-12', 'tanggal_selesai': '2026-01-11'}
    _, errors = service_form(form, tgl_spk=date(2026, 1, 13))
    assert 'tanggal_selesai' in errors
    assert 'tanggal_kunjungan' in errors


def test_service_form_status_required_on_edit():
    form = {'teknisi_id': '1', 'tanggal_kunjungan': '2026-01-12', 'tanggal_selesai': '2026-01-12'}
    _, errors = service_form(form, with_status=True)
    assert 'status_pekerjaan' in errors


def test_karyawan_form():
    assert karyawan_form({'nama': 'Arman', 'no_tlpn': '0812345678'})[1] == {}


def test_password_form():
    assert 'new_password' in password_form({'password': 'x', 'new_password': 'short', 'confirm_password': 'short'})[1]
    assert 'confirm_password' in password_form({'password': 'x', 'new_password': 'longenough',
                                                'confirm_password': 'different'})[1]
    assert password_form({'password': 'x', 'new_password': 'longenough', 'confirm_password': 'longenough'})[1] == {}
