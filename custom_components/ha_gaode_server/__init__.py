# -*- coding: utf-8 -*-
from __future__ import annotations

DOMAIN = "ha_gaode_server"

import logging

from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from datetime import datetime, timedelta
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_COMPONENT_LOADED,
)
from .dx_exception import ConfigException

from .gps_logger import DxGpsLogger, DxGpsLoggerView
from .zone import DxZone, DxZoneView

_LOGGER = logging.getLogger(__name__)


class Data:
    gps_data = []

    def store_gps_data(self, value):
        self.gps_data.append(value)

    def get_gps_data_by_timerange(self, start, end):
        filtered_list = [x for x in self.gps_data if x > 5]


def async_setup(hass, config) -> bool:
    _LOGGER.info("async_setup....")

    ha_gaode_server = config["ha_gaode_server"]
    gaode_server_key = ha_gaode_server.get("gaode_server_key")
    change_gpslogger_state = ha_gaode_server.get("change_gpslogger_state")
    if change_gpslogger_state is None:
        change_gpslogger_state = True

    if gaode_server_key is None:
        raise ConfigException("未配置高德地图key")

    gpslogger_instance = DxGpsLogger(
        hass,
        {
            "gaode_server_key": gaode_server_key,
            "change_gpslogger_state": change_gpslogger_state,
        },
    )
    zone_instance = DxZone(hass)
    gpslogger_view_instance = DxGpsLoggerView(gpslogger_instance)
    zone_view_instance = DxZoneView(zone_instance, hass)

    async def handle_event(event):
        data = event.data
        entity_id = data.get("entity_id")
        if entity_id.startswith("zone."):
            await zone_instance.handle_zone_event(event)
        elif entity_id.startswith("device_tracker."):
            await gpslogger_instance.handle_gps_event(event)

    hass.bus.async_listen(EVENT_STATE_CHANGED, handle_event)
    hass.bus.async_listen(EVENT_COMPONENT_LOADED, zone_view_instance.load_all)

    hass.http.register_view(gpslogger_view_instance)
    hass.http.register_view(zone_view_instance)

    async_track_time_interval(
        hass,
        gpslogger_instance.clear_gps_obj_dict,
        timedelta(days=1),
    )

    # return True
