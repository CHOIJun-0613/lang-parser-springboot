import re
from typing import List, Dict, Any, Optional, Set, Tuple
from csa.utils.logger import get_logger


class SQLParser:
    """SQL 파서 클래스 - MyBatis SQL 문을 분석하여 테이블과 컬럼 정보를 추출합니다."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def parse_sql_statement(self, sql_content: str, sql_type: str) -> Dict[str, Any]:
        """
        SQL 문을 분석하여 테이블과 컬럼 정보를 추출합니다.
        
        Args:
            sql_content: SQL 문 내용
            sql_type: SQL 타입 (SELECT, INSERT, UPDATE, DELETE)
            
        Returns:
            분석된 SQL 정보를 담은 딕셔너리
        """
        try:
            # SQL 내용 정리 (주석 제거, 공백 정규화)
            cleaned_sql = self._clean_sql(sql_content)
            
            if not cleaned_sql:
                return self._create_empty_result(sql_type)
            
            result = {
                'sql_type': sql_type,
                'original_sql': sql_content,
                'cleaned_sql': cleaned_sql,
                'tables': [],
                'columns': [],
                'joins': [],
                'where_conditions': [],
                'order_by_columns': [],
                'group_by_columns': [],
                'having_conditions': [],
                'subqueries': [],
                'parameters': [],
                'complexity_score': 0
            }
            
            # SQL 타입별 분석
            if sql_type.upper() == 'SELECT':
                result.update(self._analyze_select_sql(cleaned_sql))
            elif sql_type.upper() == 'INSERT':
                result.update(self._analyze_insert_sql(cleaned_sql))
            elif sql_type.upper() == 'UPDATE':
                result.update(self._analyze_update_sql(cleaned_sql))
            elif sql_type.upper() == 'DELETE':
                result.update(self._analyze_delete_sql(cleaned_sql))
            
            # 복잡도 점수 계산
            result['complexity_score'] = self._calculate_complexity_score(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"SQL 파싱 오류: {str(e)}")
            return self._create_empty_result(sql_type)
    
    def _clean_sql(self, sql_content: str) -> str:
        """SQL 내용을 정리합니다."""
        if not sql_content:
            return ""
        
        # 한 줄 주석 제거
        sql = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        
        # 블록 주석 제거
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # 연속된 공백을 하나로 변경
        sql = re.sub(r'\s+', ' ', sql)
        
        # 앞뒤 공백 제거
        sql = sql.strip()
        
        return sql
    
    def _create_empty_result(self, sql_type: str) -> Dict[str, Any]:
        """빈 결과를 생성합니다."""
        return {
            'sql_type': sql_type,
            'original_sql': '',
            'cleaned_sql': '',
            'tables': [],
            'columns': [],
            'joins': [],
            'where_conditions': [],
            'order_by_columns': [],
            'group_by_columns': [],
            'having_conditions': [],
            'subqueries': [],
            'parameters': [],
            'complexity_score': 0
        }
    
    def _analyze_select_sql(self, sql: str) -> Dict[str, Any]:
        """SELECT SQL을 분석합니다."""
        result = {}
        
        # FROM 절에서 테이블 추출
        tables = self._extract_tables_from_select(sql)
        result['tables'] = tables
        
        # SELECT 절에서 컬럼 추출
        columns = self._extract_columns_from_select(sql)
        result['columns'] = columns
        
        # JOIN 정보 추출
        joins = self._extract_joins(sql)
        result['joins'] = joins
        
        # WHERE 조건 추출
        where_conditions = self._extract_where_conditions(sql)
        result['where_conditions'] = where_conditions
        
        # ORDER BY 컬럼 추출
        order_by_columns = self._extract_order_by_columns(sql)
        result['order_by_columns'] = order_by_columns
        
        # GROUP BY 컬럼 추출
        group_by_columns = self._extract_group_by_columns(sql)
        result['group_by_columns'] = group_by_columns
        
        # HAVING 조건 추출
        having_conditions = self._extract_having_conditions(sql)
        result['having_conditions'] = having_conditions
        
        # 서브쿼리 추출
        subqueries = self._extract_subqueries(sql)
        result['subqueries'] = subqueries
        
        # 파라미터 추출
        parameters = self._extract_parameters(sql)
        result['parameters'] = parameters
        
        return result
    
    def _analyze_insert_sql(self, sql: str) -> Dict[str, Any]:
        """INSERT SQL을 분석합니다."""
        result = {}
        
        # INSERT INTO 테이블 추출
        tables = self._extract_tables_from_insert(sql)
        result['tables'] = tables
        
        # INSERT 컬럼 추출
        columns = self._extract_columns_from_insert(sql)
        result['columns'] = columns
        
        # VALUES 또는 SELECT 절에서 컬럼 추출
        values_columns = self._extract_values_columns(sql)
        result['values_columns'] = values_columns
        
        # 파라미터 추출
        parameters = self._extract_parameters(sql)
        result['parameters'] = parameters
        
        return result
    
    def _analyze_update_sql(self, sql: str) -> Dict[str, Any]:
        """UPDATE SQL을 분석합니다."""
        result = {}
        
        # UPDATE 테이블 추출
        tables = self._extract_tables_from_update(sql)
        result['tables'] = tables
        
        # SET 절에서 컬럼 추출
        columns = self._extract_columns_from_update(sql)
        result['columns'] = columns
        
        # WHERE 조건 추출
        where_conditions = self._extract_where_conditions(sql)
        result['where_conditions'] = where_conditions
        
        # 파라미터 추출
        parameters = self._extract_parameters(sql)
        result['parameters'] = parameters
        
        return result
    
    def _analyze_delete_sql(self, sql: str) -> Dict[str, Any]:
        """DELETE SQL을 분석합니다."""
        result = {}
        
        # DELETE FROM 테이블 추출
        tables = self._extract_tables_from_delete(sql)
        result['tables'] = tables
        
        # WHERE 조건 추출
        where_conditions = self._extract_where_conditions(sql)
        result['where_conditions'] = where_conditions
        
        # 파라미터 추출
        parameters = self._extract_parameters(sql)
        result['parameters'] = parameters
        
        return result
    
    def _extract_tables_from_select(self, sql: str) -> List[Dict[str, str]]:
        """SELECT 문에서 테이블을 추출합니다."""
        tables = []
        
        # FROM 절 패턴
        from_pattern = r'FROM\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?'
        from_matches = re.finditer(from_pattern, sql, re.IGNORECASE)
        
        for match in from_matches:
            table_name = match.group(1)
            alias = match.group(2) if match.group(2) else None
            tables.append({
                'name': table_name,
                'alias': alias,
                'type': 'main'
            })
        
        # JOIN 절에서 테이블 추출
        join_tables = self._extract_join_tables(sql)
        tables.extend(join_tables)
        
        return tables
    
    def _extract_tables_from_insert(self, sql: str) -> List[Dict[str, str]]:
        """INSERT 문에서 테이블을 추출합니다."""
        tables = []
        
        # INSERT INTO 테이블 패턴
        insert_pattern = r'INSERT\s+INTO\s+(\w+(?:\.\w+)?)'
        match = re.search(insert_pattern, sql, re.IGNORECASE)
        
        if match:
            table_name = match.group(1)
            tables.append({
                'name': table_name,
                'alias': None,
                'type': 'main'
            })
        
        return tables
    
    def _extract_tables_from_update(self, sql: str) -> List[Dict[str, str]]:
        """UPDATE 문에서 테이블을 추출합니다."""
        tables = []
        
        # UPDATE 테이블 패턴
        update_pattern = r'UPDATE\s+(\w+(?:\.\w+)?)'
        match = re.search(update_pattern, sql, re.IGNORECASE)
        
        if match:
            table_name = match.group(1)
            tables.append({
                'name': table_name,
                'alias': None,
                'type': 'main'
            })
        
        return tables
    
    def _extract_tables_from_delete(self, sql: str) -> List[Dict[str, str]]:
        """DELETE 문에서 테이블을 추출합니다."""
        tables = []
        
        # DELETE FROM 테이블 패턴
        delete_pattern = r'DELETE\s+FROM\s+(\w+(?:\.\w+)?)'
        match = re.search(delete_pattern, sql, re.IGNORECASE)
        
        if match:
            table_name = match.group(1)
            tables.append({
                'name': table_name,
                'alias': None,
                'type': 'main'
            })
        
        return tables
    
    def _extract_columns_from_select(self, sql: str) -> List[Dict[str, str]]:
        """SELECT 문에서 컬럼을 추출합니다."""
        columns = []
        
        # SELECT 절 패턴
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            select_clause = match.group(1)
            
            # * 패턴 처리
            if '*' in select_clause:
                columns.append({
                    'name': '*',
                    'alias': None,
                    'table': None,
                    'type': 'all'
                })
            else:
                # 개별 컬럼 추출
                column_matches = re.finditer(r'(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?', select_clause)
                for col_match in column_matches:
                    column_name = col_match.group(1)
                    alias = col_match.group(2) if col_match.group(2) else None
                    
                    # 테이블.컬럼 형태인지 확인
                    if '.' in column_name:
                        table, col = column_name.split('.', 1)
                        columns.append({
                            'name': col,
                            'alias': alias,
                            'table': table,
                            'type': 'column'
                        })
                    else:
                        columns.append({
                            'name': column_name,
                            'alias': alias,
                            'table': None,
                            'type': 'column'
                        })
        
        return columns
    
    def _extract_columns_from_insert(self, sql: str) -> List[Dict[str, str]]:
        """INSERT 문에서 컬럼을 추출합니다."""
        columns = []
        
        # INSERT INTO 테이블 (컬럼들) 패턴
        insert_pattern = r'INSERT\s+INTO\s+\w+\s*\(([^)]+)\)'
        match = re.search(insert_pattern, sql, re.IGNORECASE)
        
        if match:
            columns_clause = match.group(1)
            column_names = [col.strip() for col in columns_clause.split(',')]
            
            for col_name in column_names:
                columns.append({
                    'name': col_name,
                    'alias': None,
                    'table': None,
                    'type': 'column'
                })
        
        return columns
    
    def _extract_columns_from_update(self, sql: str) -> List[Dict[str, str]]:
        """UPDATE 문에서 컬럼을 추출합니다."""
        columns = []
        
        # SET 절 패턴
        set_pattern = r'SET\s+(.*?)(?:\s+WHERE|$)'
        match = re.search(set_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            set_clause = match.group(1)
            
            # 컬럼 = 값 패턴 추출
            column_matches = re.finditer(r'(\w+)\s*=', set_clause)
            for col_match in column_matches:
                column_name = col_match.group(1)
                columns.append({
                    'name': column_name,
                    'alias': None,
                    'table': None,
                    'type': 'column'
                })
        
        return columns
    
    def _extract_values_columns(self, sql: str) -> List[Dict[str, str]]:
        """INSERT VALUES 절에서 컬럼을 추출합니다."""
        columns = []
        
        # VALUES 절 패턴
        values_pattern = r'VALUES\s*\(([^)]+)\)'
        match = re.search(values_pattern, sql, re.IGNORECASE)
        
        if match:
            values_clause = match.group(1)
            # 파라미터나 값들을 추출
            values = [val.strip() for val in values_clause.split(',')]
            
            for i, value in enumerate(values):
                columns.append({
                    'name': f'value_{i+1}',
                    'alias': None,
                    'table': None,
                    'type': 'value',
                    'value': value
                })
        
        return columns
    
    def _extract_joins(self, sql: str) -> List[Dict[str, str]]:
        """JOIN 정보를 추출합니다."""
        joins = []
        
        # JOIN 패턴들
        join_patterns = [
            r'INNER\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?\s+ON\s+(.+)',
            r'LEFT\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?\s+ON\s+(.+)',
            r'RIGHT\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?\s+ON\s+(.+)',
            r'FULL\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?\s+ON\s+(.+)',
            r'JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?\s+ON\s+(.+)'
        ]
        
        for pattern in join_patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1)
                alias = match.group(2) if match.group(2) else None
                condition = match.group(3)
                
                join_type = 'INNER'
                if 'LEFT' in match.group(0).upper():
                    join_type = 'LEFT'
                elif 'RIGHT' in match.group(0).upper():
                    join_type = 'RIGHT'
                elif 'FULL' in match.group(0).upper():
                    join_type = 'FULL'
                
                joins.append({
                    'table': table_name,
                    'alias': alias,
                    'type': join_type,
                    'condition': condition
                })
        
        return joins
    
    def _extract_join_tables(self, sql: str) -> List[Dict[str, str]]:
        """JOIN 절에서 테이블을 추출합니다."""
        tables = []
        
        # JOIN 패턴들
        join_patterns = [
            r'INNER\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?',
            r'LEFT\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?',
            r'RIGHT\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?',
            r'FULL\s+JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?',
            r'JOIN\s+(\w+(?:\.\w+)?)\s*(?:AS\s+(\w+))?'
        ]
        
        for pattern in join_patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1)
                alias = match.group(2) if match.group(2) else None
                
                tables.append({
                    'name': table_name,
                    'alias': alias,
                    'type': 'join'
                })
        
        return tables
    
    def _extract_where_conditions(self, sql: str) -> List[Dict[str, str]]:
        """WHERE 조건을 추출합니다."""
        conditions = []
        
        # WHERE 절 패턴
        where_pattern = r'WHERE\s+(.+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+HAVING|$)'
        match = re.search(where_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            where_clause = match.group(1)
            
            # AND, OR로 분리
            condition_parts = re.split(r'\s+(?:AND|OR)\s+', where_clause, flags=re.IGNORECASE)
            
            for part in condition_parts:
                part = part.strip()
                if part:
                    conditions.append({
                        'condition': part,
                        'type': 'where'
                    })
        
        return conditions
    
    def _extract_order_by_columns(self, sql: str) -> List[Dict[str, str]]:
        """ORDER BY 컬럼을 추출합니다."""
        columns = []
        
        # ORDER BY 절 패턴
        order_by_pattern = r'ORDER\s+BY\s+(.+?)(?:\s+HAVING|$)'
        match = re.search(order_by_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            order_by_clause = match.group(1)
            
            # 컬럼들 분리
            column_parts = [col.strip() for col in order_by_clause.split(',')]
            
            for part in column_parts:
                # ASC, DESC 확인
                direction = 'ASC'
                if 'DESC' in part.upper():
                    direction = 'DESC'
                    part = part.replace('DESC', '').strip()
                elif 'ASC' in part.upper():
                    part = part.replace('ASC', '').strip()
                
                columns.append({
                    'name': part,
                    'direction': direction,
                    'type': 'order_by'
                })
        
        return columns
    
    def _extract_group_by_columns(self, sql: str) -> List[Dict[str, str]]:
        """GROUP BY 컬럼을 추출합니다."""
        columns = []
        
        # GROUP BY 절 패턴
        group_by_pattern = r'GROUP\s+BY\s+(.+?)(?:\s+HAVING|\s+ORDER\s+BY|$)'
        match = re.search(group_by_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            group_by_clause = match.group(1)
            
            # 컬럼들 분리
            column_parts = [col.strip() for col in group_by_clause.split(',')]
            
            for part in column_parts:
                columns.append({
                    'name': part,
                    'type': 'group_by'
                })
        
        return columns
    
    def _extract_having_conditions(self, sql: str) -> List[Dict[str, str]]:
        """HAVING 조건을 추출합니다."""
        conditions = []
        
        # HAVING 절 패턴
        having_pattern = r'HAVING\s+(.+?)(?:\s+ORDER\s+BY|$)'
        match = re.search(having_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            having_clause = match.group(1)
            
            # AND, OR로 분리
            condition_parts = re.split(r'\s+(?:AND|OR)\s+', having_clause, flags=re.IGNORECASE)
            
            for part in condition_parts:
                part = part.strip()
                if part:
                    conditions.append({
                        'condition': part,
                        'type': 'having'
                    })
        
        return conditions
    
    def _extract_subqueries(self, sql: str) -> List[Dict[str, str]]:
        """서브쿼리를 추출합니다."""
        subqueries = []
        
        # 서브쿼리 패턴 (괄호로 감싸진 SELECT 문)
        subquery_pattern = r'\(SELECT\s+.*?\)'
        matches = re.finditer(subquery_pattern, sql, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            subquery = match.group(0)
            subqueries.append({
                'sql': subquery,
                'type': 'subquery'
            })
        
        return subqueries
    
    def _extract_parameters(self, sql: str) -> List[Dict[str, str]]:
        """MyBatis 파라미터를 추출합니다."""
        parameters = []
        
        # MyBatis 파라미터 패턴들
        param_patterns = [
            r'#\{(\w+)\}',  # #{paramName}
            r'\$\{(\w+)\}',  # ${paramName}
            r'#\{(\w+)\.(\w+)\}',  # #{object.property}
            r'\$\{(\w+)\.(\w+)\}'  # ${object.property}
        ]
        
        for pattern in param_patterns:
            matches = re.finditer(pattern, sql)
            for match in matches:
                if len(match.groups()) == 1:
                    param_name = match.group(1)
                    parameters.append({
                        'name': param_name,
                        'type': 'simple',
                        'pattern': match.group(0)
                    })
                elif len(match.groups()) == 2:
                    object_name = match.group(1)
                    property_name = match.group(2)
                    parameters.append({
                        'name': f"{object_name}.{property_name}",
                        'object': object_name,
                        'property': property_name,
                        'type': 'nested',
                        'pattern': match.group(0)
                    })
        
        return parameters
    
    def _calculate_complexity_score(self, result: Dict[str, Any]) -> int:
        """SQL 복잡도 점수를 계산합니다."""
        score = 0
        
        # 기본 점수
        score += 1
        
        # 테이블 수
        score += len(result.get('tables', []))
        
        # JOIN 수
        score += len(result.get('joins', []))
        
        # 서브쿼리 수
        score += len(result.get('subqueries', []))
        
        # WHERE 조건 수
        score += len(result.get('where_conditions', []))
        
        # GROUP BY 컬럼 수
        score += len(result.get('group_by_columns', []))
        
        # ORDER BY 컬럼 수
        score += len(result.get('order_by_columns', []))
        
        # HAVING 조건 수
        score += len(result.get('having_conditions', []))
        
        return score
    
    def extract_table_column_mapping(self, sql_analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        SQL 분석 결과에서 테이블-컬럼 매핑을 추출합니다.
        
        Args:
            sql_analysis: SQL 분석 결과
            
        Returns:
            테이블별 컬럼 리스트를 담은 딕셔너리
        """
        table_column_mapping = {}
        
        # 테이블 정보 수집
        tables = sql_analysis.get('tables', [])
        for table in tables:
            table_name = table['name']
            if table_name not in table_column_mapping:
                table_column_mapping[table_name] = []
        
        # 컬럼 정보 수집
        columns = sql_analysis.get('columns', [])
        for column in columns:
            column_name = column['name']
            table_name = column.get('table')
            
            if table_name and table_name in table_column_mapping:
                table_column_mapping[table_name].append(column_name)
            elif not table_name:
                # 테이블 정보가 없는 경우, 모든 테이블에 추가
                for table in tables:
                    table_name = table['name']
                    if column_name not in table_column_mapping[table_name]:
                        table_column_mapping[table_name].append(column_name)
        
        return table_column_mapping
    
    def analyze_sql_complexity(self, sql_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        SQL 복잡도를 분석합니다.
        
        Args:
            sql_analysis: SQL 분석 결과
            
        Returns:
            복잡도 분석 결과
        """
        complexity = {
            'score': sql_analysis.get('complexity_score', 0),
            'level': 'simple',
            'characteristics': [],
            'recommendations': []
        }
        
        score = complexity['score']
        
        # 복잡도 레벨 결정
        if score <= 3:
            complexity['level'] = 'simple'
        elif score <= 7:
            complexity['level'] = 'medium'
        elif score <= 12:
            complexity['level'] = 'complex'
        else:
            complexity['level'] = 'very_complex'
        
        # 특징 분석
        if len(sql_analysis.get('joins', [])) > 3:
            complexity['characteristics'].append('multiple_joins')
        
        if len(sql_analysis.get('subqueries', [])) > 0:
            complexity['characteristics'].append('subqueries')
        
        if len(sql_analysis.get('where_conditions', [])) > 5:
            complexity['characteristics'].append('complex_where')
        
        if len(sql_analysis.get('group_by_columns', [])) > 0:
            complexity['characteristics'].append('grouping')
        
        if len(sql_analysis.get('order_by_columns', [])) > 3:
            complexity['characteristics'].append('complex_ordering')
        
        # 권장사항
        if 'multiple_joins' in complexity['characteristics']:
            complexity['recommendations'].append('인덱스 최적화 검토 필요')
        
        if 'subqueries' in complexity['characteristics']:
            complexity['recommendations'].append('JOIN으로 변경 검토 필요')
        
        if 'complex_where' in complexity['characteristics']:
            complexity['recommendations'].append('WHERE 조건 최적화 검토 필요')
        
        return complexity
