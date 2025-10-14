package com.carcare.domain.notification.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.notification.service.EmailService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 이메일 발송 컨트롤러 (테스트용)
 */
@RestController
@RequestMapping("/api/v1/email")
@Tag(name = "Email", description = "이메일 발송 API")
@RequiredArgsConstructor
public class EmailController {
    
    private final EmailService emailService;
    
    /**
     * 단순 텍스트 이메일 발송
     */
    @PostMapping("/send-text")
    @Operation(summary = "텍스트 이메일 발송", description = "단순 텍스트 이메일을 발송합니다")
    public ResponseEntity<ApiResponse<EmailResultDto>> sendTextEmail(@RequestBody EmailRequest request) {
        
        EmailService.EmailResult result = emailService.sendSimpleEmail(
                request.getToEmail(), 
                request.getSubject(), 
                request.getContent()
        );
        
        EmailResultDto resultDto = EmailResultDto.from(result);
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("이메일 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("이메일 발송 실패", resultDto));
        }
    }
    
    /**
     * HTML 이메일 발송
     */
    @PostMapping("/send-html")
    @Operation(summary = "HTML 이메일 발송", description = "HTML 형식의 이메일을 발송합니다")
    public ResponseEntity<ApiResponse<EmailResultDto>> sendHtmlEmail(@RequestBody HtmlEmailRequest request) {
        
        EmailService.EmailResult result = emailService.sendHtmlEmail(
                List.of(request.getToEmail()), 
                request.getSubject(), 
                request.getHtmlContent(),
                request.getAttachmentPaths()
        );
        
        EmailResultDto resultDto = EmailResultDto.from(result);
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("HTML 이메일 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("HTML 이메일 발송 실패", resultDto));
        }
    }
    
    /**
     * 사용자별 이메일 발송
     */
    @PostMapping("/send-to-user")
    @Operation(summary = "사용자별 이메일 발송", description = "특정 사용자에게 이메일을 발송합니다")
    public ResponseEntity<ApiResponse<EmailResultDto>> sendEmailToUser(@RequestBody UserEmailRequest request) {
        
        EmailService.EmailResult result = emailService.sendEmailToUser(
                request.getUserId(), 
                request.getSubject(),
                request.getContent(),
                request.isHtml()
        );
        
        EmailResultDto resultDto = EmailResultDto.from(result);
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("사용자 이메일 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("사용자 이메일 발송 실패", resultDto));
        }
    }
    
    /**
     * 예약 확인 이메일 발송
     */
    @PostMapping("/send-reservation-confirmation")
    @Operation(summary = "예약 확인 이메일 발송", description = "예약 확인 이메일을 발송합니다")
    public ResponseEntity<ApiResponse<EmailResultDto>> sendReservationConfirmationEmail(@RequestBody ReservationEmailRequest request) {
        
        EmailService.EmailResult result = emailService.sendReservationConfirmationEmail(
                request.getUserId(), 
                request.getReservationDetails()
        );
        
        EmailResultDto resultDto = EmailResultDto.from(result);
        
        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("예약 확인 이메일 발송 성공", resultDto));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("예약 확인 이메일 발송 실패", resultDto));
        }
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EmailRequest {
        private String toEmail;
        private String subject;
        private String content;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HtmlEmailRequest {
        private String toEmail;
        private String subject;
        private String htmlContent;
        private List<String> attachmentPaths;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserEmailRequest {
        private Long userId;
        private String subject;
        private String content;
        private boolean html;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReservationEmailRequest {
        private Long userId;
        private String reservationDetails;
    }
    
    @Data
    @lombok.Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class EmailResultDto {
        private boolean success;
        private java.time.LocalDateTime sentAt;
        private List<String> toEmails;
        private String subject;
        private String content;
        private List<String> attachmentPaths;
        private String errorMessage;
        
        public static EmailResultDto from(EmailService.EmailResult result) {
            return EmailResultDto.builder()
                    .success(result.isSuccess())
                    .sentAt(result.getSentAt())
                    .toEmails(result.getToEmails())
                    .subject(result.getSubject())
                    .content(result.getContent())
                    .attachmentPaths(result.getAttachmentPaths())
                    .errorMessage(result.getErrorMessage())
                    .build();
        }
    }
} 