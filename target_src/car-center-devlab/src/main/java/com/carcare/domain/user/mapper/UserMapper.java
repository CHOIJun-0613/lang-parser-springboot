package com.carcare.domain.user.mapper;

import com.carcare.domain.user.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 사용자 데이터 접근 매퍼
 */
@Mapper
public interface UserMapper {

    /**
     * 사용자 생성
     */
    int insertUser(User user);

    /**
     * 사용자 정보 수정
     */
    int updateUser(User user);

    /**
     * 사용자 삭제 (논리 삭제)
     */
    int deleteUser(@Param("id") Long id);

    /**
     * ID로 사용자 조회
     */
    Optional<User> findById(@Param("id") Long id);

    /**
     * 이메일로 사용자 조회
     */
    Optional<User> findByEmail(@Param("email") String email);

    /**
     * 사용자 UUID로 사용자 조회
     */
    Optional<User> findByUserUuid(@Param("userUuid") String userUuid);

    /**
     * 전화번호로 사용자 조회
     */
    Optional<User> findByPhone(@Param("phone") String phone);

    /**
     * 이메일 존재 여부 확인
     */
    boolean existsByEmail(@Param("email") String email);

    /**
     * 전화번호 존재 여부 확인
     */
    boolean existsByPhone(@Param("phone") String phone);

    /**
     * 활성 사용자만 조회
     */
    List<User> findActiveUsers();

    /**
     * 역할별 사용자 조회
     */
    List<User> findByRole(@Param("role") String role);

    /**
     * 페이징을 통한 사용자 목록 조회
     */
    List<User> findUsersWithPaging(@Param("offset") int offset, @Param("limit") int limit);

    /**
     * 전체 사용자 수 조회
     */
    long countUsers();

    /**
     * 특정 조건의 사용자 수 조회
     */
    long countUsersByCondition(@Param("isActive") Boolean isActive, @Param("role") String role);

    /**
     * 사용자 검색 (이름, 이메일로)
     */
    List<User> searchUsers(@Param("keyword") String keyword, @Param("offset") int offset, @Param("limit") int limit);

    /**
     * 최근 가입한 사용자들 조회
     */
    List<User> findRecentUsers(@Param("days") int days, @Param("limit") int limit);
} 