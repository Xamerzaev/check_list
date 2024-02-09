from datetime import datetime, timedelta
import aiosqlite
import logging
import secrets

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
                FOREIGN KEY (creator_user_id) REFERENCES profile(user_id)
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS employee (
              employee_id TEXT PRIMARY KEY,
              employee_first_name TEXT,
              employee_last_name TEXT,
              room_id TEXT,
              tasks_completed_count INTEGER DEFAULT 0,
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
              FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
              FOREIGN KEY (room_id) REFERENCES room(room_id) ON DELETE CASCADE
            )
            """)

        logger.info("Database initialized and table created")
    except Exception as e:
        logger.error(f"Database error: {e}")


async def create_profile(user_id):
    async with aiosqlite.connect('users.db') as db:
        try:
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
    async with state.proxy() as data, aiosqlite.connect('users.db') as db:
        try:
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
        except Exception as e:
            logger.error(f"Database error: {e}")


async def get_pending_profiles():
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("""
        SELECT * FROM profile WHERE status_check = 0
        """)
        return await cursor.fetchall()


async def get_status(user_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("""
        SELECT * FROM profile WHERE user_id = ?
        """, (user_id,))
        return await cursor.fetchall()


async def get_all_subscribers():
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("""
        SELECT * FROM profile
        """)
        return await cursor.fetchall()


async def update_profile_status(user_id, status_check):
    async with aiosqlite.connect('users.db') as db:
        await db.execute("""
        UPDATE profile SET status_check = ? WHERE user_id = ?
        """, (status_check, user_id))
        await db.commit()


async def update_profile_status_payment(user_id, payment):
    async with aiosqlite.connect('users.db') as db:
        await db.execute("""
        UPDATE profile SET status_payment = ? WHERE user_id = ?
        """, (payment, user_id))
        await db.commit()


async def update_subscribe_period(user_id, period):
    async with aiosqlite.connect('users.db') as db:
        await db.execute("""
        UPDATE profile SET subscribe_period = ? WHERE user_id = ?
        """, (period, user_id))
        await db.commit()


async def get_current_end_date(user_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("""
        SELECT end_date FROM profile WHERE user_id = ?
        """, (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def update_end_date(user_id, days):
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


async def create_new_room(user_id):
    room_id = secrets.randbelow(10 ** 6)

    async with aiosqlite.connect('users.db') as db:
        try:
            room = await db.execute("""
            SELECT 1 FROM room 
            WHERE room_id = ?
            """, (room_id,))
            room = await room.fetchone()

            if not room:
                await db.execute("""
                INSERT INTO room (room_id, creator_user_id)
                VALUES (?, ?)
                """, (room_id, user_id))
                await db.commit()
                logger.info(f"Room created for user_id: {user_id}")
            else:
                logger.info("Room with such ID already exists")
        except Exception as e:
            logger.error(f"Error creating room for user_id {user_id}: {e}")


async def check_room_exists(room_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT * FROM room
            WHERE room_id = ?
        """, (room_id,))
        room_data = await result.fetchone()
        return room_data if room_data else None


async def get_room_id(user_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT room_id FROM room
            WHERE creator_user_id = ?
        """, (user_id,))
        owner_id = await result.fetchone()
        return owner_id[0] if owner_id else None


async def check_employee_in_room(room_id, user_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT 1 FROM employee
            WHERE room_id = ? AND employee_id = ?
        """, (room_id, user_id))
        employee_data = await result.fetchone()
        return bool(employee_data)


async def get_employees(room_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT * FROM employee
            WHERE room_id = ?
        """, (room_id,))
        employees = await result.fetchall()
        return employees


async def add_employee_in_room(employee_id, room_id):
    async with aiosqlite.connect('users.db') as db:
        try:
            await db.execute("""
            INSERT INTO employee (employee_id, employee_first_name, employee_last_name, room_id)
            VALUES (?, '', '',  ?)""",
                             (employee_id, room_id))
            await db.commit()
            logger.info(f"employee {employee_id} added in room: {room_id}")
        except Exception as e:
            logger.error(f"Error adding an employee {employee_id} to the room {room_id}: {e}")


async def get_checklist_for_user(employee_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT * FROM checklist
            WHERE employee_id = ?
        """, (employee_id,))
        employees = await result.fetchall()
        return employees


async def get_checklist_for_room(room_id):
    async with aiosqlite.connect('users.db') as db:
        result = await db.execute("""
            SELECT * FROM checklist
            WHERE room_id = ? AND task_type = 'room'
        """, (room_id,))
        checklist = await result.fetchall()
        return checklist


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
            cursor = await db.execute("SELECT room_id FROM employee WHERE employee_id = ?", (employee_id,))
            row = await cursor.fetchone()
            if row:
                return row[0]
            else:
                return None
    except Exception as e:
        logger.error(f"Error fetching room_id by employee_id: {e}")
        return None


async def change_room_task_status(task_id, user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute("SELECT task_status FROM checklist WHERE checklist_id = ?", (task_id,))
            current_status = await cursor.fetchone()
            if current_status[0] == '0':
                new_status = '1'
                await tasks_completed_count(user_id, '+')
            else:
                new_status = '0'
                await tasks_completed_count(user_id, '-')

            await db.execute("UPDATE checklist SET task_status = ? WHERE checklist_id = ?", (new_status, task_id,))
            await db.commit()

            logger.info(f"Task {task_id} status toggled: {new_status}")

    except Exception as e:
        logger.error(f"Error toggling task status for task {task_id}: {e}")


async def tasks_completed_count(employee_id, action):
    try:
        async with aiosqlite.connect('users.db') as db:
            if action == '+':
                await db.execute(
                    "UPDATE employee SET tasks_completed_count = tasks_completed_count + 1 WHERE employee_id = ?",
                    (employee_id,))
            elif action == '-':
                await db.execute(
                    "UPDATE employee SET tasks_completed_count = tasks_completed_count - 1 WHERE employee_id = ?",
                    (employee_id,))
            await db.commit()
            logger.info(f"Employee {employee_id} tasks_completed_count incremented")

    except Exception as e:
        logger.error(f"Error incrementing tasks_completed_count for employee {employee_id}: {e}")


async def get_admin_activity(user_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("SELECT is_active FROM profile WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return row[0]


async def get_employee_activity(employee_id):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("SELECT is_active FROM employee WHERE employee_id = ?", (employee_id,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            return None


async def set_employee_activity(user_id, is_active):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("UPDATE employee SET is_active = ? WHERE employee_id = ?", (is_active, user_id))
            await db.commit()
            logger.info(f"User activity updated for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")


async def set_admin_activity(user_id, is_active):
    try:
        async with aiosqlite.connect('users.db') as db:
            await db.execute("UPDATE profile SET is_active = ? WHERE user_id = ?", (is_active, user_id))
            await db.commit()
            logger.info(f"User activity updated for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")


async def get_monthly_report(user_id):
    try:
        async with aiosqlite.connect('users.db') as db:
            cursor = await db.execute(
                "SELECT * FROM room WHERE creator_user_id = ?",
                (user_id,))
            room_user = await cursor.fetchone()
            cursor = await db.execute(
                "SELECT employee_id, tasks_completed_count FROM employee WHERE room_id = ?",
                (room_user[0],))
            employees = await cursor.fetchall()
            data = {}

            for employee in employees:
                data[room_user[1]] = {employee[0]: employee[1]}
        return data

    except Exception as e:
        logger.error(f"Error sending monthly report for {user_id}: {e}")