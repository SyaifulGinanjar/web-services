from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.extensions import login_limiter
from app.models import Users

bp = Blueprint('auth', __name__)

PUBLIC_ENDPOINTS = {'auth.login', 'static', 'health'}


@bp.before_app_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if 'username' not in session:
        return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
    return None


def _safe_next(target):
    # Hanya izinkan redirect ke path internal (cegah open redirect)
    if not target or not target.startswith('/') or target.startswith('//'):
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        key = f'{request.remote_addr}:{username.lower()}'

        if login_limiter.blocked(key):
            flash('Terlalu banyak percobaan login. Coba lagi beberapa menit lagi.', 'danger')
            return render_template('auth/login.html', username=username), 429

        if username and password and Users().authenticate(username, password):
            login_limiter.reset(key)
            session.clear()  # cegah session fixation
            session.permanent = True
            session['username'] = username
            return redirect(_safe_next(request.args.get('next')) or url_for('dashboard.index'))

        login_limiter.hit(key)
        flash('Username atau password salah.', 'danger')
        return render_template('auth/login.html', username=username), 401

    return render_template('auth/login.html')


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('auth.login'))
