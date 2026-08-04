from flask import Flask, render_template, redirect, url_for, request, jsonify, session, make_response
from flask_apscheduler import APScheduler
from backend import task_manager
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "mysecretkey123"

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

task = task_manager()

AUTH_EXEMPT = {"login", "login_func", "setup", "setup_func", "static"}


@app.before_request
def check_auth():
    if not task.is_password_set():
        if request.endpoint not in ("setup", "setup_func", "static"):
            return redirect(url_for("setup"))
        return
    if request.endpoint in AUTH_EXEMPT:
        return
    if session.get("authenticated"):
        return
    token = request.cookies.get("remember_token")
    if token and task.validate_remember_token(token):
        session["authenticated"] = True
        return
    return redirect(url_for("login"))


@scheduler.task('cron', id='reset_daily', hour=0, minute=0)
def reset_daily_job():
    task.update_current_task('daily')


@scheduler.task('cron', id='reset_weekly', hour=0, minute=5, day_of_week='mon')
def reset_weekly_job():
    task.update_current_task('weekly')


@scheduler.task('cron', id='reset_monthly', hour=0, minute=10, day=1)
def reset_monthly_job():
    task.update_current_task('monthly')


def translate_raw_data(raw_task_list, streaks=None):
    task_list = []
    for raw_task in raw_task_list:
        item = dict(raw_task)
        if streaks and item["id"] in streaks:
            item["streak_current"], item["streak_best"] = streaks[item["id"]]
        else:
            item["streak_current"], item["streak_best"] = 0, 0
        task_list.append(item)
    return task_list


def load_dashboard_data():
    streaks = task.get_streaks()
    task_dates = task.select_all_completion_dates_grouped()
    result = {}
    for tp in ("daily", "weekly", "monthly"):
        all_tasks = translate_raw_data(task.select_current_task(tp), streaks)
        unfinished = []
        finished = []
        for t in all_tasks:
            t["finished"] = (t["frequency"] or 0) <= 0
            if t["finished"]:
                finished.append(t)
            else:
                unfinished.append(t)
        result[tp] = {"unfinished": unfinished, "finished": finished, "all": all_tasks}
    return {
        "daily": result["daily"],
        "weekly": result["weekly"],
        "monthly": result["monthly"],
        "task_dates": task_dates,
    }


@app.template_filter("rupiah")
def rupiah_filter(value):
    return "Rp " + f"{int(value or 0):,}".replace(",", ".")


@app.template_filter("datetime_ind")
def datetime_ind(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value
    return dt.strftime("%d %b %Y, %H:%M")


@app.template_filter("days_until")
def days_until_filter(value):
    if not value:
        return None
    try:
        dl = datetime.strptime(value[:10], "%Y-%m-%d").date()
        return (dl - date.today()).days
    except (ValueError, TypeError):
        return None


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if task.is_password_set():
        return redirect(url_for("login"))
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()
        if password and password == confirm and len(password) >= 4:
            task.set_password(password)
            session["authenticated"] = True
            return redirect(url_for("index"))
        return render_template("setup.html", error="Password harus minimal 4 karakter dan cocok.")
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not task.is_password_set():
        return redirect(url_for("setup"))
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        if task.verify_password(password):
            session["authenticated"] = True
            resp = make_response(redirect(url_for("index")))
            if request.form.get("remember"):
                token = task.generate_remember_token()
                resp.set_cookie("remember_token", token, max_age=365*24*3600)
            return resp
        return render_template("login.html", error="Password salah.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("remember_token")
    return resp


@app.route("/")
def index():
    data = load_dashboard_data()
    stats = {
        "done_today": task.count_completed_today(),
        "total": sum(len(task.select_task(t)) for t in ("daily", "weekly", "monthly")),
    }
    return render_template(
        "index.html",
        task_list_daily=data["daily"],
        task_list_weekly=data["weekly"],
        task_list_monthly=data["monthly"],
        task_dates=data["task_dates"],
        stats=stats,
    )


@app.route("/add_task", methods=["POST"])
def add_task_func():
    task_name = request.form.get("task_name", "").strip()
    task_description = request.form.get("task_description", "").strip()
    task_type = request.form.get("task_type", "daily")
    frequency = request.form.get("frequency", 1, type=int) or 1
    priority = request.form.get("priority", 0, type=int) or 0
    deadline = request.form.get("deadline", "").strip() or None
    tags = request.form.get("tags", "").strip()
    if task_name:
        task.add_task(task_name, task_description, task_type, max(1, frequency),
                      max(0, min(3, priority)), deadline, tags)
    return redirect(url_for("index"))


@app.route("/edit_task/<int:task_id>", methods=["POST"])
def edit_task_func(task_id):
    task_name = request.form.get("task_name", "").strip()
    task_description = request.form.get("task_description", "").strip()
    task_type = request.form.get("task_type", "daily")
    frequency = request.form.get("frequency", 1, type=int) or 1
    priority = request.form.get("priority", 0, type=int) or 0
    deadline = request.form.get("deadline", "").strip() or None
    tags = request.form.get("tags", "").strip()
    if task_name:
        task.edit_task(task_id, task_name, task_description, task_type, max(1, frequency),
                       max(0, min(3, priority)), deadline, tags)
    return redirect(url_for("index"))


@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task_func(task_id):
    task.delete_task(task_id)
    return redirect(url_for("index"))


@app.route("/finish_a_task/<int:task_id>", methods=["POST"])
def finish_a_task_func(task_id):
    task.check_task_completion(task_id)
    return redirect(url_for("index"))


@app.route("/task_detail/<int:task_id>")
def task_detail(task_id):
    detail = task.get_task_detail(task_id)
    if not detail:
        return redirect(url_for("index"))
    logs = task.select_logs_by_task(task_id)
    chart = task.select_completions_by_day_per_task(task_id, 30)
    return render_template("detail_task.html", task=detail, logs=logs, chart=chart)


@app.route("/reset_daily", methods=["POST"])
def reset_daily_func():
    task.update_current_task('daily')
    return redirect(url_for("index"))


@app.route("/reset_weekly", methods=["POST"])
def reset_weekly_func():
    task.update_current_task('weekly')
    return redirect(url_for("index"))


@app.route("/reset_monthly", methods=["POST"])
def reset_monthly_func():
    task.update_current_task('monthly')
    return redirect(url_for("index"))


@app.route("/reset_all", methods=["POST"])
def reset_all_func():
    task.reset_all_current_task()
    return redirect(url_for("index"))


@app.route("/history")
def history():
    page = request.args.get("page", 1, type=int)
    logs, total, total_pages = task.select_logs_paginated(page, 50)
    chart = task.select_completions_by_day(30)
    heatmap = task.select_activity_heatmap(52)
    return render_template("history.html", logs=logs, chart=chart, heatmap=heatmap,
                           page=page, total_pages=total_pages, total_logs=total)


@app.route("/export")
def export_data():
    data = task.export_data()
    return jsonify(data)


@app.route("/wishlist")
def wishlist():
    items = task.select_wishlist()
    return render_template("wishlist.html", wishlist=items)


@app.route("/add_wishlist", methods=["POST"])
def add_wishlist_func():
    item_name = request.form.get("item_name", "").strip()
    item_description = request.form.get("item_description", "").strip()
    target_price = request.form.get("target_price", 0, type=int) or 0
    category = request.form.get("category", "barang")
    if category not in ("barang", "keinginan"):
        category = "barang"
    if item_name:
        task.add_wishlist(item_name, item_description, max(0, target_price), category)
    return redirect(url_for("wishlist"))


@app.route("/edit_wishlist/<int:item_id>", methods=["POST"])
def edit_wishlist_func(item_id):
    item_name = request.form.get("item_name", "").strip()
    item_description = request.form.get("item_description", "").strip()
    target_price = request.form.get("target_price", 0, type=int) or 0
    category = request.form.get("category", "barang")
    if category not in ("barang", "keinginan"):
        category = "barang"
    if item_name:
        task.edit_wishlist(item_id, item_name, item_description, max(0, target_price), category)
    return redirect(url_for("wishlist"))


@app.route("/delete_wishlist/<int:item_id>", methods=["POST"])
def delete_wishlist_func(item_id):
    task.delete_wishlist(item_id)
    return redirect(url_for("wishlist"))


@app.route("/wishlist_save/<int:item_id>", methods=["POST"])
def wishlist_save_func(item_id):
    amount = request.form.get("amount", 0, type=int) or 0
    task.wishlist_save(item_id, amount)
    return redirect(url_for("wishlist"))


@app.route("/wishlist_achieve/<int:item_id>", methods=["POST"])
def wishlist_achieve_func(item_id):
    task.wishlist_achieve(item_id)
    return redirect(url_for("wishlist"))


if __name__ == "__main__":
    for task_type in ("daily", "weekly", "monthly"):
        if not task.select_current_task(task_type):
            task.update_current_task(task_type)
    print("Server dimulai :", datetime.now())
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=8010)