# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import (
    async_track_time_interval,
)
from datetime import datetime, timedelta
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    EVENT_COMPONENT_LOADED,
    ATTR_ENTITY_ID,
)
from homeassistant.core import HomeAssistant, Config

from .dx_exception import ConfigException
from .gps_logger import DxGpsLogger, DxGpsLoggerCacheView, DxGpsLoggerSearchView
from .zone import DxZone, DxZoneView
from .db import DxDb
from .const import (
    DEFAULT_DB_NAME,
    DOMAIN,
    CONFIG_DB_URL,
    CONFIG_CHANGE_GPSLOGGER_STATE,
    CONFIG_GAODE_SERVER_KEY,
)


_LOGGER = logging.getLogger(__name__)


def handle_config(hass: HomeAssistant, config: Config):
    """
    Handle hass config
    """
    config_entries = hass.config_entries
    entries = config_entries.async_entries(DOMAIN)
    entry_config = None
    if len(entries) > 0:
        entry_config = entries[0].data
    config_dir = hass.config.path()
    gaode_server_key = None
    change_gpslogger_state = None
    db_url = None
    if entry_config is not None:
        gaode_server_key = entry_config.get(CONFIG_GAODE_SERVER_KEY)
        change_gpslogger_state = entry_config.get(CONFIG_CHANGE_GPSLOGGER_STATE)
        db_url = entry_config.get(CONFIG_DB_URL)
    else:
        ha_gaode_server = config.get(DOMAIN)
        if ha_gaode_server is None:
            raise ConfigException("未配置ha_gaode_server节点")
        gaode_server_key = ha_gaode_server.get(CONFIG_GAODE_SERVER_KEY)
        if gaode_server_key is None:
            raise ConfigException("未配置高德地图key")
        change_gpslogger_state = ha_gaode_server.get(CONFIG_CHANGE_GPSLOGGER_STATE)
        if change_gpslogger_state is None:
            change_gpslogger_state = True
        db_url = ha_gaode_server.get(CONFIG_DB_URL)
        if db_url is None:
            db_url = DEFAULT_DB_NAME

    db_url = os.path.join(config_dir, db_url)
    return {
        CONFIG_GAODE_SERVER_KEY: gaode_server_key,
        CONFIG_CHANGE_GPSLOGGER_STATE: change_gpslogger_state,
        CONFIG_DB_URL: db_url,
    }


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up ikuai from a config entry."""
    return True


def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """
    Hass entry
    """
    _LOGGER.debug("Async_setup")

    dx_config = handle_config(hass, config)
    gaode_server_key, change_gpslogger_state, db_url = dx_config.values()

    # 实例化数据库
    db_instance = DxDb(db_url)

    gpslogger_instance = DxGpsLogger(
        hass,
        {
            "gaode_server_key": gaode_server_key,
            "change_gpslogger_state": change_gpslogger_state,
            "db_instance": db_instance,
        },
    )
    zone_instance = DxZone(hass)
    gpslogger_cache_view_instance = DxGpsLoggerCacheView(gpslogger_instance)
    zone_view_instance = DxZoneView(zone_instance, hass)
    gpslogger_search_view_instance = DxGpsLoggerSearchView(db_instance)

    async def handle_event(event):
        data = event.data
        entity_id = data.get(ATTR_ENTITY_ID)
        if entity_id.startswith("zone."):
            await zone_instance.handle_zone_event(event)
        elif entity_id.startswith("device_tracker."):
            await gpslogger_instance.handle_gps_event(event)

    hass.bus.async_listen(EVENT_STATE_CHANGED, handle_event)
    hass.bus.async_listen(EVENT_COMPONENT_LOADED, zone_view_instance.load_all)

    hass.http.register_view(gpslogger_cache_view_instance)
    hass.http.register_view(zone_view_instance)
    hass.http.register_view(gpslogger_search_view_instance)

    async_track_time_interval(
        hass,
        gpslogger_instance.clear_gps_obj_dict,
        timedelta(days=1),
    )
