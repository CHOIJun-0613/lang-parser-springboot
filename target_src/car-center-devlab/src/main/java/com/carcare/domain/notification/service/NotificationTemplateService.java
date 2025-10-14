package com.carcare.domain.notification.service;

import com.carcare.domain.notification.entity.NotificationTemplate;
import com.carcare.domain.notification.repository.NotificationTemplateRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 알림 템플릿 관리 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class NotificationTemplateService {
    
    private final NotificationTemplateRepository templateRepository;
    
    // 템플릿 변수 패턴 {변수명}
    private static final Pattern VARIABLE_PATTERN = Pattern.compile("\\{([^}]+)\\}");
    
    /**
     * 템플릿 생성
     */
    @Transactional
    public NotificationTemplate createTemplate(NotificationTemplate template) {
        template.setTemplateUuid(UUID.randomUUID().toString());
        template.setCreatedAt(LocalDateTime.now());
        template.setUpdatedAt(LocalDateTime.now());
        
        templateRepository.insert(template);
        
        log.info("알림 템플릿 생성 완료 - ID: {}, 이름: {}", template.getId(), template.getName());
        return template;
    }
    
    /**
     * 활성 템플릿 조회
     */
    public Optional<NotificationTemplate> getActiveTemplate(String type, String channel, String language) {
        return templateRepository.findActiveTemplate(type, channel, language);
    }
    
    /**
     * 템플릿으로 메시지 렌더링 (변수 치환)
     */
    public TemplateRenderResult renderTemplate(String type, String channel, String language, Map<String, Object> variables) {
        
        Optional<NotificationTemplate> templateOpt = getActiveTemplate(type, channel, language);
        
        if (templateOpt.isEmpty()) {
            log.warn("활성 템플릿을 찾을 수 없습니다 - type: {}, channel: {}, language: {}", type, channel, language);
            return TemplateRenderResult.builder()
                    .success(false)
                    .errorMessage("활성 템플릿을 찾을 수 없습니다")
                    .build();
        }
        
        NotificationTemplate template = templateOpt.get();
        
        try {
            String renderedSubject = template.getSubject() != null ? 
                    replaceVariables(template.getSubject(), variables) : null;
            String renderedTitle = template.getTitleTemplate() != null ? 
                    replaceVariables(template.getTitleTemplate(), variables) : null;
            String renderedContent = replaceVariables(template.getContentTemplate(), variables);
            
            return TemplateRenderResult.builder()
                    .success(true)
                    .template(template)
                    .renderedSubject(renderedSubject)
                    .renderedTitle(renderedTitle)
                    .renderedContent(renderedContent)
                    .build();
            
        } catch (Exception e) {
            log.error("템플릿 렌더링 실패 - templateId: {}", template.getId(), e);
            return TemplateRenderResult.builder()
                    .success(false)
                    .template(template)
                    .errorMessage("템플릿 렌더링 실패: " + e.getMessage())
                    .build();
        }
    }
    
    /**
     * 변수 치환
     */
    private String replaceVariables(String template, Map<String, Object> variables) {
        if (template == null || variables == null) {
            return template;
        }
        
        Matcher matcher = VARIABLE_PATTERN.matcher(template);
        StringBuffer result = new StringBuffer();
        
        while (matcher.find()) {
            String variableName = matcher.group(1);
            Object value = variables.get(variableName);
            String replacement = value != null ? value.toString() : "{" + variableName + "}";
            matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(result);
        
        return result.toString();
    }
    
    /**
     * 템플릿 미리보기
     */
    public TemplatePreviewResult previewTemplate(Long templateId, Map<String, Object> variables) {
        
        Optional<NotificationTemplate> templateOpt = templateRepository.findById(templateId);
        
        if (templateOpt.isEmpty()) {
            return TemplatePreviewResult.builder()
                    .success(false)
                    .errorMessage("템플릿을 찾을 수 없습니다")
                    .build();
        }
        
        NotificationTemplate template = templateOpt.get();
        
        try {
            String previewSubject = template.getSubject() != null ? 
                    replaceVariables(template.getSubject(), variables) : null;
            String previewTitle = template.getTitleTemplate() != null ? 
                    replaceVariables(template.getTitleTemplate(), variables) : null;
            String previewContent = replaceVariables(template.getContentTemplate(), variables);
            
            // 사용된 변수와 누락된 변수 분석
            List<String> usedVariables = extractVariables(template.getContentTemplate());
            List<String> missingVariables = usedVariables.stream()
                    .filter(var -> !variables.containsKey(var))
                    .toList();
            
            return TemplatePreviewResult.builder()
                    .success(true)
                    .template(template)
                    .previewSubject(previewSubject)
                    .previewTitle(previewTitle)
                    .previewContent(previewContent)
                    .usedVariables(usedVariables)
                    .missingVariables(missingVariables)
                    .build();
            
        } catch (Exception e) {
            log.error("템플릿 미리보기 실패 - templateId: {}", templateId, e);
            return TemplatePreviewResult.builder()
                    .success(false)
                    .template(template)
                    .errorMessage("템플릿 미리보기 실패: " + e.getMessage())
                    .build();
        }
    }
    
    /**
     * 템플릿에서 변수 추출
     */
    private List<String> extractVariables(String template) {
        if (template == null) {
            return List.of();
        }
        
        Matcher matcher = VARIABLE_PATTERN.matcher(template);
        return matcher.results()
                .map(matchResult -> matchResult.group(1))
                .distinct()
                .toList();
    }
    
    /**
     * 템플릿 목록 조회
     */
    public List<NotificationTemplate> getTemplates(int page, int size) {
        int offset = page * size;
        return templateRepository.findAll(offset, size);
    }
    
    /**
     * 활성 템플릿만 조회
     */
    public List<NotificationTemplate> getActiveTemplates(int page, int size) {
        int offset = page * size;
        return templateRepository.findActiveTemplates(offset, size);
    }
    
    /**
     * 템플릿 검색
     */
    public TemplateSearchResult searchTemplates(String keyword, String type, String channel, 
                                              String language, Boolean isActive, int page, int size) {
        int offset = page * size;
        
        List<NotificationTemplate> templates = templateRepository.searchTemplates(
                keyword, type, channel, language, isActive, offset, size);
        
        int totalCount = templateRepository.countTemplates(
                keyword, type, channel, language, isActive);
        
        return TemplateSearchResult.builder()
                .templates(templates)
                .totalCount(totalCount)
                .page(page)
                .size(size)
                .build();
    }
    
    /**
     * 템플릿 업데이트
     */
    @Transactional
    public NotificationTemplate updateTemplate(NotificationTemplate template) {
        template.setUpdatedAt(LocalDateTime.now());
        templateRepository.update(template);
        
        log.info("템플릿 업데이트 완료 - ID: {}, 이름: {}", template.getId(), template.getName());
        return template;
    }
    
    /**
     * 템플릿 활성화
     */
    @Transactional
    public void activateTemplate(Long templateId) {
        Optional<NotificationTemplate> templateOpt = templateRepository.findById(templateId);
        
        if (templateOpt.isPresent()) {
            NotificationTemplate template = templateOpt.get();
            
            // 같은 타입/채널의 다른 템플릿들을 비활성화
            templateRepository.deactivateOtherTemplates(
                    template.getType(), 
                    template.getChannel().name(), 
                    template.getLanguage(), 
                    templateId
            );
            
            // 현재 템플릿 활성화
            templateRepository.updateActiveStatus(templateId, true);
            
            log.info("템플릿 활성화 완료 - ID: {}", templateId);
        }
    }
    
    /**
     * 템플릿 비활성화
     */
    @Transactional
    public void deactivateTemplate(Long templateId) {
        templateRepository.updateActiveStatus(templateId, false);
        log.info("템플릿 비활성화 완료 - ID: {}", templateId);
    }
    
    /**
     * 템플릿 삭제
     */
    @Transactional
    public void deleteTemplate(Long templateId) {
        templateRepository.deleteById(templateId);
        log.info("템플릿 삭제 완료 - ID: {}", templateId);
    }
    
    /**
     * 템플릿 ID로 조회
     */
    public Optional<NotificationTemplate> getTemplateById(Long id) {
        return templateRepository.findById(id);
    }
    
    /**
     * 템플릿 UUID로 조회
     */
    public Optional<NotificationTemplate> getTemplateByUuid(String uuid) {
        return templateRepository.findByTemplateUuid(uuid);
    }
    
    // 결과 클래스들
    
    public static class TemplateRenderResult {
        private boolean success;
        private NotificationTemplate template;
        private String renderedSubject;
        private String renderedTitle;
        private String renderedContent;
        private String errorMessage;
        
        public static TemplateRenderResultBuilder builder() {
            return new TemplateRenderResultBuilder();
        }
        
        // Getters
        public boolean isSuccess() { return success; }
        public NotificationTemplate getTemplate() { return template; }
        public String getRenderedSubject() { return renderedSubject; }
        public String getRenderedTitle() { return renderedTitle; }
        public String getRenderedContent() { return renderedContent; }
        public String getErrorMessage() { return errorMessage; }
        
        public static class TemplateRenderResultBuilder {
            private boolean success;
            private NotificationTemplate template;
            private String renderedSubject;
            private String renderedTitle;
            private String renderedContent;
            private String errorMessage;
            
            public TemplateRenderResultBuilder success(boolean success) {
                this.success = success;
                return this;
            }
            
            public TemplateRenderResultBuilder template(NotificationTemplate template) {
                this.template = template;
                return this;
            }
            
            public TemplateRenderResultBuilder renderedSubject(String renderedSubject) {
                this.renderedSubject = renderedSubject;
                return this;
            }
            
            public TemplateRenderResultBuilder renderedTitle(String renderedTitle) {
                this.renderedTitle = renderedTitle;
                return this;
            }
            
            public TemplateRenderResultBuilder renderedContent(String renderedContent) {
                this.renderedContent = renderedContent;
                return this;
            }
            
            public TemplateRenderResultBuilder errorMessage(String errorMessage) {
                this.errorMessage = errorMessage;
                return this;
            }
            
            public TemplateRenderResult build() {
                TemplateRenderResult result = new TemplateRenderResult();
                result.success = this.success;
                result.template = this.template;
                result.renderedSubject = this.renderedSubject;
                result.renderedTitle = this.renderedTitle;
                result.renderedContent = this.renderedContent;
                result.errorMessage = this.errorMessage;
                return result;
            }
        }
    }
    
    public static class TemplatePreviewResult {
        private boolean success;
        private NotificationTemplate template;
        private String previewSubject;
        private String previewTitle;
        private String previewContent;
        private List<String> usedVariables;
        private List<String> missingVariables;
        private String errorMessage;
        
        public static TemplatePreviewResultBuilder builder() {
            return new TemplatePreviewResultBuilder();
        }
        
        // Getters
        public boolean isSuccess() { return success; }
        public NotificationTemplate getTemplate() { return template; }
        public String getPreviewSubject() { return previewSubject; }
        public String getPreviewTitle() { return previewTitle; }
        public String getPreviewContent() { return previewContent; }
        public List<String> getUsedVariables() { return usedVariables; }
        public List<String> getMissingVariables() { return missingVariables; }
        public String getErrorMessage() { return errorMessage; }
        
        public static class TemplatePreviewResultBuilder {
            private boolean success;
            private NotificationTemplate template;
            private String previewSubject;
            private String previewTitle;
            private String previewContent;
            private List<String> usedVariables;
            private List<String> missingVariables;
            private String errorMessage;
            
            public TemplatePreviewResultBuilder success(boolean success) {
                this.success = success;
                return this;
            }
            
            public TemplatePreviewResultBuilder template(NotificationTemplate template) {
                this.template = template;
                return this;
            }
            
            public TemplatePreviewResultBuilder previewSubject(String previewSubject) {
                this.previewSubject = previewSubject;
                return this;
            }
            
            public TemplatePreviewResultBuilder previewTitle(String previewTitle) {
                this.previewTitle = previewTitle;
                return this;
            }
            
            public TemplatePreviewResultBuilder previewContent(String previewContent) {
                this.previewContent = previewContent;
                return this;
            }
            
            public TemplatePreviewResultBuilder usedVariables(List<String> usedVariables) {
                this.usedVariables = usedVariables;
                return this;
            }
            
            public TemplatePreviewResultBuilder missingVariables(List<String> missingVariables) {
                this.missingVariables = missingVariables;
                return this;
            }
            
            public TemplatePreviewResultBuilder errorMessage(String errorMessage) {
                this.errorMessage = errorMessage;
                return this;
            }
            
            public TemplatePreviewResult build() {
                TemplatePreviewResult result = new TemplatePreviewResult();
                result.success = this.success;
                result.template = this.template;
                result.previewSubject = this.previewSubject;
                result.previewTitle = this.previewTitle;
                result.previewContent = this.previewContent;
                result.usedVariables = this.usedVariables;
                result.missingVariables = this.missingVariables;
                result.errorMessage = this.errorMessage;
                return result;
            }
        }
    }
    
    public static class TemplateSearchResult {
        private List<NotificationTemplate> templates;
        private int totalCount;
        private int page;
        private int size;
        
        public static TemplateSearchResultBuilder builder() {
            return new TemplateSearchResultBuilder();
        }
        
        // Getters
        public List<NotificationTemplate> getTemplates() { return templates; }
        public int getTotalCount() { return totalCount; }
        public int getPage() { return page; }
        public int getSize() { return size; }
        
        public static class TemplateSearchResultBuilder {
            private List<NotificationTemplate> templates;
            private int totalCount;
            private int page;
            private int size;
            
            public TemplateSearchResultBuilder templates(List<NotificationTemplate> templates) {
                this.templates = templates;
                return this;
            }
            
            public TemplateSearchResultBuilder totalCount(int totalCount) {
                this.totalCount = totalCount;
                return this;
            }
            
            public TemplateSearchResultBuilder page(int page) {
                this.page = page;
                return this;
            }
            
            public TemplateSearchResultBuilder size(int size) {
                this.size = size;
                return this;
            }
            
            public TemplateSearchResult build() {
                TemplateSearchResult result = new TemplateSearchResult();
                result.templates = this.templates;
                result.totalCount = this.totalCount;
                result.page = this.page;
                result.size = this.size;
                return result;
            }
        }
    }
} 