from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from pymysql.err import IntegrityError

from app.forms import karyawan_form
from app.models import Teknisi
from app.pagination import ListParams

bp = Blueprint('karyawan', __name__, url_prefix='/karyawan')


def _render_index(status=200, **extra):
    params = ListParams(Teknisi.SORTABLE, default_sort='nama')
    return render_template('karyawan/data-karyawan.html', page=Teknisi().paginate(params), params=params,
                           **extra), status


@bp.route('/')
def index():
    return _render_index()


@bp.route('/tambah', methods=['POST'])
def create():
    data, errors = karyawan_form(request.form)
    if errors:
        return _render_index(422, form=request.form, errors=errors, open_modal=True)
    Teknisi().create(data)
    flash(f'Karyawan "{data["nama"]}" berhasil ditambahkan.', 'success')
    return redirect(url_for('karyawan.index'))


@bp.route('/<int:id>/ubah', methods=['GET', 'POST'])
def edit(id):
    teknisi = Teknisi()
    karyawan = teknisi.get(id) or abort(404)
    form, errors = karyawan, {}

    if request.method == 'POST':
        data, errors = karyawan_form(request.form)
        if not errors:
            teknisi.update(id, data)
            flash('Data karyawan berhasil diubah.', 'success')
            return redirect(url_for('karyawan.index'))
        form = request.form

    return render_template('karyawan/ubah-karyawan.html', data=karyawan, form=form,
                           errors=errors), 422 if errors else 200


@bp.route('/<int:id>/hapus', methods=['POST'])
def delete(id):
    teknisi = Teknisi()
    teknisi.get(id) or abort(404)
    try:
        teknisi.delete(id)
        flash('Karyawan berhasil dihapus.', 'success')
    except IntegrityError:
        flash('Karyawan tidak bisa dihapus karena masih tercatat di data service.', 'danger')
    return redirect(request.referrer or url_for('karyawan.index'))
