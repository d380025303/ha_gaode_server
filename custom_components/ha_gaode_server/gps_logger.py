# -*- coding: utf-8 -*-
import logging
import aiohttp
from .cache import get_cache, set_cache
from .dx_exception import GaoDeException
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


class DxGpsLogger:
    gps_obj_dict = {}
    gaode_server_key = ""

    def __init__(self, hass, gaode_server_key):
        self.hass = hass
        self.gaode_server_key = gaode_server_key

    async def clear_gps_obj_dict(self, now):
        delete_datetime = now - timedelta(days=1)
        for key, value in self.gps_obj_dict.items():
            filtered_list = [
                item for item in value if delete_datetime < item["dx_record_datetime"]
            ]
            self.gps_obj_dict[key] = filtered_list
        filtered_dict = {
            key: value for key, value in self.gps_obj_dict.items() if len(value) > 0
        }
        self.gps_obj_dict = filtered_dict

    def get_obj_list_by_entity_id(self, entity_id):
        if entity_id in self.gps_obj_dict:
            gps_obj_list = self.gps_obj_dict[entity_id]
            return gps_obj_list
        return []

    def get_last_obj_4_entity_id(self, entity_id):
        if entity_id in self.gps_obj_dict:
            gps_obj_list = self.gps_obj_dict[entity_id]
            if len(gps_obj_list) > 0:
                gps_obj = gps_obj_list[len(gps_obj_list) - 1]
                return gps_obj
        return None

    async def handle_gps_event(self, event):
        data = event.data
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        attributes = new_state.attributes
        last_changed = new_state.last_changed
        latitude = attributes.get("latitude")
        longitude = attributes.get("longitude")
        gcj02_longitude = attributes.get("gcj02_longitude")
        gcj02_latitude = attributes.get("gcj02_latitude")
        if gcj02_longitude and gcj02_latitude:
            _LOGGER.info(
                "this gps have been set, gcj02_longitude: %s, gcj02_latitude: %s",
                gcj02_longitude,
                gcj02_latitude,
            )
        elif latitude and longitude:
            _LOGGER.info(
                "entity_id: %s latitude: %s longitude: %s",
                entity_id,
                str(latitude),
                str(longitude),
            )
            ll = await self._transform_gps(entity_id, latitude, longitude)
            dd = await self._calc_distance_of_zone(entity_id, ll)
            _LOGGER.info(ll)
            _LOGGER.info(dd)

            last_gpslogger = self.get_last_obj_4_entity_id(entity_id)
            # 如果经纬度跟上次一样, 不记录
            not_append_ind = False
            if last_gpslogger is not None:
                last_gpslogger_longitude = last_gpslogger["longitude"]
                last_gpslogger_latitude = last_gpslogger["latitude"]
                if (
                    last_gpslogger_longitude == longitude
                    and last_gpslogger_latitude == latitude
                ):
                    not_append_ind = True

            clone_attributes = dict(attributes)
            now_state = new_state
            if ll is not None:
                clone_attributes["gcj02_longitude"] = ll["gcj02_longitude"]
                clone_attributes["gcj02_latitude"] = ll["gcj02_latitude"]
            if dd is not None:
                dx_state = dd["dx_state"]
                now_state = dx_state
                clone_attributes["dx_state"] = dx_state
                clone_attributes["dx_state_entity_id"] = dd["dx_state_entity_id"]
                clone_attributes["dx_distance"] = dd["dx_distance"]
                clone_attributes["dx_pre_state"] = dd["dx_pre_state"]
            clone_attributes["dx_record_datetime"] = last_changed.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if not_append_ind is False:
                if entity_id in self.gps_obj_dict:
                    gps_obj_list = self.gps_obj_dict[entity_id]
                    gps_obj_list.append(clone_attributes)
                    self.gps_obj_dict[entity_id] = gps_obj_list
                else:
                    gps_obj_list = []
                    gps_obj_list.append(clone_attributes)
                    self.gps_obj_dict[entity_id] = gps_obj_list
            # 修改状态
            self.hass.states.async_set(entity_id, now_state, clone_attributes)

    async def _transform_gps(self, entity_id, latitude, longitude):
        _LOGGER.info("_transform_gps")
        key = self.gaode_server_key
        locations = str(longitude) + "," + str(latitude)

        last_gpslogger = self.get_last_obj_4_entity_id(entity_id)

        if last_gpslogger is not None:
            last_gpslogger_gcj02_longitude = last_gpslogger["gcj02_longitude"]
            last_gpslogger_gcj02_latitude = last_gpslogger["gcj02_latitude"]
            last_gpslogger_longitude = last_gpslogger["longitude"]
            last_gpslogger_latitude = last_gpslogger["latitude"]
            # 如果经纬度跟上次一样, 不需要调用请求
            if (
                last_gpslogger_longitude == longitude
                and last_gpslogger_latitude == latitude
            ):
                return {
                    "gcj02_longitude": last_gpslogger_gcj02_longitude,
                    "gcj02_latitude": last_gpslogger_gcj02_latitude,
                }
        # 如果缓存存在, 不需要调用请求
        cache_v = get_cache(locations)
        if cache_v is not None:
            locations_arr = cache_v.split(",")
            return {
                "gcj02_longitude": locations_arr[0],
                "gcj02_latitude": locations_arr[1],
            }

        parse_locations = None
        try:
            session = aiohttp.ClientSession()
            async with session.get(
                "https://restapi.amap.com/v3/assistant/coordinate/convert?"
                + "key="
                + key
                + "&locations="
                + locations
                + "&coordsys=gps"
            ) as response:
                data = await response.json()
                status = data.get("status")
                info = data.get("info")
                if status == "1" and info == "ok":
                    parse_locations = data.get("locations")
                else:
                    _LOGGER.error(
                        "status: %s info: %s  parse location: %s",
                        status,
                        info,
                        locations,
                    )
                    raise GaoDeException(
                        "高德地图地址转换错误 status: " + status + " info: " + info
                    )
        except Exception as e:
            _LOGGER.error(str(e))
            raise GaoDeException("高德地图地址转换错误: " + str(e))
        finally:
            await session.close()
        # 获取到的经纬度
        parse_locations_arr = parse_locations.split(",")
        parse_longitude = str(round(float(parse_locations_arr[0]), 6))
        parse_latitude = str(round(float(parse_locations_arr[1]), 6))
        set_cache(locations, parse_longitude + "," + parse_latitude)
        return {
            "gcj02_longitude": parse_longitude,
            "gcj02_latitude": parse_latitude,
        }

    def _handle_origins(self, zone_list):
        origins_zone_list = []
        origins_list = []
        for zone in zone_list:
            attributes = zone.attributes
            gcj02_longitude = attributes.get("gcj02_longitude")
            gcj02_latitude = attributes.get("gcj02_latitude")
            radius = attributes.get("radius")
            entity_id = zone.entity_id
            if gcj02_longitude and gcj02_latitude:
                l = str(gcj02_longitude) + "," + str(gcj02_latitude)
                origins_list.append(l)
                origins_zone = {
                    "entity_id": entity_id,
                    "radius": radius,
                    "zone": zone,
                }
                origins_zone_list.append(origins_zone)
        return origins_zone_list, "|".join(origins_list)

    async def _calc_distance_of_zone(self, entity_id, ll):
        _LOGGER.info("_calc_distance_of_zone")
        key = self.gaode_server_key

        gcj02_longitude = ll["gcj02_longitude"]
        gcj02_latitude = ll["gcj02_latitude"]
        # 如果经纬度跟上次一样, 不需要调用请求
        last_gpslogger = self.get_last_obj_4_entity_id(entity_id)
        last_gpslogger_dx_state = ""
        if last_gpslogger is not None:
            last_gpslogger_gcj02_longitude = last_gpslogger["gcj02_longitude"]
            last_gpslogger_gcj02_latitude = last_gpslogger["gcj02_latitude"]
            last_gpslogger_dx_state = last_gpslogger["dx_state"]
            if (
                gcj02_longitude == last_gpslogger_gcj02_longitude
                and gcj02_latitude == last_gpslogger_gcj02_latitude
            ):
                return {
                    "dx_state": last_gpslogger_dx_state,
                    "dx_state_entity_id": last_gpslogger["dx_state_entity_id"],
                    "dx_distance": -1,
                    "dx_pre_state": last_gpslogger_dx_state,
                }

        return_value = None
        hass = self.hass
        zone_list = hass.states.async_all(["zone"])
        origins_zone_list, origins = self._handle_origins(zone_list)
        if len(origins_zone_list) == 0:
            return {
                "dx_state": "dx_unknown",
                "dx_state_entity_id": "",
                "dx_distance": -1,
                "dx_pre_state": "",
            }

        destination = gcj02_longitude + "," + gcj02_latitude
        try:
            session = aiohttp.ClientSession()
            async with session.get(
                "https://restapi.amap.com/v3/distance?"
                + "key="
                + key
                + "&origins="
                + origins
                + "&destination="
                + destination
                + "&type="
                + "0"
                + "&coordsys=gps"
            ) as response:
                data = await response.json()

                status = data.get("status")
                info = data.get("info")
                if status == "1" and info == "OK":
                    results = data.get("results")
                    # 只要有一个范围内就是范围内 否则全是范围外
                    for result in results:
                        origin_id = result.get("origin_id")
                        distance = result.get("distance")
                        origins_zone = origins_zone_list[int(origin_id) - 1]
                        # entity_id, radius, state, zone
                        radius = origins_zone["radius"]
                        zone_entity_id = origins_zone["entity_id"]
                        # 在范围内
                        if int(radius) > int(distance):
                            if zone_entity_id == "zone.home":
                                return_value = {
                                    "dx_state": "dx_in_home",
                                    "dx_state_entity_id": zone_entity_id,
                                    "dx_distance": int(distance),
                                    "dx_pre_state": last_gpslogger_dx_state,
                                }
                            else:
                                return_value = {
                                    "dx_state": "dx_in_zone",
                                    "dx_state_entity_id": zone_entity_id,
                                    "dx_distance": int(distance),
                                    "dx_pre_state": last_gpslogger_dx_state,
                                }
                else:
                    _LOGGER.error("status: %s info: %s", status, info)
                    raise GaoDeException(
                        "高德地图距离计算错误 status: " + status + " info: " + info
                    )

        except Exception as e:
            _LOGGER.error(str(e))
            raise GaoDeException("高德地图距离计算错误: " + str(e))
        finally:
            await session.close()
        if return_value is not None:
            return return_value
        else:
            return {
                "dx_state": "dx_out",
                "dx_state_entity_id": "",
                "dx_distance": -1,
                "dx_pre_state": last_gpslogger_dx_state,
            }


class DxGpsLoggerView(HomeAssistantView):
    url = "/api/dx/gps/gps_list_by_entity_id"
    name = "search gps_list by entity_id"
    gps_logger_instance = None

    def __init__(self, gps_logger_instance):
        self.gps_logger_instance = gps_logger_instance

    async def get(self, request):
        entity_id = request.query.get("entity_id")
        obj_list = self.gps_logger_instance.get_obj_list_by_entity_id(entity_id)
        return web.json_response(obj_list)
