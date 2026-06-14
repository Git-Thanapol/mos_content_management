"""
Database router for the JST read-only connection.

Routes reads for JST mirror models to the 'jst' database.
Blocks all writes and migrations on 'jst'.
"""

JST_MODEL_NAMES = {
    "jstmasteritem",
    "jststocksnapshot",
    "jstpoheader",
    "jstpoitem",
}


class JstRouter:
    def db_for_read(self, model, **hints):
        if model._meta.model_name in JST_MODEL_NAMES:
            return "jst"
        return None

    def db_for_write(self, model, **hints):
        # Never allow writes to JST models
        if model._meta.model_name in JST_MODEL_NAMES:
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Only allow relations within the same database
        if obj1._meta.model_name in JST_MODEL_NAMES or obj2._meta.model_name in JST_MODEL_NAMES:
            return None
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Never run migrations on the JST database
        if db == "jst":
            return False
        return None
