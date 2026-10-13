# Importing each adapter module here triggers its @register decorator,
# making it selectable in the UI. New contributed adapters (mysql, mongo,
# snowflake, ...) get one line added here.
from dbchat.adapters import postgres  # noqa: F401
