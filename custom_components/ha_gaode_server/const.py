from typing import Final

DOMAIN: Final = "ha_gaode_server"
"""
CONFIG
"""
CONFIG_DB: Final = "config_db"
CONFIG_DB_URL: Final = "db_url"
CONFIG_CHANGE_GPSLOGGER_STATE: Final = "change_gpslogger_state"
CONFIG_GAODE_SERVER_KEY: Final = "gaode_server_key"
"""
DEFAULT VALUE
"""
DEFAULT_DB_NAME: Final = "dx_db.db"
DEFAULT_ZONE_STORE_NAME: Final = "zone.json"
DEFAULT_DX_RECORD_DATETIME_FORMAT: Final = "%Y-%m-%d %H:%M:%S"
"""
CUSTOM_ATTR
"""
CUSTOM_ATTR_DX_RECORD_DATETIME: Final = "dx_record_datetime"
CUSTOM_ATTR_GCJ02_LONGITUDE: Final = "gcj02_longitude"
CUSTOM_ATTR_GCJ02_LATITUDE: Final = "gcj02_latitude"
CUSTOM_ATTR_DX_STATE: Final = "dx_state"
CUSTOM_ATTR_DX_DISTANCE: Final = "dx_distance"
CUSTOM_ATTR_DX_PRE_STATE: Final = "dx_pre_state"


EVENT_NEW_STATE = "new_state"
