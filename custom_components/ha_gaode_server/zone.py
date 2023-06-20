# -*- coding: utf-8 -*-
import logging
import aiohttp
from .cache import get_cache, set_cache
from homeassistant.components.http import HomeAssistantView

from aiohttp import web
import json
import os
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_ZONE,
)
from .const import (
    DEFAULT_ZONE_STORE_NAME,
    EVENT_NEW_STATE,
    CUSTOM_ATTR_GCJ02_LATITUDE,
    CUSTOM_ATTR_GCJ02_LONGITUDE,
)

_LOGGER = logging.getLogger(__name__)


class DxZone:
    """ Hanlde zone"""
    gps_obj_list = {}

    def __init__(self, hass):
        self.hass = hass

    async def handle_zone_event(self, event):
        """Handle zone event"""
        data = event.data
        entity_id = data.get(ATTR_ENTITY_ID)
        new_state = data.get(EVENT_NEW_STATE)
        if new_state is None:
            # 被删除了不处理
            return
        attributes = new_state.attributes
        latitude = attributes.get(ATTR_LATITUDE)
        longitude = attributes.get(ATTR_LONGITUDE)
        gcj02_longitude = attributes.get(CUSTOM_ATTR_GCJ02_LONGITUDE)
        gcj02_latitude = attributes.get(CUSTOM_ATTR_GCJ02_LATITUDE)
        if gcj02_longitude and gcj02_latitude:
            _LOGGER.debug(
                "This zone have been set ---> entity_id: %s gcj02_latitude: %s gcj02_longitude: %s ",
                entity_id,
                str(gcj02_latitude),
                str(gcj02_longitude),
            )
        elif latitude and longitude:
            _LOGGER.debug(
                "Entity_id: %s latitude: %s longitude: %s",
                entity_id,
                str(latitude),
                str(longitude),
            )


class DxZoneView(HomeAssistantView):
    """Class for save or update zone"""

    url = "/api/dx/zone/save"
    name = "save zone entity"
    zone_instance = None
    hass = None
    absolute_file_name = DEFAULT_ZONE_STORE_NAME

    def __init__(self, zone_instance, hass) -> None:
        self.zone_instance = zone_instance
        self.hass = hass
        config_dir = hass.config.path()
        self.absolute_file_name = os.path.join(config_dir, DEFAULT_ZONE_STORE_NAME)

    async def post(self, request):
        """Handle POST request"""
        resp_json = await request.json()
        await self.save(resp_json)
        # entity_id = request.query.get("entity_id")
        # obj_list = self.gps_logger_instance.get_obj_list_by_entity_id(entity_id)
        return web.json_response({"msg": "ok"})

    async def save(self, data):
        """To save zone entity"""
        hass = self.hass
        save_data = {}
        entity_id = data.get(ATTR_ENTITY_ID)
        zone = hass.states.get(entity_id)

        if os.path.exists(self.absolute_file_name):
            with open(self.absolute_file_name, "r", encoding="utf-8") as file:
                save_data = json.load(file)
                if save_data is None:
                    save_data = {}
        if zone is not None:
            save_data[entity_id] = data
            with open(file=self.absolute_file_name, mode="w", encoding="utf-8") as file:
                json.dump(save_data, file)
            clone_attributes = dict(zone.attributes)
            clone_attributes.update(data)
            self.hass.states.async_set(entity_id, zone.state, clone_attributes)

    async def load_all(self, event):
        """Load data from file and delete data if not exists"""
        hass = self.hass
        if os.path.exists(self.absolute_file_name):
            new_save_data = {}
            with open(self.absolute_file_name, "r", encoding="utf-8") as file:
                save_data = json.load(file)
            if save_data is not None:
                zone_list = hass.states.async_all([CONF_ZONE])
                if len(zone_list) > 0:
                    for zone in zone_list:
                        attributes = zone.attributes
                        entity_id = zone.entity_id
                        if entity_id in save_data:
                            clone_attributes = dict(attributes)
                            now_data = save_data[entity_id]
                            clone_attributes.update(now_data)
                            new_save_data[entity_id] = now_data
                            self.hass.states.async_set(entity_id, 0, clone_attributes)
                    with open(
                        file=self.absolute_file_name, mode="w", encoding="utf-8"
                    ) as file:
                        json.dump(new_save_data, file)
