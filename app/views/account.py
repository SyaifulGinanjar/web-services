from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.forms import password_form
from app.models import Users

bp = Blueprint('account', __name__, url_prefix='/akun')


@bp.route('/setting', methods=['GET', 'POST'])
def setting():
    errors = {}
    if request.method == 'POST':
        data, errors = password_form(request.form)
        if not errors:
            try:
                if Users().change_password(session['username'], data['password'], data['new_password']):
                    flash('Password berhasil diganti.', 'success')
                    return redirect(url_for('account.setting'))
                errors['password'] = 'Password saat ini salah.'
            except RuntimeError as exc:
                current_app.logger.error('Gagal ganti password: %s', exc)
                flash('Password gagal diganti. Hubungi administrator.', 'danger')
    return render_template('account/user-setting.html', errors=errors), 422 if errors else 200
