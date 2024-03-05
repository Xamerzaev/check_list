from os import getenv

from dotenv import load_dotenv

load_dotenv()


TOKEN = getenv("BOT_TOKEN")
MODERATOR = getenv("ID_MODERATOR")
USER_NAME_ADMIN = getenv("USER_NAME_ADMIN")
PROVIDER_TOKEN = getenv("PROVIDER_TOKEN")

TARIFFS = {
    100: (3, 30, 41),
    120: (6, 30, 42),
    140: (15, 30, 43),
    2490: ('Безлимит', 30, 44),
    1490: (3, 90, 51),
    2100: (6, 90, 52),
    4500: (15, 90, 53),
    7470: ('Безлимит', 90, 54),
    6000: (3, 365, 61),
    8400: (6, 365, 62),
    18000: (15, 365, 63),
    29880: ('Безлимит', 365, 64),
}
