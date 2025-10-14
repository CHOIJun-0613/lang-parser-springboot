package com.carcare.domain.vehicle.repository;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import com.carcare.domain.vehicle.entity.VehicleModel;

import java.util.List;
import java.util.Optional;

/**
 * 차량 모델 데이터 접근 레이어
 */
@Mapper
public interface VehicleModelRepository {
    
    /**
     * 모델 등록
     */
    int insertModel(VehicleModel model);
    
    /**
     * 모델 정보 수정
     */
    int updateModel(VehicleModel model);
    
    /**
     * 모델 삭제 (소프트 삭제)
     */
    int deleteModel(@Param("id") Long id);
    
    /**
     * ID로 모델 조회
     */
    Optional<VehicleModel> findById(@Param("id") Long id);
    
    /**
     * 모델 코드로 조회
     */
    Optional<VehicleModel> findByCode(@Param("code") String code);
    
    /**
     * 제조사별 모든 활성 모델 목록 조회
     */
    List<VehicleModel> findByBrandId(@Param("brandId") Long brandId);
    
    /**
     * 제조사별 활성 모델 목록 조회 (정렬 순서별)
     */
    List<VehicleModel> findActiveByBrandId(@Param("brandId") Long brandId);
    
    /**
     * 제조사별 차종 필터링된 모델 목록 조회
     */
    List<VehicleModel> findByBrandIdAndCategory(@Param("brandId") Long brandId, @Param("category") String category);
    
    /**
     * 제조사와 모델명으로 조회
     */
    Optional<VehicleModel> findByBrandIdAndName(@Param("brandId") Long brandId, @Param("name") String name);
    
    /**
     * 모든 활성 모델 목록 조회 (제조사 정보 포함)
     */
    List<VehicleModel> findAllActiveWithBrand();
    
    /**
     * 모든 모델 목록 조회 (관리자용, 제조사 정보 포함)
     */
    List<VehicleModel> findAllWithBrand();
    
    /**
     * 차종별 모델 목록 조회
     */
    List<VehicleModel> findByCategory(@Param("category") String category);
    
    /**
     * 연식 범위로 모델 검색
     */
    List<VehicleModel> findByYearRange(@Param("startYear") Integer startYear, @Param("endYear") Integer endYear);
    
    /**
     * 모델명 검색 (부분 매칭)
     */
    List<VehicleModel> searchByName(@Param("keyword") String keyword);
    
    /**
     * 제조사별 모델 개수
     */
    int countByBrandId(@Param("brandId") Long brandId);
    
    /**
     * 차종별 모델 개수
     */
    int countByCategory(@Param("category") String category);
    
    /**
     * 모델 코드 중복 검사
     */
    boolean existsByCode(@Param("code") String code);
    
    /**
     * 제조사별 모델명 중복 검사
     */
    boolean existsByBrandIdAndName(@Param("brandId") Long brandId, @Param("name") String name);
    
    /**
     * 모든 차종 목록 조회
     */
    List<String> findAllCategories();
    
    /**
     * 제조사의 생산 연도 범위 조회
     */
    List<Integer> findProductionYearsByBrandId(@Param("brandId") Long brandId);
} 