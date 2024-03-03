import random
from datetime import datetime, timedelta

import aiosqlite
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


async def db_start():
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS profile(
                user_id TEXT PRIMARY KEY, 
                name TEXT,
                phone TEXT, 
                organization TEXT,
                location TEXT,
                status_check INTEGER, 
                status_payment TEXT, 
                subscribe_period INT, 
                timestamp TEXT, 
                end_date TEXT,
                is_active INTEGER DEFAULT 0
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS room(
                room_id TEXT PRIMARY KEY,
                creator_user_id TEXT,
                creation_date DATE DEFAULT (date('now')),
                FOREIGN KEY (creator_user_id) REFERENCES profile(user_id)
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS employee (
              employee_id TEXT PRIMARY KEY,
              employee_first_name TEXT,
              employee_last_name TEXT,
              room_id TEXT,
              is_active INTEGER DEFAULT 0,
              FOREIGN KEY (room_id) REFERENCES room(room_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS checklist (
              checklist_id INTEGER PRIMARY KEY AUTOINCREMENT,
              room_id TEXT,
              employee_id TEXT,
              task_description TEXT,
              task_status TEXT,
              task_type TEXT,
              creation_date DATE DEFAULT (date('now')),
              FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
              FOREIGN KEY (room_id) REFERENCES room(room_id) ON DELETE CASCADE
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS task_completion (
            completion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            employee_name TEXT,
            room_id TEXT,
            date DATE DEFAULT (date('now')),
            task_type TEXT,
            task_status TEXT DEFAULT NULL,
            FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
            )
            """)

        logger.info("Database initialized and tables created")
    except Exception as e:
        logger.error(f"Database error in db_start : {e}")


async def create_profile(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            user = await db.execute("""
            SELECT 1 FROM profile 
            WHERE user_id = ?""", (user_id,))
            user = await user.fetchone()

            if not user:
                await db.execute("""
                INSERT INTO profile (user_id, name, phone, organization, location, status_check, status_payment,
                 subscribe_period, timestamp, end_date)
                VALUES (?, '', '', '', '', 8, 8, 8, '', '')
                """, (user_id,))
                await db.commit()
                logger.info(f"Profile created for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error creating profile for user_id {user_id}: {e}")


async def edit_profile(state, user_id):
    try:
        async with state.proxy() as data, aiosqlite.connect('users.db') as db:
            await db.execute("""
            UPDATE profile SET
            name = ?, 
            phone = ?,
            organization = ?,
            location = ?
            WHERE user_id = ?""", (
                data['name'],
                data['phone'],
                data['organization'],
                data['location'],
                user_id
            ))
            await db.commit()
            logger.info(f"Profile updated successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Database error in edit_profile: {e}")


async def get_pending_profiles():
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("""
            SELECT * FROM profile WHERE status_check = 0
            """)
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Database error in get_pending_profiles: {e}")


async def get_all_subscribers():
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("""
            SELECT * FROM profile
            """)
            return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Database error in get_all_subscribers: {e}")


async def update_profile_status(user_id, status_check):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            UPDATE profile SET status_check = ? WHERE user_id = ?
            """, (status_check, user_id))
            await db.commit()
            logger.info(f"Profile status updated successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error updating profile status for user_id {user_id}: {e}")


async def get_user_info_from_db(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("""
            SELECT * FROM profile WHERE user_id = ?
            """, (user_id,))
        return await cursor.fetchall()
    except Exception as e:
        logger.error(f"Database error in get_user_info_from_db: {e}")

async def get_status_check(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("""
            SELECT status_check FROM profile WHERE user_id = ?
            """, (user_id,))
            status_check = await cursor.fetchone()
            return status_check[0] if status_check else None
    except Exception as e:
        logger.error(f"Database error in get_all_subscribers: {e}")


async def update_profile_status_payment(user_id, payment):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            UPDATE profile SET status_payment = ? WHERE user_id = ?
            """, (payment, user_id))
            await db.commit()
            logger.info(f"Profile payment status updated successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error updating profile payment status for user_id {user_id}: {e}")


async def update_subscribe_period(user_id, period):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            UPDATE profile SET subscribe_period = ? WHERE user_id = ?
            """, (period, user_id))
            await db.commit()
            logger.info(f"Profile subscribe period updated successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error updating profile subscribe_period for user_id {user_id}: {e}")


async def get_current_end_date(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("""
            SELECT end_date FROM profile WHERE user_id = ?
            """, (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Database error in get_current_end_date: {e}")


async def update_end_date(user_id, days):
    try:
        current_end_date_str = await get_current_end_date(user_id)
        if current_end_date_str:
            current_end_date = datetime.strptime(current_end_date_str, "%Y-%m-%d")
            new_end_date = current_end_date + timedelta(days=days)
        else:
            new_end_date = datetime.now() + timedelta(days=days)

        new_end_date_str = new_end_date.strftime("%Y-%m-%d")
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            UPDATE profile SET end_date = ? WHERE user_id = ?
            """, (new_end_date_str, user_id))
            await db.commit()
            logger.info(f"End date updated successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error updating end date for user_id {user_id}: {e}")


async def create_new_room(user_id):
    try:
        new_room_id = random.randint(10 ** 5, 10 ** 6)

        while True:
            existing_room = await get_room_by_id(new_room_id)
            if existing_room:
                new_room_id = random.randint(10 ** 5, 10 ** 6)
            else:
                break

        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            INSERT INTO room (room_id, creator_user_id)
            VALUES (?, ?)
            """, (new_room_id, user_id))
            await db.commit()
            logger.info(f"Room {new_room_id} created for user_id: {user_id}")

    except Exception as e:
        logger.error(f"Error creating room for user_id {user_id}: {e}")


async def get_room_by_id(room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT * FROM room
                WHERE room_id = ?
            """, (room_id,))
            room_data = await result.fetchone()
            return room_data
    except Exception as e:
        logger.error(f"Database error in get_room_by_id: {e}")


async def get_room_id(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT room_id FROM room
                WHERE creator_user_id = ?
            """, (user_id,))
            room_id = await result.fetchone()
            return room_id[0] if room_id else None
    except Exception as e:
        logger.error(f"Database error in get_room_id: {e}")


async def check_employee_in_room(room_id, user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT 1 FROM employee
                WHERE room_id = ? AND employee_id = ?
            """, (room_id, user_id))
            employee_data = await result.fetchone()
            return bool(employee_data)
    except Exception as e:
        logger.error(f"Database error in check_employee_in_room: {e}")


async def get_employees(room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT * FROM employee
                WHERE room_id = ?
            """, (room_id,))
            employees = await result.fetchall()
            return employees
    except Exception as e:
        logger.error(f"Database error in get_employees: {e}")


async def add_employee_in_room(employee_id, room_id, employee_name):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
            INSERT INTO employee (employee_id, employee_first_name, employee_last_name, room_id)
            VALUES (?, ?, '',  ?)""",
                             (employee_id, employee_name, room_id))
            await db.commit()
            logger.info(f"Employee {employee_id} added in room: {room_id}")
    except Exception as e:
        logger.error(f"Error adding an employee {employee_id} to the room {room_id}: {e}")


async def get_checklist_for_user(employee_id, room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT * FROM checklist
                WHERE employee_id = ? AND room_id = ? AND task_type = 'user'
            """, (employee_id, room_id))
            employees = await result.fetchall()
            return employees
    except Exception as e:
        logger.error(f"Database error in get_checklist_for_user: {e}")


async def get_checklist_for_room(room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            result = await db.execute("""
                SELECT * FROM checklist
                WHERE room_id = ? AND task_type = 'room'
            """, (room_id,))
            checklist = await result.fetchall()
            return checklist
    except Exception as e:
        logger.error(f"Database error in get_checklist_for_room: {e}")


async def add_task(room_id, task_for, task_description, user_id=None):
    try:
        async with aiosqlite.connect('users.db') as db:
            if task_for == 'room':
                await db.execute("""
                INSERT INTO checklist (room_id, employee_id, task_description, task_status, task_type)
                VALUES (?, '', ?,  0, ?)""",
                                 (room_id, task_description, task_for))
                await db.commit()
                logger.info(f"task {task_description} added in room: {room_id}")

            elif task_for == 'user':
                await db.execute("""
                INSERT INTO checklist (room_id, employee_id, task_description, task_status, task_type)
                VALUES (?, ?, ?,  0, ?)""",
                                 (room_id, user_id, task_description, task_for))
                await db.commit()
                logger.info(f"task {task_description} added in room: {room_id} for {user_id}")

    except Exception as e:
        logger.error(f"Error adding task in  {room_id}: {e}")


async def delete_task(task_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
                     DELETE FROM checklist
                     WHERE checklist_id = ? 
                 """, (task_id,))
            await db.commit()
            logger.info(f"Task '{task_id}' deleted")

    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")


async def get_room_id_by_employee_id(employee_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute(
                "SELECT room_id FROM employee WHERE employee_id = ? AND is_active = 1",
                (employee_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    except Exception as e:
        logger.error(f"Database error in get_room_id_by_employee_id: {e}")


async def change_task_status(task_id, user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT * FROM checklist WHERE checklist_id = ?", (task_id,))
            checklist_id_data = await cursor.fetchone()
            task_for = checklist_id_data[5]
            task_status = checklist_id_data[4]

            if task_for == 'room':
                if task_status == '0':
                    await db.execute(
                        "UPDATE checklist SET task_status = 1, employee_id = ?  WHERE checklist_id = ?",
                        (user_id, task_id,))
                else:
                    await db.execute(
                        "UPDATE checklist SET task_status = 0, employee_id = NULL  WHERE checklist_id = ?",
                        (task_id,))

            elif task_for == 'user':
                if task_status == '0':
                    await db.execute(
                        "UPDATE checklist SET task_status = 1, employee_id = ? WHERE checklist_id = ?",
                        (user_id, task_id,))
                else:
                    await db.execute(
                        "UPDATE checklist SET task_status = 0 WHERE checklist_id = ?",
                        (task_id,))

            await db.commit()
            logger.info(f"Task {task_id} status toggled.")

    except Exception as e:
        logger.error(f"Error toggling task status for task {task_id}: {e}")


async def get_admin_activity(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute(
                "SELECT is_active FROM profile WHERE user_id = ?",
                (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    except Exception as e:
        logger.error(f"Database error in get_admin_activity: {e}")


async def get_employee_activity(employee_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute(
                "SELECT is_active FROM employee WHERE employee_id = ?",
                (employee_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    except Exception as e:
        logger.error(f"Database error in get_employee_activity: {e}")


async def set_employee_activity(user_id, is_active):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute(
                "UPDATE employee SET is_active = ? WHERE employee_id = ?",
                (is_active, user_id))
            await db.commit()
            logger.info(f"Employee {user_id} updating activity {is_active}")
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")


async def set_admin_activity(user_id, is_active):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute(
                "UPDATE profile SET is_active = ? WHERE user_id = ?",
                (is_active, user_id))
            await db.commit()
            logger.info(f"Admin {user_id} updating activity {is_active}")
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")


async def get_room_owners():
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT * FROM room")
            owners = await cursor.fetchall()
            return owners
    except Exception as e:
        logger.error(f"Database error in get_room_owners: {e}")


async def remove_employee(employee_id, room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute(
                "DELETE FROM checklist WHERE employee_id = ? AND room_id = ? AND task_type = 'user'",
                (employee_id, room_id))
            await db.execute(
                "UPDATE checklist SET employee_id = NULL, task_status = 0 WHERE employee_id = ? AND task_type = 'room'",
                (employee_id,))
            await db.execute(
                "DELETE FROM employee WHERE employee_id = ? AND room_id = ?",
                (employee_id, room_id))
            await db.execute(
                "DELETE FROM task_completion WHERE employee_id = ? AND room_id = ?",
                (employee_id, room_id))
            await db.commit()
            logger.info(
                f"All tasks of employee with ID {employee_id} and the employee himself have been removed successfully.")
    except Exception as e:
        logger.error(f"Error removing employee: {e}")


async def get_room_task_status(task_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT task_status, employee_id FROM checklist WHERE checklist_id = ?",
                                      (task_id,))
            task_status = await cursor.fetchone()
            return task_status
    except Exception as e:
        logger.error(f"Error fetching task status for task ID {task_id}: {e}")


async def block_user_access(user_id: int) -> None:
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("""
                UPDATE profile
                SET status_check = 6
                WHERE user_id = ?
            """, (user_id,))
            await db.commit()
            logger.info(f"User {user_id} access to the room has been blocked.")
    except Exception as e:
        logger.error(f"Error blocking user {user_id} access to the room: {e}")


async def count_employees_in_room(room_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT COUNT(*) FROM employee WHERE room_id = ?", (room_id,))
            count = await cursor.fetchone()
            return count[0]
    except Exception as e:
        logger.error(f"Database error in count_employees_in_room {room_id}: {e}")


async def clear_task_completion():
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("DELETE FROM task_completion")
            await db.commit()
            logger.info("All records from the task_completion table have been deleted.")
    except Exception as e:
        logger.error(f"Error deleting records from the task_completion table: {e}")


async def get_employee_name(employee_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT employee_first_name FROM employee WHERE employee_id = ?", (employee_id,))
            employee_name = await cursor.fetchone()
            return employee_name[0] if employee_name else None
    except Exception as e:
        logging.error(f"Database error in get_employee_name: {e}")


async def get_task(task_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT * FROM checklist WHERE checklist_id = ?", (task_id,))
            task_description = await cursor.fetchone()
            return task_description
    except Exception as e:
        logging.error(f"Database error in get_task: {e}")


async def reset_task_status():
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT * FROM checklist")
            tasks = await cursor.fetchall()
            for task in tasks:

                if task[5] == 'room':
                    task_status = task[4]
                    room_id = task[1]
                    if task_status:
                        employee_id = task[2]
                        employee_name = await get_employee_name(employee_id)
                        await db.execute(
                            "INSERT INTO task_completion (employee_id, employee_name, room_id, task_type) VALUES (?, ?, ?, 'room')",
                            (employee_id, employee_name, room_id))
                    else:
                        await db.execute("""
                            INSERT INTO task_completion (employee_id, employee_name, room_id, task_for)
                            VALUES (NULL, NULL, ?, 'room')
                        """, (room_id,))
                    await db.execute(
                        "UPDATE checklist SET task_status = 0, employee_id = NULL WHERE task_type = 'room'")

                elif task[5] == 'user':
                    task_status = task[4]
                    room_id = task[1]
                    employee_id = task[2]
                    employee_name = await get_employee_name(employee_id)
                    await db.execute(
                        "INSERT INTO task_completion (employee_id, employee_name, room_id, task_type, task_status) VALUES (?, ?, ?, 'user', ?)",
                        (employee_id, employee_name, room_id, task_status))
                    await db.execute("UPDATE checklist SET task_status = 0")
            await db.commit()
            logging.info(f'Tasks status have been updated')
    except Exception as e:
        logging.error(f'Error reset_task_status {e}')


async def get_report_data_for_room(room_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("SELECT * FROM task_completion WHERE room_id = ? AND task_type = 'room'",
                                  (room_id,))
        room_data = await cursor.fetchall()

        employees_completed_tasks = {}
        daily_graf = {}
        for i in room_data:
            user_id = i[1]
            name = i[2]
            date = i[4]

            if user_id:
                if user_id not in employees_completed_tasks:
                    employees_completed_tasks[user_id] = [name, 1]
                else:
                    employees_completed_tasks[user_id][1] += 1
            if date not in daily_graf:
                daily_graf[date] = {}
                if user_id:
                    daily_graf[date][user_id] = [name, 1]
                    daily_graf[date]['incomplete'] = 0
                else:
                    daily_graf[date]['incomplete'] = 1

            elif date in daily_graf:
                if user_id:
                    if user_id not in daily_graf[date]:
                        daily_graf[date][user_id] = [name, 1]
                    else:
                        daily_graf[date][user_id][1] += 1
                else:
                    daily_graf[date]['incomplete'] += 1

        data = {
            'total_tasks_added': len(room_data),
            'total_tasks_incomplete': sum([1 for i in room_data if not i[1]]),
            'employees_completed_tasks': employees_completed_tasks,
            'total_tasks_completed': sum(employees_completed_tasks[i][1] for i in employees_completed_tasks),
            'daily_graf': daily_graf
        }
        return data


async def get_report_data_for_employee(room_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("""SELECT * FROM task_completion WHERE room_id = ? AND task_type = 'user'""",
                                  (room_id,))
        tasks = await cursor.fetchall()
        data = {}
        # data = {'employee_id': [employee_name, complete_task, incomplete_task]}

        for task in tasks:
            employee_id = task[1]
            task_status = int(task[6])
            employee_name = task[2]

            if employee_id in data:
                if task_status == 1:
                    data[employee_id][1] += 1
                else:
                    data[employee_id][2] += 1
            else:
                if task_status == 1:
                    data[employee_id] = [employee_name, 1, 0]
                else:
                    data[employee_id] = [employee_name, 0, 1]
        return data
