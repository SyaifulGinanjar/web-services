import hmac
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import execute, fetch_all, fetch_one, get_db
from app.pagination import Page

# Batas KPI (hari sejak tanggal SPK)
KPI_KUNJUNGAN_MAKS_HARI = 1
KPI_SELESAI_MAKS_HARI = 3


def paginate(params, select, from_where, args=(), tiebreak='id'):
    total = fetch_one(f'select count(*) as total {from_where}', args)['total']
    page = Page([], total, params.page, params.per_page)
    offset = (page.page - 1) * page.per_page
    page.items = fetch_all(
        f'select {select} {from_where} order by {params.order_by}, {tiebreak} desc limit %s offset %s',
        (*args, page.per_page, offset),
    )
    return page


def to_int(row):
    """SUM() di MySQL menghasilkan Decimal/None; ubah ke int agar bisa di-JSON-kan."""
    return {k: int(v) if isinstance(v, Decimal) else (0 if v is None else v) for k, v in row.items()}


# Customer
class Customers:
    FIELDS = ('no_spk', 'nama', 'alamat', 'no_tlpn', 'sn_indoor', 'model_indoor',
              'sn_outdoor', 'model_outdoor', 'tgl_spk', 'kerusakan', 'garansi')
    SORTABLE = {
        'no_spk': 'no_spk', 'tgl_spk': 'tgl_spk', 'nama': 'nama', 'alamat': 'alamat',
        'garansi': 'garansi', 'model_indoor': 'model_indoor',
    }
    GARANSI = ('Under Warranty', 'Out Of Warranty')

    def paginate(self, params):
        where, args = ['1=1'], []
        if params.q:
            where.append('(no_spk like %s or nama like %s or alamat like %s or no_tlpn like %s '
                         'or sn_indoor like %s or sn_outdoor like %s or model_indoor like %s '
                         'or model_outdoor like %s or kerusakan like %s)')
            args += [params.like] * 9
        if params.filters.get('garansi') in self.GARANSI:
            where.append('garansi = %s')
            args.append(params.filters['garansi'])
        return paginate(params, '*', f"from customer where {' and '.join(where)}", tuple(args))

    def get(self, id):
        return fetch_one('select * from customer where id = %s', (id,))

    def create(self, data):
        columns = ', '.join(self.FIELDS)
        placeholders = ', '.join(['%s'] * len(self.FIELDS))
        return execute(f'insert into customer ({columns}) values ({placeholders})',
                       tuple(data[f] for f in self.FIELDS))

    def update(self, id, data):
        assignments = ', '.join(f'{f} = %s' for f in self.FIELDS)
        execute(f'update customer set {assignments} where id = %s',
                (*(data[f] for f in self.FIELDS), id))

    def delete(self, id):
        execute('delete from customer where id = %s', (id,))


# Service
class Services:
    STATUS = ('in progress', 'completed')
    SORTABLE = {
        'no_spk': 'c.no_spk', 'nama': 'c.nama', 'tgl_spk': 'c.tgl_spk',
        'tanggal_kunjungan': 's.tanggal_kunjungan', 'tanggal_selesai': 's.tanggal_selesai',
        'teknisi': 't.nama', 'waktu_service': 'waktu_service', 'status': 's.status_pekerjaan',
    }

    def paginate(self, params):
        where, args = ['1=1'], []
        if params.q:
            where.append('(c.no_spk like %s or c.nama like %s or c.alamat like %s or c.no_tlpn like %s '
                         'or s.remark_unit like %s or t.nama like %s or s.keterangan_service like %s)')
            args += [params.like] * 7

        status = params.filters.get('status')
        if status == 'belum':
            where.append('s.id is null')
        elif status in self.STATUS:
            where.append('s.status_pekerjaan = %s')
            args.append(status)

        teknisi_id = params.filters.get('teknisi_id')
        if teknisi_id and teknisi_id.isdigit():
            where.append('s.teknisi_id = %s')
            args.append(int(teknisi_id))

        select = '''c.id as customer_id, c.no_spk, c.nama, c.alamat, c.no_tlpn, c.tgl_spk,
                    s.id as service_id, s.tanggal_kunjungan, s.tanggal_selesai, s.remark_unit,
                    s.status_pekerjaan, s.keterangan_service, t.nama as teknisi_nama,
                    datediff(s.tanggal_selesai, c.tgl_spk) + 1 as waktu_service'''
        from_where = f'''from customer c
                         left join service_ac s on c.id = s.customer_id
                         left join teknisi t on s.teknisi_id = t.id
                         where {' and '.join(where)}'''
        return paginate(params, select, from_where, tuple(args), tiebreak='c.id')

    def get(self, id):
        return fetch_one('''select s.*, c.nama, c.no_spk, c.tgl_spk
                            from service_ac s join customer c on s.customer_id = c.id
                            where s.id = %s''', (id,))

    def create(self, customer_id, data):
        return execute('''insert into service_ac
                          (customer_id, teknisi_id, tanggal_kunjungan, tanggal_selesai, remark_unit, status_pekerjaan)
                          values (%s, %s, %s, %s, %s, %s)''',
                       (customer_id, data['teknisi_id'], data['tanggal_kunjungan'],
                        data['tanggal_selesai'], data['remark_unit'], 'in progress'))

    def update(self, id, data):
        execute('''update service_ac set teknisi_id = %s, tanggal_kunjungan = %s, tanggal_selesai = %s,
                   remark_unit = %s, status_pekerjaan = %s, keterangan_service = %s
                   where id = %s''',
                (data['teknisi_id'], data['tanggal_kunjungan'], data['tanggal_selesai'],
                 data['remark_unit'], data['status_pekerjaan'], data['keterangan_service'], id))

    def delete(self, id):
        execute('delete from service_ac where id = %s', (id,))


# Teknisi / Karyawan
class Teknisi:
    SORTABLE = {'nama': 'nama', 'no_tlpn': 'no_tlpn', 'id': 'id'}

    def paginate(self, params):
        where, args = '1=1', ()
        if params.q:
            where = '(nama like %s or no_tlpn like %s)'
            args = (params.like, params.like)
        return paginate(params, '*', f'from teknisi where {where}', args)

    def all(self):
        return fetch_all('select id, nama from teknisi order by nama')

    def get(self, id):
        return fetch_one('select * from teknisi where id = %s', (id,))

    def create(self, data):
        return execute('insert into teknisi (nama, no_tlpn) values (%s, %s)', (data['nama'], data['no_tlpn']))

    def update(self, id, data):
        execute('update teknisi set nama = %s, no_tlpn = %s where id = %s', (data['nama'], data['no_tlpn'], id))

    def delete(self, id):
        execute('delete from teknisi where id = %s', (id,))


# Dashboard
class Dashboard:
    def _period(self, tahun, bulan):
        where, args = ['1=1'], []
        if tahun:
            where.append('year(c.tgl_spk) = %s')
            args.append(tahun)
        if bulan:
            where.append('month(c.tgl_spk) = %s')
            args.append(bulan)
        return ' and '.join(where), tuple(args)

    def years(self):
        rows = fetch_all('select distinct year(tgl_spk) as tahun from customer '
                         'where tgl_spk is not null order by tahun desc')
        return [r['tahun'] for r in rows]

    def summary(self, tahun=None, bulan=None):
        where, args = self._period(tahun, bulan)
        base = f'from customer c left join service_ac s on s.customer_id = c.id where {where}'

        totals = fetch_one(f'''select count(distinct c.id) as total_customer,
                                      count(s.id) as total_pekerjaan,
                                      sum(s.status_pekerjaan = 'completed') as selesai,
                                      sum(s.id is not null and coalesce(s.status_pekerjaan, '') <> 'completed') as proses,
                                      sum(s.id is null) as belum_dijadwalkan
                               {base}''', args)

        kpi = fetch_one(f'''select
                sum(datediff(s.tanggal_kunjungan, c.tgl_spk) <= {KPI_KUNJUNGAN_MAKS_HARI}) as kunjungan_ok,
                sum(datediff(s.tanggal_kunjungan, c.tgl_spk) > {KPI_KUNJUNGAN_MAKS_HARI}) as kunjungan_gagal,
                sum(datediff(s.tanggal_selesai, c.tgl_spk) <= {KPI_SELESAI_MAKS_HARI}) as selesai_ok,
                sum(datediff(s.tanggal_selesai, c.tgl_spk) > {KPI_SELESAI_MAKS_HARI}) as selesai_gagal
                {base}''', args)

        garansi = fetch_all(f'''select coalesce(c.garansi, 'Tidak diketahui') as label, count(*) as total
                                from customer c where {where} group by label order by label''', args)

        teknisi = fetch_all(f'''select t.nama as label, count(s.id) as total,
                                       sum(s.status_pekerjaan = 'completed') as selesai
                                from service_ac s
                                join teknisi t on t.id = s.teknisi_id
                                join customer c on c.id = s.customer_id
                                where {where}
                                group by t.id, t.nama order by total desc''', args)

        unit = fetch_all(f'''select coalesce(nullif(c.model_indoor, ''), '-') as label, count(*) as total
                             from customer c where {where}
                             group by label order by total desc limit 10''', args)

        return {
            'totals': to_int(totals),
            'kpi': to_int(kpi),
            'garansi': [to_int(r) for r in garansi],
            'teknisi': [to_int(r) for r in teknisi],
            'unit': [to_int(r) for r in unit],
            'batas': {'kunjungan': KPI_KUNJUNGAN_MAKS_HARI, 'selesai': KPI_SELESAI_MAKS_HARI},
        }


# Pengguna / Login
class Users:
    @staticmethod
    def _verify(stored, password):
        if not stored:
            return False
        # Mendukung password yang sudah di-hash maupun data lama (plaintext)
        if stored.startswith(('scrypt:', 'pbkdf2:')):
            return check_password_hash(stored, password)
        return hmac.compare_digest(stored.encode(), password.encode())

    def authenticate(self, username, password):
        user = fetch_one('select username, password from pengguna where username = %s', (username,))
        return bool(user) and self._verify(user['password'], password)

    def change_password(self, username, current_password, new_password):
        """Return True jika berhasil. Hash diverifikasi ulang sebelum commit
        supaya tidak terkunci jika kolom password terlalu pendek."""
        if not self.authenticate(username, current_password):
            return False
        hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute('update pengguna set password = %s where username = %s', (hashed, username))
                cursor.execute('select password from pengguna where username = %s', (username,))
                stored = cursor.fetchone()['password']
            if stored != hashed:
                raise RuntimeError('Kolom password terlalu pendek untuk menyimpan hash.')
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
