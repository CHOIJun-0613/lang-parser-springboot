import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logger(name: str = None) -> logging.Logger:
    """
    환경변수에서 LOG_LEVEL을 읽어서 로거를 설정합니다.
    
    Args:
        name: 로거 이름 (기본값: None)
    
    Returns:
        설정된 로거 객체
    """
    # 환경변수에서 로그 레벨 읽기
    log_level_str = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    
    # 로그 레벨 매핑
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = log_levels.get(log_level_str, logging.INFO)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 핸들러가 이미 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 포맷터 생성
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    
    # 부모 로거로 전파하지 않음 (중복 출력 방지)
    logger.propagate = False
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """
    로거를 가져옵니다. 환경변수 변경을 반영하기 위해 항상 새로 설정합니다.
    
    Args:
        name: 로거 이름 (기본값: None)
    
    Returns:
        로거 객체
    """
    return setup_logger(name)
