import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from app.core.config import settings

# 全局上下文变量，存储当前请求的 trace_id
trace_id_var: ContextVar[str] = ContextVar('trace_id', default=None)


class RequestContextFilter(logging.Filter):
    """请求上下文过滤器，添加 trace_id 到日志记录"""
    
    def filter(self, record):
        trace_id = trace_id_var.get()
        if trace_id:
            record.trace_id = trace_id
        else:
            record.trace_id = "-"
        return True


class TZFormatter(logging.Formatter):
    """带有时区和毫秒的日志格式化器"""
    
    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        super().__init__(fmt, datefmt, style, validate)
    
    def formatTime(self, record, datefmt=None):
        """格式化时间，包含毫秒和时区"""
        # 获取配置的时区
        try:
            import pytz
            tz = pytz.timezone(settings.app_timezone)
            dt = datetime.fromtimestamp(record.created, tz)
        except ImportError:
            # 如果没有 pytz，使用系统时区
            dt = datetime.fromtimestamp(record.created)
            tz = None
        
        # 获取时区偏移（秒）
        if tz is not None and hasattr(dt, 'utcoffset'):
            tz_offset_seconds = dt.utcoffset()
        else:
            # 如果没有时区信息，使用本地时区
            tz_offset_seconds = datetime.now().astimezone().utcoffset() or timedelta(0)
        
        # 计算时区偏移（小时和分钟）
        total_seconds = int(tz_offset_seconds.total_seconds())
        offset_hours = abs(total_seconds) // 3600
        offset_minutes = (abs(total_seconds) % 3600) // 60
        offset_sign = '+' if total_seconds >= 0 else '-'
        tz_str = f'{offset_sign}{offset_hours:02d}{offset_minutes:02d}'
        
        # 格式化时间：YYYY-MM-DD HH:MM:SS.mmm +HHMM
        # 例如：2026-03-07 22:40:11.123 +0800
        return dt.strftime('%Y-%m-%d %H:%M:%S') + f'.{int(record.msecs):03d} {tz_str}'


def get_trace_id() -> str:
    """获取当前请求的 trace_id"""
    trace_id = trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())
        trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """设置当前请求的 trace_id"""
    trace_id_var.set(trace_id)


def reset_trace_id() -> None:
    """重置 trace_id"""
    trace_id_var.set(None)


def _get_log_path(name: str = None) -> str:
    """根据日志名称获取日志文件路径
    
    Args:
        name: 日志名称，如 'blacklist'、'user' 等
        
    Returns:
        日志文件的完整路径
    """
    if name:
        # 业务日志：runtime/logs/{name}/{name}.log
        log_dir = os.path.join(settings.log_dir, name)
        log_file = os.path.join(log_dir, f'{name}.log')
    else:
        # 默认日志：runtime/logs/fastapi/fastapi.log
        log_dir = os.path.join(settings.log_dir, settings.app_name)
        log_file = os.path.join(log_dir, f'{settings.app_name}.log')
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    return log_file


def _create_file_handler(log_file: str) -> TimedRotatingFileHandler:
    """创建按天分割的文件处理器
    
    Args:
        log_file: 日志文件路径
        
    Returns:
        TimedRotatingFileHandler 实例
    """
    # 日志格式
    log_format = (
        '%(asctime)s [%(levelname)s] [%(trace_id)s] '
        '%(filename)s:%(lineno)d - %(message)s'
    )
    
    # 创建格式化器
    formatter = TZFormatter(log_format)
    
    # 创建过滤器
    context_filter = RequestContextFilter()
    
    # 文件处理器 - 按天分割
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',  # 每天午夜分割
        interval=1,  # 间隔为1天
        backupCount=settings.log_backup_day,  # 保留天数
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)
    
    return file_handler


def init_logging():
    """初始化日志配置"""
    # 日志格式
    log_format = (
        '%(asctime)s [%(levelname)s] [%(trace_id)s] '
        '%(filename)s:%(lineno)d - %(message)s'
    )
    
    # 创建格式化器
    formatter = TZFormatter(log_format)
    
    # 创建过滤器
    context_filter = RequestContextFilter()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    
    # 配置根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # 过滤掉 httpx 的日志，避免格式不一致
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # 根据 SQL_LOG 配置控制 SQL 日志输出
    if not settings.sql_log:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_logger(name: str = None) -> logging.Logger:
    """获取 logger 实例
    
    Args:
        name: 日志名称，如 'blacklist'、'user' 等
              为 None 时使用默认日志名称（app_name）
              
    Returns:
        logging.Logger 实例
        
    Examples:
        # 默认日志：runtime/logs/fastapi/fastapi.log
        logger = get_logger()
        
        # 黑名单业务日志：runtime/logs/blacklist/blacklist.log
        logger = get_logger('blacklist')
        
        # 用户业务日志：runtime/logs/user/user.log
        logger = get_logger('user')
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有处理器，直接返回
    if logger.handlers:
        return logger
    
    # 获取日志文件路径（会自动创建目录）
    log_file = _get_log_path(name)
    
    # 创建文件处理器
    file_handler = _create_file_handler(log_file)
    
    # 添加文件处理器
    logger.addHandler(file_handler)
    
    # 设置日志级别
    logger.setLevel(logging.INFO)
    
    # 不向上传播，避免重复输出
    logger.propagate = False
    
    return logger
