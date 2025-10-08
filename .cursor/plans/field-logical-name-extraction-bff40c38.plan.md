<!-- bff40c38-27b4-4bd2-b705-f5f5040bca5a f9c834c3-de23-4868-b061-c55ac5d3a3c6 -->
# 추가 로그 레벨 통일

## 변경 대상 로그

### 1. DDL 분석 관련 로그

**파일**: `csa/cli/main.py`

**변경할 로그들**:

- `Also analyzing database objects from DDL scripts...` → `logger.info()` (2개 위치)
- `Processing DDL file 1...` → `logger.info()`
- `Processing DDL file 2...` → `logger.info()`
- `Added 2 database schemas.` → `logger.info()`
- `Analysis complete.` → `logger.info()`
- `Analysis complete (dry run).` → `logger.info()` (2개 위치)

**위치**:

- 라인 629: `Processing DDL file {i+1}...`
- 라인 721: `Analysis complete (dry run).`
- 라인 981: `Also analyzing database objects from DDL scripts...`
- 라인 1016: `Analysis complete (dry run).`
- 라인 1156: `Also analyzing database objects from DDL scripts...`
- 라인 1167: `Processing DDL file {i+1}...`
- 라인 1184: `Added {len(all_db_objects)} database schemas.`
- 라인 1190: `Analysis complete.`

### 2. 기타 확인 필요 로그

**파일**: `csa/services/java_parser.py`

**로그 위치** (라인 3154):

- `INFO: - Classes list length: {len(classes_list)}`
- 이미 `logger.info()`를 사용 중이므로 수정 불필요

## 수정 방법

**replace_all 사용**으로 모든 위치 일괄 변경:

1. `click.echo("\nAlso analyzing database objects from DDL scripts...")` → `logger.info("\nAlso analyzing database objects from DDL scripts...")`
2. `click.echo(f"Processing DDL file {i+1}...")` → `logger.info(f"Processing DDL file {i+1}...")`
3. `click.echo(f"Added {len(all_db_objects)} database schemas.")` → `logger.info(f"Added {len(all_db_objects)} database schemas.")`
4. `click.echo("Analysis complete.")` → `logger.info("Analysis complete.")`
5. `click.echo("Analysis complete (dry run).")` → `logger.info("Analysis complete (dry run).")`

## 결과

모든 주요 진행 상황 로그가 `logger.info()`로 통일되어:

- ✅ 일관된 로깅 패턴
- ✅ 로그 레벨 기반 필터링 가능
- ✅ 표준 로깅 프레임워크 활용

### To-dos

- [ ] DDL 분석 및 Analysis complete 로그를 logger.info()로 변경