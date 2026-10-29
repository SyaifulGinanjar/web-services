from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.forms import service_tambahan_form
from app.models import Customers, Lampiran, ServiceTambahan, Teknisi
from app.pagination import ListParams

bp = Blueprint('service_tambahan', __name__, url_prefix='/service-tambahan')

STATUS_OPTIONS = (('belum', 'Belum dijadwalkan'), ('in progress', 'In progress'), ('completed', 'Completed'))


def _validate(customer, exclude_id=None):
    data, errors = service_tambahan_form(request.form, tgl_spk_lama=customer['tgl_spk'],
                                         garansi=customer['garansi'])
    if 'no_spk_baru' not in errors and data['no_spk_baru'] == customer['no_spk']:
        errors['no_spk_baru'] = 'No. SPK Baru tidak boleh sama dengan No. SPK Lama.'
    elif 'no_spk_baru' not in errors and ServiceTambahan().spk_exists(data['no_spk_baru'], exclude_id):
        errors['no_spk_baru'] = 'No. SPK Baru sudah dipakai.'
    return data, errors


def _form_page(template, status=200, **context):
    return render_template(template, teknisi=Teknisi().all(), status_options=STATUS_OPTIONS,
                           **context), status


@bp.route('/')
def index():
    params = ListParams(ServiceTambahan.SORTABLE, default_sort='tgl_spk', default_dir='desc',
                        filters=('status', 'teknisi_id'))
    return render_template('service_tambahan/data-service-tambahan.html',
                           page=ServiceTambahan().paginate(params), params=params,
                           status_options=STATUS_OPTIONS, teknisi=Teknisi().all())


@bp.route('/tambah')
def pick_customer():
    """Langkah 1: cari dan pilih SPK lama."""
    q = (request.args.get('q') or '').strip()[:50]
    return render_template('service_tambahan/pilih-spk.html', q=q,
                           results=Customers().search(q, limit=20) if q else [])


@bp.route('/tambah/<int:customer_id>', methods=['GET', 'POST'])
def create(customer_id):
    """Langkah 2: isi data service tambahan untuk SPK lama yang dipilih."""
    customer = Customers().get(customer_id) or abort(404)
    form, errors = {'status_pekerjaan': 'belum'}, {}

    if request.method == 'POST':
        data, errors = _validate(customer)
        if not errors:
            ServiceTambahan().create(customer_id, data)
            flash(f'Service tambahan "{data["no_spk_baru"]}" untuk "{customer["nama"]}" berhasil dibuat.',
                  'success')
            return redirect(url_for('service_tambahan.index'))
        form = request.form

    return _form_page('service_tambahan/tambah-service-tambahan.html', 422 if errors else 200,
                      customer=customer, form=form, errors=errors, garansi=customer['garansi'])


@bp.route('/<int:id>/ubah', methods=['GET', 'POST'])
def edit(id):
    services = ServiceTambahan()
    service = services.get(id) or abort(404)
    customer = Customers().get(service['customer_id'])
    form, errors = dict(service, status_pekerjaan=service['status_pekerjaan'] or 'belum'), {}

    if request.method == 'POST':
        data, errors = _validate(customer, exclude_id=id)
        if not errors:
            services.update(id, data)
            flash('Data service tambahan berhasil diubah.', 'success')
            return redirect(url_for('service_tambahan.index'))
        form = request.form

    return _form_page('service_tambahan/ubah-service-tambahan.html', 422 if errors else 200,
                      data=service, customer=customer, form=form, errors=errors, garansi=customer['garansi'],
                      lampiran=Lampiran().list('service_tambahan', id), lampiran_owner=('service_tambahan', id))


@bp.route('/<int:id>/hapus', methods=['POST'])
def delete(id):
    services = ServiceTambahan()
    services.get(id) or abort(404)
    services.delete(id)
    flash('Data service tambahan berhasil dihapus.', 'success')
    return redirect(request.referrer or url_for('service_tambahan.index'))
