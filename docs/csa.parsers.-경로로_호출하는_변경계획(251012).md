## parser 호출부 전 환 계 획                                                                                                                                                                      

  - 1단계 – 파서 의존 정리 범위 확정                                                                                                                                 
      - csa/services/java_analysis/project.py, mybatis.py 등에서 직접 import 하는 래퍼 목록과 사용 패턴을 정리합니다.                                                
      - csa/services/analysis/db_pipeline.py(DDL 파서)와 연관 유닛 테스트(tests/test_java_parser_addon_r001.py 등)에서 기대하는 인터페이스를 확인해 둡니다.          
  - 2단계 – 호출부 개별 전환 계획                                                                                                                                    
      - DDL 파서: db_pipeline.py가 DBParser 래퍼 대신 csa.parsers.db.ddl_parser.DDLParser를 바로 사용하도록 인터페이스를 맞추고, 반환 구조 변환이 필요하면 helper 함 
        수로 감쌉니다.                                                                                                                                               
      - SQL 파서: mybatis.py 등에서 csa.parsers.sql.parser.SQLParser를 직접 import 하도록 변경하고, 기존 래퍼가 제공하던 추가 로직(없다면 그대로)도 확인합니다.      
      - Rule001 논리명 추출: project.py, mybatis.py에서 csa.parsers.java.logical_name 하위 클래스를 직접 사용하도록 수정하면서, 기존 래퍼가 제공하던 호환 레이어 없이        도 동작하는지 검증합니다.                                                                                                                                    
  - 3단계 – 테스트 정렬                                                                                                                                              
      - tests/test_java_parser_addon_r001.py 등 관련 테스트를 새 모듈 경로에 맞게 수정하고, 필요 시 fixture나 mock을 최신 인터페이스에 맞게 조정합니다.              
      - 추가로 파서 결과 타입이 바뀌는 구간이 있다면, 그에 맞춰 assertion을 업데이트합니다.                                                                          
  - 4단계 – 통합 검증 준비                                                                                                                                           
      - 위 단계별 전환 후 전체 pytest를 돌려 영향 범위를 확인하고, 차후 문서/백업 스크립트 갱신과 deprecated 안내를 이어서 진행할 수 있는 상태로 만듭니다.           
                                                                                                                                                                     
  이 정도 로드맵을 먼저 세워두고, 각 단계별로 작업량을 나눠 처리하면 비교적 안전하게 레거시 래퍼를 걷어낼 수 있을 것입니다.