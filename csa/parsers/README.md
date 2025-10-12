# csa.parsers 안내

`csa.parsers` 패키지는 다양한 소스(예: Java, SQL, DB 메타데이터)를 파싱해 분석 서비스에서 사용 가능한 구조화된 모델로 변환하는 책임을 집니다. 모든 파서는 일관된 인터페이스와 반환 타입을 유지해 상위 계층에서의 재사용과 테스트를 용이하게 해야 합니다.

## 디렉터리 구조

- `base.py` : 파서 공통 인터페이스와 헬퍼 유틸 정의
- `java/` : Java 소스 전용 파서 모듈
- `sql/` : SQL 및 매퍼 관련 파서 모듈
- `db/` : 데이터베이스 메타 정보 파서 모듈

새로운 서브 패키지를 추가할 때도 동일한 패턴(`__init__.py`, 하위 모듈, 테스트)으로 구성해 주세요.

## 공통 규칙

1. **반환 타입** : 모든 파서는 `dataclasses.dataclass` 또는 pydantic `BaseModel` 인스턴스를 반환합니다. 가능한 경우 `csa.models`에 정의된 도메인 모델을 재사용합니다.
2. **타입 힌트** : 입력 인자와 반환 값에 명시적 타입 힌트를 작성합니다.
3. **의존성 주입** : 외부 리소스 접근(파일 시스템, DB, 네트워크)은 함수 인자나 설정 객체를 통해 주입하고, 전역 변수 사용을 피합니다.
4. **로깅** : `csa.utils.logger.get_logger()`를 사용하며, 디버그·정보 레벨 메시지를 상황에 맞게 구분합니다.
5. **예외 처리** : 파싱 실패는 `ParserError`(필요 시 새 커스텀 예외)로 래핑해 상위 계층에서 일관되게 처리할 수 있도록 합니다.
6. **규칙 준수** : 네이밍은 snake_case, 클래스는 PascalCase를 지키며, 함수 길이는 100줄 이내를 권장합니다.

## 사용 예시

```python
from dataclasses import dataclass

from csa.parsers.base import BaseParser, ParserResult


@dataclass
class SampleEntity(ParserResult):
    """파싱 결과 데이터 구조(필요 시 csa.models.* 재사용)."""
    name: str
    attributes: dict[str, str]


class SampleParser(BaseParser[str, SampleEntity]):
    """샘플 파서: 입력 문자열을 구조화된 모델로 변환."""

    def parse(self, source: str) -> SampleEntity:
        self.logger.debug("샘플 파서 실행: %s", source)
        name, raw_attr = source.split(":", maxsplit=1)
        attributes = dict(item.split("=") for item in raw_attr.split(","))
        return SampleEntity(name=name.strip(), attributes=attributes)
```

## 테스트 지침

- 새 파서를 추가할 때 `tests/unit`에 최소한의 정상/에러 시나리오 테스트를 작성합니다.
- 외부 리소스를 다루는 경우 `pytest`의 fixture를 활용해 가짜 리포지토리나 샘플 파일(`tests/sample_*`)을 준비합니다.
- 파서 반환 모델이 다른 서비스와 연동된다면 `tests/integration`에 연동 테스트를 추가해 계약을 검증합니다.

## 기여 절차

1. 규칙 변경이 필요한 경우 먼저 Issue를 열어 팀 합의를 구합니다.
2. 새 파서 추가 시 README의 규칙·예시를 준수하며, 필요한 경우 본 문서를 업데이트합니다.
3. 코드 변경과 함께 테스트를 실행하고 결과를 PR 설명에 포함합니다.
4. CI가 규칙 위반(타입 힌트 누락, 포맷 오류 등)을 감지하면 PR이 거절될 수 있으므로 사전에 점검합니다.
