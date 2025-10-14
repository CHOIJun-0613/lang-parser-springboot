package com.carcare.domain.service.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 정비소 관련 DTO 클래스들
 */
public class ServiceCenterDto {

    /**
     * 정비소 등록/수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Request {
        @NotBlank(message = "정비소명은 필수입니다")
        @Size(max = 100, message = "정비소명은 100자 이하여야 합니다")
        private String name;

        @Size(max = 500, message = "설명은 500자 이하여야 합니다")
        private String description;

        @NotBlank(message = "주소는 필수입니다")
        @Size(max = 200, message = "주소는 200자 이하여야 합니다")
        private String address;

        @Size(max = 100, message = "상세주소는 100자 이하여야 합니다")
        private String addressDetail;

        @NotBlank(message = "전화번호는 필수입니다")
        @Pattern(regexp = "^\\d{2,3}-\\d{3,4}-\\d{4}$", message = "올바른 전화번호 형식이 아닙니다")
        private String phoneNumber;

        @Email(message = "올바른 이메일 형식이 아닙니다")
        @Size(max = 100, message = "이메일은 100자 이하여야 합니다")
        private String email;

        @NotBlank(message = "사업자등록번호는 필수입니다")
        @Pattern(regexp = "^\\d{3}-\\d{2}-\\d{5}$", message = "올바른 사업자등록번호 형식이 아닙니다")
        private String businessNumber;

        @NotBlank(message = "대표자명은 필수입니다")
        @Size(max = 50, message = "대표자명은 50자 이하여야 합니다")
        private String ownerName;

        @DecimalMin(value = "33.0", message = "위도는 33.0 이상이어야 합니다")
        @DecimalMax(value = "38.0", message = "위도는 38.0 이하여야 합니다")
        private BigDecimal latitude;

        @DecimalMin(value = "125.0", message = "경도는 125.0 이상이어야 합니다")
        @DecimalMax(value = "132.0", message = "경도는 132.0 이하여야 합니다")
        private BigDecimal longitude;

        @Size(max = 200, message = "웹사이트 URL은 200자 이하여야 합니다")
        private String website;

        @Size(max = 1000, message = "특화서비스는 1000자 이하여야 합니다")
        private String specializedServices;

        @Size(max = 1000, message = "시설정보는 1000자 이하여야 합니다")
        private String facilities;

        private Boolean isActive;
        private Boolean isOperating;
    }

    /**
     * 정비소 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private String name;
        private String description;
        private String address;
        private String addressDetail;
        private String phoneNumber;
        private String email;
        private String businessNumber;
        private String ownerName;
        private BigDecimal latitude;
        private BigDecimal longitude;
        private String website;
        private String specializedServices;
        private String facilities;
        private BigDecimal averageRating;
        private Integer reviewCount;
        private Boolean isVerified;
        private Boolean isActive;
        private Boolean isOperating;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private String createdBy;
        private String updatedBy;
        
        // 검색 시 추가 정보
        private Double distance; // 검색자로부터의 거리 (km)
        private Boolean isRecommended; // 추천 정비소 여부
    }

    /**
     * 정비소 검색 조건 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchCriteria {
        private String keyword;              // 정비소명, 주소 검색
        private String name;                 // 정비소명 필터
        private String address;              // 주소 필터
        private String specializedService;   // 특화서비스 필터
        private BigDecimal minRating;        // 최소 평점
        private BigDecimal maxRating;        // 최대 평점
        private Boolean isVerified;          // 인증 상태 필터
        private Boolean isActive;            // 활성 상태 필터
        private Boolean isOperating;         // 운영 상태 필터
        private String businessNumber;       // 사업자등록번호로 검색
        private String ownerName;            // 대표자명으로 검색
        
        // 위치 기반 검색
        private BigDecimal latitude;         // 검색 중심 위도
        private BigDecimal longitude;        // 검색 중심 경도
        private Double radius;               // 검색 반경 (km)
        
        // 정렬 및 페이징
        private String sortBy;               // 정렬 기준 (name, rating, distance, createdAt)
        private String sortDirection;        // 정렬 방향 (ASC, DESC)
        private int page;                    // 페이지 번호 (0부터 시작)
        private int size;                    // 페이지 크기
        
        // 계산된 오프셋 (MyBatis용)
        public int getOffset() {
            return page * size;
        }
    }

    /**
     * 정비소 목록 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ListResponse {
        private List<Response> serviceCenters;
        private int currentPage;
        private int totalPages;
        private int pageSize;
        private long totalElements;
        private boolean hasNext;
        private boolean hasPrevious;
        
        // 검색 통계
        private Double averageDistance;      // 평균 거리
        private Integer verifiedCount;       // 인증된 정비소 수
        private Integer operatingCount;      // 운영 중인 정비소 수
    }

    /**
     * 위치 정보 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LocationRequest {
        @NotNull(message = "위도는 필수입니다")
        @DecimalMin(value = "33.0", message = "위도는 33.0 이상이어야 합니다")
        @DecimalMax(value = "38.0", message = "위도는 38.0 이하여야 합니다")
        private BigDecimal latitude;

        @NotNull(message = "경도는 필수입니다")
        @DecimalMin(value = "125.0", message = "경도는 125.0 이상이어야 합니다")
        @DecimalMax(value = "132.0", message = "경도는 132.0 이하여야 합니다")
        private BigDecimal longitude;

        @NotNull(message = "검색 반경은 필수입니다")
        @DecimalMin(value = "0.1", message = "검색 반경은 0.1km 이상이어야 합니다")
        @DecimalMax(value = "50.0", message = "검색 반경은 50km 이하여야 합니다")
        private Double radius;
    }

    /**
     * 정비소 통계 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Statistics {
        private Long totalServiceCenters;
        private Long activeServiceCenters;
        private Long verifiedServiceCenters;
        private Long operatingServiceCenters;
        private BigDecimal averageRating;
        private Long totalReviews;
        private Double averageReviewCount;
    }

    /**
     * 정비소 간단 정보 DTO (autocomplete용)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SimpleResponse {
        private Long id;
        private String name;
        private String address;
        private String phoneNumber;
        private BigDecimal averageRating;
        private Boolean isVerified;
        private Boolean isOperating;
        private Double distance;
    }
} 