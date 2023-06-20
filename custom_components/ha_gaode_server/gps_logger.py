# -*- coding: utf-8 -*-
import logging
import aiohttp
from aiohttp import ClientSession
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cache import get_cache, set_cache
from .dx_exception import GaoDeException
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from datetime import datetime, timedelta
from homeassistant.const import (
    STATE_HOME,
    STATE_NOT_HOME,
    ATTR_ENTITY_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_RADIUS,
    CONF_ZONE,
)
from homeassistant.core import HomeAssistant, Config
from .db import DxDb
from .const import (
    CUSTOM_ATTR_DX_RECORD_DATETIME,
    EVENT_NEW_STATE,
    CUSTOM_ATTR_GCJ02_LATITUDE,
    CUSTOM_ATTR_GCJ02_LONGITUDE,
    CUSTOM_ATTR_DX_STATE,
    CUSTOM_ATTR_DX_DISTANCE,
    CUSTOM_ATTR_DX_PRE_STATE,
    CUSTOM_ATTR_DX_POLYGON,
    DEFAULT_DX_RECORD_DATETIME_FORMAT,
)

_LOGGER = logging.getLogger(__name__)


class DxGpsLogger:
    """
    Enhance GPSLogger Class
    """

    gps_obj_dict = {}
    gaode_server_key = None
    change_gpslogger_state = True
    db_instance: DxDb = None
    ignore_transform_device_trackers = []
    push_device_trackers_post = None

    def __init__(self, hass: HomeAssistant, config: Config) -> None:
        self.hass = hass
        self.gaode_server_key = config.get("gaode_server_key")
        self.change_gpslogger_state = config.get("change_gpslogger_state")
        self.db_instance = config.get("db_instance")
        self.ignore_transform_device_trackers = config.get(
            "ignore_transform_device_trackers"
        )
        self.push_device_trackers_post = config.get("push_device_trackers_post")

    async def clear_gps_obj_dict(self, now):
        """
        Clear cache of gps_obj

        Parameters:
            now (datetime): datetime of now
        """
        delete_datetime = now - timedelta(days=1)
        for key, value in self.gps_obj_dict.items():
            # FIXME
            filtered_list = [
                item
                for item in value
                if delete_datetime < item[CUSTOM_ATTR_DX_RECORD_DATETIME]
            ]
            self.gps_obj_dict[key] = filtered_list
        filtered_dict = {
            key: value for key, value in self.gps_obj_dict.items() if len(value) > 0
        }
        self.gps_obj_dict = filtered_dict

    def get_obj_list_by_entity_id(self, entity_id):
        """
        This function to get gps data by entity_id in cache.

        Parameters:
            entity_id (str): The entity_id.

        Returns:
            List: gps data list, [] for no any data.
        """
        if entity_id in self.gps_obj_dict:
            gps_obj_list = self.gps_obj_dict[entity_id]
            return gps_obj_list
        return []

    def get_last_obj_4_entity_id(self, entity_id):
        """
        This function to get last gps data by entity_id in cache.

        Parameters:
            entity_id (str): The entity_id.

        Returns:
            dict: latest gps data, None for no any data.
        """
        if entity_id in self.gps_obj_dict:
            gps_obj_list = self.gps_obj_dict[entity_id]
            if len(gps_obj_list) > 0:
                gps_obj = gps_obj_list[len(gps_obj_list) - 1]
                return gps_obj
        return None

    async def handle_gps_event(self, event) -> None:
        """
        To handle GPSLogger Event

        Parameters:
            event (object): The hass event.

        Returns:
            None
        """
        data = event.data
        entity_id = data.get(ATTR_ENTITY_ID)
        new_state = data.get(EVENT_NEW_STATE)
        attributes = new_state.attributes
        last_changed = new_state.last_changed
        gpslogger_state = new_state.state
        latitude = attributes.get(ATTR_LATITUDE)
        longitude = attributes.get(ATTR_LONGITUDE)
        gcj02_longitude = attributes.get(CUSTOM_ATTR_GCJ02_LONGITUDE)
        gcj02_latitude = attributes.get(CUSTOM_ATTR_GCJ02_LATITUDE)
        if gcj02_longitude and gcj02_latitude:
            _LOGGER.debug(
                "This gps have been set, gcj02_longitude: %s, gcj02_latitude: %s",
                gcj02_longitude,
                gcj02_latitude,
            )
        elif latitude and longitude:
            _LOGGER.debug(
                "Entity_id: %s latitude: %s longitude: %s",
                entity_id,
                str(latitude),
                str(longitude),
            )
            ll = await self._transform_gps(entity_id, latitude, longitude)
            dd = await self._calc_distance_of_zone(entity_id, gpslogger_state, ll)
            _LOGGER.debug(ll)
            _LOGGER.debug(dd)

            last_gpslogger = self.get_last_obj_4_entity_id(entity_id)
            # 如果经纬度跟上次一样, 不记录
            not_append_ind = False
            if last_gpslogger is not None:
                last_gpslogger_longitude = last_gpslogger[ATTR_LONGITUDE]
                last_gpslogger_latitude = last_gpslogger[ATTR_LATITUDE]
                if (
                    last_gpslogger_longitude == longitude
                    and last_gpslogger_latitude == latitude
                ):
                    not_append_ind = True

            clone_attributes = dict(attributes)
            now_state = gpslogger_state
            if ll is not None:
                clone_attributes[CUSTOM_ATTR_GCJ02_LONGITUDE] = ll[
                    CUSTOM_ATTR_GCJ02_LONGITUDE
                ]
                clone_attributes[CUSTOM_ATTR_GCJ02_LATITUDE] = ll[
                    CUSTOM_ATTR_GCJ02_LATITUDE
                ]
            if dd is not None:
                dx_state = dd[CUSTOM_ATTR_DX_STATE]
                if self.change_gpslogger_state:
                    now_state = dx_state
                clone_attributes[CUSTOM_ATTR_DX_STATE] = dx_state
                clone_attributes[CUSTOM_ATTR_DX_DISTANCE] = dd[CUSTOM_ATTR_DX_DISTANCE]
                clone_attributes[CUSTOM_ATTR_DX_PRE_STATE] = dd[
                    CUSTOM_ATTR_DX_PRE_STATE
                ]
            clone_attributes[CUSTOM_ATTR_DX_RECORD_DATETIME] = last_changed.strftime(
                DEFAULT_DX_RECORD_DATETIME_FORMAT
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
                if self.db_instance is not None:
                    # 插入数据库
                    self.db_instance.insert(
                        """
            INSERT INTO gps_logger_history (entity_id, longitude, latitude, gcj02_longitude, gcj02_latitude, dx_state, dx_pre_state, dx_distance, dx_record_datetime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                        entity_id,
                        longitude,
                        latitude,
                        clone_attributes[CUSTOM_ATTR_GCJ02_LONGITUDE],
                        clone_attributes[CUSTOM_ATTR_GCJ02_LATITUDE],
                        clone_attributes[CUSTOM_ATTR_DX_STATE],
                        clone_attributes[CUSTOM_ATTR_DX_PRE_STATE],
                        clone_attributes[CUSTOM_ATTR_DX_DISTANCE],
                        int(last_changed.timestamp()),
                    )
                if self.push_device_trackers_post is not None:
                    # 调用服务
                    request_data = {"entity_id": entity_id}
                    request_data.update(clone_attributes)
                    session: ClientSession = async_get_clientsession(self.hass, False)
                    async with session.request(
                        "POST", self.push_device_trackers_post, data=request_data
                    ) as response:
                        response_data = await response.json()
                        _LOGGER.debug("Resp data: %s", response_data)

            # 修改状态
            self.hass.states.async_set(entity_id, now_state, clone_attributes)

    async def _transform_gps(self, entity_id, latitude, longitude):
        _LOGGER.debug("Start method _transform_gps")
        if (
            self.ignore_transform_device_trackers is not None
            and entity_id in self.ignore_transform_device_trackers
        ):
            # 无需转换的实体
            return {
                CUSTOM_ATTR_GCJ02_LONGITUDE: str(round(longitude, 6)),
                CUSTOM_ATTR_GCJ02_LATITUDE: str(round(latitude, 6)),
            }

        key = self.gaode_server_key
        locations = str(longitude) + "," + str(latitude)

        last_gpslogger = self.get_last_obj_4_entity_id(entity_id)

        if last_gpslogger is not None:
            last_gpslogger_gcj02_longitude = last_gpslogger[CUSTOM_ATTR_GCJ02_LONGITUDE]
            last_gpslogger_gcj02_latitude = last_gpslogger[CUSTOM_ATTR_GCJ02_LATITUDE]
            last_gpslogger_longitude = last_gpslogger[ATTR_LONGITUDE]
            last_gpslogger_latitude = last_gpslogger[ATTR_LATITUDE]
            # 如果经纬度跟上次一样, 不需要调用请求
            if (
                last_gpslogger_longitude == longitude
                and last_gpslogger_latitude == latitude
            ):
                return {
                    CUSTOM_ATTR_GCJ02_LONGITUDE: last_gpslogger_gcj02_longitude,
                    CUSTOM_ATTR_GCJ02_LATITUDE: last_gpslogger_gcj02_latitude,
                }
        # 如果缓存存在, 不需要调用请求
        cache_v = get_cache(locations)
        if cache_v is not None:
            locations_arr = cache_v.split(",")
            return {
                CUSTOM_ATTR_GCJ02_LONGITUDE: locations_arr[0],
                CUSTOM_ATTR_GCJ02_LATITUDE: locations_arr[1],
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
                        "Status: %s info: %s  parse location: %s",
                        status,
                        info,
                        locations,
                    )
                    raise GaoDeException(
                        "高德地图地址转换错误 status: " + status + " info: " + info
                    )
        except Exception as e:
            _LOGGER.error(str(e))
            raise GaoDeException("高德地图地址转换错误: %s", str(e))
        finally:
            await session.close()
        # 获取到的经纬度
        parse_locations_arr = parse_locations.split(",")
        parse_longitude = str(round(float(parse_locations_arr[0]), 6))
        parse_latitude = str(round(float(parse_locations_arr[1]), 6))
        set_cache(locations, parse_longitude + "," + parse_latitude)
        return {
            CUSTOM_ATTR_GCJ02_LONGITUDE: parse_longitude,
            CUSTOM_ATTR_GCJ02_LATITUDE: parse_latitude,
        }

    def _handle_origins(self, zone_list):
        origins_zone_list = []
        origins_list = []
        for zone in zone_list:
            attributes = zone.attributes
            gcj02_longitude = attributes.get(CUSTOM_ATTR_GCJ02_LONGITUDE)
            gcj02_latitude = attributes.get(CUSTOM_ATTR_GCJ02_LATITUDE)
            radius = attributes.get(CONF_RADIUS)
            dx_polygon = attributes.get(CUSTOM_ATTR_DX_POLYGON)
            entity_id = zone.entity_id
            if gcj02_longitude and gcj02_latitude:
                l = str(gcj02_longitude) + "," + str(gcj02_latitude)
                origins_list.append(l)
                origins_zone = {
                    ATTR_ENTITY_ID: entity_id,
                    CONF_RADIUS: radius,
                    CONF_ZONE: zone,
                    CUSTOM_ATTR_DX_POLYGON: dx_polygon,
                }
                origins_zone_list.append(origins_zone)
        return origins_zone_list, "|".join(origins_list)

    def is_in_poly(self, p, poly):
        """
        :param p: [x, y]
        :param poly: [[], [], [], [], ...]
        :return:
        """
        px, py = p
        is_in = False
        for i, corner in enumerate(poly):
            next_i = i + 1 if i + 1 < len(poly) else 0
            x1, y1 = corner
            x2, y2 = poly[next_i]
            # 点在顶点上
            if (x1 == px and y1 == py) or (x2 == px and y2 == py):
                is_in = True
                break
            if min(y1, y2) < py <= max(y1, y2):  # find horizontal edges of polygon
                x = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                # 点在边上
                if x == px:
                    is_in = True
                    break
                # 点在线左边
                elif x > px:
                    is_in = not is_in
        return is_in

    async def _calc_distance_of_zone(self, entity_id, new_state, ll):
        _LOGGER.debug("Start _calc_distance_of_zone")
        key = self.gaode_server_key

        gcj02_longitude = ll[CUSTOM_ATTR_GCJ02_LONGITUDE]
        gcj02_latitude = ll[CUSTOM_ATTR_GCJ02_LATITUDE]
        # 如果经纬度跟上次一样, 不需要调用请求
        last_gpslogger = self.get_last_obj_4_entity_id(entity_id)
        last_gpslogger_dx_state = ""
        if last_gpslogger is not None:
            last_gpslogger_gcj02_longitude = last_gpslogger[CUSTOM_ATTR_GCJ02_LONGITUDE]
            last_gpslogger_gcj02_latitude = last_gpslogger[CUSTOM_ATTR_GCJ02_LATITUDE]
            last_gpslogger_dx_state = last_gpslogger[CUSTOM_ATTR_DX_STATE]
            if (
                gcj02_longitude == last_gpslogger_gcj02_longitude
                and gcj02_latitude == last_gpslogger_gcj02_latitude
            ):
                return {
                    CUSTOM_ATTR_DX_STATE: last_gpslogger_dx_state,
                    CUSTOM_ATTR_DX_DISTANCE: last_gpslogger[CUSTOM_ATTR_DX_DISTANCE],
                    CUSTOM_ATTR_DX_PRE_STATE: last_gpslogger_dx_state,
                }

        return_value = None
        hass = self.hass
        zone_list = hass.states.async_all([CONF_ZONE])
        origins_zone_list, origins = self._handle_origins(zone_list)
        if len(origins_zone_list) == 0:
            return {
                CUSTOM_ATTR_DX_STATE: new_state,
                CUSTOM_ATTR_DX_DISTANCE: -1,
                CUSTOM_ATTR_DX_PRE_STATE: "",
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
                        radius = origins_zone[CONF_RADIUS]
                        polygon = origins_zone[CUSTOM_ATTR_DX_POLYGON]
                        zone_entity_id = origins_zone[ATTR_ENTITY_ID]
                        # 如果有多边形记录优先计算多边形
                        is_in = False
                        if polygon is not None and polygon != "":
                            arr_1 = polygon.split(";")
                            arr_2 = [
                                list(map(float, elem.split(","))) for elem in arr_1
                            ]
                            p = [float(gcj02_longitude), float(gcj02_latitude)]
                            _LOGGER.info(arr_2)
                            _LOGGER.info(p)
                            is_in = self.is_in_poly(p, arr_2)
                        else:
                            is_in = int(radius) > int(distance)
                        if is_in:
                            if zone_entity_id == "zone.home":
                                return_value = {
                                    CUSTOM_ATTR_DX_STATE: STATE_HOME,
                                    CUSTOM_ATTR_DX_DISTANCE: int(distance),
                                    CUSTOM_ATTR_DX_PRE_STATE: last_gpslogger_dx_state,
                                }
                            else:
                                return_value = {
                                    CUSTOM_ATTR_DX_STATE: zone_entity_id,
                                    CUSTOM_ATTR_DX_DISTANCE: int(distance),
                                    CUSTOM_ATTR_DX_PRE_STATE: last_gpslogger_dx_state,
                                }
                else:
                    _LOGGER.error("Status: %s info: %s", status, info)
                    raise GaoDeException(
                        "高德地图距离计算错误 status: " + status + " info: " + info
                    )

        except Exception as e:
            _LOGGER.error("高德地图距离计算错误: %s", str(e))
            raise GaoDeException("高德地图距离计算错误: " + str(e))
        finally:
            await session.close()
        if return_value is not None:
            return return_value
        else:
            return {
                CUSTOM_ATTR_DX_STATE: STATE_NOT_HOME,
                CUSTOM_ATTR_DX_DISTANCE: -1,
                CUSTOM_ATTR_DX_PRE_STATE: last_gpslogger_dx_state,
            }


class DxGpsLoggerCacheView(HomeAssistantView):
    """
    API for search in cache
    """

    url = "/api/dx/gps/gps_list_by_entity_id"
    name = "search gps_list by entity_id"
    gps_logger_instance = None

    def __init__(self, gps_logger_instance) -> None:
        self.gps_logger_instance = gps_logger_instance

    async def get(self, request):
        """
        get gps data by entity_id in cache
        """
        entity_id = request.query.get(ATTR_ENTITY_ID)
        obj_list = self.gps_logger_instance.get_obj_list_by_entity_id(entity_id)
        return web.json_response(obj_list)


class DxGpsLoggerSearchView(HomeAssistantView):
    """
    API for search gps in db
    """

    url = "/api/dx/gps/gps_list_from_db"
    name = "search gps_list in db"
    db_instance = None

    def __init__(self, db_instance: DxDb) -> None:
        self.db_instance = db_instance

    async def get(self, request):
        """
        get gps data by entity_id in cache
        """
        entity_id = request.query.get(ATTR_ENTITY_ID)
        start_time_seconds = request.query.get("start_time_seconds")
        end_time_seconds = request.query.get("end_time_seconds")

        rows = self.db_instance.search(
            """
            select entity_id, gcj02_longitude, gcj02_latitude, dx_record_datetime from gps_logger_history where entity_id = ? and dx_record_datetime > ? and dx_record_datetime < ? order by dx_record_datetime asc
        """,
            entity_id,
            start_time_seconds,
            end_time_seconds,
        )
        return web.json_response(rows)
