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

        **출력 형식:**
        - `### Overview` 섹션: 클래스 책임과 대표 사용 시나리오를 3~5문장으로 요약합니다.
        - `### Key Responsibilities` 섹션: 핵심 메서드/필드/패턴을 불릿 목록으로 정리합니다.
        - `### Integrations` 섹션: 외부 시스템·DB·프레임워크와의 연계를 불릿 목록으로 기술합니다.
        - 필요한 경우 주석, 어노테이션, 예외 처리 등 추가 통찰을 간단히 언급합니다.

        **제약사항:**
        - **절대로 코드 블록(```java, ```python 등)을 생성하지 마세요.**
        - **절대로 예시 코드나 테스트 코드를 생성하지 마세요.**
        - 전체 길이는 20줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 순수한 텍스트 형식의 Markdown만 출력하세요.
        """
    ).strip(),
    "method_doc": dedent(
        """
        당신은 시니어 Software Architect이자 Software Development 전문가입니다.
        입력으로 ```java ...``` 형식의 Java 메서드 소스 코드가 제공됩니다.
        제공된 소스코드만 가지고 판단하세요.
        아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.

        **출력 형식:**
        - `### Purpose` 섹션: 메서드의 의도와 호출 흐름을 2~3문장으로 요약합니다.
        - `### Inputs & Outputs` 섹션: 파라미터, 반환값, 부작용을 불릿 목록으로 명시합니다.
        - `### Important Details` 섹션: 예외 처리, 성능 고려, 동시성, 호출 의존성 등을 불릿으로 정리합니다.

        **제약사항:**
        - 테스트 포인트나 검증이 필요한 부분은 Important Details 섹션에 텍스트로만 설명합니다.
        - **절대로 코드 블록(```java, ```python 등)을 생성하지 마세요.**
        - **절대로 테스트 코드 예시를 생성하지 마세요.**
        - 전체 길이는 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 순수한 텍스트 형식의 Markdown만 출력하세요.
        """
    ).strip(),
    "sql_doc": dedent(
        """
        당신은 시니어 Software Architect이자 SQL 전문가입니다.
        입력으로 ```sql ...``` 형식의 SQL 문이 제공됩니다.
        아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.

        **출력 형식:**
        - `### Operation` 섹션: 수행하는 CRUD 목적과 데이터 흐름을 1~2문장으로 설명합니다.
        - `### Tables & Conditions` 섹션: 주요 테이블, 조인 조건, 필터를 불릿 목록으로 정리합니다.
        - `### Considerations` 섹션: 인덱스 활용, 잠금, 트랜잭션, 에러 가능성 등 주의사항을 불릿으로 기술합니다.
        - 필요한 경우 입력 파라미터나 바인딩 변수의 의미를 간단히 언급합니다.

        **제약사항:**
        - **절대로 코드 블록(```sql, ```java 등)을 생성하지 마세요.**
        - **절대로 예시 쿼리나 테스트 코드를 생성하지 마세요.**
        - 전체 길이는 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 순수한 텍스트 형식의 Markdown만 출력하세요.
        """
    ).strip(),
    "sql_batch_doc": dedent(
        """
        당신은 시니어 Software Architect이자 SQL 전문가입니다.
        입력으로 여러 개의 SQL 문이 제공됩니다. 각 SQL은 다음 형식으로 구분됩니다:

        **SQL #1** (ID: {sql_id})
        ```sql
        {sql_content}
        ```
        **END #1**

        각 SQL 문에 대해 아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.

        **중요: 출력 형식을 정확히 따라야 합니다!**

        각 SQL에 대해 다음 형식으로 분석 결과를 작성하세요 (예시 참고):

        ---SQL#1---
        ### Operation
        사용자 ID를 기준으로 단일 레코드를 조회하는 SELECT 문입니다.

        ### Tables & Conditions
        - 테이블: users
        - 조건: id = #{userId}

        ### Considerations
        - 인덱스: id 컬럼에 인덱스가 필요합니다.
        - 단일 레코드 조회로 성능 영향은 최소화됩니다.
        ---END#1---

        ---SQL#2---
        ### Operation
        새로운 사용자 정보를 users 테이블에 삽입하는 INSERT 문입니다.

        ### Tables & Conditions
        - 테이블: users
        - 컬럼: name, email

        ### Considerations
        - 트랜잭션: 커밋 전까지 다른 세션에서 보이지 않습니다.
        - 제약조건: email은 UNIQUE 제약이 있을 가능성이 높습니다.
        ---END#2---

        **제약사항:**
        - 각 SQL 분석은 반드시 `---SQL#1---`, `---SQL#2---` 형식으로 시작합니다 (# 기호 필수!)
        - 각 SQL 분석은 반드시 `---END#1---`, `---END#2---` 형식으로 끝나야 합니다.(# 기호 필수)
        - **절대로 코드 블록(```sql, ```java 등)을 생성하지 마세요.**
        - **절대로 예시 쿼리나 테스트 코드를 생성하지 마세요.**
        - 각 SQL 분석은 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 순수한 텍스트 형식의 Markdown만 출력하세요.
        - 모든 SQL에 대해 반드시 분석 결과를 제공해야 합니다.
        """
    ).strip(),
    "method_batch_doc": dedent(
        """
        당신은 시니어 Software Architect이자 Software Development 전문가입니다.
        입력으로 여러 개의 Java 메서드가 제공됩니다. 각 메서드는 다음 형식으로 구분됩니다:

        **Method #1** (Class: {class_name}, Method: {method_name})
        ```java
        {method_source}
        ```
        **END #1**

        제공된 소스코드만 가지고 판단하세요.
        각 메서드에 대해 아래 요구사항을 모두 충족하는 한국어 Markdown 보고서를 생성하세요.

        **중요: 출력 형식을 정확히 따라야 합니다!**

        각 메서드에 대해 다음 형식으로 분석 결과를 작성하세요 (예시 참고):

        ---Method#1---
        ### Purpose
        사용자 ID를 받아서 데이터베이스에서 사용자 정보를 조회합니다.

        ### Inputs & Outputs
        - 입력: userId (Long 타입)
        - 반환: User 객체
        - 예외: 사용자를 찾지 못하면 NotFoundException 발생

        ### Important Details
        - 트랜잭션: readOnly = true로 설정되어 조회 전용입니다.
        - 캐싱: @Cacheable 어노테이션으로 결과를 캐시합니다.
        ---END#1---

        ---Method#2---
        ### Purpose
        새로운 사용자를 생성하고 데이터베이스에 저장합니다.

        ### Inputs & Outputs
        - 입력: UserDto (사용자 정보)
        - 반환: 생성된 User 엔티티
        - 부작용: 데이터베이스에 INSERT 실행

        ### Important Details
        - 검증: 입력 데이터의 유효성을 검사합니다.
        - 트랜잭션: 저장 작업이 실패하면 롤백됩니다.
        ---END#2---

        **제약사항:**
        - 각 메서드 분석은 반드시 `---Method#1---`, `---Method#2---` 형식으로 시작합니다 (# 기호 필수!)
        - 각 메서드 분석은 반드시 `---END#1---`, `---END#2---` 형식으로 끝나야 합니다.(# 기호 필수)
        - 테스트 포인트나 검증이 필요한 부분은 Important Details 섹션에 텍스트로만 설명합니다.
        - **절대로 코드 블록(```java, ```python 등)을 생성하지 마세요.**
        - **절대로 테스트 코드 예시를 생성하지 마세요.**
        - 각 메서드 분석은 10줄 이내로 유지하고, 불필요한 서두나 마무리 문구는 생략합니다.
        - 순수한 텍스트 형식의 Markdown만 출력하세요.
        - 모든 메서드에 대해 반드시 분석 결과를 제공해야 합니다.
        """
    ).strip(),
}


def get_prompt(name: str) -> str:
    """Return the prompt text registered under the given name."""
    try:
        return PROMPTS[name]
    except KeyError as exc:
        raise KeyError(f"Unregistered prompt requested: {name}") from exc
