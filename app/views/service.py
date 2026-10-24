from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.forms import service_form
from app.models import Customers, Services, Teknisi
from app.pagination import ListParams

bp = Blueprint('service', __name__, url_prefix='/service')

STATUS_FILTER = (('belum', 'Belum dijadwalkan'), ('in progress', 'In progress'), ('completed', 'Completed'))


@bp.route('/')
def index():
    params = ListParams(Services.SORTABLE, default_sort='tgl_spk', default_dir='desc',
                        filters=('status', 'teknisi_id'))
    return render_template('service/data-service.html', page=Services().paginate(params), params=params,
                           status_options=STATUS_FILTER, teknisi=Teknisi().all())


@bp.route('/jadwal/<int:customer_id>', methods=['GET', 'POST'])
def create(customer_id):
    customer = Customers().get(customer_id) or abort(404)
    form, errors = {}, {}

    if request.method == 'POST':
        data, errors = service_form(request.form, tgl_spk=customer['tgl_spk'])
        if not errors:
            Services().create(customer_id, data)
            flash(f'Jadwal service untuk "{customer["nama"]}" berhasil dibuat.', 'success')
            return redirect(url_for('service.index'))
        form = request.form

    return render_template('service/tambah-service.html', customer=customer, form=form, errors=errors,
                           teknisi=Teknisi().all()), 422 if errors else 200


@bp.route('/<int:id>/ubah', methods=['GET', 'POST'])
def edit(id):
    services = Services()
    service = services.get(id) or abort(404)
    form, errors = service, {}

    if request.method == 'POST':
        data, errors = service_form(request.form, tgl_spk=service['tgl_spk'], with_status=True)
        if not errors:
            services.update(id, data)
            flash('Data service berhasil diubah.', 'success')
            return redirect(url_for('service.index'))
        form = request.form

    return render_template('service/ubah-service.html', data=service, form=form, errors=errors,
                           teknisi=Teknisi().all(), status_options=STATUS_FILTER[1:]), 422 if errors else 200


@bp.route('/<int:id>/hapus', methods=['POST'])
def delete(id):
    services = Services()
    services.get(id) or abort(404)
    services.delete(id)
    flash('Data service berhasil dihapus.', 'success')
    return redirect(request.referrer or url_for('service.index'))
