package com.carcare.domain.service.repository;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import com.carcare.domain.service.entity.ServiceCenter;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

/**
 * 정비소 데이터 접근 레이어
 */
@Mapper
public interface ServiceCenterRepository {
    
    /**
     * 정비소 등록
     */
    int insertServiceCenter(ServiceCenter serviceCenter);
    
    /**
     * 정비소 정보 수정
     */
    int updateServiceCenter(ServiceCenter serviceCenter);
    
    /**
     * 정비소 삭제 (소프트 삭제)
     */
    int deleteServiceCenter(@Param("id") Long id, @Param("updatedBy") Long updatedBy);
    
    /**
     * 정비소 완전 삭제 (하드 삭제)
     */
    int deleteServiceCenterCompletely(@Param("id") Long id);
    
    /**
     * ID로 정비소 조회
     */
    Optional<ServiceCenter> findById(@Param("id") Long id);
    
    /**
     * 사업자 등록번호로 정비소 조회
     */
    Optional<ServiceCenter> findByBusinessNumber(@Param("businessNumber") String businessNumber);
    
    /**
     * 정비소명으로 검색
     */
    List<ServiceCenter> findByNameContaining(@Param("keyword") String keyword);
    
    /**
     * 모든 활성 정비소 목록 조회
     */
    List<ServiceCenter> findAllActive();
    
    /**
     * 모든 정비소 목록 조회 (관리자용)
     */
    List<ServiceCenter> findAll();
    
    /**
     * 지역별 정비소 검색
     */
    List<ServiceCenter> findByAddress(@Param("keyword") String keyword);
    
    /**
     * 위치 기반 정비소 검색 (반경 내)
     */
    List<ServiceCenter> findByLocation(
        @Param("latitude") BigDecimal latitude,
        @Param("longitude") BigDecimal longitude,
        @Param("radiusKm") Double radiusKm
    );
    
    /**
     * 평점 범위별 정비소 검색
     */
    List<ServiceCenter> findByRatingRange(
        @Param("minRating") BigDecimal minRating,
        @Param("maxRating") BigDecimal maxRating
    );
    
    /**
     * 복합 조건 정비소 검색 (페이징 포함)
     */
    List<ServiceCenter> searchServiceCenters(@Param("criteria") SearchCriteria criteria);
    
    /**
     * 검색 결과 총 개수
     */
    int countSearchResults(@Param("criteria") SearchCriteria criteria);
    
    /**
     * 인증 상태별 정비소 조회
     */
    List<ServiceCenter> findByVerificationStatus(@Param("status") ServiceCenter.VerificationStatus status);
    
    /**
     * 현재 운영 중인 정비소 조회
     */
    List<ServiceCenter> findCurrentlyOperating();
    
    /**
     * 정비소 평점 업데이트
     */
    int updateRating(@Param("id") Long id, @Param("averageRating") BigDecimal averageRating, @Param("reviewCount") Integer reviewCount);
    
    /**
     * 정비소 상태 업데이트 (활성/비활성)
     */
    int updateStatus(@Param("id") Long id, @Param("isActive") Boolean isActive, @Param("updatedBy") Long updatedBy);
    
    /**
     * 정비소 운영 상태 업데이트
     */
    int updateOperatingStatus(@Param("id") Long id, @Param("isOperating") Boolean isOperating, @Param("updatedBy") Long updatedBy);
    
    /**
     * 정비소 인증 상태 업데이트
     */
    int updateVerificationStatus(@Param("id") Long id, @Param("isVerified") Boolean isVerified, @Param("updatedBy") Long updatedBy);
    
    /**
     * 사업자 등록번호 중복 검사
     */
    boolean existsByBusinessNumber(@Param("businessNumber") String businessNumber);
    
    /**
     * 사업자 등록번호 중복 검사 (본인 제외)
     */
    boolean existsByBusinessNumberAndNotId(
        @Param("businessNumber") String businessNumber, 
        @Param("id") Long id
    );
    
    /**
     * 전화번호 중복 검사
     */
    boolean existsByPhoneNumber(@Param("phoneNumber") String phoneNumber);
    
    /**
     * 총 정비소 수 조회
     */
    int countAll();
    
    /**
     * 활성 정비소 수 조회
     */
    int countActive();
    
    /**
     * 정비소 통계 조회
     */
    com.carcare.domain.service.dto.ServiceCenterDto.Statistics getStatistics();
    
    /**
     * 자동완성용 정비소 검색
     */
    List<ServiceCenter> findForAutocomplete(@Param("keyword") String keyword, @Param("limit") int limit);
    
    /**
     * 정비소 검색 조건 DTO
     */
    public static class SearchCriteria {
        private String keyword;              // 검색 키워드
        private String address;              // 주소 검색
        private BigDecimal latitude;         // 위도
        private BigDecimal longitude;        // 경도
        private Double radiusKm;             // 검색 반경 (km)
        private BigDecimal minRating;        // 최소 평점
        private BigDecimal maxRating;        // 최대 평점
        private ServiceCenter.VerificationStatus verificationStatus; // 인증 상태
        private Boolean isActive;            // 활성 상태
        private Boolean isOperating;         // 운영 상태
        private String sortBy;               // 정렬 기준 (rating, distance, name, createdAt)
        private String sortDirection;        // 정렬 방향 (ASC, DESC)
        private int page;                    // 페이지 번호 (0부터 시작)
        private int size;                    // 페이지 크기
        
        // Getters and Setters
        public String getKeyword() { return keyword; }
        public void setKeyword(String keyword) { this.keyword = keyword; }
        
        public String getAddress() { return address; }
        public void setAddress(String address) { this.address = address; }
        
        public BigDecimal getLatitude() { return latitude; }
        public void setLatitude(BigDecimal latitude) { this.latitude = latitude; }
        
        public BigDecimal getLongitude() { return longitude; }
        public void setLongitude(BigDecimal longitude) { this.longitude = longitude; }
        
        public Double getRadiusKm() { return radiusKm; }
        public void setRadiusKm(Double radiusKm) { this.radiusKm = radiusKm; }
        
        public BigDecimal getMinRating() { return minRating; }
        public void setMinRating(BigDecimal minRating) { this.minRating = minRating; }
        
        public BigDecimal getMaxRating() { return maxRating; }
        public void setMaxRating(BigDecimal maxRating) { this.maxRating = maxRating; }
        
        public ServiceCenter.VerificationStatus getVerificationStatus() { return verificationStatus; }
        public void setVerificationStatus(ServiceCenter.VerificationStatus verificationStatus) { this.verificationStatus = verificationStatus; }
        
        public Boolean getIsActive() { return isActive; }
        public void setIsActive(Boolean isActive) { this.isActive = isActive; }
        
        public Boolean getIsOperating() { return isOperating; }
        public void setIsOperating(Boolean isOperating) { this.isOperating = isOperating; }
        
        public String getSortBy() { return sortBy; }
        public void setSortBy(String sortBy) { this.sortBy = sortBy; }
        
        public String getSortDirection() { return sortDirection; }
        public void setSortDirection(String sortDirection) { this.sortDirection = sortDirection; }
        
        public int getPage() { return page; }
        public void setPage(int page) { this.page = page; }
        
        public int getSize() { return size; }
        public void setSize(int size) { this.size = size; }
        
        // 페이징을 위한 OFFSET 계산
        public int getOffset() {
            return page * size;
        }
    }
} 