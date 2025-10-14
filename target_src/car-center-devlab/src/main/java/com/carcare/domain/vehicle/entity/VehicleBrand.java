package com.carcare.domain.vehicle.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import java.time.OffsetDateTime;

/**
 * 차량 제조사 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VehicleBrand {
    
    private Long id;
    
    @NotBlank(message = "제조사명은 필수입니다")
    @Size(max = 100, message = "제조사명은 100자 이하여야 합니다")
    private String name;
    
    @NotBlank(message = "제조사 영문명은 필수입니다")
    @Size(max = 100, message = "제조사 영문명은 100자 이하여야 합니다")
    private String nameEn;
    
    @Size(max = 10, message = "제조사 코드는 10자 이하여야 합니다")
    private String code;
    
    @NotBlank(message = "원산지는 필수입니다")
    @Size(max = 50, message = "원산지는 50자 이하여야 합니다")
    private String country;
    
    @Size(max = 500, message = "설명은 500자 이하여야 합니다")
    private String description;
    
    @Size(max = 255, message = "로고 URL은 255자 이하여야 합니다")
    private String logoUrl;
    
    private Boolean isActive;
    
    private Integer sortOrder;
    
    private OffsetDateTime createdAt;
    
    private OffsetDateTime updatedAt;
} 