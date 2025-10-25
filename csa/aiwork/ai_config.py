"""
AI Provider 설정 관리 모듈
환경변수를 통해 AI Provider와 모델을 설정하고 관리합니다.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서 찾기)
# load_dotenv()는 자동으로 현재 디렉토리와 상위 디렉토리에서 .env 파일을 찾습니다
load_dotenv()

class AIConfig:
    """AI Provider 설정 클래스"""
    
    def __init__(self):
        # AI 분석 사용 여부 설정
        self.ai_use_analysis = os.getenv("AI_USE_ANALYSIS", "false").lower() == "true"

        # AI Provider 설정 (google, groq, lmstudio, openai)
        self.ai_provider = os.getenv("AI_PROVIDER", "google").lower()

        # Google Gemini 설정
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

        # Groq 설정
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model_name = os.getenv("GROQ_MODEL_NAME", "qwen/qwen3-32b")

        # LM Studio 설정
        self.lmstudio_base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self.lmstudio_qwen_model_name = os.getenv("LMSTUDIO_QWEN_MODEL_NAME", "lm_studio/qwen/qwen3-8b")


        # OpenAI 설정
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-oss:20b")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "http://devlab.skax.co.kr/ollama/v1")
    def get_current_provider(self) -> str:
        """현재 설정된 AI Provider를 반환합니다."""
        return self.ai_provider
    
    def get_current_model_name(self) -> str:
        """현재 설정된 AI Provider에 따른 모델명을 반환합니다."""
        if self.ai_provider == "groq":
            return self.groq_model_name
        elif self.ai_provider == "lmstudio":
            return self.lmstudio_qwen_model_name
        elif self.ai_provider == "openai":
            return self.openai_model_name
        else:  # google (기본값)
            return self.gemini_model_name
    
    def is_google_available(self) -> bool:
        """Google Gemini가 사용 가능한지 확인합니다."""
        return self.ai_provider == "google" and self.google_api_key is not None
    
    def is_groq_available(self) -> bool:
        """Groq가 사용 가능한지 확인합니다."""
        return self.ai_provider == "groq" and self.groq_api_key is not None
    
    def is_lmstudio_available(self) -> bool:
        """LM Studio가 사용 가능한지 확인합니다."""
        return self.ai_provider == "lmstudio"
    
    def is_openai_available(self) -> bool:
        """OpenAI가 사용 가능한지 확인합니다."""
        return self.ai_provider == "openai" and self.openai_api_key is not None
    
    def get_provider_info(self) -> dict:
        """현재 Provider 정보를 반환합니다."""
        return {
            "provider": self.ai_provider,
            "model": self.get_current_model_name(),
            "available": self.is_current_provider_available()
        }
    
    def is_current_provider_available(self) -> bool:
        """현재 설정된 Provider가 사용 가능한지 확인합니다."""
        if self.ai_provider == "google":
            return self.is_google_available()
        elif self.ai_provider == "groq":
            return self.is_groq_available()
        elif self.ai_provider == "lmstudio":
            return self.is_lmstudio_available()
        elif self.ai_provider == "openai":
            return self.is_openai_available()
        return False

# 전역 설정 인스턴스
ai_config = AIConfig()
