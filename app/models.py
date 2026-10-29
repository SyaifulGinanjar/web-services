import hmac
from decimal import Decimal

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app import storage
from app.db import execute, fetch_all, fetch_one, get_db
from app.pagination import Page

# Batas KPI (hari sejak tanggal SPK)
KPI_KUNJUNGAN_MAKS_HARI = 2
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

    def search(self, q, limit=10):
        """Saran SPK lama untuk form Service Tambahan."""
        like = '%' + q.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_') + '%'
        return fetch_all('''select id, no_spk, nama, alamat, tgl_spk, garansi from customer
                            where no_spk like %s or nama like %s
                            order by tgl_spk desc limit %s''', (like, like, limit))

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

        select = f'''c.id as customer_id, c.no_spk, c.nama, c.alamat, c.no_tlpn, c.tgl_spk, c.garansi,
                    s.id as service_id, s.tanggal_kunjungan, s.tanggal_selesai, s.remark_unit,
                    s.status_pekerjaan, s.keterangan_service, s.biaya, t.nama as teknisi_nama,
                    datediff(s.tanggal_selesai, c.tgl_spk) + 1 as waktu_service,
                    {Lampiran.count_sql('service', 's.id')} as jumlah_lampiran'''
        from_where = f'''from customer c
                         left join service_ac s on c.id = s.customer_id
                         left join teknisi t on s.teknisi_id = t.id
                         where {' and '.join(where)}'''
        return paginate(params, select, from_where, tuple(args), tiebreak='c.id')

    def get(self, id):
        return fetch_one('''select s.*, c.nama, c.no_spk, c.tgl_spk, c.garansi
                            from service_ac s join customer c on s.customer_id = c.id
                            where s.id = %s''', (id,))

    def create(self, customer_id, data):
        return execute('''insert into service_ac
                          (customer_id, teknisi_id, tanggal_kunjungan, tanggal_selesai, remark_unit,
                           status_pekerjaan, biaya)
                          values (%s, %s, %s, %s, %s, %s, %s)''',
                       (customer_id, data['teknisi_id'], data['tanggal_kunjungan'],
                        data['tanggal_selesai'], data['remark_unit'], 'in progress', data.get('biaya')))

    def update(self, id, data):
        execute('''update service_ac set teknisi_id = %s, tanggal_kunjungan = %s, tanggal_selesai = %s,
                   remark_unit = %s, status_pekerjaan = %s, keterangan_service = %s, biaya = %s
                   where id = %s''',
                (data['teknisi_id'], data['tanggal_kunjungan'], data['tanggal_selesai'],
                 data['remark_unit'], data['status_pekerjaan'], data['keterangan_service'],
                 data.get('biaya'), id))

    def delete(self, id):
        execute('delete from service_ac where id = %s', (id,))
        Lampiran().delete_for('service', id)


# Service Tambahan (kunjungan ulang dengan SPK baru yang merujuk SPK lama)
class ServiceTambahan:
    STATUS = ('belum', 'in progress', 'completed')  # 'belum' disimpan sebagai NULL
    SORTABLE = {
        'no_spk_lama': 'c.no_spk', 'no_spk_baru': 'st.no_spk_baru', 'nama': 'c.nama', 'tgl_spk': 'st.tgl_spk',
        'tanggal_kunjungan': 'st.tanggal_kunjungan', 'tanggal_selesai': 'st.tanggal_selesai',
        'teknisi': 't.nama', 'waktu_service': 'waktu_service', 'status': 'st.status_pekerjaan',
        'biaya': 'st.biaya',
    }
    FIELDS = ('no_spk_baru', 'tgl_spk', 'teknisi_id', 'tanggal_kunjungan', 'tanggal_selesai',
              'remark_unit', 'status_pekerjaan', 'keterangan', 'biaya')

    def paginate(self, params):
        where, args = ['1=1'], []
        if params.q:
            where.append('(c.no_spk like %s or st.no_spk_baru like %s or c.nama like %s or c.alamat like %s '
                         'or c.no_tlpn like %s or st.remark_unit like %s or t.nama like %s or st.keterangan like %s)')
            args += [params.like] * 8

        status = params.filters.get('status')
        if status == 'belum':
            where.append('st.status_pekerjaan is null')
        elif status in self.STATUS:
            where.append('st.status_pekerjaan = %s')
            args.append(status)

        teknisi_id = params.filters.get('teknisi_id')
        if teknisi_id and teknisi_id.isdigit():
            where.append('st.teknisi_id = %s')
            args.append(int(teknisi_id))

        select = f'''st.*, c.no_spk as no_spk_lama, c.nama, c.alamat, c.no_tlpn, c.garansi,
                    t.nama as teknisi_nama,
                    datediff(st.tanggal_selesai, st.tgl_spk) + 1 as waktu_service,
                    {Lampiran.count_sql('service_tambahan', 'st.id')} as jumlah_lampiran'''
        from_where = f'''from service_tambahan st
                         join customer c on c.id = st.customer_id
                         left join teknisi t on t.id = st.teknisi_id
                         where {' and '.join(where)}'''
        return paginate(params, select, from_where, tuple(args), tiebreak='st.id')

    def get(self, id):
        return fetch_one('''select st.*, c.no_spk as no_spk_lama, c.nama, c.alamat, c.no_tlpn, c.garansi
                            from service_tambahan st join customer c on c.id = st.customer_id
                            where st.id = %s''', (id,))

    def by_customer(self, customer_id):
        return fetch_all('''select st.*, t.nama as teknisi_nama from service_tambahan st
                            left join teknisi t on t.id = st.teknisi_id
                            where st.customer_id = %s order by st.tgl_spk desc, st.id desc''', (customer_id,))

    def spk_exists(self, no_spk_baru, exclude_id=None):
        row = fetch_one('select id from service_tambahan where no_spk_baru = %s and id <> %s',
                        (no_spk_baru, exclude_id or 0))
        return row is not None

    def create(self, customer_id, data):
        columns = ', '.join(('customer_id',) + self.FIELDS)
        placeholders = ', '.join(['%s'] * (len(self.FIELDS) + 1))
        return execute(f'insert into service_tambahan ({columns}) values ({placeholders})',
                       (customer_id, *(data[f] for f in self.FIELDS)))

    def update(self, id, data):
        assignments = ', '.join(f'{f} = %s' for f in self.FIELDS)
        execute(f'update service_tambahan set {assignments} where id = %s',
                (*(data[f] for f in self.FIELDS), id))

    def delete(self, id):
        execute('delete from service_tambahan where id = %s', (id,))
        Lampiran().delete_for('service_tambahan', id)


# Lampiran file (karyawan, service, service tambahan)
class Lampiran:
    OWNER_TYPES = ('teknisi', 'service', 'service_tambahan')

    @staticmethod
    def count_sql(owner_type, id_column):
        # owner_type & id_column berasal dari kode, bukan input user
        return (f"(select count(*) from lampiran l where l.owner_type = '{owner_type}' "
                f"and l.owner_id = {id_column})")

    def list(self, owner_type, owner_id):
        return fetch_all('select * from lampiran where owner_type = %s and owner_id = %s order by id desc',
                         (owner_type, owner_id))

    def get(self, id):
        return fetch_one('select * from lampiran where id = %s', (id,))

    def create(self, data):
        return execute('''insert into lampiran
                          (owner_type, owner_id, nama_file, storage_key, content_type, ukuran, keterangan, uploaded_by)
                          values (%s, %s, %s, %s, %s, %s, %s, %s)''',
                       (data['owner_type'], data['owner_id'], data['nama_file'], data['storage_key'],
                        data['content_type'], data['ukuran'], data['keterangan'], data['uploaded_by']))

    def delete(self, id):
        row = self.get(id)
        if row:
            execute('delete from lampiran where id = %s', (id,))
            _delete_stored(row['storage_key'])
        return row

    def delete_for(self, owner_type, owner_id):
        rows = self.list(owner_type, owner_id)
        if rows:
            execute('delete from lampiran where owner_type = %s and owner_id = %s', (owner_type, owner_id))
            for row in rows:
                _delete_stored(row['storage_key'])


def _delete_stored(key):
    """Hapus file di storage. Gagal hapus file tidak membatalkan hapus data (cukup dicatat)."""
    try:
        storage.delete(key)
    except Exception:
        current_app.logger.exception('Gagal menghapus file lampiran %s', key)


# Teknisi / Karyawan
class Teknisi:
    SORTABLE = {'nama': 'nama', 'no_tlpn': 'no_tlpn', 'id': 'id'}

    def paginate(self, params):
        where, args = '1=1', ()
        if params.q:
            where = '(nama like %s or no_tlpn like %s)'
            args = (params.like, params.like)
        select = f"teknisi.*, {Lampiran.count_sql('teknisi', 'teknisi.id')} as jumlah_lampiran"
        return paginate(params, select, f'from teknisi where {where}', args)

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
        Lampiran().delete_for('teknisi', id)


# Dashboard
class Dashboard:
    def _period(self, tahun, bulan, column='c.tgl_spk'):
        where, args = ['1=1'], []
        if tahun:
            where.append(f'year({column}) = %s')
            args.append(tahun)
        if bulan:
            where.append(f'month({column}) = %s')
            args.append(bulan)
        return ' and '.join(where), tuple(args)

    def tambahan(self, tahun=None, bulan=None):
        """Rekap Service Tambahan, periode berdasarkan tanggal SPK baru."""
        where, args = self._period(tahun, bulan, 'st.tgl_spk')
        return to_int(fetch_one(f'''select count(distinct st.customer_id) as total_customer,
                                           count(*) as total_pekerjaan,
                                           sum(st.status_pekerjaan = 'completed') as selesai,
                                           sum(st.status_pekerjaan = 'in progress') as proses,
                                           sum(st.status_pekerjaan is null) as belum_dijadwalkan
                                    from service_tambahan st where {where}''', args))

    def biaya_per_teknisi(self, tahun=None, bulan=None):
        """Total biaya pekerjaan Out of Warranty yang sudah Completed per karyawan,
        gabungan Service (service_ac) dan Service Tambahan."""
        where, args = self._period(tahun, bulan)
        where_st, args_st = self._period(tahun, bulan, 'st.tgl_spk')
        rows = fetch_all(f'''select t.id, t.nama, count(*) as jumlah,
                                    coalesce(sum(case when p.tambahan = 0 then p.biaya end), 0) as service,
                                    coalesce(sum(case when p.tambahan = 1 then p.biaya end), 0) as tambahan,
                                    coalesce(sum(p.biaya), 0) as total
                             from (
                                 select 0 as tambahan, s.teknisi_id, s.biaya
                                 from service_ac s join customer c on c.id = s.customer_id
                                 where c.garansi = 'Out Of Warranty' and s.status_pekerjaan = 'completed'
                                       and {where}
                                 union all
                                 select 1, st.teknisi_id, st.biaya
                                 from service_tambahan st join customer c on c.id = st.customer_id
                                 where c.garansi = 'Out Of Warranty' and st.status_pekerjaan = 'completed'
                                       and {where_st}
                             ) p
                             join teknisi t on t.id = p.teknisi_id
                             group by t.id, t.nama order by total desc, t.nama''', args + args_st)
        return [to_int(r) for r in rows]

    def biaya_oow(self, tahun=None, bulan=None):
        """Total biaya pekerjaan Out of Warranty (service + service tambahan)."""
        where, args = self._period(tahun, bulan)
        where_st, args_st = self._period(tahun, bulan, 'st.tgl_spk')
        service = to_int(fetch_one(f'''select coalesce(sum(s.biaya), 0) as total, count(s.biaya) as jumlah
                                       from service_ac s join customer c on c.id = s.customer_id
                                       where c.garansi = 'Out Of Warranty' and {where}''', args))
        tambahan = to_int(fetch_one(f'''select coalesce(sum(st.biaya), 0) as total, count(st.biaya) as jumlah
                                        from service_tambahan st join customer c on c.id = st.customer_id
                                        where c.garansi = 'Out Of Warranty' and {where_st}''', args_st))
        return {
            'service': service['total'],
            'tambahan': tambahan['total'],
            'total': service['total'] + tambahan['total'],
            'jumlah': service['jumlah'] + tambahan['jumlah'],
        }

    def years(self):
        rows = fetch_all('select distinct year(tgl_spk) as tahun from customer '
                         'where tgl_spk is not null order by tahun desc')
        return [r['tahun'] for r in rows]

    def summary(self, tahun=None, bulan=None):
        where, args = self._period(tahun, bulan)
        base = f'from customer c left join service_ac s on s.customer_id = c.id where {where}'
        base2 = f'from customer c left join service_tambahan st on st.customer_id = c.id where {where}'

        totals = fetch_one(f'''select count(distinct c.id) as total_customer,
                                      count(s.id) as total_pekerjaan,
                                      sum(s.status_pekerjaan = 'completed') as selesai,
                                    sum(s.status_pekerjaan = 'in progress') as proses, 
                                      sum(s.id is null) as belum_dijadwalkan
                               {base}''', args)

        kpi = fetch_one(f'''select
                sum(datediff(s.tanggal_selesai, c.tgl_spk) <= {KPI_KUNJUNGAN_MAKS_HARI}) as dispatch_ok,
                sum(datediff(s.tanggal_selesai, c.tgl_spk) > {KPI_KUNJUNGAN_MAKS_HARI}) as dispatch_gagal
                {base}''', args)
        
        kpi2 = fetch_one(f'''select
                sum(datediff(st.tanggal_selesai, c.tgl_spk) <= {KPI_SELESAI_MAKS_HARI}) as completion_ok,
                sum(datediff(st.tanggal_selesai, c.tgl_spk) > {KPI_SELESAI_MAKS_HARI}) as completion_gagal
                {base2}''', args)

        garansi = fetch_all(f'''select coalesce(c.garansi, 'Tidak diketahui') as label, count(*) as total
                                from customer c where {where} group by label order by label''', args)

        # Kinerja karyawan: gabungan Service dan Service Tambahan.
        # Kolom di UNION sengaja angka (bukan teks) supaya tidak bentrok collation antar tabel.
        where_st, args_st = self._period(tahun, bulan, 'st.tgl_spk')
        teknisi = fetch_all(f'''select t.nama as label, count(*) as total,
                                       sum(p.tambahan = 0) as service,
                                       sum(p.tambahan = 1) as tambahan,
                                       sum(p.selesai) as selesai
                                from (
                                    select 0 as tambahan, s.teknisi_id,
                                           (s.status_pekerjaan = 'completed') as selesai
                                    from service_ac s join customer c on c.id = s.customer_id
                                    where {where}
                                    union all
                                    select 1, st.teknisi_id, (st.status_pekerjaan = 'completed')
                                    from service_tambahan st
                                    where st.teknisi_id is not null and {where_st}
                                ) p
                                join teknisi t on t.id = p.teknisi_id
                                group by t.id, t.nama order by total desc''', args + args_st)

        unit = fetch_all(f'''select coalesce(nullif(c.model_indoor, ''), '-') as label, count(*) as total
                             from customer c where {where}
                             group by label order by total desc limit 10''', args)

        return {
            'totals': to_int(totals),
            'kpi': to_int(kpi),
            'kpi2': to_int(kpi2),
            'garansi': [to_int(r) for r in garansi],
            'teknisi': [to_int(r) for r in teknisi],
            'unit': [to_int(r) for r in unit],
            'batas': {'kunjungan': KPI_KUNJUNGAN_MAKS_HARI, 'selesai': KPI_SELESAI_MAKS_HARI},
            'tambahan': self.tambahan(tahun, bulan),
            'biaya_oow': self.biaya_oow(tahun, bulan),
            'biaya_teknisi': self.biaya_per_teknisi(tahun, bulan),
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
