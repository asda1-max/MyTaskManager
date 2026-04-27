from flask import Flask, render_template, redirect, url_for
from flask_apscheduler import APScheduler
from backend import task_manager
from datetime import datetime

app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

task = None

@scheduler.task('cron', id='update_task', hour = 15, minute = 6 )
def update_task_begin():
    
    task.timing_update()

@app.route('/')
def index():
    
    raw_task_list_daily = task.select_current_task(task_type='daily')
    raw_task_list_weekly = task.select_current_task(task_type='weekly')
    raw_task_list_monthly = task.select_current_task(task_type='monthly')
    task_list_daily = translate_raw_data(raw_task_list_daily)
    task_list_weekly = translate_raw_data(raw_task_list_weekly)
    task_list_monthly = translate_raw_data(raw_task_list_monthly)


    return render_template('index.html', task_list_daily = task_list_daily, task_list_weekly = task_list_weekly, task_list_monthly = task_list_monthly)

@app.route('/finish_a_task/<int:id_task>', methods=['POST'])
def finish_a_task_func(id_task):
    print(f"Selesaikan task dengan id : {id_task}")
    task.check_task_completion(id_task)
    return redirect('/')

def translate_raw_data(raw_task_list):
    task_list = []
    # print(f"processing : {task_list} \n\n")
    for raw_task in raw_task_list:
        ids, task_name,task_description, task_type, frequency = raw_task
        task_list.append(
            {
                "id" : ids,
                "task_name" : task_name,
                "task_description" : task_description,
                "task_type" : task_type,
                "frequency" : frequency
            }
        )
    print("data didapat : ", task_list, "\n\n")
    return task_list



if __name__ == "__main__":
    task = task_manager()
    today = datetime.now()
    print(today.day, today.time())
    app.run(debug=True, use_reloader=False, host="0.0.0.0")

    

    