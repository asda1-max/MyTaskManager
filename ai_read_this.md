# AI Read This

Panduan untuk AI assistant / agent yang mengerjakan proyek ini. Baca file ini sebelum mulai.

## Gambaran Proyek

**MyTaskManager** — aplikasi habit tracker berbasis web (Flask + SQLite + Tailwind CSS v4).
Fitur utama:

- **Task harian / mingguan / bulanan** dengan frekuensi per periode (bisa selesai >1x per periode), prioritas (Normal/Sedang/Tinggi/Urgent), deadline, dan tags
- **Streak** per task (consecutive days) + pesan "Anda telah melakukan ini Nx berturut-turut"
- **Riwayat penyelesaian** + graph timeline (bar chart 30 hari) di halaman `/history`
- **Kalender aktivitas tahunan** (GitHub-style heatmap, 52 minggu) di halaman `/history`
- **Timeline per-task** di dashboard: riwayat tanggal penyelesaian per task (collapsible)
- **Wishlist** 2 kategori: `barang` (tabungan + progress bar Rp) dan `keinginan` (tanpa harga, cukup toggle selesai)
- **Password & Remember Device**: pertama kali buka, disuruh buat password; selanjutnya login dengan "Ingat device ini" checkbox (cookie 1 tahun via token acak di `config.json`)
- **Reset per tipe**: tombol terpisah untuk reset Daily/Weekly/Monthly (masing-masing ada konfirmasi yes/no)

## Cara Menjalankan

```bash
python main.py
```

- Buka `http://localhost:5000`
- `debug=True`, `use_reloader=False`, bind `0.0.0.0`
- APScheduler: reset harian 00:00, mingguan Senin 00:05, bulanan tanggal 1 00:10 (meng-copy `TASK` -> `CURRENT_TASK`)
- Saat startup: jika `CURRENT_TASK` untuk suatu tipe kosong, otomatis diisi ulang dari `TASK`

## Struktur File

| File | Isi |
|---|---|
| `main.py` | Route Flask (~245 baris), scheduler APScheduler, filter Jinja (`rupiah`, `datetime_ind`, `days_until`), helper `translate_raw_data()` dan `load_dashboard_data()`, auth `before_request` + login/setup/logout |
| `backend.py` | Kelas `task_manager()` (~585 baris): semua logika CRUD task (termasuk prioritas/deadline/tags), streak, log, wishlist, migrasi DB otomatis, export data, pagination log, password management |
| `templates/base.html` | Layout + navbar (Dashboard / Riwayat / Wishlist), sticky, backdrop-blur, dark theme |
| `templates/index.html` | Dashboard: hero stats + 3 section (daily/blue, weekly/violet, monthly/emerald) via macro `render_section` + `render_task_form` (termasuk prioritas/deadline/tags), tombol Selesai, Edit, Hapus, streak message, badge prioritas, deadline countdown, tags, per-task completion timeline, tombol Reset Semua |
| `templates/history.html` | Bar chart 30 hari + kalender aktivitas tahunan 52 minggu (GitHub-style, grid Senin-Minggu dengan legenda warna) + stat total tahun ini + daftar log dengan pagination + tombol Export JSON |
| `templates/login.html` | Halaman login dengan "Ingat device ini" checkbox |
| `templates/setup.html` | Halaman setup password pertama kali |
| `static/src/input.css` | Entry Tailwind v4, `@source "../../templates"` |
| `static/css/output.css` | **Jangan diedit manual** — hasil build Tailwind (1018 baris) |
| `taskmanager.db` | Database SQLite (ter-commit di repo, hati-hati) |
| `requirements.txt` | `flask` dan `flask_apscheduler` |
| `.gitignore` | `tailwindcss.exe` |
| `tailwindcss.exe` | Standalone Tailwind v4 binary (tidak ter-commit) |

## Penting: Build CSS

Setiap kali mengubah class Tailwind di template, wajib rebuild:

```bash
.\tailwindcss.exe -i static\src\input.css -o static\css\output.css
```

- `tailwindcss.exe` (standalone v4) terdaftar di `.gitignore`
- Scanner Tailwind hanya membaca `templates/` — **class yang dibangun dinamis lewat Python (filter/backend) TIDAK akan digenerate**. Semua class harus berupa string literal di template (contoh: palet warna per tipe task dideklarasikan penuh di template, bukan di-backend)

## Database (SQLite)

Tabel:

- `TASK` — task master: `id, task_name, task_description, task_type ('daily'/'weekly'/'monthly'), frequency, priority (0-3), deadline, tags, created_at`
- `CURRENT_TASK` — task aktif periode sekarang (salinan `TASK`; `frequency` = sisa; dihapus saat selesai semua frekuensi). Punya `priority, deadline, tags` tapi tidak punya `created_at`.
- `COMPLETION_LOG` — riwayat: `task_id, task_name, task_type, completed_at` (dipakai untuk graph & streak)
- `STREAK` — `task_id, current_streak, best_streak, last_completed` (update di `check_task_completion`)
- `WISHLIST` — `item_name, item_description, target_price, saved_amount, achieved, category ('barang'/'keinginan'), created_at`
- Tabel lama `LOG` (kosong, tak terpakai) — jangan dipakai

Migrasi otomatis di `migrate_database()` (saat startup): membuat tabel baru bila belum ada, `ALTER TABLE` menambah kolom `category` di WISHLIST jika belum ada, dan menghapus duplikat task (GROUP BY semua kolom, keep MIN(id)).

## Route Flask (main.py)

| Route | Method | Fungsi |
|---|---|---|
| `/setup` | GET/POST | Setup password pertama kali (redirect ke /login jika sudah ada password) |
| `/login` | GET/POST | Login. POST: verifikasi password, "Ingat device ini" set cookie remember_token 1 tahun |
| `/logout` | GET | Hapus session + cookie remember_token |
| `/` | GET | Dashboard: menampilkan semua current task + stats + per-task completion dates |
| `/add_task` | POST | Tambah task baru (dengan frequency, default 1) |
| `/edit_task/<id>` | POST | Edit task (bisa ganti task_type, sinkron CURRENT_TASK) |
| `/delete_task/<id>` | POST | Hapus task + streak + current task (log tetap) |
| `/finish_a_task/<id>` | POST | Tandai selesai: log + streak + kurangi frequency |
| `/reset_daily` | POST | Reset hanya Daily Task (konfirmasi via `confirm()` di template) |
| `/reset_weekly` | POST | Reset hanya Weekly Task |
| `/reset_monthly` | POST | Reset hanya Monthly Task |
| `/reset_all` | POST | Reset semua task (Daily+Weekly+Monthly) |
| `/history` | GET | Riwayat: log (paginated, 50/halaman), bar chart 30 hari, heatmap tahunan 52 minggu |
| `/export` | GET | Export seluruh data (tasks, logs, streaks, wishlist) sebagai JSON |
| `/wishlist` | GET | Daftar wishlist |
| `/add_wishlist` | POST | Tambah item wishlist |
| `/edit_wishlist/<id>` | POST | Edit item wishlist |
| `/delete_wishlist/<id>` | POST | Hapus item wishlist |
| `/wishlist_save/<id>` | POST | Nabung (+) atau tarik (-) tabungan |
| `/wishlist_achieve/<id>` | POST | Toggle achieved (tercapai / buka lagi) |

## Konvensi Kode

- Bahasa kode: Inggris (nama method, variabel). Teks UI: **Indonesia** (label, tombol, pesan)
- Tidak ada komentar berlebih; docstring pendek per method
- Backend: tiap method buka-tutup koneksi sendiri via `_connect()` (`sqlite3.Row` -> `dict`)
- Template: Jinja macros untuk bagian berulang, class Tailwind selalu literal
- Route POST lalu `redirect(...)`; filter `rupiah` format `Rp 1.000.000`
- Filter `datetime_ind` mengubah `"2024-01-15 14:30:00"` -> `"15 Jan 2024, 14:30"`
- APScheduler tidak pakai `requests` — job cron langsung panggil method backend

## Gotcha / Catatan

- Jangan menimpa `taskmanager.db`; backup dulu sebelum eksperimen (`Copy-Item taskmanager.db taskmanager.db.bak`)
- Server lama yang masih berjalan di port 5000 bisa membingungkan test (Werkzeug debug traceback membaca source dari disk, jadi tampak seperti kode baru). Matikan semua `python` sebelum test: `Get-Process python | Stop-Process -Force`
- `check_task_completion(task_id)`: insert log + update streak + kurangi frequency; task dihapus dari `CURRENT_TASK` jika frequency habis. TASK master tetap ada sampai di-reset period (scheduler atau startup)
- Halaman history: chart berisi data 0 — jaga dari division-by-zero (`peak` = 0 -> pakai `scale = 1`)
- `delete_task` juga menghapus `STREAK`, tapi **riwayat `COMPLETION_LOG` tetap disimpan**
- Jinja division `0/0` melempar ZeroDivisionError — selalu guard
- Filter `rupiah` menggunakan `int()` — pastikan value numerik atau 0 (guard `or 0`)
- Streak logic: reset ke 1 jika ada jeda (>1 hari), +1 jika kemarin selesai, abaikan jika hari ini sudah selesai
- `update_current_task()` menghapus semua CURRENT_TASK untuk tipe tertentu, lalu re-insert dari TASK master — frequency kembali ke nilai asli
- Wishlist `wishlist_save()` menerima amount negatif untuk tarik tabungan (dibatasi min 0)
- Wishlist `wishlist_achieve()` adalah toggle: jika sudah tercapai jadi dibuka lagi, dan sebaliknya
- JS di wishlist.html: disable input price saat kategori "keinginan" dipilih (di form tambah)
- Per-task timeline: di dashboard, setiap task punya details "Riwayat penyelesaian" yang menampilkan daftar tanggal (dd/mm) saat task itu diselesaikan. Data dimuat via `task_dates` dict yang diisi di `load_dashboard_data()` dengan memanggil `select_task_completion_dates()` per task
- Kalender tahunan di history menggunakan `select_activity_heatmap(weeks=52)` — grid 52 minggu x 7 hari dengan 5 level warna (putih, emerald-900, emerald-700, emerald-500, emerald-300). Dilengkapi legenda "Kurang" — "Banyak" dan statistik "Total tahun ini"
- Prioritas: 0=Normal (tanpa badge), 1=Sedang (kuning), 2=Tinggi (oranye), 3=Urgent (merah). Deadline menampilkan countdown "Sisa X hari", "Hari ini!", atau "Terlambat X hari" via filter `days_until`.
- Tags: comma-separated string di database, ditampilkan sebagai badge kecil di task card
- Export data via `/export` mengembalikan JSON seluruh data (tasks, completion_logs, streaks, wishlist)
- Pagination di history: 50 log per halaman, navigasi Sebelumnya/Selanjutnya, parameter `?page=N`
- Password: disimpan di `config.json` (file lokal) dengan format `salt:sha256_hash`. Token remember device juga disimpan di file yang sama. **Hapus config.json untuk reset password** atau ganti password via edit manual file.
- Auth: `before_request` mengecek session/cookie. Route yang dikecualikan: `login`, `login_func`, `setup`, `setup_func`, `static`. Setelah login sukses, checkbox "Ingat device ini" menyimpan cookie `remember_token` selama 1 tahun.
- Tombol "Keluar" di navbar (base.html) untuk logout dan hapus cookie.