package com.carcare.domain.service.controller;

import com.carcare.domain.service.service.ServiceCenterOperatingHoursService;
import com.carcare.domain.service.service.SpecialOperatingHoursManagementService;
import com.carcare.domain.service.entity.ServiceCenterOperatingHours;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.format.annotation.DateTimeFormat;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponses;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import com.carcare.common.exception.BusinessException;

/**
 * 정비소 운영시간 관리 컨트롤러
 * 운영시간 CRUD, 상태 조회, 특별 운영시간 관리 등의 API 제공
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/service-centers/{serviceCenterId}/operating-hours")
@RequiredArgsConstructor
@Validated
@Tag(name = "ServiceCenter Operating Hours", description = "정비소 운영시간 관리 API")
public class ServiceCenterOperatingHoursController {

    private final ServiceCenterOperatingHoursService operatingHoursService;
    private final SpecialOperatingHoursManagementService specialHoursManagementService;

    /**
     * 기본 운영시간 생성
     */
    @PostMapping("/initialize")
    @Operation(summary = "기본 운영시간 생성", description = "정비소에 기본 운영시간을 설정합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "운영시간 생성 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 운영시간이 설정됨")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.OperatingHoursResult>> initializeOperatingHours(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {

        log.info("기본 운영시간 생성 요청: 정비소ID={}", serviceCenterId);

        ServiceCenterOperatingHoursService.OperatingHoursResult result = 
            operatingHoursService.createDefaultOperatingHours(serviceCenterId, userId);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("기본 운영시간이 생성되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 운영시간 조회
     */
    @GetMapping
    @Operation(summary = "운영시간 조회", description = "정비소의 운영시간 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.OperatingHoursDetailResult>> getOperatingHours(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId) {

        log.debug("운영시간 조회: 정비소ID={}", serviceCenterId);

        ServiceCenterOperatingHoursService.OperatingHoursDetailResult result = 
            operatingHoursService.getOperatingHours(serviceCenterId);

        return ResponseEntity.ok(ResponseUtils.success("운영시간 조회가 완료되었습니다", result));
    }

    /**
     * 운영시간 업데이트
     */
    @PutMapping
    @Operation(summary = "운영시간 업데이트", description = "정비소의 운영시간을 업데이트합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "업데이트 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "운영시간 정보를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.OperatingHoursResult>> updateOperatingHours(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Valid @RequestBody OperatingHoursUpdateRequest request,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {

        log.info("운영시간 업데이트 요청: 정비소ID={}", serviceCenterId);

        ServiceCenterOperatingHoursService.OperatingHoursUpdateRequest serviceRequest = 
            ServiceCenterOperatingHoursService.OperatingHoursUpdateRequest.builder()
                .weeklySchedule(request.getWeeklySchedule())
                .specialDates(request.getSpecialDates())
                .holidays(request.getHolidays())
                .regularClosedDays(request.getRegularClosedDays())
                .temporaryClosures(request.getTemporaryClosures())
                .defaultSettings(request.getDefaultSettings())
                .build();

        ServiceCenterOperatingHoursService.OperatingHoursResult result = 
            operatingHoursService.updateOperatingHours(serviceCenterId, serviceRequest, userId);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("운영시간이 업데이트되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 현재 운영 상태 조회
     */
    @GetMapping("/status")
    @Operation(summary = "현재 운영 상태 조회", description = "정비소의 현재 운영 상태를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "상태 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.OperatingStatusResult>> getCurrentStatus(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId) {

        log.debug("현재 운영 상태 조회: 정비소ID={}", serviceCenterId);

        ServiceCenterOperatingHoursService.OperatingStatusResult result = 
            operatingHoursService.getCurrentOperatingStatus(serviceCenterId);

        return ResponseEntity.ok(ResponseUtils.success("운영 상태 조회가 완료되었습니다", result));
    }

    /**
     * 예약 가능한 시간대 조회
     */
    @GetMapping("/reservation-slots")
    @Operation(summary = "예약 가능한 시간대 조회", description = "지정된 날짜의 예약 가능한 시간대를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 날짜 형식"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.ReservationSlotsResult>> getAvailableReservationSlots(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Parameter(description = "조회할 날짜 (yyyy-MM-dd)") 
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {

        log.debug("예약 가능 시간대 조회: 정비소ID={}, 날짜={}", serviceCenterId, date);

        ServiceCenterOperatingHoursService.ReservationSlotsResult result = 
            operatingHoursService.getAvailableReservationSlots(serviceCenterId, date);

        return ResponseEntity.ok(ResponseUtils.success("예약 가능 시간대 조회가 완료되었습니다", result));
    }

    /**
     * 특별 운영시간 등록
     */
    @PostMapping("/special")
    @Operation(summary = "특별 운영시간 등록", description = "특정 날짜의 특별 운영시간을 등록합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "이미 설정된 날짜")
    })
    public ResponseEntity<ApiResponse<SpecialOperatingHoursManagementService.SpecialHoursResult>> addSpecialOperatingHours(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Valid @RequestBody SpecialHoursRequest request) {

        log.info("특별 운영시간 등록: 정비소ID={}, 날짜={}", serviceCenterId, request.getDate());

        SpecialOperatingHoursManagementService.SpecialHoursRequest serviceRequest = 
            SpecialOperatingHoursManagementService.SpecialHoursRequest.builder()
                .date(request.getDate())
                .isOpen(request.isOpen())
                .timeSlots(request.getTimeSlots())
                .reason(request.getReason())
                .note(request.getNote())
                .replaceExisting(request.isReplaceExisting())
                .build();

        SpecialOperatingHoursManagementService.SpecialHoursResult result = 
            specialHoursManagementService.addSpecialOperatingHours(serviceCenterId, serviceRequest);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("특별 운영시간이 등록되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 임시 휴무 등록
     */
    @PostMapping("/temporary-closure")
    @Operation(summary = "임시 휴무 등록", description = "임시 휴무 기간을 등록합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "등록 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "겹치는 휴무 기간 존재")
    })
    public ResponseEntity<ApiResponse<SpecialOperatingHoursManagementService.TemporaryClosureResult>> addTemporaryClosure(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Valid @RequestBody TemporaryClosureRequest request) {

        log.info("임시 휴무 등록: 정비소ID={}, 기간={} ~ {}", serviceCenterId, request.getStartDate(), request.getEndDate());

        SpecialOperatingHoursManagementService.TemporaryClosureRequest serviceRequest = 
            SpecialOperatingHoursManagementService.TemporaryClosureRequest.builder()
                .startDate(request.getStartDate())
                .endDate(request.getEndDate())
                .reason(request.getReason())
                .note(request.getNote())
                .allowOverlap(request.isAllowOverlap())
                .build();

        SpecialOperatingHoursManagementService.TemporaryClosureResult result = 
            specialHoursManagementService.addTemporaryClosure(serviceCenterId, serviceRequest);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("임시 휴무가 등록되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 임시 휴무 제거
     */
    @DeleteMapping("/temporary-closure")
    @Operation(summary = "임시 휴무 제거", description = "지정된 기간의 임시 휴무를 제거합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "제거 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "해당 휴무 기간을 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<SpecialOperatingHoursManagementService.TemporaryClosureResult>> removeTemporaryClosure(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Parameter(description = "시작 날짜") @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @Parameter(description = "종료 날짜") @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {

        log.info("임시 휴무 제거: 정비소ID={}, 기간={} ~ {}", serviceCenterId, startDate, endDate);

        SpecialOperatingHoursManagementService.TemporaryClosureResult result = 
            specialHoursManagementService.removeTemporaryClosure(serviceCenterId, startDate, endDate);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success("임시 휴무가 제거되었습니다", result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 한국 공휴일 자동 적용
     */
    @PostMapping("/korean-holidays/{year}")
    @Operation(summary = "한국 공휴일 자동 적용", description = "지정된 연도의 한국 공휴일을 자동으로 적용합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "적용 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 연도")
    })
    public ResponseEntity<ApiResponse<SpecialOperatingHoursManagementService.HolidayManagementResult>> applyKoreanHolidays(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Parameter(description = "연도") @PathVariable @Min(2020) @Max(2030) int year,
            @Parameter(description = "기존 공휴일 교체 여부") @RequestParam(defaultValue = "true") boolean replaceExisting) {

        log.info("한국 공휴일 적용: 정비소ID={}, 연도={}, 교체={}", serviceCenterId, year, replaceExisting);

        SpecialOperatingHoursManagementService.HolidayManagementResult result = 
            specialHoursManagementService.applyKoreanHolidays(serviceCenterId, year, replaceExisting);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success(result.getMessage(), result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 특별 운영시간 목록 조회
     */
    @GetMapping("/special")
    @Operation(summary = "특별 운영시간 목록 조회", description = "지정된 기간의 특별 운영시간을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 날짜 형식")
    })
    public ResponseEntity<ApiResponse<SpecialOperatingHoursManagementService.SpecialHoursListResult>> getSpecialOperatingHours(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId,
            @Parameter(description = "시작 날짜") @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate fromDate,
            @Parameter(description = "종료 날짜") @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate toDate) {

        log.debug("특별 운영시간 목록 조회: 정비소ID={}, 기간={} ~ {}", serviceCenterId, fromDate, toDate);

        SpecialOperatingHoursManagementService.SpecialHoursListResult result = 
            specialHoursManagementService.getSpecialOperatingHours(serviceCenterId, fromDate, toDate);

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success(result.getMessage(), result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }

    /**
     * 운영 중인 정비소 목록 조회
     */
    @GetMapping("/currently-open")
    @Operation(summary = "현재 운영 중인 정비소 목록", description = "현재 시점에 운영 중인 정비소 ID 목록을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<List<Long>>> getCurrentlyOpenServiceCenters() {

        log.debug("현재 운영 중인 정비소 목록 조회");

        List<Long> openServiceCenters = operatingHoursService.getCurrentlyOpenServiceCenters();

        return ResponseEntity.ok(ResponseUtils.success("현재 운영 중인 정비소 목록 조회가 완료되었습니다", openServiceCenters));
    }

    /**
     * 일괄 운영 상태 업데이트 (관리자용)
     */
    @PostMapping("/batch-update-status")
    @Operation(summary = "일괄 운영 상태 업데이트", description = "모든 정비소의 운영 상태를 일괄 업데이트합니다. (관리자 전용)")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "업데이트 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "관리자 권한 필요")
    })
    public ResponseEntity<ApiResponse<ServiceCenterOperatingHoursService.BatchUpdateResult>> batchUpdateOperatingStatus() {

        // 현재 사용자 정보 추출
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("일괄 운영 상태 업데이트 요청: 관리자ID={}, 역할={}", currentUser.getUserId(), currentUser.getRole());

        // 관리자 권한 확인
        if (!"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("시스템 관리자 권한이 필요합니다");
        }

        ServiceCenterOperatingHoursService.BatchUpdateResult result = 
            operatingHoursService.batchUpdateOperatingStatus();

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success(result.getMessage(), result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
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
    public static class OperatingHoursUpdateRequest {
        private Map<String, ServiceCenterOperatingHours.DayOperatingHours> weeklySchedule;
        private Map<String, ServiceCenterOperatingHours.SpecialOperatingHours> specialDates;
        private List<String> holidays;
        private List<String> regularClosedDays;
        private List<ServiceCenterOperatingHours.TemporaryClosurePeriod> temporaryClosures;
        private ServiceCenterOperatingHours.DefaultSettings defaultSettings;
    }

    @lombok.Data
    public static class SpecialHoursRequest {
        @NotNull(message = "날짜는 필수입니다")
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        private LocalDate date;

        private boolean isOpen = false;

        private List<ServiceCenterOperatingHours.TimeSlot> timeSlots;

        @Size(max = 100, message = "사유는 100자 이하여야 합니다")
        private String reason;

        @Size(max = 200, message = "메모는 200자 이하여야 합니다")
        private String note;

        private boolean replaceExisting = false;
    }

    @lombok.Data
    public static class TemporaryClosureRequest {
        @NotNull(message = "시작 날짜는 필수입니다")
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        private LocalDate startDate;

        @NotNull(message = "종료 날짜는 필수입니다")
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        private LocalDate endDate;

        @NotBlank(message = "휴무 사유는 필수입니다")
        @Size(max = 100, message = "휴무 사유는 100자 이하여야 합니다")
        private String reason;

        @Size(max = 200, message = "메모는 200자 이하여야 합니다")
        private String note;

        private boolean allowOverlap = false;
    }
} 