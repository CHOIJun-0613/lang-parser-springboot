"""
AI Analyzer 테스트 코드

이 테스트는 AI 분석 기능이 올바르게 작동하는지 검증합니다.
실제 LLM 호출이 필요하므로, .env 파일에 AI 설정이 되어 있어야 합니다.
"""

import os
import sys
import io

# UTF-8 출력 설정 (Windows 콘솔 인코딩 문제 해결)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from csa.aiwork.ai_analyzer import AIAnalyzer, get_ai_analyzer
from csa.aiwork.ai_config import ai_config
import logging

# DEBUG 로그 레벨 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')


def test_ai_config():
    """AI 설정이 올바르게 로드되는지 테스트"""
    print("=" * 80)
    print("1. AI 설정 테스트")
    print("=" * 80)

    print(f"AI 사용 여부: {ai_config.ai_use_analysis}")
    print(f"AI Provider: {ai_config.ai_provider}")
    print(f"현재 모델명: {ai_config.get_current_model_name()}")
    print(f"Provider 사용 가능 여부: {ai_config.is_current_provider_available()}")
    print()


def test_ai_analyzer_initialization():
    """AI Analyzer가 올바르게 초기화되는지 테스트"""
    print("=" * 80)
    print("2. AI Analyzer 초기화 테스트")
    print("=" * 80)

    analyzer = get_ai_analyzer()
    print(f"Analyzer 사용 가능 여부: {analyzer.is_available()}")

    if analyzer.is_available():
        print("✅ AI Analyzer 초기화 성공")
    else:
        print("⚠️  AI Analyzer가 비활성화되어 있습니다.")
        print("   .env 파일에서 AI_USE_ANALYSIS=true로 설정하고 API 키를 입력하세요.")
    print()


def test_analyze_class():
    """Class 분석 테스트"""
    print("=" * 80)
    print("3. Class 분석 테스트")
    print("=" * 80)

    analyzer = get_ai_analyzer()

    if not analyzer.is_available():
        print("⚠️  AI Analyzer가 비활성화되어 있어 테스트를 건너뜁니다.")
        print()
        return

    # 테스트용 Java 클래스 소스 코드
    sample_class = """
package com.example.demo.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 사용자 관리 서비스
 */
@Service
@Transactional
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * 사용자 ID로 사용자 정보를 조회합니다.
     */
    public User findById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException("User not found: " + id));
    }

    /**
     * 새로운 사용자를 생성합니다.
     */
    public User createUser(UserCreateRequest request) {
        User user = new User(request.getName(), request.getEmail());
        return userRepository.save(user);
    }
}
"""

    print("분석 중...")
    result = analyzer.analyze_class(sample_class, "UserService")

    if result:
        print("✅ Class 분석 성공!")
        print("\n--- AI 분석 결과 ---")
        print(result)
        print("-------------------\n")
    else:
        print("❌ Class 분석 실패")
    print()


def test_analyze_method():
    """Method 분석 테스트"""
    print("=" * 80)
    print("4. Method 분석 테스트")
    print("=" * 80)

    analyzer = get_ai_analyzer()

    if not analyzer.is_available():
        print("⚠️  AI Analyzer가 비활성화되어 있어 테스트를 건너뜁니다.")
        print()
        return

    # 테스트용 Java 메서드 소스 코드
    sample_method = """
    /**
     * 사용자 ID로 사용자 정보를 조회합니다.
     *
     * @param id 사용자 ID
     * @return 사용자 정보
     * @throws UserNotFoundException 사용자를 찾을 수 없는 경우
     */
    public User findById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException("User not found: " + id));
    }
"""

    print("분석 중...")
    result = analyzer.analyze_method(sample_method, "findById")

    if result:
        print("✅ Method 분석 성공!")
        print("\n--- AI 분석 결과 ---")
        print(result)
        print("-------------------\n")
    else:
        print("❌ Method 분석 실패")
    print()


def test_analyze_sql():
    """SQL 분석 테스트"""
    print("=" * 80)
    print("5. SQL 분석 테스트")
    print("=" * 80)

    analyzer = get_ai_analyzer()

    if not analyzer.is_available():
        print("⚠️  AI Analyzer가 비활성화되어 있어 테스트를 건너뜁니다.")
        print()
        return

    # 테스트용 SQL 문
    sample_sql = """
SELECT
    u.user_id,
    u.username,
    u.email,
    u.created_at,
    COUNT(o.order_id) as order_count,
    SUM(o.total_amount) as total_spent
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE u.status = 'ACTIVE'
    AND u.created_at >= #{startDate}
    AND u.created_at <= #{endDate}
GROUP BY u.user_id, u.username, u.email, u.created_at
HAVING COUNT(o.order_id) > 0
ORDER BY total_spent DESC
LIMIT 100
"""

    print("분석 중...")
    result = analyzer.analyze_sql(sample_sql, "selectActiveUsersWithOrders")

    if result:
        print("✅ SQL 분석 성공!")
        print("\n--- AI 분석 결과 ---")
        print(result)
        print("-------------------\n")
    else:
        print("❌ SQL 분석 실패")
    print()


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 80)
    print("AI Analyzer 테스트 시작")
    print("=" * 80 + "\n")

    try:
        # 1. AI 설정 테스트
        test_ai_config()

        # 2. AI Analyzer 초기화 테스트
        test_ai_analyzer_initialization()

        # 3. Class 분석 테스트
        test_analyze_class()

        # 4. Method 분석 테스트
        test_analyze_method()

        # 5. SQL 분석 테스트
        test_analyze_sql()

        print("=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
