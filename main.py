from flask import Flask, render_template
from flask_apscheduler import APScheduler
from backend import task_manager
from datetime import datetime

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@scheduler.task('cron', id='update_task', hour = 15, minute = 6 )
def update_task_begin():
    task = task_manager()
    task.timing_update()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    today = datetime.now()
    print(today.day, today.time())
    app.run(debug=True, use_reloader=False)

    

    