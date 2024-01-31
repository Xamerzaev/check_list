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
                end_date TEXT
            )
            """)
            await db.commit()
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
                INSERT INTO profile (user_id, name, phone, organization, location, status_check, status_payment, subscribe_period, timestamp, end_date)
                VALUES (?, '', '', '', '', 8, 8, 8, '', '')""",
                (user_id,))
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
                data['passport'],
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