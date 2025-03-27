from functools import lru_cache
from pathlib import Path
from typing import List, Tuple, Dict, Any

from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import TransferInfo
from app.schemas.types import EventType, MediaType
from app.utils.http import RequestUtils


class AlistCopy(_PluginBase):
    # 插件名称
    plugin_name = "目录实时监控-alist复制"
    # 插件描述
    plugin_desc = "监控目录文件变化，自动复制媒体文件至alist目录。"
    # 插件图标
    plugin_icon = "statistic.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "liuzdz"
    # 作者主页
    author_url = "https://github.com/liuzdz"
    # 插件配置项ID前缀
    plugin_config_prefix = "alistcopy_"
    # 加载顺序
    plugin_order = 5
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _save_tmp_path = None
    _enabled = False
    _host = None
    _api_key = None
    _remote_path = None
    _local_path = None

    def init_plugin(self, config: dict = None):
        self._save_tmp_path = settings.TEMP_PATH
        if config:
            self._enabled = config.get("enabled")
            self._api_key = config.get("api_key")
            self._host = config.get('host')
            if self._host:
                if not self._host.startswith('http'):
                    self._host = "http://" + self._host
                if not self._host.endswith('/'):
                    self._host = self._host + "/"
            self._local_path = config.get("local_path")
            self._remote_path = config.get("remote_path")

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'host',
                                            'label': '服务器'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_key',
                                            'label': 'API密钥'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'local_path',
                                            'label': '本地路径'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'remote_path',
                                            'label': '远端路径'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "host": "",
            "api_key": "",
            "local_path": "",
            "remote_path": ""
        }

    def get_state(self) -> bool:
        return self._enabled

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass

    @eventmanager.register(EventType.TransferComplete)
    def download(self, event: Event):
        """
        调用ChineseSubFinder下载字幕
        """
        if not self._enabled or not self._host or not self._api_key:
            return
        item = event.event_data
        if not item:
            return
        # 请求地址
        req_url = "%sapi/v1/add-job" % self._host

        # 媒体信息
        item_media: MediaInfo = item.get("mediainfo")
        # 转移信息
        item_transfer: TransferInfo = item.get("transferinfo")
        # 类型
        item_type = item_media.type
        # 目的路径
        item_dest: Path = item_transfer.target_path
        # 是否蓝光原盘
        item_bluray = item_transfer.is_bluray
        # 文件清单
        item_file_list = item_transfer.file_list_new

        if item_bluray:
            # 蓝光原盘虚拟个文件
            item_file_list = ["%s.mp4" % item_dest / item_dest.name]

        for file_path in item_file_list:
            # 路径替换
            if self._local_path and self._remote_path and file_path.startswith(self._local_path):
                file_path = file_path.replace(self._local_path, self._remote_path).replace('\\', '/')
            logger.info("目录实时监控-alist复制，转换后的源地址为: %s" % file_path)