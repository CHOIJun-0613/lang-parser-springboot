package com.carcare.domain.vehicle.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 차량 엔티티
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Vehicle {
    
    private Long id;
    
    private UUID vehicleUuid;
    
    @NotNull(message = "사용자 ID는 필수입니다")
    private Long userId;
    
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
    
    private Boolean isActive;
    
    private LocalDateTime createdAt;
    
    private LocalDateTime updatedAt;
    
    /**
     * 연료 타입 열거형
     */
    public enum FuelType {
        GASOLINE("가솔린"),
        DIESEL("디젤"),
        HYBRID("하이브리드"),
        ELECTRIC("전기"),
        LPG("LPG"),
        CNG("CNG");
        
        private final String description;
        
        FuelType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
} 