<!--
 * @Author        : dx
 * @Github        : https://github.com/d380025303
 * @Description   : 
 * @Date          : 2023-05-29 16:00:00
 * @LastEditors   : dx
 * @LastEditTime  : 2023-05-29 16:00:00
 -->

# Ha Gaode Server

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

需要配合[ha_gaode](https://github.com/d380025303/ha_gaode) 一起食用

## 手动安装
* 1. 下载 `custom_components\ha_gaode_server` 下的所有文件
* 2. 复制到 `\config\custom_components` (包括ha_gaode_server文件夹)
* 3. 重启Home Assistant
* 4. 此时应该可以在 配置 > 设备与服务 > 添加集成内搜索到了
* 5. 不过这里添加不了, 需要修改 configuration.yaml, 增加以下配置
    ```yaml
    ha_gaode_server:
      gaode_server_key: 你的高德serverkey  # tips: 此key需要是"Web服务"类型, 需要与Web端(JS API)区分开 
    ```

~~## HACS 安装~~

~~1. HACS > 集成 浏览并下载存储库 > 搜索 ```dxgaodeserver```，点击下载~~

~~2. 参见`手动安装`第三步及以后~~

~~如果搜索不到, 可手动添加自定义存储库~~
~~- 存储库: https://github.com/d380025303/ha_gaode_server~~
~~- 类别: 集成~~
