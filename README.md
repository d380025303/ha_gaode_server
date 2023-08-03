<!--
 * @Author        : dx
 * @Github        : https://github.com/d380025303
 * @Description   : 
 * @Date          : 2023-07-05
 * @LastEditors   : dx
 * @LastEditTime  : 2023-07-05 14:56:00
 -->

# Ha Gaode Server

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

需要配合[ha_gaode](https://github.com/d380025303/ha_gaode) 一起食用

# 更新
+ v3.0
 + GPSLogger可存储到数据库了(实现根据时间绘制路径轨迹功能)
+ v4.0
 + 增加配置可使某些device_tracker不自动做高德坐标转换
+ v4.1
 + 增加配置可在device_tracker上报后将数据通过POST请求推送
+ v5.0
 + 支持多边形范围计算
+ v5.1
 + 增加配置可使某些device_tracker不做距离计算
+ v5.1.1
 + 修复人员跟踪操作导致数据丢失问题

# 安装
## 手动安装
* 1. 下载 `custom_components\ha_gaode_server` 下的所有文件
* 2. 复制到 `\config\custom_components` (包括ha_gaode_server文件夹)
* 3. 重启Home Assistant
* 4. 此时应该可以在 配置 > 设备与服务 > 添加集成内搜索到了
* 5. 不过这里添加不了, 需要修改 configuration.yaml, 增加以下配置
    ```yaml
    ha_gaode_server:
      # 高德Server Key: 此key需要是"Web服务"类型, 需要与Web端(JS API)区分开 
      gaode_server_key: 你的高德serverkey  
      # 是否同步修改GPSLogger实体的状态, 虽然本项目状态与GPSLogger一致, 但某些其它包可能会自定义状态(比如本项目2.0版本,已调整), 可将此设置为 False
      change_gpslogger_state: True 
      # 数据库名称, 为SQLite数据库, 默认存储在config/dx_db.db文件中
      db_url: dx_db.db
      # 不做高德转换device_trackers列表
      ignore_transform_device_trackers:
        - device_trackers.XXXXX
      # 不做距离计算的device_tracker列表
      ignore_distance_device_trackers:
        - device_trackers.XXXXX
      # device_tracker上报后POST请求地址
      push_device_trackers_post: 
    ```

~~## HACS 安装~~

~~1. HACS > 集成 浏览并下载存储库 > 搜索 ```dxgaodeserver```，点击下载~~

~~2. 参见`手动安装`第三步及以后~~

~~如果搜索不到, 可手动添加自定义存储库~~
~~- 存储库: https://github.com/d380025303/ha_gaode_server~~
~~- 类别: 集成~~


## 详细说明
GPSLogger 通过 [ha_gaode_server](https://github.com/d380025303/ha_gaode_server) 获得了一些增强属性
![](1.jpg)

- gcj02_longitude: 高德的经度
- gcj02_latitude: 高德的纬度
- dx_state: 设备当前状态
```text
home: "我的家"实体范围内
zone.XXX: 在zone.XXX的实体范围内
not_home: 不在任何范围内
```
- dx_pre_state: 设备前一个状态, 状态值同 ```dx_state```
- dx_distance: 当进入范围内, 距离中心的距离, 如果不在范围内, 值为 -1
- `dx_record_datetime`: GPSLogger上报时间
