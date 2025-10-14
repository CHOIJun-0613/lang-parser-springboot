package com.carcare.domain.user.entity;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 사용자 엔티티 (MyBatis용)
 */
@Data
public class User {
    
    private Long id;
    private String userUuid;
    private String email;
    private String password;
    private String name;
    private String phone;
    private String role = "CUSTOMER";
    private Boolean isActive = true;
    private Boolean emailVerified = false;
    private LocalDateTime lastLoginAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
} 