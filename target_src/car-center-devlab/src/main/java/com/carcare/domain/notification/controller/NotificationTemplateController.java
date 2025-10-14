package com.carcare.domain.notification.controller;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.domain.notification.entity.NotificationTemplate;
import com.carcare.domain.notification.service.NotificationTemplateService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 알림 템플릿 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/notification-templates")
@Tag(name = "Notification Template", description = "알림 템플릿 관리 API")
@RequiredArgsConstructor
public class NotificationTemplateController {
    
    private final NotificationTemplateService templateService;
    
    /**
     * 템플릿 목록 조회
     */
    @GetMapping
    @Operation(summary = "템플릿 목록 조회", description = "알림 템플릿 목록을 조회합니다")
    public ResponseEntity<ApiResponse<List<NotificationTemplate>>> getTemplates(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "false") boolean activeOnly) {
        
        List<NotificationTemplate> templates;
        if (activeOnly) {
            templates = templateService.getActiveTemplates(page, size);
        } else {
            templates = templateService.getTemplates(page, size);
        }
        
        return ResponseEntity.ok(ResponseUtils.success("템플릿 목록 조회 성공", templates));
    }
    
    /**
     * 템플릿 검색
     */
    @GetMapping("/search")
    @Operation(summary = "템플릿 검색", description = "조건에 따라 템플릿을 검색합니다")
    public ResponseEntity<ApiResponse<NotificationTemplateService.TemplateSearchResult>> searchTemplates(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String channel,
            @RequestParam(required = false) String language,
            @RequestParam(required = false) Boolean isActive,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        
        NotificationTemplateService.TemplateSearchResult result = templateService.searchTemplates(
                keyword, type, channel, language, isActive, page, size);
        
        return ResponseEntity.ok(ResponseUtils.success("템플릿 검색 성공", result));
    }
    
    /**
     * 템플릿 상세 조회
     */
    @GetMapping("/{templateId}")
    @Operation(summary = "템플릿 상세 조회", description = "특정 템플릿의 상세 정보를 조회합니다")
    public ResponseEntity<ApiResponse<NotificationTemplate>> getTemplate(@PathVariable Long templateId) {
        
        Optional<NotificationTemplate> template = templateService.getTemplateById(templateId);
        
        if (template.isPresent()) {
            return ResponseEntity.ok(ResponseUtils.success("템플릿 조회 성공", template.get()));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("템플릿을 찾을 수 없습니다", null));
        }
    }
    
    /**
     * 활성 템플릿 조회
     */
    @GetMapping("/active")
    @Operation(summary = "활성 템플릿 조회", description = "특정 타입/채널/언어의 활성 템플릿을 조회합니다")
    public ResponseEntity<ApiResponse<NotificationTemplate>> getActiveTemplate(
            @RequestParam String type,
            @RequestParam String channel,
            @RequestParam(defaultValue = "ko") String language) {
        
        Optional<NotificationTemplate> template = templateService.getActiveTemplate(type, channel, language);
        
        if (template.isPresent()) {
            return ResponseEntity.ok(ResponseUtils.success("활성 템플릿 조회 성공", template.get()));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("활성 템플릿을 찾을 수 없습니다", null));
        }
    }
    
    /**
     * 템플릿 생성
     */
    @PostMapping
    @Operation(summary = "템플릿 생성", description = "새로운 알림 템플릿을 생성합니다")
    public ResponseEntity<ApiResponse<NotificationTemplate>> createTemplate(
            @RequestBody TemplateCreateRequest request) {
        
        NotificationTemplate template = NotificationTemplate.builder()
                .name(request.getName())
                .type(request.getType())
                .channel(NotificationTemplate.NotificationChannel.valueOf(request.getChannel()))
                .language(request.getLanguage())
                .subject(request.getSubject())
                .titleTemplate(request.getTitleTemplate())
                .contentTemplate(request.getContentTemplate())
                .variables(request.getVariables())
                .isActive(request.getIsActive())
                .description(request.getDescription())
                .build();
        
        NotificationTemplate createdTemplate = templateService.createTemplate(template);
        
        return ResponseEntity.ok(ResponseUtils.success("템플릿 생성 성공", createdTemplate));
    }
    
    /**
     * 템플릿 수정
     */
    @PutMapping("/{templateId}")
    @Operation(summary = "템플릿 수정", description = "기존 템플릿을 수정합니다")
    public ResponseEntity<ApiResponse<NotificationTemplate>> updateTemplate(
            @PathVariable Long templateId,
            @RequestBody TemplateUpdateRequest request) {
        
        Optional<NotificationTemplate> existingTemplate = templateService.getTemplateById(templateId);
        
        if (existingTemplate.isEmpty()) {
            return ResponseEntity.ok(ResponseUtils.error("템플릿을 찾을 수 없습니다", null));
        }
        
        NotificationTemplate template = existingTemplate.get();
        
        // 요청된 값으로 업데이트
        if (request.getName() != null) template.setName(request.getName());
        if (request.getType() != null) template.setType(request.getType());
        if (request.getChannel() != null) {
            template.setChannel(NotificationTemplate.NotificationChannel.valueOf(request.getChannel()));
        }
        if (request.getLanguage() != null) template.setLanguage(request.getLanguage());
        if (request.getSubject() != null) template.setSubject(request.getSubject());
        if (request.getTitleTemplate() != null) template.setTitleTemplate(request.getTitleTemplate());
        if (request.getContentTemplate() != null) template.setContentTemplate(request.getContentTemplate());
        if (request.getVariables() != null) template.setVariables(request.getVariables());
        if (request.getIsActive() != null) template.setIsActive(request.getIsActive());
        if (request.getDescription() != null) template.setDescription(request.getDescription());
        
        NotificationTemplate updatedTemplate = templateService.updateTemplate(template);
        
        return ResponseEntity.ok(ResponseUtils.success("템플릿 수정 성공", updatedTemplate));
    }
    
    /**
     * 템플릿 활성화
     */
    @PutMapping("/{templateId}/activate")
    @Operation(summary = "템플릿 활성화", description = "템플릿을 활성화합니다")
    public ResponseEntity<ApiResponse<Void>> activateTemplate(@PathVariable Long templateId) {
        
        templateService.activateTemplate(templateId);
        return ResponseEntity.ok(ResponseUtils.success("템플릿 활성화 성공", null));
    }
    
    /**
     * 템플릿 비활성화
     */
    @PutMapping("/{templateId}/deactivate")
    @Operation(summary = "템플릿 비활성화", description = "템플릿을 비활성화합니다")
    public ResponseEntity<ApiResponse<Void>> deactivateTemplate(@PathVariable Long templateId) {
        
        templateService.deactivateTemplate(templateId);
        return ResponseEntity.ok(ResponseUtils.success("템플릿 비활성화 성공", null));
    }
    
    /**
     * 템플릿 미리보기
     */
    @PostMapping("/{templateId}/preview")
    @Operation(summary = "템플릿 미리보기", description = "템플릿 변수를 적용한 미리보기를 생성합니다")
    public ResponseEntity<ApiResponse<TemplatePreviewResponse>> previewTemplate(
            @PathVariable Long templateId,
            @RequestBody Map<String, Object> variables) {
        
        NotificationTemplateService.TemplatePreviewResult result = 
                templateService.previewTemplate(templateId, variables);
        
        if (result.isSuccess()) {
            TemplatePreviewResponse response = TemplatePreviewResponse.builder()
                    .previewSubject(result.getPreviewSubject())
                    .previewTitle(result.getPreviewTitle())
                    .previewContent(result.getPreviewContent())
                    .usedVariables(result.getUsedVariables())
                    .missingVariables(result.getMissingVariables())
                    .build();
            
            return ResponseEntity.ok(ResponseUtils.success("템플릿 미리보기 성공", response));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("템플릿 미리보기 실패", null));
        }
    }
    
    /**
     * 템플릿 렌더링 테스트
     */
    @PostMapping("/render")
    @Operation(summary = "템플릿 렌더링", description = "특정 타입/채널의 활성 템플릿을 렌더링합니다")
    public ResponseEntity<ApiResponse<TemplateRenderResponse>> renderTemplate(
            @RequestBody TemplateRenderRequest request) {
        
        NotificationTemplateService.TemplateRenderResult result = templateService.renderTemplate(
                request.getType(), 
                request.getChannel(), 
                request.getLanguage(), 
                request.getVariables()
        );
        
        if (result.isSuccess()) {
            TemplateRenderResponse response = TemplateRenderResponse.builder()
                    .renderedSubject(result.getRenderedSubject())
                    .renderedTitle(result.getRenderedTitle())
                    .renderedContent(result.getRenderedContent())
                    .templateId(result.getTemplate().getId())
                    .templateName(result.getTemplate().getName())
                    .build();
            
            return ResponseEntity.ok(ResponseUtils.success("템플릿 렌더링 성공", response));
        } else {
            return ResponseEntity.ok(ResponseUtils.error("템플릿 렌더링 실패: " + result.getErrorMessage(), null));
        }
    }
    
    /**
     * 템플릿 삭제
     */
    @DeleteMapping("/{templateId}")
    @Operation(summary = "템플릿 삭제", description = "템플릿을 삭제합니다")
    public ResponseEntity<ApiResponse<Void>> deleteTemplate(@PathVariable Long templateId) {
        
        templateService.deleteTemplate(templateId);
        return ResponseEntity.ok(ResponseUtils.success("템플릿 삭제 성공", null));
    }
    
    // DTO 클래스들
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemplateCreateRequest {
        private String name;
        private String type;
        private String channel;
        private String language;
        private String subject;
        private String titleTemplate;
        private String contentTemplate;
        private Map<String, Object> variables;
        private Boolean isActive;
        private String description;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemplateUpdateRequest {
        private String name;
        private String type;
        private String channel;
        private String language;
        private String subject;
        private String titleTemplate;
        private String contentTemplate;
        private Map<String, Object> variables;
        private Boolean isActive;
        private String description;
    }
    
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemplateRenderRequest {
        private String type;
        private String channel;
        private String language;
        private Map<String, Object> variables;
    }
    
    @Data
    @lombok.Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemplatePreviewResponse {
        private String previewSubject;
        private String previewTitle;
        private String previewContent;
        private List<String> usedVariables;
        private List<String> missingVariables;
    }
    
    @Data
    @lombok.Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemplateRenderResponse {
        private String renderedSubject;
        private String renderedTitle;
        private String renderedContent;
        private Long templateId;
        private String templateName;
    }
} 