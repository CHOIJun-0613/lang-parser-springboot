package com.carcare.common.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * 헬스체크 및 기본 정보 API 컨트롤러
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Health", description = "헬스체크 및 시스템 정보 API")
public class HealthController {

    @Value("${app.name:Car Center Management System}")
    private String appName;

    @Value("${app.version:1.0.0}")
    private String appVersion;

    @Operation(
        summary = "시스템 상태 확인", 
        description = "애플리케이션의 기본 상태 정보를 반환합니다."
    )
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "성공적으로 상태 정보를 반환"),
        @ApiResponse(responseCode = "500", description = "서버 오류")
    })
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "UP");
        response.put("timestamp", LocalDateTime.now());
        response.put("application", appName);
        response.put("version", appVersion);
        response.put("message", "Car Center Management System is running successfully");
        
        return ResponseEntity.ok(response);
    }

    @Operation(
        summary = "API 정보 조회", 
        description = "API의 기본 정보와 사용 가능한 엔드포인트 정보를 반환합니다."
    )
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "성공적으로 API 정보를 반환")
    })
    @GetMapping("/info")
    public ResponseEntity<Map<String, Object>> info() {
        Map<String, Object> response = new HashMap<>();
        response.put("application", appName);
        response.put("version", appVersion);
        response.put("description", "자동차 정비소 관리 시스템 REST API");
        response.put("swagger-ui", "/swagger-ui.html");
        response.put("api-docs", "/api-docs");
        
        Map<String, String> endpoints = new HashMap<>();
        endpoints.put("사용자 관리", "/api/v1/users");
        endpoints.put("차량 관리", "/api/v1/vehicles");
        endpoints.put("정비 서비스", "/api/v1/services");
        endpoints.put("예약 관리", "/api/v1/reservations");
        endpoints.put("견적서 관리", "/api/v1/quotes");
        endpoints.put("결제 관리", "/api/v1/payments");
        endpoints.put("리뷰 관리", "/api/v1/reviews");
        endpoints.put("알림 관리", "/api/v1/notifications");
        
        response.put("available_endpoints", endpoints);
        response.put("timestamp", LocalDateTime.now());
        
        return ResponseEntity.ok(response);
    }
} 