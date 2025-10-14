package com.carcare.domain.vehicle.repository;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import com.carcare.domain.vehicle.entity.Vehicle;
import com.carcare.domain.vehicle.dto.VehicleDto;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 차량 데이터 접근 레이어
 */
@Mapper
public interface VehicleRepository {
    
    /**
     * 차량 등록
     */
    int insertVehicle(Vehicle vehicle);
    
    /**
     * 차량 정보 수정
     */
    int updateVehicle(Vehicle vehicle);
    
    /**
     * 차량 삭제 (소프트 삭제 - is_active = false)
     */
    int deleteVehicle(@Param("id") Long id, @Param("userId") Long userId);
    
    /**
     * 차량 완전 삭제 (하드 삭제)
     */
    int deleteVehicleCompletely(@Param("id") Long id, @Param("userId") Long userId);
    
    /**
     * ID로 차량 조회
     */
    Optional<Vehicle> findById(@Param("id") Long id);
    
    /**
     * UUID로 차량 조회
     */
    Optional<Vehicle> findByUuid(@Param("vehicleUuid") UUID vehicleUuid);
    
    /**
     * 차량번호로 차량 조회
     */
    Optional<Vehicle> findByLicensePlate(@Param("licensePlate") String licensePlate);
    
    /**
     * 사용자 ID로 차량 목록 조회
     */
    List<Vehicle> findByUserId(@Param("userId") Long userId);
    
    /**
     * 사용자별 활성 차량 목록 조회
     */
    List<Vehicle> findActiveVehiclesByUserId(@Param("userId") Long userId);
    
    /**
     * 차량 검색 (페이징 포함)
     */
    List<Vehicle> searchVehicles(@Param("criteria") VehicleDto.SearchCriteria criteria, 
                                @Param("userId") Long userId);
    
    /**
     * 차량 검색 결과 총 개수
     */
    int countSearchResults(@Param("criteria") VehicleDto.SearchCriteria criteria, 
                          @Param("userId") Long userId);
    
    /**
     * 사용자별 차량 총 개수
     */
    int countByUserId(@Param("userId") Long userId);
    
    /**
     * 차량번호 중복 검사 (본인 차량 제외)
     */
    boolean existsByLicensePlateAndNotId(@Param("licensePlate") String licensePlate, 
                                        @Param("id") Long id);
    
    /**
     * 차량번호 중복 검사
     */
    boolean existsByLicensePlate(@Param("licensePlate") String licensePlate);
    
    /**
     * 사용자의 차량 소유권 확인
     */
    boolean isVehicleOwnedByUser(@Param("vehicleId") Long vehicleId, @Param("userId") Long userId);
    
    /**
     * 모든 차량 목록 조회 (관리자용)
     */
    List<Vehicle> findAllVehicles(@Param("criteria") VehicleDto.SearchCriteria criteria);
    
    /**
     * 전체 차량 수 조회 (관리자용)
     */
    int countAllVehicles(@Param("criteria") VehicleDto.SearchCriteria criteria);
} 