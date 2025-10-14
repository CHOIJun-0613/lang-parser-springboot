package com.carcare.domain.service.controller;

import com.carcare.domain.service.service.ServiceCenterOperatingHoursService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

import java.util.List;

/**
 * 글로벌 운영시간 관리 컨트롤러
 * 모든 정비소에 대한 운영시간 조회 및 관리 API 제공
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/service-centers/operating-hours")
@RequiredArgsConstructor
@Validated
@Tag(name = "Global Operating Hours", description = "글로벌 운영시간 관리 API")
public class GlobalOperatingHoursController {

    private final ServiceCenterOperatingHoursService operatingHoursService;

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

        log.info("일괄 운영 상태 업데이트 요청");

        ServiceCenterOperatingHoursService.BatchUpdateResult result = 
            operatingHoursService.batchUpdateOperatingStatus();

        if (result.isSuccess()) {
            return ResponseEntity.ok(ResponseUtils.success(result.getMessage(), result));
        } else {
            return ResponseEntity.badRequest().body(ResponseUtils.error(result.getErrorMessage(), result));
        }
    }
} 