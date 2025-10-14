package com.carcare.domain.notification.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.notification.service.SmsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * SMS 발송 컨트롤러 (테스트용)
 */
@RestController
@RequestMapping("/api/v1/sms")
@Tag(name = "SMS", description = "SMS 발송 API")
@RequiredArgsConstructor
public class SmsController {
    
    @Qualifier("notificationSmsService")
    private final SmsService smsService;
    
    /**
     * SMS 발송 테스트
     */
    @PostMapping("/send")
    @Operation(summary = "SMS 발송", description = "SMS를 발송합니다")
    public ResponseEntity<ApiResponse<SmsResultDto>> sendSms(@RequestBody SmsRequest request) {
        
        SmsService.SmsResult result = smsService.sendSms(request.getToNumber(), request.getMessage());
        
        SmsResultDto resultDto = SmsResultDto.builder()
                .success(result.isSuccess())
                .requestId(result.getRequestId())
                .sentAt(result.getSentAt())
                .toNumbers(result.getToNumbers())
                .message(result.getMessage())
                .errorMessage(result.getErrorMessage())
                .build();
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("SMS 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("SMS 발송 실패", resultDto));
        }
    }
    
    /**
     * 사용자별 SMS 발송
     */
    @PostMapping("/send-to-user")
    @Operation(summary = "사용자별 SMS 발송", description = "특정 사용자에게 SMS를 발송합니다")
    public ResponseEntity<ApiResponse<SmsResultDto>> sendSmsToUser(@RequestBody UserSmsRequest request) {
        
        SmsService.SmsResult result = smsService.sendSmsToUser(
                request.getUserId(), 
                request.getMessage(),
                request.getRelatedEntityType(),
                request.getRelatedEntityId()
        );
        
        SmsResultDto resultDto = SmsResultDto.builder()
                .success(result.isSuccess())
                .requestId(result.getRequestId())
                .sentAt(result.getSentAt())
                .toNumbers(result.getToNumbers())
                .message(result.getMessage())
                .errorMessage(result.getErrorMessage())
                .build();
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("SMS 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("SMS 발송 실패", resultDto));
        }
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SmsRequest {
        private String toNumber;
        private String message;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserSmsRequest {
        private Long userId;
        private String message;
        private String relatedEntityType;
        private Long relatedEntityId;
    }
    
    @Data
    @lombok.Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SmsResultDto {
        private boolean success;
        private String requestId;
        private java.time.LocalDateTime sentAt;
        private java.util.List<String> toNumbers;
        private String message;
        private String errorMessage;
    }
} 