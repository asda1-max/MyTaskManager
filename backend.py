import sqlite3
import pathlib

class task_manager():
    """_summary_
    """
    def __init__(self):
        file_path = pathlib.Path("taskmanager.db")
        if not file_path.exists():
            print("Database existed, making new one")
            self.create_database("taskmanager.db")

    def create_database(self, database_name):
        connection = sqlite3.connect(database=database_name)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE TASK(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       task_name TEXT NOT NULL,
                       task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                       frequency INTEGER DEFAULT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE CURRENT_TASK(
                       id INTEGER NOT NULL,
                       task_name TEXT NOT NULL,
                       task_type TEXT NOT NULL CHECK(task_type IN ('daily', 'weekly', 'monthly')),
                       frequency INTEGER NOT NULL
            )
        """)
        connection.commit()
        connection.close()

    def add_task(self, task_name, task_type, frequency):
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO TASK(task_name, task_type, frequency) VALUES (?,?,?)
        """,(task_name, task_type, frequency))
        new_id = cursor.lastrowid
        self.move_task_to_current_task(cursor, new_id, task_name, task_type, frequency)
        connection.commit()
        connection.close()

    def select_task(self,task_type):
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

    def edit_task(self,id, task_name, task_type, frequency):
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE TASK 
                    SET
                       task_name = ? ,
                       task_type = ? ,
                       frequency = ?
                    WHERE
                       id = ?
                       
        """,(task_name, task_type, frequency,id))
        connection.commit()
        connection.close()

    def delete_task(self,id):
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM TASK 
                    WHERE 
                       id = ?
                       
        """,(id,))
        connection.commit()
        connection.close()
    
    def update_current_task(self,task_type):
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
            task_types = row[2]
            frequency = row[3]
            print(f"ID : {ids}, task_name : {task_name}, task_type : {task_types}, frequency : {frequency}")
            self.move_task_to_current_task(cursor,ids,task_name,task_types, frequency)
            
        connection.commit()
        connection.close()

    def move_task_to_current_task(self,cursor,id,task_name, task_type, frequency):
        cursor.execute("""
                INSERT INTO CURRENT_TASK(id,task_name, task_type, frequency) VALUES (?,?,?,?)
            """,(id,task_name, task_type, frequency))
    
    def task_logging(self):
        pass

        

asu = task_manager()
asu.add_task("eek", "daily", 3)
# asu.update_current_task("monthly")






