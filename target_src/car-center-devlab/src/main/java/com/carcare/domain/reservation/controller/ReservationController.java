package com.carcare.domain.reservation.controller;

import com.carcare.domain.reservation.dto.ReservationDto;
import com.carcare.domain.reservation.service.ReservationService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponses;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.util.List;

/**
 * 예약 관리 컨트롤러
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/reservations")
@RequiredArgsConstructor
@Validated
@Tag(name = "Reservation", description = "예약 관리 API")
public class ReservationController {

    private final ReservationService reservationService;

    /**
     * SecurityContext에서 현재 사용자 ID 추출
     */
    private Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof JwtUserPrincipal) {
            JwtUserPrincipal userPrincipal = (JwtUserPrincipal) authentication.getPrincipal();
            return userPrincipal.getUserId();
        }
        throw new RuntimeException("인증된 사용자 정보를 찾을 수 없습니다.");
    }

    /**
     * 예약 목록 조회 (페이징)
     */
    @GetMapping
    @Operation(summary = "예약 목록 조회", description = "모든 예약을 페이징하여 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<ReservationDto.ListResponse>> getAllReservations(
            @Parameter(description = "페이지 번호") @RequestParam(defaultValue = "0") @Min(0) int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") @Min(1) @Max(100) int size) {
        
        log.debug("예약 목록 조회: 페이지={}, 크기={}", page, size);
        
        ReservationDto.SearchCriteria criteria = ReservationDto.SearchCriteria.builder()
            .page(page)
            .size(size)
            .sortBy("scheduledDate")
            .sortDirection("DESC")
            .build();
        
        ReservationDto.ListResponse response = reservationService.searchReservations(criteria);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 목록을 성공적으로 조회했습니다.", response));
    }

    /**
     * 예약 생성
     */
    @PostMapping
    @Operation(summary = "예약 생성", description = "새로운 예약을 생성합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "예약 생성 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "예약 시간 충돌")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> createReservation(
            @Valid @RequestBody ReservationDto.CreateRequest request) {
        
        Long userId = getCurrentUserId();
        log.info("예약 생성 요청: 사용자={}, 정비소={}", userId, request.getServiceCenterId());
        
        ReservationDto.Response response = reservationService.createReservation(request, userId);
        
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(ResponseUtils.success("예약이 성공적으로 생성되었습니다.", response));
    }

    /**
     * 예약 수정
     */
    @PutMapping("/{id}")
    @Operation(summary = "예약 수정", description = "기존 예약을 수정합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "예약 수정 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "수정 권한 없음")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> updateReservation(
            @Parameter(description = "예약 ID") @PathVariable Long id,
            @Valid @RequestBody ReservationDto.UpdateRequest request) {
        
        Long userId = getCurrentUserId();
        log.info("예약 수정 요청: ID={}, 사용자={}", id, userId);
        
        ReservationDto.Response response = reservationService.updateReservation(id, request, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("예약이 성공적으로 수정되었습니다.", response));
    }

    /**
     * 예약 상태 변경 (ID)
     */
    @PatchMapping("/{id}/status")
    @Operation(summary = "예약 상태 변경 (ID)", description = "예약 ID로 예약의 상태를 변경합니다. (정비소 관리자용)")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "상태 변경 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 상태 변경"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> updateReservationStatus(
            @Parameter(description = "예약 ID") @PathVariable Long id,
            @Valid @RequestBody ReservationDto.StatusUpdateRequest request) {
        
        log.info("예약 상태 변경 요청: ID={}, 상태={}", id, request.getStatus());
        
        ReservationDto.Response response = reservationService.updateReservationStatus(id, request);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 상태가 성공적으로 변경되었습니다.", response));
    }

    /**
     * 예약 상태 변경 (UUID)
     */
    @PatchMapping("/uuid/{uuid}/status")
    @Operation(summary = "예약 상태 변경 (UUID)", description = "예약 UUID로 예약의 상태를 변경합니다. (정비소 관리자용)")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "상태 변경 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 상태 변경"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> updateReservationStatusByUuid(
            @Parameter(description = "예약 UUID") @PathVariable String uuid,
            @Valid @RequestBody ReservationDto.StatusUpdateRequest request) {
        
        log.info("예약 상태 변경 요청: UUID={}, 상태={}", uuid, request.getStatus());
        
        ReservationDto.Response response = reservationService.updateReservationStatusByUuid(uuid, request);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 상태가 성공적으로 변경되었습니다.", response));
    }

    /**
     * 예약 취소
     */
    @DeleteMapping("/{id}")
    @Operation(summary = "예약 취소", description = "예약을 취소합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "예약 취소 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "취소 권한 없음")
    })
    public ResponseEntity<ApiResponse<Void>> cancelReservation(
            @Parameter(description = "예약 ID") @PathVariable Long id,
            @Parameter(description = "취소 사유") @RequestParam(required = false) String reason) {
        
        Long userId = getCurrentUserId();
        log.info("예약 취소 요청: ID={}, 사용자={}", id, userId);
        
        reservationService.cancelReservation(id, reason, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("예약이 성공적으로 취소되었습니다."));
    }

    /**
     * 예약 상세 조회 (ID)
     */
    @GetMapping("/{id}")
    @Operation(summary = "예약 상세 조회 (ID)", description = "예약 ID로 예약의 상세 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> getReservation(
            @Parameter(description = "예약 ID") @PathVariable Long id) {
        
        log.debug("예약 상세 조회: ID={}", id);
        
        ReservationDto.Response response = reservationService.getReservation(id);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 정보를 성공적으로 조회했습니다.", response));
    }

    /**
     * 예약 상세 조회 (UUID)
     */
    @GetMapping("/uuid/{uuid}")
    @Operation(summary = "예약 상세 조회 (UUID)", description = "예약 UUID로 예약의 상세 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "예약을 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Response>> getReservationByUuid(
            @Parameter(description = "예약 UUID") @PathVariable String uuid) {
        
        log.debug("예약 상세 조회: UUID={}", uuid);
        
        ReservationDto.Response response = reservationService.getReservationByUuid(uuid);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 정보를 성공적으로 조회했습니다.", response));
    }

    /**
     * 예약 검색
     */
    @GetMapping("/search")
    @Operation(summary = "예약 검색", description = "다양한 조건으로 예약을 검색합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "검색 성공")
    })
    public ResponseEntity<ApiResponse<ReservationDto.ListResponse>> searchReservations(
            @Parameter(description = "고객 ID") @RequestParam(required = false) Long userId,
            @Parameter(description = "정비소 ID") @RequestParam(required = false) Long serviceCenterId,
            @Parameter(description = "차량 ID") @RequestParam(required = false) Long vehicleId,
            @Parameter(description = "예약 상태") @RequestParam(required = false) String status,
            @Parameter(description = "검색 시작 날짜 (yyyy-MM-dd)") @RequestParam(required = false) String startDate,
            @Parameter(description = "검색 종료 날짜 (yyyy-MM-dd)") @RequestParam(required = false) String endDate,
            @Parameter(description = "정렬 기준") @RequestParam(defaultValue = "scheduledDate") String sortBy,
            @Parameter(description = "정렬 방향") @RequestParam(defaultValue = "ASC") String sortDirection,
            @Parameter(description = "페이지 번호") @RequestParam(defaultValue = "0") @Min(0) int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") @Min(1) @Max(100) int size) {
        
        log.debug("예약 검색 요청: 사용자={}, 정비소={}, 페이지={}", userId, serviceCenterId, page);
        
        ReservationDto.SearchCriteria criteria = ReservationDto.SearchCriteria.builder()
            .userId(userId)
            .serviceCenterId(serviceCenterId)
            .vehicleId(vehicleId)
            .status(status != null ? com.carcare.domain.reservation.entity.Reservation.ReservationStatus.valueOf(status) : null)
            .startDate(startDate != null ? java.time.LocalDateTime.parse(startDate + "T00:00:00") : null)
            .endDate(endDate != null ? java.time.LocalDateTime.parse(endDate + "T23:59:59") : null)
            .sortBy(sortBy)
            .sortDirection(sortDirection)
            .page(page)
            .size(size)
            .build();
        
        ReservationDto.ListResponse response = reservationService.searchReservations(criteria);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 검색을 성공적으로 완료했습니다.", response));
    }

    /**
     * 내 예약 목록 조회
     */
    @GetMapping("/my")
    @Operation(summary = "내 예약 목록", description = "현재 사용자의 예약 목록을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<List<ReservationDto.Response>>> getMyReservations() {
        
        Long userId = getCurrentUserId();
        log.debug("내 예약 목록 조회: 사용자={}", userId);
        
        List<ReservationDto.Response> response = reservationService.getUserReservations(userId);
        
        return ResponseEntity.ok(ResponseUtils.success("내 예약 목록을 성공적으로 조회했습니다.", response));
    }

    /**
     * 정비소별 예약 목록 조회
     */
    @GetMapping("/service-center/{serviceCenterId}")
    @Operation(summary = "정비소별 예약 목록", description = "특정 정비소의 예약 목록을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<List<ReservationDto.Response>>> getServiceCenterReservations(
            @Parameter(description = "정비소 ID") @PathVariable Long serviceCenterId) {
        
        log.debug("정비소별 예약 목록 조회: 정비소={}", serviceCenterId);
        
        List<ReservationDto.Response> response = reservationService.getServiceCenterReservations(serviceCenterId);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 예약 목록을 성공적으로 조회했습니다.", response));
    }

    /**
     * 오늘 예약 목록 조회
     */
    @GetMapping("/today")
    @Operation(summary = "오늘 예약 목록", description = "오늘 날짜의 모든 예약을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<List<ReservationDto.Response>>> getTodayReservations() {
        
        log.debug("오늘 예약 목록 조회");
        
        List<ReservationDto.Response> response = reservationService.getTodayReservations();
        
        return ResponseEntity.ok(ResponseUtils.success("오늘 예약 목록을 성공적으로 조회했습니다.", response));
    }

    /**
     * 예약 통계 조회
     */
    @GetMapping("/statistics")
    @Operation(summary = "예약 통계", description = "예약 통계 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "조회 성공")
    })
    public ResponseEntity<ApiResponse<ReservationDto.Statistics>> getReservationStatistics(
            @Parameter(description = "정비소 ID (선택사항)") @RequestParam(required = false) Long serviceCenterId) {
        
        log.debug("예약 통계 조회: 정비소={}", serviceCenterId);
        
        ReservationDto.Statistics response = reservationService.getReservationStatistics(serviceCenterId);
        
        return ResponseEntity.ok(ResponseUtils.success("예약 통계를 성공적으로 조회했습니다.", response));
    }
} 