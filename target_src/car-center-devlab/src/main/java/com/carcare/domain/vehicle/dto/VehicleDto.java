package com.carcare.domain.vehicle.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import com.carcare.domain.vehicle.entity.Vehicle.FuelType;

import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 차량 데이터 전송 객체
 */
public class VehicleDto {
    
    /**
     * 차량 등록/수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Request {
        
        @NotBlank(message = "제조사는 필수입니다")
        @Size(max = 100, message = "제조사는 100자 이하여야 합니다")
        private String make;
        
        @NotBlank(message = "모델명은 필수입니다")
        @Size(max = 100, message = "모델명은 100자 이하여야 합니다")
        private String model;
        
        @NotNull(message = "연식은 필수입니다")
        @Min(value = 1900, message = "연식은 1900년 이후여야 합니다")
        private Integer year;
        
        @NotBlank(message = "차량번호는 필수입니다")
        @Size(max = 20, message = "차량번호는 20자 이하여야 합니다")
        @Pattern(
            regexp = "^\\d{2,3}[가-힣]\\d{4}$|^[가-힣]\\d{2}[가-힣]\\d{4}$|^\\d{3}[가-힣]\\d{4}$",
            message = "올바른 차량번호 형식이 아닙니다"
        )
        private String licensePlate;
        
        @Size(max = 17, message = "차대번호는 17자 이하여야 합니다")
        private String vin;
        
        @Size(max = 50, message = "엔진타입은 50자 이하여야 합니다")
        private String engineType;
        
        private FuelType fuelType;
        
        @Min(value = 0, message = "주행거리는 0 이상이어야 합니다")
        private Integer mileage;
        
        @Size(max = 50, message = "색상은 50자 이하여야 합니다")
        private String color;
    }
    
    /**
     * 차량 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Response {
        private Long id;
        private UUID vehicleUuid;
        private Long userId;
        private String make;
        private String model;
        private Integer year;
        private String licensePlate;
        private String vin;
        private String engineType;
        private FuelType fuelType;
        private String fuelTypeDescription;
        private Integer mileage;
        private String color;
        private Boolean isActive;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        
        // 사용자 정보 (조인된 경우)
        private String ownerName;
        private String ownerEmail;
    }
    
    /**
     * 차량 목록 조회 응답 DTO (페이징 정보 포함)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ListResponse {
        private java.util.List<Response> vehicles;
        private int totalCount;
        private int currentPage;
        private int pageSize;
        private int totalPages;
        private boolean hasNext;
        private boolean hasPrevious;
    }
    
    /**
     * 차량 검색 조건 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchCriteria {
        private String keyword;          // 차량번호, 제조사, 모델 검색
        private String make;             // 제조사 필터
        private String model;            // 모델 필터
        private Integer yearFrom;        // 연식 범위 시작
        private Integer yearTo;          // 연식 범위 끝
        private FuelType fuelType;       // 연료 타입 필터
        private String color;            // 색상 필터
        private Boolean isActive;        // 활성 상태 필터
        private String sortBy;           // 정렬 기준 (createdAt, year, make, model)
        private String sortDirection;    // 정렬 방향 (ASC, DESC)
        private int page;                // 페이지 번호 (0부터 시작)
        private int size;                // 페이지 크기
        
        // 페이징을 위한 OFFSET 계산
        public int getOffset() {
            return page * size;
        }
    }
} 