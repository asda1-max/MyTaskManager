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
        connection.commit()
        connection.close()

    def view_task(self):
        connection = sqlite3.connect(database="taskmanager.db")
        cursor = connection.cursor()
        res = cursor.execute("""
            SELECT * FROM TASK
        """)
        print(res.fetchall())
        connection.commit()
        connection.close()

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
    
    def update_current_task(self):
        pass


asu = task_manager()
asu.view_task()






