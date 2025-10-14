package com.carcare.domain.vehicle.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import java.time.OffsetDateTime;

/**
 * 차량 모델 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VehicleModel {
    
    private Long id;
    
    @NotNull(message = "제조사 ID는 필수입니다")
    private Long brandId;
    
    @NotBlank(message = "모델명은 필수입니다")
    @Size(max = 100, message = "모델명은 100자 이하여야 합니다")
    private String name;
    
    @NotBlank(message = "모델 영문명은 필수입니다")
    @Size(max = 100, message = "모델 영문명은 100자 이하여야 합니다")
    private String nameEn;
    
    @Size(max = 20, message = "모델 코드는 20자 이하여야 합니다")
    private String code;
    
    @Size(max = 50, message = "차종은 50자 이하여야 합니다")
    private String category;
    
    @Min(value = 1900, message = "생산 시작년도는 1900년 이후여야 합니다")
    private Integer startYear;
    
    private Integer endYear;
    
    @Size(max = 500, message = "설명은 500자 이하여야 합니다")
    private String description;
    
    @Size(max = 255, message = "이미지 URL은 255자 이하여야 합니다")
    private String imageUrl;
    
    private Boolean isActive;
    
    private Integer sortOrder;
    
    private OffsetDateTime createdAt;
    
    private OffsetDateTime updatedAt;
    
    // 연관된 제조사 정보 (조인 시 사용)
    private VehicleBrand brand;
} 