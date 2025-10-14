package com.carcare.domain.service.service;

import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;

/**
 * 인증 문서 업로드 및 관리 서비스
 * 파일 업로드, 검증, 저장, 분석 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationDocumentService {

    @Value("${app.file.upload.path:/tmp/uploads}")
    private String uploadPath;

    @Value("${app.file.upload.max-size:10485760}") // 10MB
    private long maxFileSize;

    @Value("${app.file.upload.business-license.enabled:true}")
    private boolean businessLicenseUploadEnabled;

    // 허용된 파일 확장자
    private static final Set<String> ALLOWED_EXTENSIONS = new HashSet<String>() {{
        add("jpg");
        add("jpeg");
        add("png");
        add("pdf");
        add("gif");
    }};

    // 허용된 MIME 타입
    private static final Set<String> ALLOWED_MIME_TYPES = new HashSet<String>() {{
        add("image/jpeg");
        add("image/png");
        add("image/gif");
        add("application/pdf");
    }};

    // 파일명 패턴 (보안)
    private static final Pattern SAFE_FILENAME_PATTERN = Pattern.compile("^[a-zA-Z0-9._-]+$");

    /**
     * 사업자등록증 파일 업로드
     */
    public DocumentUploadResult uploadBusinessLicense(Long serviceCenterId, MultipartFile file, Long uploadedBy) {
        log.info("사업자등록증 업로드 시작: 정비소ID={}, 파일명={}, 크기={}bytes", 
                serviceCenterId, file.getOriginalFilename(), file.getSize());

        if (!businessLicenseUploadEnabled) {
            throw new BusinessException("사업자등록증 업로드 기능이 비활성화되어 있습니다");
        }

        try {
            // 파일 검증
            FileValidationResult validationResult = validateFile(file, DocumentType.BUSINESS_LICENSE);
            if (!validationResult.isValid()) {
                return DocumentUploadResult.builder()
                    .success(false)
                    .errorMessage(validationResult.getErrorMessage())
                    .uploadedAt(LocalDateTime.now())
                    .build();
            }

            // 파일 저장
            String savedFilePath = saveFile(file, serviceCenterId, DocumentType.BUSINESS_LICENSE);

            // 파일 분석 (OCR, 메타데이터 등)
            DocumentAnalysisResult analysisResult = analyzeDocument(savedFilePath, DocumentType.BUSINESS_LICENSE);

            return DocumentUploadResult.builder()
                .success(true)
                .filePath(savedFilePath)
                .originalFileName(file.getOriginalFilename())
                .fileSize(file.getSize())
                .mimeType(file.getContentType())
                .documentType(DocumentType.BUSINESS_LICENSE)
                .analysisResult(analysisResult)
                .uploadedBy(uploadedBy)
                .uploadedAt(LocalDateTime.now())
                .build();

        } catch (Exception e) {
            log.error("사업자등록증 업로드 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return DocumentUploadResult.builder()
                .success(false)
                .errorMessage("파일 업로드 중 오류가 발생했습니다: " + e.getMessage())
                .uploadedAt(LocalDateTime.now())
                .build();
        }
    }

    /**
     * 추가 인증 문서 업로드
     */
    public DocumentUploadResult uploadAdditionalDocument(Long serviceCenterId, MultipartFile file, 
                                                       DocumentType documentType, Long uploadedBy) {
        log.info("추가 인증 문서 업로드 시작: 정비소ID={}, 문서타입={}, 파일명={}", 
                serviceCenterId, documentType, file.getOriginalFilename());

        try {
            FileValidationResult validationResult = validateFile(file, documentType);
            if (!validationResult.isValid()) {
                return DocumentUploadResult.builder()
                    .success(false)
                    .errorMessage(validationResult.getErrorMessage())
                    .uploadedAt(LocalDateTime.now())
                    .build();
            }

            String savedFilePath = saveFile(file, serviceCenterId, documentType);
            DocumentAnalysisResult analysisResult = analyzeDocument(savedFilePath, documentType);

            return DocumentUploadResult.builder()
                .success(true)
                .filePath(savedFilePath)
                .originalFileName(file.getOriginalFilename())
                .fileSize(file.getSize())
                .mimeType(file.getContentType())
                .documentType(documentType)
                .analysisResult(analysisResult)
                .uploadedBy(uploadedBy)
                .uploadedAt(LocalDateTime.now())
                .build();

        } catch (Exception e) {
            log.error("추가 인증 문서 업로드 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return DocumentUploadResult.builder()
                .success(false)
                .errorMessage("파일 업로드 중 오류가 발생했습니다: " + e.getMessage())
                .uploadedAt(LocalDateTime.now())
                .build();
        }
    }

    /**
     * 파일 삭제
     */
    public boolean deleteDocument(String filePath) {
        log.info("문서 파일 삭제: {}", filePath);

        try {
            Path path = Paths.get(filePath);
            if (Files.exists(path)) {
                Files.delete(path);
                log.info("파일 삭제 완료: {}", filePath);
                return true;
            } else {
                log.warn("삭제할 파일이 존재하지 않음: {}", filePath);
                return false;
            }
        } catch (Exception e) {
            log.error("파일 삭제 중 오류 발생: {}, 오류={}", filePath, e.getMessage(), e);
            return false;
        }
    }

    /**
     * 파일 정보 조회
     */
    public DocumentInfo getDocumentInfo(String filePath) {
        try {
            Path path = Paths.get(filePath);
            if (!Files.exists(path)) {
                return null;
            }

            return DocumentInfo.builder()
                .filePath(filePath)
                .fileName(path.getFileName().toString())
                .fileSize(Files.size(path))
                .mimeType(Files.probeContentType(path))
                .createdAt(Files.getLastModifiedTime(path).toInstant().atZone(java.time.ZoneId.systemDefault()).toLocalDateTime())
                .exists(true)
                .build();

        } catch (Exception e) {
            log.error("파일 정보 조회 중 오류 발생: {}, 오류={}", filePath, e.getMessage(), e);
            return DocumentInfo.builder()
                .filePath(filePath)
                .exists(false)
                .build();
        }
    }

    // === 내부 메서드들 ===

    /**
     * 파일 검증
     */
    private FileValidationResult validateFile(MultipartFile file, DocumentType documentType) {
        // 파일 존재 확인
        if (file == null || file.isEmpty()) {
            return FileValidationResult.builder()
                .isValid(false)
                .errorMessage("업로드할 파일을 선택해주세요")
                .build();
        }

        // 파일 크기 확인
        if (file.getSize() > maxFileSize) {
            return FileValidationResult.builder()
                .isValid(false)
                .errorMessage(String.format("파일 크기가 너무 큽니다. 최대 %dMB까지 업로드 가능합니다", maxFileSize / 1024 / 1024))
                .build();
        }

        // 파일명 확인
        String originalFilename = file.getOriginalFilename();
        if (!StringUtils.hasText(originalFilename)) {
            return FileValidationResult.builder()
                .isValid(false)
                .errorMessage("유효하지 않은 파일명입니다")
                .build();
        }

        // 확장자 확인
        String extension = getFileExtension(originalFilename).toLowerCase();
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            return FileValidationResult.builder()
                .isValid(false)
                .errorMessage("지원되지 않는 파일 형식입니다. (허용: " + String.join(", ", ALLOWED_EXTENSIONS) + ")")
                .build();
        }

        // MIME 타입 확인
        String mimeType = file.getContentType();
        if (!ALLOWED_MIME_TYPES.contains(mimeType)) {
            return FileValidationResult.builder()
                .isValid(false)
                .errorMessage("지원되지 않는 파일 타입입니다")
                .build();
        }

        // 문서 타입별 추가 검증
        FileValidationResult typeSpecificResult = validateDocumentTypeSpecific(file, documentType);
        if (!typeSpecificResult.isValid()) {
            return typeSpecificResult;
        }

        return FileValidationResult.builder()
            .isValid(true)
            .build();
    }

    /**
     * 문서 타입별 특화 검증
     */
    private FileValidationResult validateDocumentTypeSpecific(MultipartFile file, DocumentType documentType) {
        switch (documentType) {
            case BUSINESS_LICENSE:
                // 사업자등록증은 이미지 파일만 허용
                if (!file.getContentType().startsWith("image/")) {
                    return FileValidationResult.builder()
                        .isValid(false)
                        .errorMessage("사업자등록증은 이미지 파일만 업로드 가능합니다")
                        .build();
                }
                break;

            case ADDITIONAL_DOCUMENT:
                // 추가 문서는 모든 허용 타입 가능
                break;

            default:
                return FileValidationResult.builder()
                    .isValid(false)
                    .errorMessage("알 수 없는 문서 타입입니다")
                    .build();
        }

        return FileValidationResult.builder()
            .isValid(true)
            .build();
    }

    /**
     * 파일 저장
     */
    private String saveFile(MultipartFile file, Long serviceCenterId, DocumentType documentType) throws IOException {
        // 업로드 디렉토리 생성
        Path uploadDir = Paths.get(uploadPath, "service-center", String.valueOf(serviceCenterId), documentType.getPath());
        Files.createDirectories(uploadDir);

        // 안전한 파일명 생성
        String originalFilename = file.getOriginalFilename();
        String extension = getFileExtension(originalFilename);
        String safeFilename = generateSafeFilename(serviceCenterId, documentType, extension);

        // 파일 저장
        Path filePath = uploadDir.resolve(safeFilename);
        Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

        log.info("파일 저장 완료: {}", filePath.toString());
        return filePath.toString();
    }

    /**
     * 문서 분석 (OCR, 메타데이터 추출 등)
     */
    private DocumentAnalysisResult analyzeDocument(String filePath, DocumentType documentType) {
        log.info("문서 분석 시작: {}, 타입={}", filePath, documentType);

        try {
            // TODO: 실제 환경에서는 OCR 라이브러리나 외부 API 사용
            // 현재는 시뮬레이션으로 대체
            return simulateDocumentAnalysis(filePath, documentType);

        } catch (Exception e) {
            log.error("문서 분석 중 오류 발생: {}, 오류={}", filePath, e.getMessage(), e);
            return DocumentAnalysisResult.builder()
                .success(false)
                .errorMessage("문서 분석 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 문서 분석 시뮬레이션
     */
    private DocumentAnalysisResult simulateDocumentAnalysis(String filePath, DocumentType documentType) {
        Map<String, String> extractedData = new HashMap<>();
        List<String> detectedIssues = new ArrayList<>();

        switch (documentType) {
            case BUSINESS_LICENSE:
                // 사업자등록증 분석 시뮬레이션
                extractedData.put("businessNumber", "123-45-67890");
                extractedData.put("businessName", "ABC 자동차 정비소");
                extractedData.put("representativeName", "홍길동");
                extractedData.put("address", "서울특별시 강남구 테헤란로 123");
                extractedData.put("establishmentDate", "2020-01-01");

                // 이미지 품질 검사 시뮬레이션
                if (filePath.contains("blur")) {
                    detectedIssues.add("이미지가 흐릿합니다. 선명한 이미지로 다시 업로드해주세요.");
                }
                if (filePath.contains("dark")) {
                    detectedIssues.add("이미지가 너무 어둡습니다. 밝은 곳에서 다시 촬영해주세요.");
                }
                break;

            case ADDITIONAL_DOCUMENT:
                extractedData.put("documentType", "추가 증빙 문서");
                break;
        }

        return DocumentAnalysisResult.builder()
            .success(true)
            .confidence(detectedIssues.isEmpty() ? 0.95 : 0.75)
            .extractedData(extractedData)
            .detectedIssues(detectedIssues)
            .recommendedActions(generateRecommendedActions(detectedIssues))
            .analyzedAt(LocalDateTime.now())
            .build();
    }

    /**
     * 권장 조치 사항 생성
     */
    private List<String> generateRecommendedActions(List<String> detectedIssues) {
        List<String> recommendations = new ArrayList<>();

        if (detectedIssues.isEmpty()) {
            recommendations.add("문서가 명확하게 인식되었습니다. 인증 절차를 진행해주세요.");
        } else {
            recommendations.add("감지된 문제를 해결한 후 다시 업로드해주세요.");
            if (detectedIssues.stream().anyMatch(issue -> issue.contains("흐릿"))) {
                recommendations.add("카메라 초점을 맞춰서 다시 촬영해주세요.");
            }
            if (detectedIssues.stream().anyMatch(issue -> issue.contains("어둡"))) {
                recommendations.add("조명이 밝은 곳에서 다시 촬영해주세요.");
            }
        }

        return recommendations;
    }

    /**
     * 안전한 파일명 생성
     */
    private String generateSafeFilename(Long serviceCenterId, DocumentType documentType, String extension) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String randomId = UUID.randomUUID().toString().substring(0, 8);
        return String.format("%s_%d_%s_%s.%s", 
                documentType.getPrefix(), serviceCenterId, timestamp, randomId, extension);
    }

    /**
     * 파일 확장자 추출
     */
    private String getFileExtension(String filename) {
        int lastDotIndex = filename.lastIndexOf('.');
        return lastDotIndex > 0 ? filename.substring(lastDotIndex + 1) : "";
    }

    // === Enum 및 결과 클래스들 ===

    public enum DocumentType {
        BUSINESS_LICENSE("business-license", "사업자등록증", "bl"),
        ADDITIONAL_DOCUMENT("additional", "추가문서", "ad");

        private final String path;
        private final String description;
        private final String prefix;

        DocumentType(String path, String description, String prefix) {
            this.path = path;
            this.description = description;
            this.prefix = prefix;
        }

        public String getPath() { return path; }
        public String getDescription() { return description; }
        public String getPrefix() { return prefix; }
    }

    @lombok.Data
    @lombok.Builder
    public static class DocumentUploadResult {
        private boolean success;
        private String filePath;
        private String originalFileName;
        private Long fileSize;
        private String mimeType;
        private DocumentType documentType;
        private DocumentAnalysisResult analysisResult;
        private String errorMessage;
        private Long uploadedBy;
        private LocalDateTime uploadedAt;
    }

    @lombok.Data
    @lombok.Builder
    public static class DocumentAnalysisResult {
        private boolean success;
        private double confidence;
        private Map<String, String> extractedData;
        private List<String> detectedIssues;
        private List<String> recommendedActions;
        private String errorMessage;
        private LocalDateTime analyzedAt;
    }

    @lombok.Data
    @lombok.Builder
    public static class FileValidationResult {
        private boolean isValid;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class DocumentInfo {
        private String filePath;
        private String fileName;
        private Long fileSize;
        private String mimeType;
        private boolean exists;
        private LocalDateTime createdAt;
    }
} 