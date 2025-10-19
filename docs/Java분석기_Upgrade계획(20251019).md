# Java 분석기 업그레이드 계획서

**작성일**: 2025-10-19
**작성자**: Claude Code
**작업 범위**: JDK 17+ 지원을 위한 Java 파싱 라이브러리 교체 검토

---

## 📋 개요

현재 CSA 프로젝트는 **javalang 0.13.0** 라이브러리를 사용하여 Java 소스 코드를 파싱하고 있습니다.
javalang은 **Java 8 문법만 지원**하며, JDK 9 이상에서 도입된 최신 Java 문법(모듈, 레코드, sealed 클래스, 패턴 매칭 등)을 분석할 수 없는 한계가 있습니다.

본 문서는 **JDK 17+, 나아가 JDK 21까지 지원**하는 최신 Java 파싱 라이브러리를 조사하고,
현재 프로젝트에 적용하기 위한 마이그레이션 전략을 수립합니다.

### 핵심 목표

- ✅ JDK 17, JDK 21 최신 문법 지원
- ✅ 기존 분석 기능 호환성 유지
- ✅ 성능 및 메모리 효율성 확보
- ✅ 유지보수 및 확장성 개선

---

## 🎯 현재 상황 분석

### 1. 현재 사용 중인 javalang의 특징

**라이브러리**: `javalang 0.13.0`
**GitHub**: https://github.com/c2nes/javalang
**마지막 업데이트**: 2019년 (6년 전)

#### 장점
- ✅ **Pure Python 구현**: 외부 바이너리 의존성 없음
- ✅ **간단한 API**: AST 파싱 및 탐색이 직관적
- ✅ **안정적**: Java 8 문법에 대해서는 안정적으로 작동

#### 단점
- ❌ **JDK 9+ 미지원**: 모듈 시스템, var 키워드, 레코드, sealed 클래스 등 미지원
- ❌ **유지보수 중단**: 마지막 커밋이 6년 전 (2019년)
- ❌ **커뮤니티 비활성**: 이슈 및 PR 대응 없음

### 2. CSA 프로젝트의 javalang 사용 현황

#### 사용 위치
```
csa/
├── services/java_analysis/
│   ├── project.py                 # 주요 사용 위치 (ClassDeclaration, MethodDeclaration 등)
│   └── utils.py                   # 파싱 유틸리티 함수
├── parsers/java/
│   ├── logical_name.py            # 논리명 추출
│   └── description.py             # 설명 추출
└── vendor/javalang/               # 자체 수정 버전 (0.13.0 기반)
```

#### 주요 API 사용 패턴
```python
# 1. Java 소스 파싱
tree = javalang.parse.parse(file_content)

# 2. AST 노드 타입
- javalang.tree.ClassDeclaration
- javalang.tree.InterfaceDeclaration
- javalang.tree.MethodDeclaration
- javalang.tree.MethodInvocation
- javalang.tree.LocalVariableDeclaration

# 3. AST 탐색
for _, node in tree.filter(javalang.tree.MethodInvocation):
    # 메서드 호출 분석
```

#### 분석 대상 Java 요소
- 패키지, 클래스 (Class, Interface, Abstract Class, Enum)
- 메서드 (시그니처, 접근 제어자, 파라미터, 반환 타입)
- 필드 (타입, 어노테이션, 초기값)
- 어노테이션 (Spring Boot, JPA, MyBatis 등)
- 메서드 호출 체인
- 내부 클래스 (Inner Class)

---

## 🔍 대안 라이브러리 조사

### 1. Tree-sitter + py-tree-sitter ⭐ (최우선 권장)

**개요**: Tree-sitter는 범용 파싱 라이브러리로, 다양한 언어의 문법을 지원하며
Python 바인딩(`py-tree-sitter`)을 통해 Python에서 사용 가능합니다.

**GitHub**:
- Tree-sitter Java: https://github.com/tree-sitter/tree-sitter-java
- Python 바인딩: https://github.com/tree-sitter/py-tree-sitter

**설치**:
```bash
pip install tree-sitter tree-sitter-java
# 또는
pip install tree-sitter-languages  # 모든 언어 포함
```

#### 장점
- ✅ **최신 Java 지원**: tree-sitter-java v0.23.5 (2024.12 출시)
- ✅ **활발한 유지보수**: GitHub star 3.1k+, 활발한 커밋
- ✅ **다국어 지원**: Java 외 100+ 언어 파싱 가능
- ✅ **고성능**: C로 구현되어 빠른 파싱 속도
- ✅ **점진적 파싱**: 파일 일부만 변경 시 전체 재파싱 불필요
- ✅ **에러 복구**: 문법 오류가 있어도 부분 AST 생성 가능

#### 단점
- ⚠️ **학습 곡선**: API가 javalang보다 복잡
- ⚠️ **바이너리 의존성**: C 라이브러리 빌드 필요 (PyPI 제공 wheel로 해결 가능)
- ⚠️ **JDK 21 지원 불명확**: 공식 문서에 명시되지 않음 (검증 필요)

#### 사용 예시
```python
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

# 파서 초기화
JAVA_LANGUAGE = Language(tsjava.language())
parser = Parser(JAVA_LANGUAGE)

# Java 코드 파싱
tree = parser.parse(java_code.encode('utf-8'))
root_node = tree.root_node

# AST 탐색
for node in root_node.children:
    if node.type == 'class_declaration':
        class_name = node.child_by_field_name('name').text.decode('utf-8')
```

#### JDK 버전 지원 (추정)
- **확인된 버전**: JDK 8-17 지원 (GitHub 이슈 및 커밋 기록)
- **JDK 21 지원**: 불명확 (직접 검증 필요)
- **검증 방법**: JDK 21 신규 문법(record patterns, pattern matching for switch 등)으로 테스트 필요

---

### 2. javalang17

**개요**: javalang의 Java 17 지원 포크 프로젝트

**GitHub**: https://github.com/WorkOfArtiz/javalang17

**설치**:
```bash
pip install javalang17
```

#### 장점
- ✅ **기존 코드 호환성**: javalang API와 거의 동일
- ✅ **Java 17 지원**: 레코드, sealed 클래스 등 JDK 17 문법 파싱
- ✅ **Pure Python**: 외부 바이너리 의존성 없음

#### 단점
- ⚠️ **유지보수 불확실**: 개인 프로젝트, 커뮤니티 작음
- ⚠️ **JDK 21 미지원**: 이름에서 알 수 있듯 JDK 17까지만 목표
- ⚠️ **테스트 부족**: 프로덕션 사용 사례 부족

#### 사용 예시
```python
# javalang과 동일한 API
import javalang17 as javalang

tree = javalang.parse.parse(file_content)
for _, node in tree.filter(javalang.tree.RecordDeclaration):
    # Java 14+ record 처리
```

---

### 3. code-ast / asts

**개요**: tree-sitter를 백엔드로 사용하는 고수준 AST 분석 라이브러리

**PyPI**:
- code-ast: https://pypi.org/project/code-ast/
- asts: https://pypi.org/project/asts/

**설치**:
```bash
pip install code-ast
# 또는
pip install asts
```

#### 장점
- ✅ **간단한 API**: tree-sitter 복잡성 추상화
- ✅ **다국어 지원**: Java, Python, C++, JavaScript 등
- ✅ **최신 문법 지원**: tree-sitter 기반이므로 최신 Java 지원

#### 단점
- ⚠️ **제한적 기능**: 상위 추상화로 인해 세밀한 제어 어려움
- ⚠️ **커뮤니티 작음**: star 100 미만
- ⚠️ **문서 부족**: 사용 예시 및 가이드 부족

---

### 4. JavaParser (Java 라이브러리, Python 바인딩 없음)

**개요**: Java로 작성된 Java 파서 (JDK 1-21 완벽 지원)

**GitHub**: https://github.com/javaparser/javaparser

#### 장점
- ✅ **JDK 1-21 완벽 지원**: 공식적으로 명시된 최신 버전 지원
- ✅ **강력한 기능**: Symbol resolution, type solving 등 고급 분석 지원
- ✅ **활발한 유지보수**: GitHub star 5.3k+, 활발한 커뮤니티

#### 단점
- ❌ **Python 바인딩 없음**: Java 프로세스 실행 또는 REST API 필요
- ❌ **복잡한 통합**: Python 프로젝트에 Java 의존성 추가
- ❌ **성능 오버헤드**: JVM 기동 시간 및 프로세스 간 통신 비용

#### 통합 방안 (참고용)
```python
# 방법 1: subprocess로 Java 실행
import subprocess
import json

result = subprocess.run(
    ['java', '-jar', 'javaparser-wrapper.jar', 'input.java'],
    capture_output=True
)
ast = json.loads(result.stdout)

# 방법 2: JPype로 JVM 임베딩
import jpype
jpype.startJVM()
JavaParser = jpype.JClass('com.github.javaparser.JavaParser')
```

---

## 📊 비교 분석

### 기능 비교표

| 항목 | javalang (현재) | **tree-sitter** | javalang17 | code-ast | JavaParser |
|------|----------------|-----------------|------------|----------|-----------|
| **JDK 8 지원** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **JDK 17 지원** | ❌ | ✅ (추정) | ✅ | ✅ | ✅ |
| **JDK 21 지원** | ❌ | ❓ (검증 필요) | ❌ | ✅ (추정) | ✅ |
| **Pure Python** | ✅ | ❌ (C 바인딩) | ✅ | ❌ (C 바인딩) | ❌ (Java) |
| **설치 용이성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **API 간결성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **성능** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **유지보수** | ❌ (중단) | ✅ (활발) | ⚠️ (불확실) | ⚠️ (작은 커뮤니티) | ✅ (활발) |
| **문서/예시** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **에러 복구** | ❌ | ✅ | ❌ | ✅ | ✅ |
| **점진적 파싱** | ❌ | ✅ | ❌ | ✅ | ❌ |

### Java 신규 문법 지원 확인 필요 항목

#### JDK 9-11 주요 기능
- ✅ 모듈 시스템 (`module-info.java`)
- ✅ `var` 키워드 (지역 변수 타입 추론)
- ✅ Private interface 메서드

#### JDK 12-16 주요 기능
- ✅ Switch 표현식 (Arrow syntax)
- ✅ Text blocks (멀티라인 문자열)
- ✅ Records (데이터 클래스)
- ✅ Sealed classes/interfaces

#### JDK 17-21 주요 기능
- ✅ Pattern matching for switch
- ✅ Record patterns
- ✅ Virtual threads (구문 변경 없음, 런타임 기능)
- ✅ String templates (Preview in JDK 21)

---

## 🛠️ 적용 방안

### 권장 방안: **Tree-sitter + py-tree-sitter** 채택

#### 선정 이유

1. **장기적 안정성**: 활발한 오픈소스 커뮤니티, 지속적인 업데이트
2. **확장성**: Java 외 다른 언어 분석 확장 가능 (Kotlin, Python, TypeScript 등)
3. **고성능**: C 구현으로 대규모 프로젝트 분석 시 성능 우수
4. **에러 처리**: 문법 오류가 있는 코드도 부분 파싱 가능 (실무 환경에서 유용)

#### 적용 전략

**Phase 1: PoC (Proof of Concept) - 2주**
1. tree-sitter-java 설치 및 환경 구성
2. JDK 8, 17, 21 샘플 코드 파싱 테스트
3. 주요 Java 문법 요소 추출 가능 여부 확인
   - Class/Interface/Enum 선언
   - Method 선언 (시그니처, 파라미터, 반환 타입)
   - Field 선언
   - 어노테이션
   - Method 호출 체인
   - Inner class
4. 성능 벤치마크 (javalang 대비 파싱 속도 비교)

**Phase 2: 어댑터 레이어 구현 - 3주**
1. `csa/parsers/java/tree_sitter_adapter.py` 생성
   - tree-sitter AST → javalang 호환 데이터 구조 변환
   - 기존 코드 최소 수정으로 마이그레이션 가능하도록 설계
2. 주요 변환 로직 구현
   ```python
   # 예시: tree-sitter 노드 → Class 객체 변환
   def convert_class_declaration(ts_node) -> Class:
       class_name = ts_node.child_by_field_name('name').text.decode('utf-8')
       modifiers = extract_modifiers(ts_node)
       annotations = extract_annotations(ts_node)
       # ...
       return Class(name=class_name, modifiers=modifiers, ...)
   ```
3. 단위 테스트 작성 (기존 javalang 테스트 케이스 재사용)

**Phase 3: 점진적 교체 - 4주**
1. `csa/services/java_analysis/project.py` 수정
   - `javalang.parse.parse()` → `tree_sitter_adapter.parse()` 교체
   - 기존 `javalang.tree.*` 타입 참조 → 어댑터 타입 참조
2. 전체 테스트 스위트 실행
   - `tests/unit/test_java_parser.py` 통과 확인
   - `tests/integration/` 엔드-투-엔드 테스트 통과 확인
3. 실제 프로젝트(car-center-devlab) 재분석
   - 분석 결과 비교 (기존 javalang vs tree-sitter)
   - 노드 개수, 관계 개수 일치 여부 확인

**Phase 4: 신규 문법 지원 확장 - 2주**
1. JDK 17+ 문법 요소 추가 지원
   - Record 클래스 분석
   - Sealed 클래스 분석
   - Pattern matching 구문 분석
2. 테스트 케이스 추가 (JDK 17, 21 샘플 프로젝트)
3. 문서 업데이트 (CLAUDE.md, README 등)

**Phase 5: 프로덕션 배포 - 1주**
1. 성능 모니터링
2. 로그 분석 (에러, 경고 확인)
3. 기존 javalang 제거 (`csa/vendor/javalang/` 삭제, `requirements.txt` 수정)

**총 예상 기간**: 12주 (약 3개월)

---

## 📝 마이그레이션 전략

### 1. 점진적 마이그레이션 (Adapter 패턴)

**목표**: 기존 코드 최소 수정, 위험 최소화

**설계**:
```
┌─────────────────────────────────────────┐
│  csa/services/java_analysis/project.py  │
│  (기존 코드, javalang API 사용)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  csa/parsers/java/adapter.py (신규)     │
│  - parse(source) → AST                  │
│  - AST 노드 클래스 (javalang 호환)     │
└──────────────┬──────────────────────────┘
               │
               ├──────────────┬─────────────┐
               ▼              ▼             ▼
         [javalang]    [tree-sitter]   [future parser]
         (Phase 3까지)  (Phase 3부터)   (확장 가능)
```

**장점**:
- ✅ 기존 코드 대부분 유지 가능
- ✅ 점진적 테스트 및 검증 가능
- ✅ 롤백 용이 (어댑터만 전환)

**단점**:
- ⚠️ 어댑터 레이어 개발 비용
- ⚠️ 변환 과정에서 성능 손실 가능

---

### 2. 병렬 운영 (Feature Flag)

**목표**: 신규 파서와 기존 파서를 동시 운영하며 검증

**설계**:
```python
# .env 파일
USE_TREE_SITTER=true  # false면 javalang 사용

# csa/parsers/java/parser_factory.py
def get_java_parser():
    if os.getenv('USE_TREE_SITTER') == 'true':
        return TreeSitterJavaParser()
    else:
        return JavalangParser()
```

**장점**:
- ✅ 프로덕션 환경에서 A/B 테스트 가능
- ✅ 문제 발생 시 즉시 전환 가능
- ✅ 점진적 트래픽 이동

**단점**:
- ⚠️ 두 파서를 동시에 유지보수
- ⚠️ 코드 복잡도 증가

---

### 3. 하위 호환성 유지

**원칙**:
1. 기존 Neo4j 스키마 유지 (노드/관계 타입 변경 없음)
2. 기존 CLI 명령어 호환성 유지
3. 기존 출력 포맷 유지 (시퀀스 다이어그램, CRUD 매트릭스 등)

**검증 방법**:
```bash
# Before 마이그레이션
python -m csa.cli.main analyze --java-object --project-name test
# → Neo4j 데이터 export

# After 마이그레이션
python -m csa.cli.main analyze --java-object --project-name test2
# → Neo4j 데이터 export

# 두 export 비교 (diff)
# → 노드 개수, 관계 개수, 속성 값 일치 여부 확인
```

---

## ⚠️ 위험 요소 및 대응 방안

### 위험 1: tree-sitter-java의 JDK 21 지원 불명확

**영향도**: 높음
**발생 가능성**: 중간

**대응**:
1. **PoC 단계에서 필수 검증**
   - JDK 21 신규 문법(String templates, pattern matching 등) 샘플 코드 작성
   - tree-sitter-java로 파싱 성공 여부 확인
   - 실패 시 대안 (javalang17 + tree-sitter 병행 사용) 검토
2. **업스트림 기여**
   - JDK 21 미지원 문법 발견 시 tree-sitter-java GitHub에 이슈/PR 제출
   - 커뮤니티 협업으로 지원 추가

### 위험 2: 어댑터 레이어 개발 복잡도

**영향도**: 중간
**발생 가능성**: 높음

**대응**:
1. **단계적 구현**
   - 핵심 AST 노드부터 순차 구현 (Class → Method → Field → Annotation)
   - 각 단계마다 단위 테스트 작성
2. **기존 테스트 재사용**
   - `tests/sample_java_project/` 샘플 코드로 회귀 테스트
   - javalang 결과와 tree-sitter 결과 비교 자동화

### 위험 3: 성능 저하

**영향도**: 중간
**발생 가능성**: 낮음

**대응**:
1. **벤치마크 기준 수립**
   - 현재 javalang 파싱 속도 측정 (car-center-devlab 기준)
   - tree-sitter 목표: 동일 또는 더 빠른 속도
2. **프로파일링**
   - 병목 지점 식별 (어댑터 변환 로직 vs 파싱 자체)
   - 최적화 (캐싱, 병렬 처리 등)

### 위험 4: 기존 분석 결과 불일치

**영향도**: 높음
**발생 가능성**: 중간

**대응**:
1. **Golden Dataset 생성**
   - 기존 javalang으로 분석한 Neo4j 데이터를 JSON으로 export
   - tree-sitter 마이그레이션 후 동일 데이터 생성 여부 비교
2. **차이점 허용 기준**
   - 중요한 차이 (Class 개수, Method 개수 불일치) → 수정 필수
   - 사소한 차이 (주석 위치, 공백 차이) → 허용 가능

### 위험 5: 외부 의존성 증가 (C 바이너리)

**영향도**: 낮음
**발생 가능성**: 낮음

**대응**:
1. **PyPI Wheel 사용**
   - tree-sitter-java는 사전 컴파일된 wheel 제공
   - Windows/Linux/macOS 모두 지원
2. **Docker 이미지 포함**
   - 프로젝트 Docker 이미지에 tree-sitter 포함
   - 일관된 실행 환경 보장

---

## ✅ 결론 및 권장사항

### 최종 권장 사항

**1차 선택: Tree-sitter + py-tree-sitter**

#### 권장 이유
1. ✅ **최신 Java 지원**: JDK 17까지 확인, JDK 21 검증 가능
2. ✅ **활발한 커뮤니티**: 지속적인 업데이트 및 버그 수정
3. ✅ **확장성**: Java 외 다른 언어 분석 확장 시 동일 프레임워크 사용
4. ✅ **성능**: C 구현으로 대규모 프로젝트 분석 시 우수
5. ✅ **에러 처리**: 실무 환경(문법 오류 포함 코드)에서 강건함

#### 전제 조건
- ⚠️ **PoC 단계에서 JDK 21 지원 반드시 검증**
- ⚠️ **어댑터 레이어 설계 및 단위 테스트 철저히 수행**
- ⚠️ **최소 3개월 마이그레이션 기간 확보**

---

**2차 선택: javalang17 (단기 대안)**

#### 적용 시나리오
- tree-sitter JDK 21 미지원 확인 시
- 빠른 마이그레이션 필요 시 (1-2주 내)
- JDK 17까지만 지원해도 무방한 경우

#### 장점
- ✅ **최소 코드 수정**: javalang API와 거의 동일
- ✅ **빠른 적용**: 1-2주 내 마이그레이션 가능
- ✅ **Pure Python**: 외부 의존성 없음

#### 단점
- ⚠️ **JDK 21 미지원**: 장기적으로 재마이그레이션 필요
- ⚠️ **유지보수 불확실**: 커뮤니티 작음

---

### 다음 단계 (Action Items)

#### 즉시 실행 (1주 내)
1. ✅ **본 문서 검토 및 승인**
2. ⬜ **PoC 환경 구성**
   - tree-sitter, tree-sitter-java 설치
   - JDK 8, 17, 21 샘플 코드 준비
3. ⬜ **JDK 21 지원 검증 테스트**
   - Record, Sealed class, Pattern matching 파싱 테스트
   - 결과 문서화

#### 단기 (2-4주)
4. ⬜ **tree-sitter 채택 여부 최종 결정**
   - JDK 21 지원 확인 시 → tree-sitter 진행
   - JDK 21 미지원 시 → javalang17 또는 대안 검토
5. ⬜ **마이그레이션 계획 상세화**
   - Phase별 작업 일정 수립
   - 담당자 배정, 리소스 확보

#### 중기 (1-3개월)
6. ⬜ **Phase 1-5 순차 실행**
   - 각 Phase마다 검증 및 승인 절차
7. ⬜ **프로덕션 배포**
   - 기존 javalang 제거
   - 문서 업데이트

---

### 참고 자료

- Tree-sitter 공식 문서: https://tree-sitter.github.io/tree-sitter/
- py-tree-sitter 문서: https://tree-sitter.github.io/py-tree-sitter/
- tree-sitter-java GitHub: https://github.com/tree-sitter/tree-sitter-java
- javalang GitHub: https://github.com/c2nes/javalang
- javalang17 GitHub: https://github.com/WorkOfArtiz/javalang17

---

**작업 완료 일시**: 2025-10-19
**검토 필요 사항**: JDK 21 지원 검증 테스트 결과 대기 중
**다음 단계**: PoC 환경 구성 및 검증 테스트 실행
