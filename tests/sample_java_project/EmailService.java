package com.carcare.domain.notification.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.mail.MailException;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.io.File;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 이메일 발송 서비스
 */
@Slf4j
@Service
public class EmailService {
    
    private final JavaMailSender mailSender;
    private final NotificationService notificationService;
    
    public EmailService(@Autowired(required = false) JavaMailSender mailSender, NotificationService notificationService) {
        this.mailSender = mailSender;
        this.notificationService = notificationService;
    }
    
    @Value("${spring.mail.from:noreply@carcare.com}")
    private String fromEmail;
    
    @Value("${spring.mail.enabled:false}")
    private boolean emailEnabled;
    
    @Value("${app.name:Car Center}")
    private String appName;
    
    /**
     * 단순 텍스트 이메일 발송
     */
    @Retryable(value = {MailException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public EmailResult sendSimpleEmail(String to, String subject, String text) {
        return sendSimpleEmail(List.of(to), subject, text);
    }
    
    /**
     * 단순 텍스트 이메일 발송 (다중 수신자)
     */
    @Retryable(value = {MailException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public EmailResult sendSimpleEmail(List<String> toEmails, String subject, String text) {
        
        if (!emailEnabled || mailSender == null) {
            log.warn("이메일 발송이 비활성화되어 있습니다. (emailEnabled: {}, mailSender: {})", emailEnabled, mailSender != null ? "있음" : "없음");
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("이메일 발송이 비활성화되어 있습니다.")
                    .build();
        }
        
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(fromEmail);
            message.setTo(toEmails.toArray(new String[0]));
            message.setSubject(subject);
            message.setText(text);
            
            mailSender.send(message);
            
            log.info("이메일 발송 성공 - 수신자: {}, 제목: {}", toEmails, subject);
            
            return EmailResult.builder()
                    .success(true)
                    .sentAt(LocalDateTime.now())
                    .toEmails(toEmails)
                    .subject(subject)
                    .content(text)
                    .build();
            
        } catch (MailException e) {
            log.error("이메일 발송 실패 - 수신자: {}, 제목: {}", toEmails, subject, e);
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("이메일 발송 실패: " + e.getMessage())
                    .build();
        }
    }
    
    /**
     * HTML 이메일 발송
     */
    @Retryable(value = {MailException.class, MessagingException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public EmailResult sendHtmlEmail(String to, String subject, String htmlContent) {
        return sendHtmlEmail(List.of(to), subject, htmlContent, null);
    }
    
    /**
     * HTML 이메일 발송 (다중 수신자, 첨부파일 지원)
     */
    @Retryable(value = {MailException.class, MessagingException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public EmailResult sendHtmlEmail(List<String> toEmails, String subject, String htmlContent, List<String> attachmentPaths) {
        
        if (!emailEnabled || mailSender == null) {
            log.warn("이메일 발송이 비활성화되어 있습니다. (emailEnabled: {}, mailSender: {})", emailEnabled, mailSender != null ? "있음" : "없음");
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("이메일 발송이 비활성화되어 있습니다.")
                    .build();
        }
        
        try {
            MimeMessage mimeMessage = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(mimeMessage, true, "UTF-8");
            
            helper.setFrom(fromEmail);
            helper.setTo(toEmails.toArray(new String[0]));
            helper.setSubject(subject);
            helper.setText(htmlContent, true); // HTML 형식
            
            // 첨부파일 추가
            if (attachmentPaths != null && !attachmentPaths.isEmpty()) {
                for (String attachmentPath : attachmentPaths) {
                    File file = new File(attachmentPath);
                    if (file.exists()) {
                        FileSystemResource fileResource = new FileSystemResource(file);
                        helper.addAttachment(file.getName(), fileResource);
                        log.info("첨부파일 추가: {}", file.getName());
                    } else {
                        log.warn("첨부파일을 찾을 수 없습니다: {}", attachmentPath);
                    }
                }
            }
            
            mailSender.send(mimeMessage);
            
            log.info("HTML 이메일 발송 성공 - 수신자: {}, 제목: {}", toEmails, subject);
            
            return EmailResult.builder()
                    .success(true)
                    .sentAt(LocalDateTime.now())
                    .toEmails(toEmails)
                    .subject(subject)
                    .content(htmlContent)
                    .attachmentPaths(attachmentPaths)
                    .build();
            
        } catch (MailException | MessagingException e) {
            log.error("HTML 이메일 발송 실패 - 수신자: {}, 제목: {}", toEmails, subject, e);
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("HTML 이메일 발송 실패: " + e.getMessage())
                    .build();
        }
    }
    
    /**
     * 사용자별 이메일 발송 (알림 설정 확인)
     */
    public EmailResult sendEmailToUser(Long userId, String subject, String content, boolean isHtml) {
        
        // 사용자 알림 설정 확인
        if (!notificationService.shouldReceiveNotification(userId, 
                com.carcare.domain.notification.entity.Notification.NotificationType.SYSTEM_MAINTENANCE, "EMAIL")) {
            log.info("사용자 {}의 이메일 수신 설정이 비활성화되어 있습니다.", userId);
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("사용자 이메일 수신 설정이 비활성화되어 있습니다.")
                    .build();
        }
        
        // 사용자 이메일 주소 조회 (실제로는 UserService에서 조회해야 함)
        String userEmail = getUserEmail(userId);
        if (userEmail == null || userEmail.isEmpty()) {
            log.warn("사용자 {}의 이메일 주소가 없습니다.", userId);
            return EmailResult.builder()
                    .success(false)
                    .errorMessage("사용자 이메일 주소가 없습니다.")
                    .build();
        }
        
        if (isHtml) {
            return sendHtmlEmail(userEmail, subject, content);
        } else {
            return sendSimpleEmail(userEmail, subject, content);
        }
    }
    
    /**
     * 예약 확인 이메일 발송
     */
    public EmailResult sendReservationConfirmationEmail(Long userId, String reservationDetails) {
        String subject = String.format("[%s] 예약이 확인되었습니다", appName);
        String htmlContent = createReservationConfirmationHtml(reservationDetails);
        
        return sendEmailToUser(userId, subject, htmlContent, true);
    }
    
    /**
     * 견적서 준비 완료 이메일 발송
     */
    public EmailResult sendQuoteReadyEmail(Long userId, String quoteDetails) {
        String subject = String.format("[%s] 견적서가 준비되었습니다", appName);
        String htmlContent = createQuoteReadyHtml(quoteDetails);
        
        return sendEmailToUser(userId, subject, htmlContent, true);
    }
    
    /**
     * 서비스 완료 이메일 발송
     */
    public EmailResult sendServiceCompletedEmail(Long userId, String serviceDetails) {
        String subject = String.format("[%s] 정비 서비스가 완료되었습니다", appName);
        String htmlContent = createServiceCompletedHtml(serviceDetails);
        
        return sendEmailToUser(userId, subject, htmlContent, true);
    }
    
    /**
     * 예약 확인 HTML 템플릿 생성
     */
    private String createReservationConfirmationHtml(String reservationDetails) {
        return String.format("""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>예약 확인</title>
            </head>
            <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        🚗 예약이 확인되었습니다
                    </h2>
                    
                    <p>안녕하세요!</p>
                    <p>고객님의 예약이 성공적으로 확인되었습니다.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #495057;">📋 예약 정보</h3>
                        <pre style="white-space: pre-wrap; margin: 0;">%s</pre>
                    </div>
                    
                    <p>예약된 시간에 맞춰 방문해 주시기 바랍니다.</p>
                    
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #6c757d;">
                        이 메일은 발신전용입니다. 문의사항이 있으시면 고객센터로 연락해 주세요.
                    </p>
                </div>
            </body>
            </html>
            """, reservationDetails);
    }
    
    /**
     * 견적서 준비 완료 HTML 템플릿 생성
     */
    private String createQuoteReadyHtml(String quoteDetails) {
        return String.format("""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>견적서 준비 완료</title>
            </head>
            <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">
                        📄 견적서가 준비되었습니다
                    </h2>
                    
                    <p>안녕하세요!</p>
                    <p>요청하신 견적서가 준비되었습니다.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #495057;">💰 견적 정보</h3>
                        <pre style="white-space: pre-wrap; margin: 0;">%s</pre>
                    </div>
                    
                    <p>앱에서 자세한 견적 내용을 확인하실 수 있습니다.</p>
                    
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #6c757d;">
                        이 메일은 발신전용입니다. 문의사항이 있으시면 고객센터로 연락해 주세요.
                    </p>
                </div>
            </body>
            </html>
            """, quoteDetails);
    }
    
    /**
     * 서비스 완료 HTML 템플릿 생성
     */
    private String createServiceCompletedHtml(String serviceDetails) {
        return String.format("""
            <html>
            <head>
                <meta charset="UTF-8">
                <title>서비스 완료</title>
            </head>
            <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #27ae60; padding-bottom: 10px;">
                        ✅ 정비 서비스가 완료되었습니다
                    </h2>
                    
                    <p>안녕하세요!</p>
                    <p>고객님의 차량 정비 서비스가 성공적으로 완료되었습니다.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #495057;">🔧 서비스 내용</h3>
                        <pre style="white-space: pre-wrap; margin: 0;">%s</pre>
                    </div>
                    
                    <p>서비스 이용해 주셔서 감사합니다. 리뷰를 남겨주시면 더욱 도움이 됩니다.</p>
                    
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #6c757d;">
                        이 메일은 발신전용입니다. 문의사항이 있으시면 고객센터로 연락해 주세요.
                    </p>
                </div>
            </body>
            </html>
            """, serviceDetails);
    }
    
    /**
     * 사용자 이메일 주소 조회 (임시 구현)
     * TODO: UserService에서 실제 사용자 정보 조회하도록 수정
     */
    private String getUserEmail(Long userId) {
        // 임시로 하드코딩된 값 반환
        // 실제로는 UserService를 통해 사용자 정보를 조회해야 함
        log.warn("임시 구현: 사용자 {}의 이메일을 하드코딩된 값으로 반환합니다.", userId);
        return "user@example.com"; // 임시 값
    }
    
    /**
     * 이메일 발송 결과
     */
    public static class EmailResult {
        private boolean success;
        private LocalDateTime sentAt;
        private List<String> toEmails;
        private String subject;
        private String content;
        private List<String> attachmentPaths;
        private String errorMessage;
        
        public static EmailResultBuilder builder() {
            return new EmailResultBuilder();
        }
        
        // Getters
        public boolean isSuccess() { return success; }
        public LocalDateTime getSentAt() { return sentAt; }
        public List<String> getToEmails() { return toEmails; }
        public String getSubject() { return subject; }
        public String getContent() { return content; }
        public List<String> getAttachmentPaths() { return attachmentPaths; }
        public String getErrorMessage() { return errorMessage; }
        
        public static class EmailResultBuilder {
            private boolean success;
            private LocalDateTime sentAt;
            private List<String> toEmails;
            private String subject;
            private String content;
            private List<String> attachmentPaths;
            private String errorMessage;
            
            public EmailResultBuilder success(boolean success) {
                this.success = success;
                return this;
            }
            
            public EmailResultBuilder sentAt(LocalDateTime sentAt) {
                this.sentAt = sentAt;
                return this;
            }
            
            public EmailResultBuilder toEmails(List<String> toEmails) {
                this.toEmails = toEmails;
                return this;
            }
            
            public EmailResultBuilder subject(String subject) {
                this.subject = subject;
                return this;
            }
            
            public EmailResultBuilder content(String content) {
                this.content = content;
                return this;
            }
            
            public EmailResultBuilder attachmentPaths(List<String> attachmentPaths) {
                this.attachmentPaths = attachmentPaths;
                return this;
            }
            
            public EmailResultBuilder errorMessage(String errorMessage) {
                this.errorMessage = errorMessage;
                return this;
            }
            
            public EmailResult build() {
                EmailResult result = new EmailResult();
                result.success = this.success;
                result.sentAt = this.sentAt;
                result.toEmails = this.toEmails;
                result.subject = this.subject;
                result.content = this.content;
                result.attachmentPaths = this.attachmentPaths;
                result.errorMessage = this.errorMessage;
                return result;
            }
        }
    }
} 