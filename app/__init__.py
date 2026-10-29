import logging
import os
from decimal import Decimal
from urllib.parse import urlencode

from flask import Flask, jsonify, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError
from pymysql.err import OperationalError

from app import db, migrate
from app.config import Config
from app.extensions import csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    if hasattr(config_class, 'validate'):
        config_class.validate()
    app.config.from_object(config_class)

    logging.basicConfig(level=logging.DEBUG if app.debug else logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    db.init_app(app)
    csrf.init_app(app)

    register_blueprints(app)
    register_template_helpers(app)
    migrate.register(app)
    register_error_handlers(app)
    register_security_headers(app)

    @app.route('/health')
    def health():
        return jsonify(status='ok')

    return app


def register_blueprints(app):
    from app.views import (account, auth, customer, dashboard, files, karyawan, lampiran, service,
                           service_tambahan)

    for module in (auth, dashboard, customer, service, service_tambahan, karyawan, lampiran, account, files):
        app.register_blueprint(module.bp)


NAV_MENU = (
    ('Home', (('dashboard.index', 'Dashboard', 'dashboard'),)),
    ('Data', (
        ('customer.index', 'Data Customer', 'customer'),
        ('service.index', 'Data Service', 'service'),
        ('service_tambahan.index', 'Service Tambahan', 'service_tambahan'),
        ('karyawan.index', 'Data Karyawan', 'karyawan'),
    )),
    ('Setting', (('account.setting', 'User Setting', 'account'),)),
)


def register_template_helpers(app):
    logo = app.config['APP_LOGO']
    has_logo = bool(logo) and os.path.isfile(os.path.join(app.static_folder, logo))
    if logo and not has_logo:
        app.logger.warning('APP_LOGO "%s" tidak ditemukan di folder static; logo tidak ditampilkan.', logo)

    @app.context_processor
    def inject_globals():
        return {
            'app_logo': url_for('static', filename=logo) if has_logo else None,
            'app_name': app.config['APP_NAME'],
            'current_user': session.get('username'),
            'nav_menu': NAV_MENU,
            'active_section': request.blueprints[0] if request.blueprints else None,
            'per_page_options': app.config['PER_PAGE_OPTIONS'],
        }

    @app.template_filter('tanggal')
    def format_tanggal(value, fmt='%d-%m-%Y'):
        return value.strftime(fmt) if value else '-'

    @app.template_filter('rupiah')
    def format_rupiah(value):
        """1250000 -> 'Rp 1.250.000' (desimal ditampilkan jika ada sen)."""
        if value is None or value == '':
            return '-'
        amount = Decimal(value)
        text = f'{amount:,.2f}' if amount != amount.to_integral_value() else f'{amount:,.0f}'
        return 'Rp ' + text.replace(',', '_').replace('.', ',').replace('_', '.')

    @app.template_filter('ukuran_file')
    def format_ukuran(size):
        if size is None:
            return '-'
        if size < 1024:
            return f'{size} B'
        if size < 1024 * 1024:
            return f'{size / 1024:.0f} KB'
        return f'{size / 1024 / 1024:.1f} MB'

    @app.template_filter('options')
    def to_options(rows, value_key, label_key):
        """List of dict -> [(value, label)] untuk macro select."""
        return [(row[value_key], row[label_key]) for row in rows]

    @app.template_global()
    def url_with(**changes):
        """URL halaman saat ini dengan query string yang diubah (untuk sort/pagination/filter)."""
        args = request.args.to_dict()
        for key, value in changes.items():
            if value is None or value == '':
                args.pop(key, None)
            else:
                args[key] = value
        return request.path + ('?' + urlencode(args) if args else '')


def register_error_handlers(app):
    def wants_json():
        return request.path.startswith('/api/')

    @app.errorhandler(404)
    def not_found(error):
        if wants_json():
            return jsonify(error='Not found'), 404
        return render_template('error/error.html', code=404, title='Halaman tidak ditemukan',
                               message='Halaman yang Anda cari tidak ada atau sudah dipindahkan.'), 404

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template('error/error.html', code=400, title='Sesi form kedaluwarsa',
                               message='Silakan muat ulang halaman lalu coba lagi.'), 400

    @app.errorhandler(413)
    def too_large(error):
        return render_template('error/error.html', code=413, title='File terlalu besar',
                               message=f'Ukuran maksimal {app.config["MAX_CONTENT_LENGTH"] // 1024 // 1024} MB.'), 413

    @app.errorhandler(OperationalError)
    def db_error(error):
        app.logger.exception('Database error')
        if wants_json():
            return jsonify(error='Database tidak dapat diakses'), 503
        return render_template('error/error.html', code=503, title='Database tidak dapat diakses',
                               message='Koneksi ke database gagal. Coba beberapa saat lagi.'), 503

    @app.errorhandler(500)
    def server_error(error):
        if wants_json():
            return jsonify(error='Internal server error'), 500
        return render_template('error/error.html', code=500, title='Terjadi kesalahan',
                               message='Terjadi kesalahan pada server. Silakan coba lagi.'), 500


def register_security_headers(app):
    @app.after_request
    def set_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        if 'username' in session:
            # Halaman yang butuh login jangan di-cache browser (tombol back setelah logout)
            response.headers.setdefault('Cache-Control', 'no-store')
        return response
