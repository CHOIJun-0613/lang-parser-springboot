package com.carcare.domain.vehicle.repository;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import com.carcare.domain.vehicle.entity.VehicleBrand;

import java.util.List;
import java.util.Optional;

/**
 * 차량 제조사 데이터 접근 레이어
 */
@Mapper
public interface VehicleBrandRepository {
    
    /**
     * 제조사 등록
     */
    int insertBrand(VehicleBrand brand);
    
    /**
     * 제조사 정보 수정
     */
    int updateBrand(VehicleBrand brand);
    
    /**
     * 제조사 삭제 (소프트 삭제)
     */
    int deleteBrand(@Param("id") Long id);
    
    /**
     * ID로 제조사 조회
     */
    Optional<VehicleBrand> findById(@Param("id") Long id);
    
    /**
     * 제조사 코드로 조회
     */
    Optional<VehicleBrand> findByCode(@Param("code") String code);
    
    /**
     * 제조사명으로 조회
     */
    Optional<VehicleBrand> findByName(@Param("name") String name);
    
    /**
     * 모든 활성 제조사 목록 조회 (정렬 순서별)
     */
    List<VehicleBrand> findAllActive();
    
    /**
     * 모든 제조사 목록 조회 (관리자용)
     */
    List<VehicleBrand> findAll();
    
    /**
     * 원산지별 제조사 목록 조회
     */
    List<VehicleBrand> findByCountry(@Param("country") String country);
    
    /**
     * 제조사명 검색 (부분 매칭)
     */
    List<VehicleBrand> searchByName(@Param("keyword") String keyword);
    
    /**
     * 제조사 코드 중복 검사
     */
    boolean existsByCode(@Param("code") String code);
    
    /**
     * 제조사명 중복 검사
     */
    boolean existsByName(@Param("name") String name);
    
    /**
     * 제조사 총 개수
     */
    int countAll();
    
    /**
     * 활성 제조사 개수
     */
    int countActive();
} 