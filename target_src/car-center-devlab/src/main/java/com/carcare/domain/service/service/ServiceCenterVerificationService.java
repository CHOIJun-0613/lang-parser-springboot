package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterVerification;
import com.carcare.domain.service.entity.ServiceCenter;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

/**
 * 정비소 사업자 인증 서비스
 * 인증 프로세스 관리, 상태 변경, 승인/거부 처리 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ServiceCenterVerificationService {

    private final ServiceCenterRepository serviceCenterRepository;
    private final BusinessNumberValidationService businessNumberValidationService;
    private final VerificationDocumentService documentService;

    // 인증 유효 기간 (1년)
    private static final int VERIFICATION_VALIDITY_YEARS = 1;
    
    // 재검증 대기 시간 (1시간)
    private static final int RE_VERIFICATION_WAIT_HOURS = 1;
    
    // 최대 검증 시도 횟수
    private static final int MAX_VERIFICATION_ATTEMPTS = 5;

    /**
     * 인증 프로세스 시작
     */
    @Transactional
    public VerificationProcessResult startVerification(Long serviceCenterId, VerificationStartRequest request, Long requestedBy) {
        log.info("사업자 인증 프로세스 시작: 정비소ID={}, 사업자번호={}", serviceCenterId, 
                maskBusinessNumber(request.getBusinessNumber()));

        try {
            // 서비스 센터 존재 확인
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            // 기존 인증 중인 프로세스 확인
            // TODO: 실제 구현에서는 인증 테이블에서 조회
            Optional<ServiceCenterVerification> existingVerification = findActiveVerification(serviceCenterId);
            if (existingVerification.isPresent() && existingVerification.get().getStatus().isInProgress()) {
                throw new BusinessException("이미 진행 중인 인증 프로세스가 있습니다");
            }

            // 사업자등록번호 검증
            BusinessNumberValidationService.BusinessNumberValidationResult validationResult = 
                businessNumberValidationService.validateBusinessNumber(request.getBusinessNumber());

            if (!validationResult.isValid()) {
                return VerificationProcessResult.builder()
                    .success(false)
                    .verificationId(null)
                    .status(ServiceCenterVerification.VerificationStatus.REJECTED)
                    .errorMessage("사업자등록번호 검증 실패: " + validationResult.getErrorMessage())
                    .build();
            }

            // 인증 레코드 생성
            ServiceCenterVerification verification = ServiceCenterVerification.builder()
                .serviceCenterId(serviceCenterId)
                .businessNumber(request.getBusinessNumber())
                .representativeName(request.getRepresentativeName())
                .businessName(request.getBusinessName())
                .businessAddress(request.getBusinessAddress())
                .establishmentDate(request.getEstablishmentDate())
                .businessType(request.getBusinessType())
                .status(ServiceCenterVerification.VerificationStatus.PENDING)
                .statusUpdatedAt(LocalDateTime.now())
                .ntsStatus(validationResult.getNtsStatus())
                .ntsResponseCode(validationResult.getNtsResponseCode())
                .ntsResponseMessage(validationResult.getNtsResponseMessage())
                .ntsVerifiedAt(LocalDateTime.now())
                .isActive(true)
                .verificationAttempts(1)
                .lastVerificationAttemptAt(LocalDateTime.now())
                .nextAllowedVerificationAt(LocalDateTime.now().plusHours(RE_VERIFICATION_WAIT_HOURS))
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .createdBy(requestedBy)
                .updatedBy(requestedBy)
                .build();

            // TODO: 실제 구현에서는 데이터베이스에 저장
            Long verificationId = saveVerification(verification);

            // 다음 단계 결정
            ServiceCenterVerification.VerificationStatus nextStatus = verification.getNextRecommendedStatus();
            updateVerificationStatus(verificationId, nextStatus, "자동 단계 진행", requestedBy);

            log.info("인증 프로세스 시작 완료: 정비소ID={}, 인증ID={}, 상태={}", serviceCenterId, verificationId, nextStatus);

            return VerificationProcessResult.builder()
                .success(true)
                .verificationId(verificationId)
                .status(nextStatus)
                .message("인증 프로세스가 시작되었습니다")
                .nextSteps(generateNextSteps(verification))
                .estimatedCompletionDays(calculateEstimatedDays(verification))
                .build();

        } catch (Exception e) {
            log.error("인증 프로세스 시작 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return VerificationProcessResult.builder()
                .success(false)
                .verificationId(null)
                .status(ServiceCenterVerification.VerificationStatus.REJECTED)
                .errorMessage("인증 프로세스 시작 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 문서 업로드 및 인증 진행
     */
    @Transactional
    public VerificationProcessResult uploadDocumentAndProceed(Long verificationId, MultipartFile businessLicenseFile, 
                                                             MultipartFile additionalFile, Long uploadedBy) {
        log.info("인증 문서 업로드 및 진행: 인증ID={}", verificationId);

        try {
            ServiceCenterVerification verification = getVerificationById(verificationId);
            
            if (!verification.getStatus().isInProgress()) {
                throw new BusinessException("진행 중인 인증 프로세스가 아닙니다");
            }

            // 사업자등록증 업로드
            if (businessLicenseFile != null && !businessLicenseFile.isEmpty()) {
                VerificationDocumentService.DocumentUploadResult uploadResult = 
                    documentService.uploadBusinessLicense(verification.getServiceCenterId(), businessLicenseFile, uploadedBy);

                if (!uploadResult.isSuccess()) {
                    return VerificationProcessResult.builder()
                        .success(false)
                        .verificationId(verificationId)
                        .status(verification.getStatus())
                        .errorMessage("사업자등록증 업로드 실패: " + uploadResult.getErrorMessage())
                        .build();
                }

                // 업로드된 파일 경로 저장
                verification.setBusinessLicenseFilePath(uploadResult.getFilePath());
            }

            // 추가 문서 업로드
            if (additionalFile != null && !additionalFile.isEmpty()) {
                VerificationDocumentService.DocumentUploadResult uploadResult = 
                    documentService.uploadAdditionalDocument(verification.getServiceCenterId(), additionalFile, 
                                                           VerificationDocumentService.DocumentType.ADDITIONAL_DOCUMENT, uploadedBy);

                if (uploadResult.isSuccess()) {
                    verification.setAdditionalDocumentPath(uploadResult.getFilePath());
                }
            }

            // 다음 단계로 진행
            ServiceCenterVerification.VerificationStatus nextStatus = verification.getNextRecommendedStatus();
            updateVerificationStatus(verificationId, nextStatus, "문서 업로드 완료 후 자동 진행", uploadedBy);

            return VerificationProcessResult.builder()
                .success(true)
                .verificationId(verificationId)
                .status(nextStatus)
                .message("문서 업로드가 완료되었습니다")
                .nextSteps(generateNextSteps(verification))
                .estimatedCompletionDays(calculateEstimatedDays(verification))
                .build();

        } catch (Exception e) {
            log.error("문서 업로드 및 인증 진행 중 오류 발생: 인증ID={}, 오류={}", verificationId, e.getMessage(), e);
            return VerificationProcessResult.builder()
                .success(false)
                .verificationId(verificationId)
                .errorMessage("문서 업로드 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 관리자 승인
     */
    @Transactional
    public VerificationProcessResult approveVerification(Long verificationId, String approvalComment, Long approvedBy) {
        log.info("인증 승인 처리: 인증ID={}, 승인자={}", verificationId, approvedBy);

        try {
            ServiceCenterVerification verification = getVerificationById(verificationId);

            if (verification.getStatus() != ServiceCenterVerification.VerificationStatus.ADMIN_REVIEW) {
                throw new BusinessException("관리자 승인 대기 상태가 아닙니다");
            }

            // 승인 처리
            LocalDateTime now = LocalDateTime.now();
            verification.setStatus(ServiceCenterVerification.VerificationStatus.VERIFIED);
            verification.setStatusUpdatedAt(now);
            verification.setApprovedBy(approvedBy);
            verification.setApprovedAt(now);
            verification.setVerificationExpiryDate(LocalDate.now().plusYears(VERIFICATION_VALIDITY_YEARS));
            verification.setUpdatedAt(now);
            verification.setUpdatedBy(approvedBy);

            updateVerification(verification);

            // 서비스 센터 인증 상태 업데이트
            updateServiceCenterVerificationStatus(verification.getServiceCenterId(), true, approvedBy);

            log.info("인증 승인 완료: 인증ID={}, 만료일={}", verificationId, verification.getVerificationExpiryDate());

            return VerificationProcessResult.builder()
                .success(true)
                .verificationId(verificationId)
                .status(ServiceCenterVerification.VerificationStatus.VERIFIED)
                .message("인증이 승인되었습니다")
                .expiryDate(verification.getVerificationExpiryDate())
                .build();

        } catch (Exception e) {
            log.error("인증 승인 처리 중 오류 발생: 인증ID={}, 오류={}", verificationId, e.getMessage(), e);
            return VerificationProcessResult.builder()
                .success(false)
                .verificationId(verificationId)
                .errorMessage("인증 승인 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 관리자 거부
     */
    @Transactional
    public VerificationProcessResult rejectVerification(Long verificationId, String rejectionReason, Long rejectedBy) {
        log.info("인증 거부 처리: 인증ID={}, 거부자={}", verificationId, rejectedBy);

        try {
            ServiceCenterVerification verification = getVerificationById(verificationId);

            if (!verification.getStatus().isInProgress()) {
                throw new BusinessException("진행 중인 인증 프로세스가 아닙니다");
            }

            // 거부 처리
            LocalDateTime now = LocalDateTime.now();
            verification.setStatus(ServiceCenterVerification.VerificationStatus.REJECTED);
            verification.setStatusUpdatedAt(now);
            verification.setRejectedAt(now);
            verification.setRejectionReason(rejectionReason);
            verification.setIsActive(false);
            verification.setUpdatedAt(now);
            verification.setUpdatedBy(rejectedBy);

            updateVerification(verification);

            // 서비스 센터 인증 상태 업데이트
            updateServiceCenterVerificationStatus(verification.getServiceCenterId(), false, rejectedBy);

            log.info("인증 거부 완료: 인증ID={}, 거부사유={}", verificationId, rejectionReason);

            return VerificationProcessResult.builder()
                .success(true)
                .verificationId(verificationId)
                .status(ServiceCenterVerification.VerificationStatus.REJECTED)
                .message("인증이 거부되었습니다")
                .rejectionReason(rejectionReason)
                .build();

        } catch (Exception e) {
            log.error("인증 거부 처리 중 오류 발생: 인증ID={}, 오류={}", verificationId, e.getMessage(), e);
            return VerificationProcessResult.builder()
                .success(false)
                .verificationId(verificationId)
                .errorMessage("인증 거부 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 인증 상태 조회
     */
    public VerificationStatusResult getVerificationStatus(Long serviceCenterId) {
        log.debug("인증 상태 조회: 정비소ID={}", serviceCenterId);

        try {
            Optional<ServiceCenterVerification> verificationOpt = findActiveVerification(serviceCenterId);
            
            if (verificationOpt.isEmpty()) {
                return VerificationStatusResult.builder()
                    .serviceCenterId(serviceCenterId)
                    .hasActiveVerification(false)
                    .isVerified(false)
                    .message("진행 중인 인증이 없습니다")
                    .build();
            }

            ServiceCenterVerification verification = verificationOpt.get();

            return VerificationStatusResult.builder()
                .serviceCenterId(serviceCenterId)
                .verificationId(verification.getId())
                .hasActiveVerification(true)
                .isVerified(verification.isVerified())
                .status(verification.getStatus())
                .progress(verification.getVerificationProgress())
                .remainingSteps(verification.getRemainingSteps())
                .expiryDate(verification.getVerificationExpiryDate())
                .isExpired(verification.isExpired())
                .canReVerify(verification.canReVerify())
                .nextSteps(generateNextSteps(verification))
                .statusUpdatedAt(verification.getStatusUpdatedAt())
                .build();

        } catch (Exception e) {
            log.error("인증 상태 조회 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return VerificationStatusResult.builder()
                .serviceCenterId(serviceCenterId)
                .hasActiveVerification(false)
                .isVerified(false)
                .errorMessage("인증 상태 조회 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 만료된 인증 갱신
     */
    @Transactional
    public VerificationProcessResult renewExpiredVerification(Long serviceCenterId, Long requestedBy) {
        log.info("만료된 인증 갱신: 정비소ID={}", serviceCenterId);

        try {
            Optional<ServiceCenterVerification> verificationOpt = findActiveVerification(serviceCenterId);
            
            if (verificationOpt.isEmpty()) {
                throw new BusinessException("갱신할 인증 정보가 없습니다");
            }

            ServiceCenterVerification verification = verificationOpt.get();
            
            if (!verification.isExpired()) {
                throw new BusinessException("아직 만료되지 않은 인증입니다");
            }

            // 갱신 프로세스 시작 (기존 정보 재사용)
            VerificationStartRequest renewalRequest = VerificationStartRequest.builder()
                .businessNumber(verification.getBusinessNumber())
                .representativeName(verification.getRepresentativeName())
                .businessName(verification.getBusinessName())
                .businessAddress(verification.getBusinessAddress())
                .establishmentDate(verification.getEstablishmentDate())
                .businessType(verification.getBusinessType())
                .build();

            return startVerification(serviceCenterId, renewalRequest, requestedBy);

        } catch (Exception e) {
            log.error("인증 갱신 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return VerificationProcessResult.builder()
                .success(false)
                .verificationId(null)
                .errorMessage("인증 갱신 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    // === 내부 메서드들 ===

    private Optional<ServiceCenterVerification> findActiveVerification(Long serviceCenterId) {
        // TODO: 실제 구현에서는 데이터베이스에서 조회
        // 현재는 시뮬레이션 데이터 반환
        return Optional.empty();
    }

    private ServiceCenterVerification getVerificationById(Long verificationId) {
        // TODO: 실제 구현에서는 데이터베이스에서 조회
        throw new BusinessException("인증 정보를 찾을 수 없습니다: " + verificationId);
    }

    private Long saveVerification(ServiceCenterVerification verification) {
        // TODO: 실제 구현에서는 데이터베이스에 저장
        return 1L; // 임시 ID 반환
    }

    private void updateVerification(ServiceCenterVerification verification) {
        // TODO: 실제 구현에서는 데이터베이스 업데이트
    }

    private void updateVerificationStatus(Long verificationId, ServiceCenterVerification.VerificationStatus status, 
                                        String reason, Long updatedBy) {
        // TODO: 실제 구현에서는 상태 업데이트 및 히스토리 기록
        log.info("인증 상태 업데이트: ID={}, 상태={}, 사유={}", verificationId, status, reason);
    }

    private void updateServiceCenterVerificationStatus(Long serviceCenterId, Boolean isVerified, Long updatedBy) {
        // TODO: 실제 구현에서는 서비스 센터의 인증 상태 업데이트
        log.info("서비스 센터 인증 상태 업데이트: ID={}, 인증여부={}", serviceCenterId, isVerified);
    }

    private List<String> generateNextSteps(ServiceCenterVerification verification) {
        List<String> nextSteps = new java.util.ArrayList<>();

        switch (verification.getStatus()) {
            case PENDING:
            case DOCUMENT_REQUIRED:
                nextSteps.add("사업자등록증 이미지를 업로드해주세요");
                if (!verification.hasRequiredDocuments()) {
                    nextSteps.add("필요시 추가 증빙 문서를 업로드해주세요");
                }
                break;
            case IN_REVIEW:
                nextSteps.add("제출된 문서를 검토 중입니다");
                nextSteps.add("국세청 사업자 상태 조회가 진행됩니다");
                break;
            case NTS_VERIFICATION:
                nextSteps.add("국세청 조회 결과를 확인 중입니다");
                break;
            case ADMIN_REVIEW:
                nextSteps.add("관리자 최종 승인을 대기 중입니다");
                nextSteps.add("영업일 기준 1-2일 소요됩니다");
                break;
            case VERIFIED:
                nextSteps.add("인증이 완료되었습니다");
                if (verification.getVerificationExpiryDate() != null) {
                    nextSteps.add("인증 만료일: " + verification.getVerificationExpiryDate());
                }
                break;
            default:
                break;
        }

        return nextSteps;
    }

    private int calculateEstimatedDays(ServiceCenterVerification verification) {
        switch (verification.getStatus()) {
            case PENDING:
            case DOCUMENT_REQUIRED:
                return 5; // 문서 제출 + 검토 + 승인
            case IN_REVIEW:
            case NTS_VERIFICATION:
                return 3; // 검토 + 승인
            case ADMIN_REVIEW:
                return 2; // 승인만
            case VERIFIED:
                return 0; // 완료
            default:
                return -1; // 실패
        }
    }

    private String maskBusinessNumber(String businessNumber) {
        if (businessNumber == null || businessNumber.length() < 4) {
            return "***";
        }
        return businessNumber.substring(0, 3) + "-**-****" + businessNumber.substring(businessNumber.length() - 1);
    }

    // === 요청/응답 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class VerificationStartRequest {
        private String businessNumber;
        private String representativeName;
        private String businessName;
        private String businessAddress;
        private LocalDate establishmentDate;
        private String businessType;
    }

    @lombok.Data
    @lombok.Builder
    public static class VerificationProcessResult {
        private boolean success;
        private Long verificationId;
        private ServiceCenterVerification.VerificationStatus status;
        private String message;
        private String errorMessage;
        private List<String> nextSteps;
        private Integer estimatedCompletionDays;
        private LocalDate expiryDate;
        private String rejectionReason;
    }

    @lombok.Data
    @lombok.Builder
    public static class VerificationStatusResult {
        private Long serviceCenterId;
        private Long verificationId;
        private boolean hasActiveVerification;
        private boolean isVerified;
        private ServiceCenterVerification.VerificationStatus status;
        private Integer progress; // 0-100%
        private Integer remainingSteps;
        private LocalDate expiryDate;
        private boolean isExpired;
        private boolean canReVerify;
        private List<String> nextSteps;
        private LocalDateTime statusUpdatedAt;
        private String message;
        private String errorMessage;
    }
} 