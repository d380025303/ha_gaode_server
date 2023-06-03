# -*- coding: utf-8 -*-
import logging
import aiohttp
from .cache import get_cache, set_cache
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import json
import os

_LOGGER = logging.getLogger(__name__)


class DxZone:
    gps_obj_list = {}

    def __init__(self, hass):
        self.hass = hass

    async def handle_zone_event(self, event):
        data = event.data
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        attributes = new_state.attributes
        latitude = attributes.get("latitude")
        longitude = attributes.get("longitude")
        gcj02_longitude = attributes.get("gcj02_longitude")
        gcj02_latitude = attributes.get("gcj02_latitude")
        if gcj02_longitude and gcj02_latitude:
            _LOGGER.info(
                "this zone have been set ---> entity_id: %s gcj02_latitude: %s gcj02_longitude: %s ",
                entity_id,
                str(gcj02_latitude),
                str(gcj02_longitude),
            )
        elif latitude and longitude:
            _LOGGER.info(
                "entity_id: %s latitude: %s longitude: %s",
                entity_id,
                str(latitude),
                str(longitude),
            )
            # await self._transform_gps(entity_id, latitude, longitude)

    async def _transform_gps(self, entity_id, latitude, longitude):
        hass = self.hass
        session = aiohttp.ClientSession()
        key = "db04577df1bc58e6a075a8a024a95fa2"
        locations = str(longitude) + "," + str(latitude)
        cache_v = get_cache(locations)
        if cache_v is not None:
            locations_arr = cache_v.split(",")
            return locations_arr[0], locations_arr[1]

        async with session.get(
            "https://restapi.amap.com/v3/assistant/coordinate/convert?"
            + "key="
            + key
            + "&locations="
            + locations
            + "&coordsys=gps"
        ) as response:
            data = await response.json()
            await session.close()
            status = data.get("status")
            info = data.get("info")
            parse_locations = data.get("locations")
            if status == "1" and info == "ok":
                parse_locations_arr = parse_locations.split(",")
                set_cache(locations, parse_locations)
                # 设置值
                entity_state = hass.states.get(entity_id)
                current_attributes = dict(entity_state.attributes)
                current_attributes["gcj02_longitude"] = round(
                    float(parse_locations_arr[0]), 6
                )
                current_attributes["gcj02_latitude"] = round(
                    float(parse_locations_arr[1]), 6
                )
                hass.states.async_set(entity_id, entity_state.state, current_attributes)
            else:
                _LOGGER.error(
                    "status: %s info: %s  parse location: %s", status, info, locations
                )


class DxZoneView(HomeAssistantView):
    url = "/api/dx/zone/save"
    name = "save zone entity"
    zone_instance = None
    hass = None
    absolute_file_name = "zone.json"

    def __init__(self, zone_instance, hass):
        self.zone_instance = zone_instance
        self.hass = hass
        config_dir = hass.config.path()
        self.absolute_file_name = os.path.join(config_dir, "zone.json")

    async def post(self, request):
        respJson = await request.json()
        self.save(respJson)
        # entity_id = request.query.get("entity_id")
        # obj_list = self.gps_logger_instance.get_obj_list_by_entity_id(entity_id)
        return web.json_response({"msg": "ok"})

    def save(self, data):
        hass = self.hass
        if os.path.exists(self.absolute_file_name):
            with open(self.absolute_file_name, "r") as file:
                save_data = json.load(file)
        else:
            save_data = {}
        entity_id = data.get("entity_id")
        save_data[entity_id] = data
        with open(self.absolute_file_name, "w") as file:
            json.dump(save_data, file)
        zone = hass.states.get(entity_id)
        clone_attributes = dict(zone.attributes)
        clone_attributes.update(data)
        self.hass.states.async_set(entity_id, zone.state, clone_attributes)

    async def load_all(self, event):
        hass = self.hass
        if os.path.exists(self.absolute_file_name):
            with open(self.absolute_file_name, "r") as file:
                save_data = json.load(file)
            if save_data is not None:
                zone_list = hass.states.async_all(["zone"])
                for zone in zone_list:
                    attributes = zone.attributes
                    entity_id = zone.entity_id
                    if entity_id in save_data:
                        clone_attributes = dict(attributes)
                        clone_attributes.update(save_data[entity_id])
                        self.hass.states.async_set(entity_id, 0, clone_attributes)
