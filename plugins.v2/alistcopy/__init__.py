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
from app.schemas.file import FileItem
from app.modules.filemanager.storages.alist import Alist


class AlistCopy(_PluginBase):
    # 插件名称
    plugin_name = "alist复制"
    # 插件描述
    plugin_desc = "监控目录文件变化，自动复制媒体文件至alist目录。"
    # 插件图标
    plugin_icon = "statistic.png"
    # 插件版本
    plugin_version = "1.0.5"
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
    _remote_target_path = None
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
            self._remote_target_path = config.get("remote_target_path")

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
                                            'model': 'remote_target_path',
                                            'label': '目标路径',
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
            "remote_path": "",
            "remote_target_path": ""
        }

    def get_state(self) -> bool:
        return self._enabled

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        pass

    @eventmanager.register(EventType.TransferComplete)
    def download(self, event: Event):
        logger.info("目录实时监控-alist复制，开始处理")
        if not self._enabled or not self._host or not self._api_key:
            return
        item = event.event_data
        if not item:
            return
        # 转移信息
        item_transfer: TransferInfo = item.get("transferinfo")
        # 文件清单
        item_file_list = item_transfer.file_list_new
        # 转移后的目录项
        #target_diritem: FileItem = item_transfer.target_diritem
        # 文件路径
        #target_diritem_path = target_diritem.path
        #logger.info("目录实时监控-alist复制，文件路径: %s" % target_diritem_path)
        # 转移后路径
        #target_item: FileItem = item_transfer.target_item
        #target_item_name = target_item.name
        # 文件清单
        item_file_list = item_transfer.file_list_new
        for file_path in item_file_list:
            target_diritem_path = os.path.dirname(file_path)
            target_item_name = os.path.basename(file_path)
            logger.info("目录实时监控-alist复制，文件路径: %s" % target_diritem_path)
            logger.info("目录实时监控-alist复制，文件名称: %s" % target_item_name)
            src_dir = ''
            dst_dir = ''
            if self._local_path and self._remote_path and file_path.startswith(self._local_path):
                src_dir = file_path.replace(self._local_path, self._remote_path).replace('\\', '/')
            if self._local_path and self._remote_target_path and target_diritem_path.startswith(self._local_path):
                dst_dir = target_diritem_path.replace(self._local_path, self._remote_target_path).replace('\\', '/')
            logger.info("目录实时监控-alist复制，源文件: %s" % src_dir)
            logger.info("目录实时监控-alist复制，目标文件夹: %s" % dst_dir)

            if src_dir and dst_dir:
                logger.info("目录实时监控-alist复制，准备调用alist")
                fileItem: FileItem = FileItem()
                fileItem.path = src_dir
                fileItem.name = target_item_name
                logger.info("目录实时监控-alist复制，准备调用alist-11111")
                alist = Alist()
                alist.get_folder(Path(dst_dir))
                logger.info("目录实时监控-alist复制，准备调用alist-22222")
                alist.copy(fileItem, Path(dst_dir), name)
                logger.info("目录实时监控-alist复制，结束调用alist")
