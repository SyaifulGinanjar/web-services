# Data Service — CV. Twin Anugrah Jaya

Aplikasi pencatatan customer, jadwal service AC, dan karyawan (teknisi) berbasis Flask + MySQL.

## Struktur

```
app/
├── __init__.py        # create_app(): app factory, error handler, security header
├── config.py          # Semua konfigurasi dibaca dari environment (.env)
├── db.py              # Koneksi MySQL per-request (flask.g) + helper query
├── models.py          # Query ke database (Customers, Services, ServiceTambahan, Teknisi, Lampiran, Dashboard, Users)
├── forms.py           # Validasi input form
├── pagination.py      # Search / sort / pagination server-side
├── storage.py         # Simpan file lampiran: lokal (development) atau Vercel Blob (production)
├── migrate.py         # Perintah `flask migrate` untuk file migrations/*.sql
├── extensions.py      # CSRF & rate limit login
├── views/             # Blueprint per modul (auth, dashboard, customer, service, service_tambahan,
│                      #   karyawan, lampiran, account, files)
├── templates/         # Jinja template (layout.html + components/macros.html)
└── static/            # CSS, JS (script.js = navigasi tanpa reload), vendor (Bootstrap, Chart.js)
migrations/            # Perubahan skema database (SQL, berurutan)
tests/                 # pytest
run_app.py             # Entry point (dipakai juga oleh Vercel)
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
copy .env.example .env          # lalu isi nilainya
```

## Database (migrasi)

Perubahan skema ada di folder `migrations/` (file `.sql` berurutan). Jalankan setelah pull/sebelum deploy:

```bash
flask --app run_app migrate --dry-run   # lihat migrasi yang belum dijalankan
flask --app run_app migrate             # jalankan (backup database dulu)
```

Migrasi yang sudah dijalankan dicatat di tabel `schema_migrations`, jadi aman diulang.

## Menjalankan

```bash
flask --app run_app run --debug
```

Buka http://localhost:5000.

## Test

```bash
pytest
```

## Konfigurasi (.env)

Lihat `.env.example`. Yang wajib: `SECRET_KEY` (production) dan `DB_*`.
Di Vercel, isi variabel yang sama di **Project Settings → Environment Variables** dan set
`FLASK_ENV=production`, `SESSION_COOKIE_SECURE=true`.

Lampiran file: filesystem Vercel tidak permanen, jadi di Vercel wajib `STORAGE_BACKEND=blob`.
Hubungkan Blob store ke project (**Storage → Create → Blob**); `BLOB_READ_WRITE_TOKEN` akan terisi otomatis.
Batas body request Vercel ±4,5 MB, jadi file lampiran efektif maksimal ±4 MB di sana.

## Fitur

- Navigasi tanpa reload penuh: navbar & sidebar tetap, hanya konten yang diganti (fetch + History API).
  Tanpa JavaScript, semua link/form tetap berfungsi normal.
- Search (live, debounce), filter, sort per kolom, dan pagination server-side di semua tabel.
- Validasi form server-side dengan pesan error per field.
- CSRF protection, hapus data via POST + dialog konfirmasi, rate limit login,
  password hash (pbkdf2) dengan dukungan password lama (plaintext) saat login.
- Dashboard KPI dari data asli dengan filter tahun/bulan; data juga tersedia di `GET /api/dashboard?tahun=&bulan=`.
- Service Tambahan: kunjungan ulang dengan No. SPK Baru yang merujuk No. SPK Lama (customer), lengkap dengan
  rekapnya di dashboard.
- Biaya (Rp) untuk pekerjaan Out of Warranty, wajib saat status Completed; total per periode di dashboard.
- Lampiran file (PDF/JPG/PNG) di Data Karyawan, Data Service, dan Service Tambahan. Isi file dicek
  (bukan hanya ekstensi) dan file hanya bisa dibuka oleh user yang login.
- Logo di halaman login & navbar (`APP_LOGO`).
