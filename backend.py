import sqlite3
import pathlib
import hashlib
import json
import secrets
from datetime import date, timedelta

DATABASE = "taskmanager.db"
CONFIG_FILE = "config.json"


class task_manager():
    """
    CRUD task (daily/weekly/monthly), log penyelesaian, streak, dan wishlist
    """
    def __init__(self):
        file_path = pathlib.Path(DATABASE)
        if not file_path.exists():
            print("Database tidak ditemukan, membuat database baru...")
            self.create_database(DATABASE)
        else:
            self.migrate_database()

    def _connect(self):
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        return connection

    def create_database(self, database_name):
        """
        Membuat database beserta seluruh tabel
        """
        connection = sqlite3.connect(database_name)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE TASK(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                task_description TEXT,
                task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                frequency INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 0,
                deadline TEXT,
                tags TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cursor.execute("""
            CREATE TABLE CURRENT_TASK(
                id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_description TEXT,
                task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                frequency INTEGER NOT NULL,
                priority INTEGER DEFAULT 0,
                deadline TEXT,
                tags TEXT DEFAULT ''
            )
        """)
        cursor.execute("""
            CREATE TABLE COMPLETION_LOG(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                completed_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cursor.execute("""
            CREATE TABLE STREAK(
                task_id INTEGER PRIMARY KEY,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_completed TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE WISHLIST(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                item_description TEXT,
                target_price INTEGER DEFAULT 0,
                saved_amount INTEGER DEFAULT 0,
                achieved INTEGER DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'barang' CHECK(category IN ('barang', 'keinginan')),
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        connection.commit()
        connection.close()
        print("Database berhasil dibuat")

    def migrate_database(self):
        """
        Migrasi database lama: tambahkan tabel baru dan rapikan data duplikat
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS COMPLETION_LOG(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                completed_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS STREAK(
                task_id INTEGER PRIMARY KEY,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_completed TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS WISHLIST(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                item_description TEXT,
                target_price INTEGER DEFAULT 0,
                saved_amount INTEGER DEFAULT 0,
                achieved INTEGER DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'barang' CHECK(category IN ('barang', 'keinginan')),
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        columns = [row["name"] for row in cursor.execute("PRAGMA table_info(WISHLIST)")]
        if "category" not in columns:
            cursor.execute("ALTER TABLE WISHLIST ADD COLUMN category TEXT NOT NULL DEFAULT 'barang'")
        task_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(TASK)")]
        if "priority" not in task_columns:
            cursor.execute("ALTER TABLE TASK ADD COLUMN priority INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE TASK ADD COLUMN deadline TEXT")
            cursor.execute("ALTER TABLE TASK ADD COLUMN tags TEXT DEFAULT ''")
            cursor.execute("ALTER TABLE CURRENT_TASK ADD COLUMN priority INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE CURRENT_TASK ADD COLUMN deadline TEXT")
            cursor.execute("ALTER TABLE CURRENT_TASK ADD COLUMN tags TEXT DEFAULT ''")
        cursor.execute("""
            DELETE FROM TASK WHERE id NOT IN (
                SELECT MIN(id) FROM TASK
                GROUP BY task_name, task_description, task_type, frequency
            )
        """)
        cursor.execute("""
            DELETE FROM CURRENT_TASK WHERE id NOT IN (
                SELECT MIN(id) FROM CURRENT_TASK
                GROUP BY task_name, task_description, task_type, frequency
            )
        """)
        connection.commit()
        connection.close()
        print("Database dimigrasi")

    # ============ TASK ============

    def add_task(self, task_name, task_description, task_type, frequency=1, priority=0, deadline=None, tags=''):
        """
        Menambahkan task ke tabel TASK dan CURRENT_TASK
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO TASK(task_name, task_description, task_type, frequency, priority, deadline, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task_name, task_description, task_type, frequency, priority, deadline, tags))
        new_id = cursor.lastrowid
        self.move_task_to_current_task(cursor, new_id, task_name, task_description, task_type, frequency, priority, deadline, tags)
        connection.commit()
        connection.close()

    def select_task(self, task_type):
        """
        Memilih semua task berdasarkan tipe ('daily', 'weekly', 'monthly')
        """
        connection = self._connect()
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM TASK WHERE task_type = ? ORDER BY id", (task_type,))]
        connection.close()
        return rows

    def select_current_task(self, task_type):
        """
        Memilih task aktif (current period) berdasarkan tipe
        """
        connection = self._connect()
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM CURRENT_TASK WHERE task_type = ? ORDER BY id", (task_type,))]
        connection.close()
        return rows

    def edit_task(self, task_id, task_name, task_description, task_type, frequency, priority=0, deadline=None, tags=''):
        """
        Mengedit task, sekaligus menyinkronkan ke CURRENT_TASK
        """
        connection = self._connect()
        cursor = connection.cursor()
        old = cursor.execute("SELECT task_type FROM TASK WHERE id = ?", (task_id,)).fetchone()
        cursor.execute("""
            UPDATE TASK SET
                task_name = ?,
                task_description = ?,
                task_type = ?,
                frequency = ?,
                priority = ?,
                deadline = ?,
                tags = ?
            WHERE id = ?
        """, (task_name, task_description, task_type, frequency, priority, deadline, tags, task_id))
        if old and old["task_type"] != task_type:
            cursor.execute("DELETE FROM CURRENT_TASK WHERE id = ?", (task_id,))
            self.move_task_to_current_task(cursor, task_id, task_name, task_description, task_type, frequency, priority, deadline, tags)
        else:
            cursor.execute("""
                UPDATE CURRENT_TASK SET
                    task_name = ?,
                    task_description = ?,
                    priority = ?,
                    deadline = ?,
                    tags = ?
                WHERE id = ?
            """, (task_name, task_description, priority, deadline, tags, task_id))
        connection.commit()
        connection.close()

    def delete_task(self, task_id):
        """
        Menghapus task beserta data streak dan current task (riwayat log tetap disimpan)
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM TASK WHERE id = ?", (task_id,))
        cursor.execute("DELETE FROM CURRENT_TASK WHERE id = ?", (task_id,))
        cursor.execute("DELETE FROM STREAK WHERE task_id = ?", (task_id,))
        connection.commit()
        connection.close()

    def update_current_task(self, task_type):
        """
        Mereset CURRENT_TASK dari tabel TASK (periode baru)
        """
        connection = self._connect()
        cursor = connection.cursor()
        data = self.select_task(task_type)
        cursor.execute("DELETE FROM CURRENT_TASK WHERE task_type = ?", (task_type,))
        for row in data:
            print(f"memindahkan task : [ID: {row['id']}, nama: {row['task_name']}]")
            self.move_task_to_current_task(
                cursor, row["id"], row["task_name"],
                row["task_description"], row["task_type"], row["frequency"],
                row.get("priority", 0), row.get("deadline"), row.get("tags", ''))
        connection.commit()
        connection.close()

    def move_task_to_current_task(self, cursor, task_id, task_name, task_description, task_type, frequency, priority=0, deadline=None, tags=''):
        """
        Memindahkan task dari tabel TASK ke CURRENT_TASK
        """
        cursor.execute("""
            INSERT INTO CURRENT_TASK(id, task_name, task_description, task_type, frequency, priority, deadline, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, task_name, task_description, task_type, frequency, priority, deadline, tags))

    def reset_all_current_task(self):
        """
        Mereset seluruh task ke periode baru
        """
        self.update_current_task('daily')
        self.update_current_task('weekly')
        self.update_current_task('monthly')

    def timing_update(self):
        """
        Update periodik: harian setiap hari, mingguan tiap Senin, bulanan tanggal 1
        """
        today = date.today()
        print(f"debug : UPDATING DAILY TASK... ({today})")
        self.update_current_task('daily')
        if today.weekday() == 0:
            print("debug : UPDATING WEEKLY TASK...")
            self.update_current_task('weekly')
        if today.day == 1:
            print("debug : UPDATING MONTHLY TASK...")
            self.update_current_task('monthly')

    # ============ PENYELESAIAN & STREAK ============

    def check_task_completion(self, task_id):
        """
        Kurangi frequency task sebanyak 1, catat ke log.
        Task dianggap selesai untuk periode ini saat frequency mencapai 0.
        Setiap klik Selesai = 1 baris log (misal '09:00', '10:00', dst).
        Task tetap di CURRENT_TASK (tidak dihapus).
        """
        connection = self._connect()
        cursor = connection.cursor()
        row = cursor.execute(
            "SELECT * FROM CURRENT_TASK WHERE id = ?", (task_id,)).fetchone()
        if not row:
            connection.close()
            return False
        if row["frequency"] > 0:
            new_frequency = row["frequency"] - 1
            cursor.execute(
                "UPDATE CURRENT_TASK SET frequency = ? WHERE id = ?",
                (new_frequency, task_id))
            cursor.execute("""
                INSERT INTO COMPLETION_LOG(task_id, task_name, task_type)
                VALUES (?, ?, ?)
            """, (task_id, row["task_name"], row["task_type"]))
            self.update_streak(cursor, task_id)
        connection.commit()
        connection.close()
        return True

    def update_streak(self, cursor, task_id):
        """
        Update streak: +1 jika kemarin selesai, reset ke 1 jika putus
        """
        today = date.today()
        today_str = today.isoformat()
        yesterday_str = (today - timedelta(days=1)).isoformat()
        row = cursor.execute(
            "SELECT current_streak, best_streak, last_completed FROM STREAK WHERE task_id = ?",
            (task_id,)).fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO STREAK(task_id, current_streak, best_streak, last_completed) VALUES (?, 1, 1, ?)",
                (task_id, today_str))
        elif row["last_completed"] == today_str:
            return
        elif row["last_completed"] == yesterday_str:
            new_streak = row["current_streak"] + 1
            best_streak = max(row["best_streak"], new_streak)
            cursor.execute(
                "UPDATE STREAK SET current_streak = ?, best_streak = ?, last_completed = ? WHERE task_id = ?",
                (new_streak, best_streak, today_str, task_id))
        else:
            cursor.execute(
                "UPDATE STREAK SET current_streak = 1, last_completed = ? WHERE task_id = ?",
                (today_str, task_id))

    def get_streaks(self):
        """
        Mengambil seluruh streak: {task_id: (current, best)}
        """
        connection = self._connect()
        rows = connection.execute("SELECT task_id, current_streak, best_streak FROM STREAK").fetchall()
        connection.close()
        return {row["task_id"]: (row["current_streak"], row["best_streak"]) for row in rows}

    # ============ LOG ============

    def count_completed_today(self):
        """
        Jumlah task yang selesai hari ini
        """
        connection = self._connect()
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM COMPLETION_LOG WHERE date(completed_at) = date('now', 'localtime')"
        ).fetchone()
        connection.close()
        return row["total"] if row else 0

    def select_logs(self, limit=200):
        """
        Mengambil riwayat penyelesaian terbaru
        """
        connection = self._connect()
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM COMPLETION_LOG ORDER BY id DESC LIMIT ?", (limit,))]
        connection.close()
        return rows

    def select_completions_by_day(self, days=30):
        """
        Jumlah penyelesaian per hari untuk N hari terakhir (termasuk hari tanpa aktivitas)
        """
        connection = self._connect()
        rows = {
            row["day"]: row["total"] for row in connection.execute(
                "SELECT date(completed_at) AS day, COUNT(*) AS total "
                "FROM COMPLETION_LOG "
                "WHERE date(completed_at) >= date('now', 'localtime', ?) "
                "GROUP BY date(completed_at) ORDER BY day",
                (f"-{days - 1} days",))
        }
        connection.close()
        result = []
        today = date.today()
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            result.append({"day": day.isoformat(), "total": rows.get(day.isoformat(), 0)})
        return result

    def select_activity_heatmap(self, weeks=52):
        """
        Aktivitas per hari dalam grid mingguan (mulai Senin), untuk heatmap kalender ala GitHub (default 52 minggu / 1 tahun)
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        grid_start = week_start - timedelta(days=(weeks - 1) * 7)

        connection = self._connect()
        rows = {
            row["day"]: row["total"] for row in connection.execute(
                "SELECT date(completed_at) AS day, COUNT(*) AS total "
                "FROM COMPLETION_LOG WHERE date(completed_at) >= ? "
                "GROUP BY date(completed_at)",
                (grid_start.isoformat(),))
        }
        connection.close()

        months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        weeks_data = []
        for week_index in range(weeks):
            week = []
            month_label = ""
            for day_offset in range(7):
                day = grid_start + timedelta(days=week_index * 7 + day_offset)
                week.append({
                    "day": day,
                    "total": rows.get(day.isoformat(), 0),
                    "future": day > today,
                })
                if day.day == 1:
                    month_label = months[day.month - 1]
            weeks_data.append({"days": week, "month_label": month_label})
        return weeks_data

    def select_task_completion_dates(self, task_id):
        """
        Mengambil daftar tanggal (string) saat task tertentu diselesaikan, untuk timeline per-task
        """
        connection = self._connect()
        rows = [row["day"] for row in connection.execute(
            "SELECT DISTINCT date(completed_at) AS day FROM COMPLETION_LOG WHERE task_id = ? ORDER BY day",
            (task_id,))]
        connection.close()
        return rows

    def select_all_completion_dates_grouped(self):
        """
        Optimasi N+1: satu query mengambil semua tanggal completion per task_id
        Returns: {task_id: [date_strings]}
        """
        connection = self._connect()
        rows = connection.execute(
            "SELECT task_id, date(completed_at) AS day FROM COMPLETION_LOG ORDER BY task_id, day"
        ).fetchall()
        connection.close()
        result = {}
        for row in rows:
            result.setdefault(row["task_id"], []).append(row["day"])
        return result

    def select_logs_paginated(self, page=1, per_page=50):
        """
        Mengambil riwayat penyelesaian dengan pagination
        Returns: (rows, total_count, total_pages)
        """
        connection = self._connect()
        total = connection.execute("SELECT COUNT(*) AS c FROM COMPLETION_LOG").fetchone()["c"]
        total_pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM COMPLETION_LOG ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))]
        connection.close()
        return rows, total, total_pages

    def export_data(self):
        """
        Export seluruh data sebagai dict (tasks, logs, streaks, wishlist)
        """
        connection = self._connect()
        tasks = [dict(row) for row in connection.execute("SELECT * FROM TASK ORDER BY id")]
        logs = [dict(row) for row in connection.execute("SELECT * FROM COMPLETION_LOG ORDER BY id")]
        streaks = [dict(row) for row in connection.execute("SELECT * FROM STREAK")]
        wishlist = [dict(row) for row in connection.execute("SELECT * FROM WISHLIST ORDER BY id")]
        connection.close()
        today = date.today().isoformat()
        return {
            "export_date": today,
            "tasks": tasks,
            "completion_logs": logs,
            "streaks": streaks,
            "wishlist": wishlist,
        }

    def get_task_detail(self, task_id):
        """
        Mengambil detail task dari TASK + streak + jumlah log
        """
        connection = self._connect()
        task_row = connection.execute("SELECT * FROM TASK WHERE id = ?", (task_id,)).fetchone()
        streak_row = connection.execute("SELECT * FROM STREAK WHERE task_id = ?", (task_id,)).fetchone()
        log_count = connection.execute("SELECT COUNT(*) AS c FROM COMPLETION_LOG WHERE task_id = ?", (task_id,)).fetchone()["c"]
        connection.close()
        if not task_row:
            return None
        result = dict(task_row)
        if streak_row:
            result["streak_current"] = streak_row["current_streak"]
            result["streak_best"] = streak_row["best_streak"]
            result["last_completed"] = streak_row["last_completed"]
        else:
            result["streak_current"] = 0
            result["streak_best"] = 0
            result["last_completed"] = None
        result["log_count"] = log_count
        return result

    def select_logs_by_task(self, task_id, limit=100):
        """
        Mengambil daftar log penyelesaian untuk task tertentu
        """
        connection = self._connect()
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM COMPLETION_LOG WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit))]
        connection.close()
        return rows

    def select_completions_by_day_per_task(self, task_id, days=30):
        """
        Jumlah penyelesaian per hari untuk task tertentu dalam N hari terakhir
        """
        connection = self._connect()
        rows = {
            row["day"]: row["total"] for row in connection.execute(
                "SELECT date(completed_at) AS day, COUNT(*) AS total "
                "FROM COMPLETION_LOG "
                "WHERE task_id = ? AND date(completed_at) >= date('now', 'localtime', ?) "
                "GROUP BY date(completed_at) ORDER BY day",
                (task_id, f"-{days - 1} days"))
        }
        connection.close()
        result = []
        today = date.today()
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            result.append({"day": day.isoformat(), "total": rows.get(day.isoformat(), 0)})
        return result

    # ============ PASSWORD & AUTH ============

    def _load_config(self):
        p = pathlib.Path(CONFIG_FILE)
        if p.exists():
            with open(p, "r") as f:
                return json.load(f)
        return {}

    def _save_config(self, data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def is_password_set(self):
        cfg = self._load_config()
        return bool(cfg.get("password_hash"))

    def set_password(self, raw_password):
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + raw_password).encode()).hexdigest()
        cfg = self._load_config()
        cfg["password_hash"] = f"{salt}:{h}"
        self._save_config(cfg)

    def verify_password(self, raw_password):
        cfg = self._load_config()
        stored = cfg.get("password_hash", "")
        if ":" not in stored:
            return False
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + raw_password).encode()).hexdigest() == h

    def generate_remember_token(self):
        token = secrets.token_hex(32)
        cfg = self._load_config()
        if "remember_tokens" not in cfg:
            cfg["remember_tokens"] = {}
        cfg["remember_tokens"][token] = date.today().isoformat()
        self._save_config(cfg)
        return token

    def validate_remember_token(self, token):
        cfg = self._load_config()
        return token in cfg.get("remember_tokens", {})

    # ============ WISHLIST ============

    def add_wishlist(self, item_name, item_description, target_price, category='barang', saved_amount=0):
        """
        Menambahkan item wishlist (kategori 'barang' atau 'keinginan')
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO WISHLIST(item_name, item_description, target_price, saved_amount, category)
            VALUES (?, ?, ?, ?, ?)
        """, (item_name, item_description, target_price, saved_amount, category))
        connection.commit()
        connection.close()

    def select_wishlist(self):
        """
        Mengambil seluruh item wishlist (yang belum tercapai di urutan atas)
        """
        connection = self._connect()
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM WISHLIST ORDER BY achieved ASC, id DESC")]
        connection.close()
        return rows

    def edit_wishlist(self, item_id, item_name, item_description, target_price, category='barang'):
        """
        Mengedit item wishlist
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE WISHLIST SET
                item_name = ?,
                item_description = ?,
                target_price = ?,
                category = ?
            WHERE id = ?
        """, (item_name, item_description, target_price, category, item_id))
        connection.commit()
        connection.close()

    def delete_wishlist(self, item_id):
        """
        Menghapus item wishlist
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM WISHLIST WHERE id = ?", (item_id,))
        connection.commit()
        connection.close()

    def wishlist_save(self, item_id, amount):
        """
        Menambah/mengurangi tabungan (amount negatif = tarik)
        """
        connection = self._connect()
        cursor = connection.cursor()
        row = cursor.execute("SELECT saved_amount FROM WISHLIST WHERE id = ?", (item_id,)).fetchone()
        if not row:
            connection.close()
            return
        new_amount = max(0, row["saved_amount"] + amount)
        cursor.execute("UPDATE WISHLIST SET saved_amount = ? WHERE id = ?", (new_amount, item_id))
        connection.commit()
        connection.close()

    def wishlist_achieve(self, item_id):
        """
        Toggle status tercapai / dibuka lagi
        """
        connection = self._connect()
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE WISHLIST SET achieved = CASE WHEN achieved = 1 THEN 0 ELSE 1 END
            WHERE id = ?
        """, (item_id,))
        connection.commit()
        connection.close()
