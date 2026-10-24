# Data Service — CV. Twin Anugrah Jaya

Aplikasi pencatatan customer, jadwal service AC, dan karyawan (teknisi) berbasis Flask + MySQL.

## Struktur

```
app/
├── __init__.py        # create_app(): app factory, error handler, security header
├── config.py          # Semua konfigurasi dibaca dari environment (.env)
├── db.py              # Koneksi MySQL per-request (flask.g) + helper query
├── models.py          # Query ke database (Customers, Services, Teknisi, Dashboard, Users)
├── forms.py           # Validasi input form
├── pagination.py      # Search / sort / pagination server-side
├── extensions.py      # CSRF & rate limit login
├── views/             # Blueprint per modul (auth, dashboard, customer, service, karyawan, account, files)
├── templates/         # Jinja template (layout.html + components/macros.html)
└── static/            # CSS, JS (script.js = navigasi tanpa reload), vendor (Bootstrap, Chart.js)
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

## Fitur

- Navigasi tanpa reload penuh: navbar & sidebar tetap, hanya konten yang diganti (fetch + History API).
  Tanpa JavaScript, semua link/form tetap berfungsi normal.
- Search (live, debounce), filter, sort per kolom, dan pagination server-side di semua tabel.
- Validasi form server-side dengan pesan error per field.
- CSRF protection, hapus data via POST + dialog konfirmasi, rate limit login,
  password hash (pbkdf2) dengan dukungan password lama (plaintext) saat login.
- Dashboard KPI dari data asli dengan filter tahun/bulan; data juga tersedia di `GET /api/dashboard?tahun=&bulan=`.
