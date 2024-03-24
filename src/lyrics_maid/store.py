import atexit
import json
from pathlib import Path

from .log import logger


class JSONStore:
    """
    A simple JSON-based persistent non-relational key-value data storage implementation.
    The whole JSON is automatically written to disk when program exits.

    Do NOT use if performance is an issue.
    """

    STORE_VERSION = 1

    STORE_VER_KEY = "store_ver"
    TABLE_VER_KEY = "table_ver"
    DATA_KEY = "data"

    def __init__(self, storage_file: str, table_version: int):
        self.storage_file = Path(storage_file)
        self.table_version = table_version
        self.changed = False
        self.refresh()
        atexit.register(self.save)

    def serialize(self, data):
        return {
            JSONStore.STORE_VER_KEY: JSONStore.STORE_VERSION,
            JSONStore.TABLE_VER_KEY: self.table_version,
            JSONStore.DATA_KEY: data,
        }

    def invalid_store(self, store):
        return (
            # Validate store version
            JSONStore.STORE_VER_KEY not in store
            or store[JSONStore.STORE_VER_KEY] != JSONStore.STORE_VERSION
            # Validate table version
            or JSONStore.TABLE_VER_KEY not in store
            or store[JSONStore.TABLE_VER_KEY] != self.table_version
            # Validate data struct
            or JSONStore.DATA_KEY not in store
        )

    def refresh(self):
        # Create a default store if storage file does not exist
        if not self.storage_file.exists():
            return self.reset()
        # Load the store into memory
        try:
            with open(self.storage_file, "r", encoding="utf-8") as file:
                store = json.load(file)
        except Exception as e:
            logger.error(
                "Encountered error when loading JSON from file [%s], file will be reset: %s"
                % (self.storage_file, e)
            )
            return self.reset()
        if self.invalid_store(store):
            return self.reset()
        try:
            self.store = JSONStore.KeyValueStore(store[JSONStore.DATA_KEY])
            logger.debug("Loaded JSONStore [%s]" % (self))
        except Exception as e:
            logger.error(
                "Encountered error when initailize store [%s], file will be reset: %s"
                % (self.storage_file, e)
            )
            return self.reset()

    def __str__(self) -> str:
        return self.storage_file.name

    def __repr__(self) -> str:
        return self.storage_file.name

    def reset(self):
        logger.debug("Reset JSONStore [%s]" % (self))
        self.store = JSONStore.KeyValueStore()
        self.changed = True

    def save(self):
        if not self.changed:
            return
        store = self.serialize(self.store.serialize())
        with open(self.storage_file, "w") as file:
            json.dump(store, file)
        logger.debug("Saved JSONStore [%s]" % (self))

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.changed = True
        return self.store.set(key, value)

    def remove(self, key):
        return self.store.remove(key, None)

    def __del__(self):
        atexit.unregister(self.save)

    class KeyValueStore:

        def __init__(self, data=dict()):
            if type(data) is not dict:
                raise TypeError(
                    "KeyValueStore initialization data are in unexpected format"
                )
            # TODO: accept a table schema and validate the data
            self.data = data

        def get(self, key):
            if key in self.data:
                return self.data[key]
            return None

        def set(self, key, value):
            self.data[key] = value
            return value

        def remove(self, key):
            return self.data.pop(key, None)

        def serialize(self):
            return self.data

        def __str__(self):
            return str(self.serialize())

        def __repr__(self):
            return str(self)
