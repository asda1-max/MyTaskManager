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
    task = task_manager()
    raw_task_list_daily = task.select_task(task_type='daily')
    raw_task_list_weekly = task.select_task(task_type='weekly')
    raw_task_list_monthly = task.select_task(task_type='monthly')
    task_list_daily = translate_raw_data(raw_task_list_daily)
    task_list_weekly = translate_raw_data(raw_task_list_weekly)
    task_list_monthly = translate_raw_data(raw_task_list_monthly)


    return render_template('index.html', task_list_daily = task_list_daily, task_list_weekly = task_list_weekly, task_list_monthly = task_list_monthly)

def translate_raw_data(raw_task_list):
    task_list = []
    for raw_task in raw_task_list:
        ids, task_name, task_type, frequency = raw_task
        task_list.append(
            {
                "id" : ids,
                "task_name" : task_name,
                "task_type" : task_type,
                "frequency" : frequency
            }
        )
    print("data didapat : ", task_list)
    return task_list



if __name__ == "__main__":
    today = datetime.now()
    print(today.day, today.time())
    app.run(debug=True, use_reloader=False)

    

    