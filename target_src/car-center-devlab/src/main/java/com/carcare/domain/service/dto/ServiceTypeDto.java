package com.carcare.domain.service.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 서비스 타입 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceTypeDto {
    
    private Long id;
    
    private String name;
    
    private String description;
    
    private String category;
    
    private Integer estimatedDuration;  // 예상 소요시간(분)
    
    private BigDecimal basePrice;       // 기본 가격
    
    private Boolean isActive;
    
} 