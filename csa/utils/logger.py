import os
import logging
import glob
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 전역 변수: 현재 실행 중인 명령어 저장
_current_command = None

# 로거 캐시 (스레드 안전)
_logger_cache = {}
_logger_lock = threading.Lock()

def set_command_context(command: str):
    """현재 실행 중인 명령어 컨텍스트 설정"""
    global _current_command
    _current_command = command

def _cleanup_old_logs(logs_dir: str):
    """
    7일 이전 로그 파일들을 삭제합니다.
    
    Args:
        logs_dir: 로그 디렉토리 경로
    """
    try:
        if not os.path.exists(logs_dir):
            return
        
        # 7일 이전 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # 모든 .log 파일 검색
        log_pattern = os.path.join(logs_dir, "*.log")
        log_files = glob.glob(log_pattern)
        
        for log_file in log_files:
            try:
                # 파일 수정 시간 확인
                file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if file_mtime < cutoff_date:
                    os.remove(log_file)
                    print(f"Deleted old log file: {log_file}")
            except (OSError, IOError) as e:
                print(f"Error deleting log file {log_file}: {e}")
    except Exception as e:
        print(f"Error during log cleanup: {e}")

def _get_log_level_char(level: int) -> str:
    """
    로그 레벨을 1자리 문자로 변환합니다.
    
    Args:
        level: 로그 레벨 (logging.DEBUG, logging.INFO 등)
    
    Returns:
        로그 레벨 1자리 문자 (D, I, W, E, C)
    """
    level_mapping = {
        logging.DEBUG: 'D',
        logging.INFO: 'I',
        logging.WARNING: 'W',
        logging.ERROR: 'E',
        logging.CRITICAL: 'C'
    }
    return level_mapping.get(level, 'I')

class CustomFormatter(logging.Formatter):
    """커스텀 로그 포맷터"""
    
    def format(self, record):
        # 로그 레벨 1자리 문자 가져오기
        level_char = _get_log_level_char(record.levelno)
        
        # 타임스탬프 포맷: YYYY-MM-DD HH24:MI:SS.sss
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 포맷된 메시지: YYYY-MM-DD HH24:MI:SS.sss [D/I/W/E/C] : 로그 메시지
        formatted_message = f"{timestamp} [{level_char}] : {record.getMessage()}"
        
        return formatted_message

def setup_logger(name: str = None, command: str = None) -> logging.Logger:
    """
    환경변수에서 LOG_LEVEL을 읽어서 로거를 설정합니다.
    파일과 콘솔 양방향 출력을 지원합니다.
    
    Args:
        name: 로거 이름 (기본값: None)
        command: 작업 명령어 (로그 파일명 결정용, 기본값: None, 전역 컨텍스트 사용)
    
    Returns:
        설정된 로거 객체
    """
    global _current_command
    
    # command가 명시적으로 전달되지 않으면 전역 컨텍스트 사용
    if command is None:
        command = _current_command if _current_command else "run"
    
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
    
    # 커스텀 포맷터 생성
    formatter = CustomFormatter()
    
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 파일 핸들러 생성
    try:
        # 프로젝트 루트 디렉토리 찾기 (현재 파일 기준으로 상위 탐색)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        logs_dir = os.path.join(project_root, "logs")
        
        # logs 디렉토리 생성
        os.makedirs(logs_dir, exist_ok=True)
        
        # 과거 로그 파일 정리
        _cleanup_old_logs(logs_dir)
        
        # 로그 파일명 생성: {작업명령어}-YYYYMMDD.log
        today = datetime.now().strftime('%Y%m%d')
        log_filename = f"{command}-{today}.log"
        log_filepath = os.path.join(logs_dir, log_filename)
        
        # 파일 핸들러 생성
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
    except Exception as e:
        # 파일 핸들러 생성 실패 시 콘솔만 사용
        logger.addHandler(console_handler)
        print(f"Warning: Could not create file handler: {e}")
    
    # 부모 로거로 전파하지 않음 (중복 출력 방지)
    logger.propagate = False
    
    return logger

def get_logger(name: str = None, command: str = None) -> logging.Logger:
    """
    로거를 가져옵니다. 스레드 안전하게 캐시된 로거를 반환합니다.

    Args:
        name: 로거 이름 (기본값: None)
        command: 작업 명령어 (로그 파일명 결정용, 기본값: None, 전역 컨텍스트 사용)

    Returns:
        로거 객체
    """
    global _current_command

    # command가 명시적으로 전달되지 않으면 전역 컨텍스트 사용
    if command is None:
        command = _current_command if _current_command else "run"

    # 캐시 키 생성 (name + command 조합)
    cache_key = f"{name}:{command}"

    # 이미 캐시된 로거가 있으면 반환 (스레드 안전)
    with _logger_lock:
        if cache_key in _logger_cache:
            return _logger_cache[cache_key]

        # 새 로거 생성 및 캐시
        logger = setup_logger(name, command)
        _logger_cache[cache_key] = logger
        return logger
