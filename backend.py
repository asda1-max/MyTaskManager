import sqlite3
import pathlib
from datetime import datetime

class task_manager():
    """
    This Class is for CRUD-ing the task
    """
    def __init__(self):
        """
        Class Intitialization :
            -Creating Database if not existed
        """
        file_path = pathlib.Path("taskmanager.db")
        if not file_path.exists():
            print("Database not existed, making new one")
            self.create_database("taskmanager.db")

    def create_database(self, database_name):
        """
        Creating Database
        """
        connection = sqlite3.connect(database=database_name)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE TASK(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       task_name TEXT NOT NULL,
                       task_description TEXT,
                       task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                       frequency INTEGER DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE CURRENT_TASK(
                       id INTEGER NOT NULL,
                       task_name TEXT NOT NULL,
                       task_description TEXT,
                       task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                       frequency INTEGER NOT NULL
            )
        """)
        connection.commit()
        connection.close()

    def add_task(self, task_name, task_description, task_type, frequency):
        """
        adding task to the databases
        """
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO TASK(task_name,task_description, task_type, frequency) VALUES (?,?,?,?)
        """,(task_name,task_description, task_type, frequency))
        new_id = cursor.lastrowid
        self.move_task_to_current_task(cursor, new_id, task_name, task_description, task_type, frequency)
        connection.commit()
        connection.close()

    def select_task(self,task_type):
        """
        selecting task based on task type ('daily', 'weekly', 'monthly')
        """
        current_data = []
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        res = cursor.execute("""
            SELECT * FROM TASK WHERE 
                             task_type = ?
        """, (task_type,))
        for row in res:
            current_data.append(row)
            
        connection.commit()
        connection.close()
        return current_data
    
    def select_current_task(self,task_type):
        """
        selecting task based on task type ('daily', 'weekly', 'monthly')
        """
        current_data = []
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        res = cursor.execute("""
            SELECT * FROM CURRENT_TASK WHERE 
                             task_type = ?
        """, (task_type,))
        for row in res:
            current_data.append(row)
            
        connection.commit()
        connection.close()
        return current_data

    def edit_task(self,id, task_name, task_description, task_type, frequency):
        """
        edit task
        """
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE TASK 
                    SET
                       task_name = ? ,
                       task_description = ? ,
                       task_type = ? ,
                       frequency = ?
                    WHERE
                       id = ?
                       
        """,(task_name, task_description, task_type, frequency,id))
        connection.commit()
        connection.close()

    def delete_task(self,id):
        """
        delete task
        """
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM TASK 
                    WHERE 
                       id = ?
                       
        """,(id,))
        cursor.execute("""
            DELETE FROM CURRENT_TASK 
                    WHERE 
                       id = ?
                       
        """,(id,))
        connection.commit()
        connection.close()
    
    def update_current_task(self,task_type):
        """updating current task"""
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        data = self.select_task(task_type)

        cursor.execute("""
            DELETE FROM CURRENT_TASK 
                    WHERE 
                       task_type = ?
                       
        """,(task_type,))

        for row in data:
            ids = row[0]
            task_name = row[1]
            task_description = row[2]
            task_types = row[3]
            frequency = row[4]
            print(f"moving task : [ ID : {ids}, task_name : {task_name},task_description : {task_description}, task_type : {task_types}, frequency : {frequency} ]")
            self.move_task_to_current_task(cursor,ids,task_name,task_description,task_types, frequency)
            
        connection.commit()
        connection.close()

    def move_task_to_current_task(self,cursor,id,task_name,task_description, task_type, frequency):
        """
        moving task from table 'TASK' to 'CURRENT_TASK"
        """
        cursor.execute("""
                INSERT INTO CURRENT_TASK(id,task_name,task_description,task_type, frequency) VALUES (?,?,?,?,?)
            """,(id,task_name,task_description, task_type, frequency))
        
    def timing_update(self):
        today = datetime.now()
        print("date : ", today.day)

        print("debug : UPDATING DAILY TASK...")
        self.update_current_task('daily')
        print("\n")
        
        if today.weekday() == 5:
            print("debug : UPDATING WEEKLY TASK...")
            self.update_current_task('weekly')
            print("\n")
            
        if today.day == 25:
            print("debug : UPDATING MONTHLY TASK...")
            self.update_current_task('monthly')
            print("\n")

    def check_task_completion(self, id):
        current_data = []
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        res = cursor.execute("""
            SELECT frequency FROM CURRENT_TASK 
                        WHERE 
                             id = ?
        """, (id,))
        data_selected_frequency = res.fetchone()
        print(f"frquency remaining : {data_selected_frequency[0]}")
        connection.commit()
        if data_selected_frequency[0] - 1 == 0:
            print("jatah task habis")
            cursor.execute("""
            DELETE FROM CURRENT_TASK 
                    WHERE 
                       id = ?         
            """,(id,))
        else:
            print(f"dikurangi 1 jadi : {data_selected_frequency[0]-1}")
            cursor.execute("""
            UPDATE CURRENT_TASK 
                    SET
                       frequency = ?
                    WHERE
                       id = ?
                       
        """,(data_selected_frequency[0]-1,id))

        connection.commit()
        connection.close()
        return current_data

    def reset_all_current_task(self):
        self.update_current_task('daily')
        self.update_current_task('weekly')
        self.update_current_task('monthly')



    
    def task_logging(self):
        """
        WIP
        """
        pass

        

asu = task_manager()
# asu.add_task("Tidur", "Istirahat di Kasur, untuk recovery energy buat hari besok", 'daily',1)
# asu.add_task("Exercise", "30 minutes of physical activity", 'daily', 1)
# asu.add_task("Read", "Read for 20 minutes before bed", 'daily', 1)
# asu.add_task("Meditate", "10 minutes meditation session", 'daily', 1)
# asu.add_task("Drink Water", "Consume 8 glasses of water", 'daily', 1)
# asu.add_task("Study", "Study new programming concepts", 'daily', 1)
# asu.add_task("Clean Room", "Tidy up and organize workspace", 'weekly', 1)
# asu.add_task("Laundry", "Wash and fold clothes", 'weekly', 1)
# asu.add_task("Grocery Shopping", "Buy weekly groceries and essentials", 'weekly', 1)
# asu.add_task("Review Goals", "Review weekly progress and goals", 'weekly', 1)
# asu.add_task("Pay Bills", "Check and pay monthly bills", 'monthly', 1)
# asu.add_task("Car Maintenance", "Service and maintain vehicle", 'monthly', 1)
# asu.add_task("Health Checkup", "Schedule monthly health checkup", 'monthly', 1)
# asu.reset_all_current_task()






