from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from pymysql.err import IntegrityError

from app.forms import customer_form
from app.models import Customers, ServiceTambahan
from app.pagination import ListParams

bp = Blueprint('customer', __name__, url_prefix='/customer')

GARANSI_OPTIONS = [(g, g) for g in Customers.GARANSI]


def _render_index(status=200, **extra):
    params = ListParams(Customers.SORTABLE, default_sort='tgl_spk', default_dir='desc', filters=('garansi',))
    return render_template('customer/data-customer.html', page=Customers().paginate(params), params=params,
                           garansi_options=GARANSI_OPTIONS, **extra), status


@bp.route('/')
def index():
    return _render_index()


@bp.route('/tambah', methods=['POST'])
def create():
    data, errors = customer_form(request.form)
    if errors:
        return _render_index(422, form=request.form, errors=errors, open_modal=True)
    Customers().create(data)
    flash(f'Customer "{data["nama"]}" berhasil ditambahkan.', 'success')
    return redirect(url_for('customer.index'))


@bp.route('/<int:id>/ubah', methods=['GET', 'POST'])
def edit(id):
    customers = Customers()
    customer = customers.get(id) or abort(404)
    form, errors = customer, {}

    if request.method == 'POST':
        data, errors = customer_form(request.form)
        if not errors:
            customers.update(id, data)
            flash('Data customer berhasil diubah.', 'success')
            return redirect(url_for('customer.index'))
        form = request.form

    return render_template('customer/ubah-customer.html', data=customer, form=form, errors=errors,
                           garansi_options=GARANSI_OPTIONS,
                           service_tambahan=ServiceTambahan().by_customer(id)), 422 if errors else 200


@bp.route('/<int:id>/hapus', methods=['POST'])
def delete(id):
    customers = Customers()
    customers.get(id) or abort(404)
    try:
        customers.delete(id)
        flash('Customer berhasil dihapus.', 'success')
    except IntegrityError:
        flash('Customer tidak bisa dihapus karena masih memiliki data service / service tambahan.', 'danger')
    return redirect(request.referrer or url_for('customer.index'))
