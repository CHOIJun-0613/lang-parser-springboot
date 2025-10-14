package com.carcare.domain.service.repository;

import com.carcare.domain.service.entity.ServiceCenterOperatingHours;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 정비소 운영시간 Repository
 */
@Mapper
public interface ServiceCenterOperatingHoursRepository {

    /**
     * 운영시간 저장 (PostgreSQL)
     */
    Long save(ServiceCenterOperatingHours operatingHours);

    /**
     * 운영시간 저장 (H2)
     */
    Long saveH2(ServiceCenterOperatingHours operatingHours);

    /**
     * 서비스 센터 ID로 운영시간 조회
     */
    Optional<ServiceCenterOperatingHours> findByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId);

    /**
     * ID로 운영시간 조회
     */
    Optional<ServiceCenterOperatingHours> findById(@Param("id") Long id);

    /**
     * 운영시간 업데이트
     */
    int update(ServiceCenterOperatingHours operatingHours);

    /**
     * 운영 상태만 업데이트
     */
    int updateStatus(@Param("id") Long id, 
                    @Param("status") ServiceCenterOperatingHours.OperatingStatus status,
                    @Param("nextStatusChangeAt") LocalDateTime nextStatusChangeAt,
                    @Param("statusUpdatedAt") LocalDateTime statusUpdatedAt);

    /**
     * 서비스 센터 ID로 운영시간 존재 여부 확인
     */
    boolean existsByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId);

    /**
     * 모든 운영시간 조회 (스케줄러용)
     */
    List<ServiceCenterOperatingHours> findAll();

    /**
     * 상태 업데이트가 필요한 운영시간 조회
     */
    List<ServiceCenterOperatingHours> findNeedingStatusUpdate();

    /**
     * 서비스 센터 ID로 운영시간 삭제
     */
    int deleteByServiceCenterId(@Param("serviceCenterId") Long serviceCenterId);
} 