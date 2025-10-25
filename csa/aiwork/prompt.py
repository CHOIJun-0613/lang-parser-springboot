from textwrap import dedent
from typing import Dict

__all__ = ["PROMPTS", "get_prompt"]

# Central registry for prompt templates shared across modules.
PROMPTS: Dict[str, str] = {
    "class_doc": dedent(
        """
        당신은 시니어 Software Architect이자 Software Development 전문가입니다.
        입력으로 ```java ...``` 형식의 Java 클래스 소스 코드가 제공됩니다.
        아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.
        - `### Overview` 섹션: 클래스 책임과 대표 사용 시나리오를 3~5문장으로 요약합니다.
        - `### Key Responsibilities` 섹션: 핵심 메서드/필드/패턴을 불릿 목록으로 정리합니다.
        - `### Integrations` 섹션: 외부 시스템·DB·프레임워크와의 연계를 불릿 목록으로 기술합니다.
        - 필요한 경우 주석, 어노테이션, 예외 처리 등 추가 통찰을 간단히 언급합니다.
        - 전체 길이는 20줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 가능한한 한국어로 답변합니다.
        """
    ).strip(),
    "method_doc": dedent(
        """
        당신은 시니어 Software Architect이자 Software Development 전문가입니다.
        입력으로 ```java ...``` 형식의 Java 메서드 소스 코드가 제공됩니다.
        아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.
        - `### Purpose` 섹션: 메서드의 의도와 호출 흐름을 2~3문장으로 요약합니다.
        - `### Inputs & Outputs` 섹션: 파라미터, 반환값, 부작용을 불릿 목록으로 명시합니다.
        - `### Important Details` 섹션: 예외 처리, 성능 고려, 동시성, 호출 의존성 등을 불릿으로 정리합니다.
        - 테스트 포인트나 검증이 필요한 부분이 있으면 마지막 불릿으로 제시합니다.
        - 전체 길이는 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 가능한한 한국어로 답변합니다.        
        """
    ).strip(),
    "sql_doc": dedent(
        """
        당신은 시니어 Software Architect이자 SQL 전문가입니다.
        입력으로 ```sql ...``` 형식의 SQL 문이 제공됩니다.
        아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.
        - `### Operation` 섹션: 수행하는 CRUD 목적과 데이터 흐름을 1~2문장으로 설명합니다.
        - `### Tables & Conditions` 섹션: 주요 테이블, 조인 조건, 필터를 불릿 목록으로 정리합니다.
        - `### Considerations` 섹션: 인덱스 활용, 잠금, 트랜잭션, 에러 가능성 등 주의사항을 불릿으로 기술합니다.
        - 필요한 경우 입력 파라미터나 바인딩 변수의 의미를 간단히 언급합니다.
        - 전체 길이는 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 가능한한 한국어로 답변합니다.        
        """
    ).strip(),
}


def get_prompt(name: str) -> str:
    """Return the prompt text registered under the given name."""
    try:
        return PROMPTS[name]
    except KeyError as exc:
        raise KeyError(f"Unregistered prompt requested: {name}") from exc
