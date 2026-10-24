from datetime import date

from flask import Blueprint, jsonify, render_template, request

from app.models import Dashboard

bp = Blueprint('dashboard', __name__)

BULAN = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
         'Agustus', 'September', 'Oktober', 'November', 'Desember')


def _period():
    tahun = request.args.get('tahun', type=int)
    bulan = request.args.get('bulan', type=int)
    if bulan is not None and not 1 <= bulan <= 12:
        bulan = None
    return tahun, bulan


@bp.route('/')
def index():
    dashboard = Dashboard()
    years = dashboard.years()
    tahun, bulan = _period()
    if 'tahun' not in request.args:
        tahun = years[0] if years else date.today().year
    return render_template('home/dashboard.html', years=years, tahun=tahun, bulan=bulan, bulan_list=BULAN,
                           summary=dashboard.summary(tahun, bulan))


@bp.route('/api/dashboard')
def api_summary():
    tahun, bulan = _period()
    return jsonify(Dashboard().summary(tahun, bulan))
