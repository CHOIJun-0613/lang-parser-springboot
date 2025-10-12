# csa.diagrams 안내

`csa.diagrams` 패키지는 분석 결과를 기반으로 시퀀스 다이어그램 등 다양한 시각화를 생성해 외부 도구(PlantUML, Mermaid 등)와 연동할 수 있는 아티팩트를 제공합니다. 생성 로직은 서비스 계층(`csa.services.*`)에서 호출되며, 공통 규칙을 통해 일관된 출력 형식을 유지합니다.

## 디렉터리 구조

- `sequence/` : 시퀀스 다이어그램 생성기와 관련 지원 모듈
- `__init__.py` : 공개 API 정리 및 헬퍼 재노출

새 다이어그램 유형을 추가할 때는 별도 서브 패키지로 분리하고, `__all__`을 통해 외부 노출 대상을 명시합니다.

## 공통 규칙

1. **입력 모델** : 다이어그램 생성기는 반드시 `csa.models` 또는 `csa.parsers`가 반환하는 dataclass/pydantic 모델을 입력으로 받습니다.
2. **출력 형식** : 문자열 기반 DSL(PlantUML, Mermaid)을 반환하거나, 파일 경로를 반환해 상위 계층에서 후속 처리를 수행하도록 합니다. 반환 타입은 명시적으로 표현합니다.
3. **환경 의존성** : 출력 경로나 외부 명령 호출은 서비스 계층에서 주입하며, 패키지 내부에서 직접 하드코딩하지 않습니다.
4. **로깅/에러** : `csa.utils.logger.get_logger()`를 사용하고, 예외는 `DiagramGenerationError` 등 의미 있는 도메인 예외로 감쌉니다.
5. **문서화** : 새 다이어그램 유형을 추가하면 이 README에 구조와 사용 예시를 업데이트합니다.

## 사용 예시

```python
from dataclasses import dataclass

from csa.diagrams.sequence.plantuml import SequencePlantUmlRenderer
from csa.models.sequence import SequenceFlow


@dataclass
class SimpleFlow(SequenceFlow):
    """시퀀스 다이어그램 입력 모델 예시."""
    source: str
    target: str
    action: str


def render_example() -> str:
    renderer = SequencePlantUmlRenderer()
    flow = SimpleFlow(source="Controller", target="Service", action="invoke()")
    return renderer.render([flow])
```

## 테스트 지침

- 다이어그램 생성기는 문자열 비교가 어렵다면 스냅샷 테스트(pytest-regressions 등)를 활용합니다.
- 외부 도구 연동이 필요한 경우, 통합 테스트에서만 실제 명령을 호출하고 단위 테스트에서는 목(mock) 객체로 대체합니다.
- 생성된 텍스트가 PlantUML/ Mermaid 문법에 맞는지 검사하는 헬퍼가 있다면 반드시 사용합니다.

## 기여 절차

1. 새 다이어그램 유형 제안 시 문서(README)와 예시 코드를 동시 업데이트합니다.
2. 출력 포맷 변경이나 breaking change는 팀 논의 후 진행하고, `docs/`의 관련 문서도 갱신합니다.
3. 테스트와 코드 스타일(PEP 8, 타입 힌트)을 통과한 뒤 PR을 생성하며, 예상되는 영향 범위를 PR 설명에 기록합니다.
