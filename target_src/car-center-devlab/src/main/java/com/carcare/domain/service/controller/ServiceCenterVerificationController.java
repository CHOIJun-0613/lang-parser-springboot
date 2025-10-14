package com.carcare.domain.service.controller;

import com.carcare.domain.service.service.ServiceCenterVerificationService;
import com.carcare.domain.service.service.BusinessNumberValidationService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponses;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.LocalDate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import com.carcare.common.exception.BusinessException;

/**
 * 정비소 사업자 인증 컨트롤러
 * 인증 프로세스 관리, 문서 업로드, 상태 조회, 관리자 승인 등의 API 제공
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/service-centers/verification")
@RequiredArgsConstructor
@Validated
@Tag(name = "ServiceCenter Verification", description = "정비소 사업자 인증 API")
public class ServiceCenterVerificationController {

    private final ServiceCenterVerificationService verificationService;
    private final BusinessNumberValidationService businessNumberValidationService;

    /**
     * 사업자등록번호 검증
     */
    @PostMapping("/validate-business-number")
    @Operation(summary = "사업자등록번호 검증", description = "사업자등록번호의 형식, 체크섬, 국세청 상태를 검증합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "검증 완료"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청")
    })
    public ResponseEntity<ApiResponse<BusinessNumberValidationService.BusinessNumberValidationResult>> validateBusinessNumber(
            @Valid @RequestBody BusinessNumberValidationRequest request) {
        
        log.info("사업자등록번호 검증 요청: {}", maskBusinessNumber(request.getBusinessNumber()));

        BusinessNumberValidationService.BusinessNumberValidationResult result = 
            businessNumberValidationService.validateBusinessNumber(request.getBusinessNumber());

        return ResponseEntity.ok(ResponseUtils.success("사업자등록번호 검증이 완료되었습니다", result));
    }

    /**
     * 인증 프로세스 시작
     */
    @PostMapping("/{serviceCenterId}/start")
    @Operation(summary = "인증 프로세스 시작", description = "정비소 사업자 인증 프로세스를 시작합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "인증 프로세스 시작 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 진행 중인 인증이 있음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationProcessResult>> startVerification(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Valid @RequestBody VerificationStartRequest request,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        
        log.info("인증 프로세스 시작 요청: 정비소ID={}, 사업자번호={}", serviceCenterId, maskBusinessNumber(request.getBusinessNumber()));

        ServiceCenterVerificationService.VerificationStartRequest serviceRequest = 
            ServiceCenterVerificationService.VerificationStartRequest.builder()
                .businessNumber(request.getBusinessNumber())
                .representativeName(request.getRepresentativeName())
                .businessName(request.getBusinessName())
                .businessAddress(request.getBusinessAddress())
                .establishmentDate(request.getEstablishmentDate())
                .businessType(request.getBusinessType())
                .build();

        ServiceCenterVerificationService.VerificationProcessResult result = 
            verificationService.startVerification(serviceCenterId, serviceRequest, userId);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("인증 프로세스가 시작되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 인증 문서 업로드
     */
    @PostMapping(value = "/{verificationId}/upload-documents", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "인증 문서 업로드", description = "사업자등록증 및 추가 증빙 문서를 업로드합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "문서 업로드 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 파일 형식 또는 크기"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "인증 정보를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationProcessResult>> uploadDocuments(
            @Parameter(description = "인증 ID") @PathVariable Long verificationId,
            @Parameter(description = "사업자등록증 파일") @RequestParam(value = "businessLicense", required = false) MultipartFile businessLicenseFile,
            @Parameter(description = "추가 증빙 문서") @RequestParam(value = "additionalDocument", required = false) MultipartFile additionalFile,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {

        log.info("인증 문서 업로드 요청: 인증ID={}, 사업자등록증={}, 추가문서={}", 
                verificationId, 
                businessLicenseFile != null ? businessLicenseFile.getOriginalFilename() : "없음",
                additionalFile != null ? additionalFile.getOriginalFilename() : "없음");

        if (businessLicenseFile == null || businessLicenseFile.isEmpty()) {
            return ResponseEntity.badRequest().body(ResponseUtils.error("사업자등록증 파일은 필수입니다", null));
        }

        ServiceCenterVerificationService.VerificationProcessResult result = 
            verificationService.uploadDocumentAndProceed(verificationId, businessLicenseFile, additionalFile, userId);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("문서 업로드가 완료되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 인증 상태 조회
     */
    @GetMapping("/{serviceCenterId}/status")
    @Operation(summary = "인증 상태 조회", description = "정비소의 현재 인증 상태를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "상태 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationStatusResult>> getVerificationStatus(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId) {

        log.debug("인증 상태 조회: 정비소ID={}", serviceCenterId);

        ServiceCenterVerificationService.VerificationStatusResult result = 
            verificationService.getVerificationStatus(serviceCenterId);

        return ResponseEntity.ok(ResponseUtils.success("인증 상태 조회가 완료되었습니다", result));
    }

    /**
     * 관리자 승인
     */
    @PostMapping("/{verificationId}/approve")
    @Operation(summary = "인증 승인", description = "관리자가 인증을 승인합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "승인 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "승인할 수 없는 상태"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "관리자 권한 필요"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "인증 정보를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationProcessResult>> approveVerification(
            @Parameter(description = "인증 ID") @PathVariable Long verificationId,
            @Valid @RequestBody VerificationApprovalRequest request) {

        // 현재 사용자 정보 추출
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("인증 승인 요청: 인증ID={}, 관리자ID={}, 역할={}", verificationId, currentUser.getUserId(), currentUser.getRole());

        // 관리자 권한 확인
        if (!"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("시스템 관리자 권한이 필요합니다");
        }

        ServiceCenterVerificationService.VerificationProcessResult result = 
            verificationService.approveVerification(verificationId, request.getComment(), currentUser.getUserId());

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("인증이 승인되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 관리자 거부
     */
    @PostMapping("/{verificationId}/reject")
    @Operation(summary = "인증 거부", description = "관리자가 인증을 거부합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "거부 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "거부할 수 없는 상태"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "관리자 권한 필요"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "인증 정보를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationProcessResult>> rejectVerification(
            @Parameter(description = "인증 ID") @PathVariable Long verificationId,
            @Valid @RequestBody VerificationRejectionRequest request) {

        // 현재 사용자 정보 추출
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("인증 거부 요청: 인증ID={}, 관리자ID={}, 역할={}", verificationId, currentUser.getUserId(), currentUser.getRole());

        // 관리자 권한 확인
        if (!"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("시스템 관리자 권한이 필요합니다");
        }

        ServiceCenterVerificationService.VerificationProcessResult result = 
            verificationService.rejectVerification(verificationId, request.getReason(), currentUser.getUserId());

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("인증이 거부되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 인증 갱신
     */
    @PostMapping("/{serviceCenterId}/renew")
    @Operation(summary = "인증 갱신", description = "만료된 인증을 갱신합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "갱신 시작 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "갱신할 수 없는 상태"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterVerificationService.VerificationProcessResult>> renewVerification(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {

        log.info("인증 갱신 요청: 정비소ID={}", serviceCenterId);

        ServiceCenterVerificationService.VerificationProcessResult result = 
            verificationService.renewExpiredVerification(serviceCenterId, userId);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("인증 갱신 프로세스가 시작되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    // === 헬퍼 메서드 ===

    private String maskBusinessNumber(String businessNumber) {
        if (businessNumber == null || businessNumber.length() < 4) {
            return "***";
        }
        return businessNumber.substring(0, 3) + "-**-****" + businessNumber.substring(businessNumber.length() - 1);
    }

    /**
     * SecurityContext에서 현재 사용자 정보 추출
     */
    private JwtUserPrincipal getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof JwtUserPrincipal) {
            return (JwtUserPrincipal) authentication.getPrincipal();
        }
        throw new BusinessException("인증된 사용자 정보를 찾을 수 없습니다");
    }

    // === 요청 DTO 클래스들 ===

    @lombok.Data
    public static class BusinessNumberValidationRequest {
        @NotBlank(message = "사업자등록번호는 필수입니다")
        @Pattern(regexp = "^\\d{3}-\\d{2}-\\d{5}$|^\\d{10}$", message = "사업자등록번호 형식이 올바르지 않습니다")
        private String businessNumber;
    }

    @lombok.Data
    public static class VerificationStartRequest {
        @NotBlank(message = "사업자등록번호는 필수입니다")
        @Pattern(regexp = "^\\d{3}-\\d{2}-\\d{5}$", message = "사업자등록번호 형식이 올바르지 않습니다 (예: 123-45-67890)")
        private String businessNumber;

        @NotBlank(message = "대표자명은 필수입니다")
        @Size(max = 50, message = "대표자명은 50자 이하여야 합니다")
        private String representativeName;

        @NotBlank(message = "상호명은 필수입니다")
        @Size(max = 100, message = "상호명은 100자 이하여야 합니다")
        private String businessName;

        @NotBlank(message = "사업장 주소는 필수입니다")
        @Size(max = 200, message = "사업장 주소는 200자 이하여야 합니다")
        private String businessAddress;

        @NotNull(message = "개업일자는 필수입니다")
        private LocalDate establishmentDate;

        @Size(max = 100, message = "업종은 100자 이하여야 합니다")
        private String businessType;
    }

    @lombok.Data
    public static class VerificationApprovalRequest {
        @Size(max = 500, message = "승인 의견은 500자 이하여야 합니다")
        private String comment;
    }

    @lombok.Data
    public static class VerificationRejectionRequest {
        @NotBlank(message = "거부 사유는 필수입니다")
        @Size(max = 500, message = "거부 사유는 500자 이하여야 합니다")
        private String reason;
    }
} 