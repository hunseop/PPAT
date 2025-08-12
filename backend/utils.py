import time
import logging
from datetime import datetime
import re

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('proxy_monitor')

def interruptible_sleep(seconds, is_running):
    """중단 가능한 sleep 함수"""
    end_time = time.time() + seconds
    while time.time() < end_time and is_running():
        time.sleep(0.1)

def split_line(lst: str) -> list:
    """파이프 구분 문자열을 리스트로 분리 (양쪽 공백 허용)
    예: 'a | b|c| d ' -> ['a','b','c','d']
    
    테이블 형식으로 선두/말미에 파이프가 있는 경우("| a | b |"),
    선두/말미의 빈 셀만 제거하고 내부의 빈 값은 유지한다.
    """
    if lst is None:
        return []
    # 줄끝 개행 제거 및 앞뒤 공백 제거 후 파이프 기준 분리
    line = lst.strip().rstrip('\n')
    parts = re.split(r"\s*\|\s*", line)

    # 선두/말미의 빈 요소만 제거 (내부의 빈 값은 보존)
    if parts and (parts[0] is None or parts[0].strip() == ""):
        parts = parts[1:]
    if parts and (parts[-1] is None or parts[-1].strip() == ""):
        parts = parts[:-1]

    # 각 요소 트리밍 (내부 빈 값은 그대로 남김)
    return [p.strip() if p is not None else "" for p in parts]

def get_current_timestamp():
    """현재 시간을 반환"""
    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S')
    }

def validate_resource_data(data: dict) -> bool:
    """리소스 데이터 유효성 검사
    
    Args:
        data (dict): 검사할 데이터
        
    Returns:
        bool: 유효성 검사 통과 여부
    """
    required_fields = ['cpu', 'memory', 'uc', 'cc', 'cs', 'http', 'https', 'ftp']
    
    try:
        # 필수 필드 존재 확인
        for field in required_fields:
            if field not in data:
                logger.error(f"필수 필드 누락: {field}")
                return False
        
        # CPU 값 검증
        if data['cpu'] != 'error' and not (-1 <= float(data['cpu']) <= 100):
            logger.error(f"잘못된 CPU 값: {data['cpu']}")
            return False
            
        # 메모리 값 검증
        if data['memory'] != 'error' and not (-1 <= float(data['memory']) <= 100):
            logger.error(f"잘못된 메모리 값: {data['memory']}")
            return False
            
        return True
    except ValueError as e:
        logger.error(f"데이터 검증 중 형식 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"데이터 검증 중 오류 발생: {e}")
        return False


def format_bytes(num: int) -> str:
    """바이트 단위를 읽기 쉬운 문자열로 변환"""
    step_unit = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < step_unit:
            return f"{num:.2f}{unit}"
        num /= step_unit
    return f"{num:.2f}PB"


def parse_size(text: str) -> int:
    """예: '100MB' -> 104857600"""
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5,
    }
    text = text.strip().upper()
    for unit, factor in units.items():
        if text.endswith(unit):
            try:
                value = float(text[:-len(unit)])
                return int(value * factor)
            except ValueError:
                break
    raise ValueError(f"잘못된 크기 표현: {text}")