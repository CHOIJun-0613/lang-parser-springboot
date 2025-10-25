"""
AI Provider별 LLM 관리 모듈
각 AI Provider에 맞는 LLM 설정과 연결을 관리합니다.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# Google GenAI (최신 google-genai 라이브러리)
try:
    from google import genai
    from google.genai.errors import APIError
    GOOGLE_LLM_AVAILABLE = True
except ImportError:
    genai = None
    APIError = None
    GOOGLE_LLM_AVAILABLE = False

# LiteLLM (순수 litellm 라이브러리 사용)
try:
    import litellm
    LITE_LLM_AVAILABLE = True
except ImportError:
    litellm = None
    LITE_LLM_AVAILABLE = False

# AI 설정
try:
    from ai_config import ai_config
except ImportError:
    # 상대 import 시도
    try:
        from .ai_config import ai_config
    except ImportError:
        # 절대 경로 import 시도
        from ai_config import ai_config

logger = logging.getLogger(__name__)

class BaseAIProvider(ABC):
    """AI Provider 기본 클래스"""
    
    @abstractmethod
    def create_llm(self) -> Any:
        """LLM 인스턴스를 생성합니다."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Provider가 사용 가능한지 확인합니다."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """모델명을 반환합니다."""
        pass

class GoogleAIProvider(BaseAIProvider):
    """Google Gemini AI Provider (google-genai 라이브러리 사용)"""

    def __init__(self):
        self.api_key = ai_config.google_api_key
        self.model_name = ai_config.gemini_model_name

    def create_llm(self):
        """Google Gemini LLM을 생성합니다."""
        if not self.is_available():
            raise ValueError("Google API 키가 설정되지 않았습니다.")

        if not GOOGLE_LLM_AVAILABLE:
            raise ImportError("google-genai 모듈을 사용할 수 없습니다. google-genai 패키지를 설치해주세요.")

        # 환경변수 설정 (genai.Client가 자동으로 읽음)
        os.environ["GEMINI_API_KEY"] = self.api_key

        # Google GenAI Wrapper 클래스
        class GoogleGenAIWrapper:
            def __init__(self, model_name):
                self.model_name = model_name
                self.client = genai.Client()

            def __call__(self, prompt):
                """직접 호출 시 genai.Client 사용"""
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=[prompt]
                    )
                    return response.text
                except APIError as e:
                    raise RuntimeError(f"Gemini API 호출 오류: {e}")
                except Exception as e:
                    raise RuntimeError(f"Gemini 알 수 없는 오류: {e}")

        return GoogleGenAIWrapper(model_name=self.model_name)

    def is_available(self) -> bool:
        """Google Gemini가 사용 가능한지 확인합니다."""
        return self.api_key is not None and GOOGLE_LLM_AVAILABLE

    def get_model_name(self) -> str:
        """모델명을 반환합니다."""
        return self.model_name

class GroqAIProvider(BaseAIProvider):
    """Groq AI Provider"""

    def __init__(self):
        self.api_key = ai_config.groq_api_key
        self.model_name = ai_config.groq_model_name

    def create_llm(self):
        """Groq LLM을 생성합니다."""
        if not self.is_available():
            raise ValueError("Groq API 키가 설정되지 않았습니다.")

        if not LITE_LLM_AVAILABLE:
            raise ImportError("litellm 모듈을 사용할 수 없습니다. litellm 패키지를 설치해주세요.")

        # 순수 litellm을 사용하여 Groq 연결
        # LiteLLM Wrapper 객체 반환
        class LiteLLMWrapper:
            def __init__(self, model, api_key):
                self.model = model
                self.api_key = api_key

            def __call__(self, prompt):
                """직접 호출 시 litellm.completion 사용"""
                response = litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.api_key,
                    temperature=0.1
                )
                return response.choices[0].message.content

        return LiteLLMWrapper(
            model=f"groq/{self.model_name}",
            api_key=self.api_key
        )

    def is_available(self) -> bool:
        """Groq가 사용 가능한지 확인합니다."""
        return self.api_key is not None and LITE_LLM_AVAILABLE

    def get_model_name(self) -> str:
        """모델명을 반환합니다."""
        return self.model_name

class LMStudioAIProvider(BaseAIProvider):
    """LM Studio AI Provider"""

    def __init__(self):
        self.base_url = ai_config.lmstudio_base_url
        self.model_name = ai_config.lmstudio_qwen_model_name

    def create_llm(self):
        """LM Studio LLM을 생성합니다."""
        if not self.is_available():
            raise ValueError("LM Studio가 설정되지 않았습니다.")

        if not LITE_LLM_AVAILABLE:
            raise ImportError("litellm 모듈을 사용할 수 없습니다. litellm 패키지를 설치해주세요.")

        # 순수 litellm을 사용하여 LM Studio 연결
        # LiteLLM Wrapper 객체 반환
        class LiteLLMWrapper:
            def __init__(self, model, base_url):
                self.model = model
                self.base_url = base_url

            def __call__(self, prompt):
                """직접 호출 시 litellm.completion 사용"""
                response = litellm.completion(
                    model=f"openai/{self.model}",
                    messages=[{"role": "user", "content": prompt}],
                    api_base=self.base_url,
                    api_key="lm-studio",  # Dummy key
                    temperature=0.1
                )
                return response.choices[0].message.content

        return LiteLLMWrapper(
            model=self.model_name,
            base_url=self.base_url
        )

    def is_available(self) -> bool:
        """LM Studio가 사용 가능한지 확인합니다."""
        # LM Studio는 로컬에서 실행되므로 litellm만 사용 가능한지 확인
        return LITE_LLM_AVAILABLE

    def get_model_name(self) -> str:
        """모델명을 반환합니다."""
        return self.model_name

class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider"""

    def __init__(self):
        self.api_key = ai_config.openai_api_key
        self.model_name = ai_config.openai_model_name
        self.base_url = ai_config.openai_base_url

    def create_llm(self):
        """OpenAI LLM을 생성합니다."""
        if not self.is_available():
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")

        if not LITE_LLM_AVAILABLE:
            raise ImportError("litellm 모듈을 사용할 수 없습니다. litellm 패키지를 설치해주세요.")

        # 순수 litellm을 사용하여 OpenAI/Ollama 연결
        # LiteLLM Wrapper 객체 반환
        class LiteLLMWrapper:
            def __init__(self, model, base_url, api_key):
                self.model = model
                self.base_url = base_url
                self.api_key = api_key

            def __call__(self, prompt):
                """직접 호출 시 litellm.completion 사용"""
                response = litellm.completion(
                    model=f"openai/{self.model}",
                    messages=[{"role": "user", "content": prompt}],
                    api_base=self.base_url,
                    api_key=self.api_key or "dummy-key",
                    temperature=0.1
                )
                return response.choices[0].message.content

        return LiteLLMWrapper(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key
        )

    def is_available(self) -> bool:
        """OpenAI가 사용 가능한지 확인합니다."""
        return self.api_key is not None and LITE_LLM_AVAILABLE

    def get_model_name(self) -> str:
        """모델명을 반환합니다."""
        return self.model_name

class AIProviderManager:
    """AI Provider 관리자"""
    
    def __init__(self):
        self.providers = {
            "google": GoogleAIProvider(),
            "groq": GroqAIProvider(),
            "lmstudio": LMStudioAIProvider(),
            "openai": OpenAIProvider()
        }
        self.current_provider_name = ai_config.get_current_provider()

    def get_current_provider(self, provider_name: Optional[str] = None) -> BaseAIProvider:
        """
        현재 설정된 Provider를 반환합니다.
        provider_name이 주어지면 해당 provider를 반환하고,
        없으면 self.current_provider_name을 사용합니다.
        """
        name = provider_name if provider_name is not None else self.current_provider_name
        provider = self.providers.get(name)
        self.current_provider_name = name
        if not provider:
            logger.warning(f"알 수 없는 AI Provider: {name}, Google로 기본 설정")
            return self.providers["google"]
        return provider

    # def get_current_provider(self) -> BaseAIProvider:
    #     """현재 설정된 Provider를 반환합니다."""
    #     provider = self.providers.get(self.current_provider_name)
    #     if not provider:
    #         logger.warning(f"알 수 없는 AI Provider: {self.current_provider_name}, Google로 기본 설정")
    #         return self.providers["google"]
    #     return provider
    
    def create_llm(self, provider_name: Optional[str] = None, model_name: Optional[str] = None):
        """
        provider_name이 주어지면 해당 provider로 LLM을 생성하고,
        없으면 현재 provider(self.get_current_provider())로 LLM을 생성합니다.
        model_name이 주어지면 해당 모델명을 사용합니다.
        """
        provider = self.get_current_provider(provider_name)
        provider_name_to_use = provider_name if provider_name is not None else self.current_provider_name

        # model_name이 제공되면 provider의 model_name을 업데이트
        if model_name is not None:
            provider.model_name = model_name

        if not provider.is_available():
            print(f"Provider '{provider_name_to_use}'가 사용 불가능합니다.")
            # Google으로 폴백
            fallback_provider = self.providers["google"]
            if fallback_provider.is_available():
                print("Google Gemini로 폴백합니다.")
                return fallback_provider.create_llm()
            else:
                raise ValueError("사용 가능한 AI Provider가 없습니다.")

        print(f"AI Provider '{provider_name_to_use}' 사용, 모델: {provider.get_model_name()}")
        return provider.create_llm()

    # def create_llm(self):
    #     """현재 Provider에 맞는 LLM을 생성합니다."""
    #     provider = self.get_current_provider()
        
    #     if not provider.is_available():
    #         logger.warning(f"현재 Provider '{self.current_provider_name}'가 사용 불가능합니다.")
    #         # Google으로 폴백
    #         fallback_provider = self.providers["google"]
    #         if fallback_provider.is_available():
    #             logger.info("Google Gemini로 폴백합니다.")
    #             return fallback_provider.create_llm()
    #         else:
    #             raise ValueError("사용 가능한 AI Provider가 없습니다.")
        
    #     logger.info(f"AI Provider '{self.current_provider_name}' 사용, 모델: {provider.get_model_name()}")
    #     return provider.create_llm()
    

    def get_provider_info(self) -> Dict[str, Any]:
        """현재 Provider 정보를 반환합니다."""
        provider = self.get_current_provider()
        return {
            "provider": self.current_provider_name,
            "model": provider.get_model_name(),
            "available": provider.is_available()
        }

# 전역 AI Provider Manager 인스턴스
ai_provider_manager = AIProviderManager()
