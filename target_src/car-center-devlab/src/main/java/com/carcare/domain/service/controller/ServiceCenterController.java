package com.carcare.domain.service.controller;

import com.carcare.domain.service.dto.ServiceCenterDto;
import com.carcare.domain.service.service.ServiceCenterService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponses;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;
import com.carcare.common.exception.BusinessException;
import com.carcare.domain.service.dto.ServiceTypeDto;

/**
 * 정비소 관리 컨트롤러
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/service-centers")
@RequiredArgsConstructor
@Validated
@Tag(name = "ServiceCenter", description = "정비소 관리 API")
public class ServiceCenterController {

    private final ServiceCenterService serviceCenterService;

    /**
     * 정비소 등록
     */
    @PostMapping
    @Operation(summary = "정비소 등록", description = "새로운 정비소를 등록합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "정비소 등록 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "센터 매니저 또는 시스템 관리자 권한 필요"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "중복된 사업자등록번호")
    })
    public ResponseEntity<ApiResponse<ServiceCenterDto.Response>> createServiceCenter(
            @Valid @RequestBody ServiceCenterDto.Request request) {
        
        // 현재 사용자 정보 추출
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("정비소 등록 요청: 사용자ID={}, 역할={}, 정비소명={}", currentUser.getUserId(), currentUser.getRole(), request.getName());
        
        // 권한 확인 (CENTER_MANAGER 또는 SYSTEM_ADMIN)
        if (!"CENTER_MANAGER".equals(currentUser.getRole()) && !"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("센터 매니저 또는 시스템 관리자 권한이 필요합니다");
        }
        
        ServiceCenterDto.Response response = serviceCenterService.createServiceCenter(request, currentUser.getUserId());
        
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(ResponseUtils.success("정비소가 성공적으로 등록되었습니다.", response));
    }

    /**
     * 정비소 정보 수정
     */
    @PutMapping("/{id}")
    @Operation(summary = "정비소 정보 수정", description = "기존 정비소 정보를 수정합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "정비소 정보 수정 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "센터 매니저 또는 시스템 관리자 권한 필요"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "중복된 사업자등록번호")
    })
    public ResponseEntity<ApiResponse<ServiceCenterDto.Response>> updateServiceCenter(
            @Parameter(description = "정비소 ID", required = true) @PathVariable Long id,
            @Valid @RequestBody ServiceCenterDto.Request request) {
        
        // 현재 사용자 정보 추출
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("정비소 정보 수정 요청: 정비소ID={}, 사용자ID={}, 역할={}", id, currentUser.getUserId(), currentUser.getRole());
        
        // 권한 확인 (CENTER_MANAGER 또는 SYSTEM_ADMIN)
        if (!"CENTER_MANAGER".equals(currentUser.getRole()) && !"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("센터 매니저 또는 시스템 관리자 권한이 필요합니다");
        }
        
        ServiceCenterDto.Response response = serviceCenterService.updateServiceCenter(id, request, currentUser.getUserId());
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 정보가 성공적으로 수정되었습니다.", response));
    }

    /**
     * 정비소 삭제
     */
    @DeleteMapping("/{id}")
    @Operation(summary = "정비소 삭제", description = "정비소를 삭제합니다. (소프트 삭제)")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "정비소 삭제 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<Void>> deleteServiceCenter(
            @Parameter(description = "정비소 ID", required = true) @PathVariable Long id,
            @RequestHeader(value = "X-User-Id", defaultValue = "1") Long userId) {
        
        log.info("정비소 삭제 요청: 정비소ID={}, 사용자ID={}", id, userId);
        
        serviceCenterService.deleteServiceCenter(id, userId);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소가 성공적으로 삭제되었습니다.", null));
    }

    /**
     * 서비스 타입 목록 조회 (공개 API)
     */
    @GetMapping("/service-types")
    @Operation(summary = "서비스 타입 목록 조회", description = "제공 가능한 서비스 타입 목록을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "서비스 타입 조회 성공")
    })
    public ResponseEntity<ApiResponse<List<ServiceTypeDto>>> getServiceTypes() {
        
        log.debug("서비스 타입 목록 조회");
        
        // 임시 하드코딩된 서비스 타입 목록 (향후 DB 연동)
        List<ServiceTypeDto> serviceTypes = List.of(
            ServiceTypeDto.builder()
                .id(1L)
                .name("정기점검")
                .description("차량 정기 안전점검 서비스")
                .category("점검")
                .estimatedDuration(60)
                .basePrice(new BigDecimal("50000.00"))
                .isActive(true)
                .build(),
            ServiceTypeDto.builder()
                .id(2L)
                .name("엔진정비")
                .description("엔진 관련 정비 및 수리")
                .category("정비")
                .estimatedDuration(120)
                .basePrice(new BigDecimal("150000.00"))
                .isActive(true)
                .build(),
            ServiceTypeDto.builder()
                .id(3L)
                .name("브레이크정비")
                .description("브레이크 시스템 점검 및 정비")
                .category("정비")
                .estimatedDuration(90)
                .basePrice(new BigDecimal("80000.00"))
                .isActive(true)
                .build(),
            ServiceTypeDto.builder()
                .id(4L)
                .name("오일교환")
                .description("엔진오일 및 각종 오일 교환 서비스")
                .category("교체")
                .estimatedDuration(30)
                .basePrice(new BigDecimal("30000.00"))
                .isActive(true)
                .build(),
            ServiceTypeDto.builder()
                .id(5L)
                .name("타이어교체")
                .description("타이어 점검 및 교체 서비스")
                .category("교체")
                .estimatedDuration(45)
                .basePrice(new BigDecimal("40000.00"))
                .isActive(true)
                .build()
        );
        
        return ResponseEntity.ok(ResponseUtils.success("서비스 타입 목록을 성공적으로 조회했습니다.", serviceTypes));
    }

    /**
     * 정비소 상세 조회
     */
    @GetMapping("/{id}")
    @Operation(summary = "정비소 상세 조회", description = "특정 정비소의 상세 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "정비소 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "정비소를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<ServiceCenterDto.Response>> getServiceCenter(
            @Parameter(description = "정비소 ID", required = true) @PathVariable Long id) {
        
        log.debug("정비소 상세 조회 요청: 정비소ID={}", id);
        
        ServiceCenterDto.Response response = serviceCenterService.getServiceCenter(id);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 정보를 성공적으로 조회했습니다.", response));
    }

    /**
     * 정비소 검색 (페이징 포함)
     */
    @GetMapping("/search")
    @Operation(summary = "정비소 검색", description = "다양한 조건으로 정비소를 검색합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "검색 성공")
    })
    public ResponseEntity<ApiResponse<ServiceCenterDto.ListResponse>> searchServiceCenters(
            @Parameter(description = "검색 키워드") @RequestParam(required = false) String keyword,
            @Parameter(description = "정비소명 필터") @RequestParam(required = false) String name,
            @Parameter(description = "주소 필터") @RequestParam(required = false) String address,
            @Parameter(description = "특화서비스 필터") @RequestParam(required = false) String specializedService,
            @Parameter(description = "최소 평점") @RequestParam(required = false) @DecimalMin("0.0") @DecimalMax("5.0") BigDecimal minRating,
            @Parameter(description = "최대 평점") @RequestParam(required = false) @DecimalMin("0.0") @DecimalMax("5.0") BigDecimal maxRating,
            @Parameter(description = "인증 상태 필터") @RequestParam(required = false) Boolean isVerified,
            @Parameter(description = "활성 상태 필터") @RequestParam(required = false) Boolean isActive,
            @Parameter(description = "운영 상태 필터") @RequestParam(required = false) Boolean isOperating,
            @Parameter(description = "사업자등록번호") @RequestParam(required = false) String businessNumber,
            @Parameter(description = "대표자명") @RequestParam(required = false) String ownerName,
            @Parameter(description = "검색 중심 위도") @RequestParam(required = false) @DecimalMin("33.0") @DecimalMax("38.0") BigDecimal latitude,
            @Parameter(description = "검색 중심 경도") @RequestParam(required = false) @DecimalMin("125.0") @DecimalMax("132.0") BigDecimal longitude,
            @Parameter(description = "검색 반경 (km)") @RequestParam(required = false) @DecimalMin("0.1") @DecimalMax("50.0") Double radius,
            @Parameter(description = "정렬 기준 (name, rating, distance, createdAt)") @RequestParam(defaultValue = "createdAt") String sortBy,
            @Parameter(description = "정렬 방향 (ASC, DESC)") @RequestParam(defaultValue = "DESC") String sortDirection,
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") @Min(0) int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") @Min(1) @Max(100) int size) {
        
        log.debug("정비소 검색 요청: 키워드={}, 페이지={}, 크기={}", keyword, page, size);
        
        ServiceCenterDto.SearchCriteria criteria = ServiceCenterDto.SearchCriteria.builder()
            .keyword(keyword)
            .name(name)
            .address(address)
            .specializedService(specializedService)
            .minRating(minRating)
            .maxRating(maxRating)
            .isVerified(isVerified)
            .isActive(isActive)
            .isOperating(isOperating)
            .businessNumber(businessNumber)
            .ownerName(ownerName)
            .latitude(latitude)
            .longitude(longitude)
            .radius(radius)
            .sortBy(sortBy)
            .sortDirection(sortDirection)
            .page(page)
            .size(size)
            .build();
        
        ServiceCenterDto.ListResponse response = serviceCenterService.searchServiceCenters(criteria);
        
        return ResponseEntity.ok(ResponseUtils.success("정비소 검색을 성공적으로 완료했습니다.", response));
    }

    /**
     * 정비소 자동완성 검색
     */
    @GetMapping("/autocomplete")
    @Operation(summary = "정비소 자동완성 검색", description = "정비소명 자동완성을 위한 검색 결과를 반환합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "자동완성 검색 성공")
    })
    public ResponseEntity<ApiResponse<List<ServiceCenterDto.SimpleResponse>>> autocompleteServiceCenters(
            @Parameter(description = "검색 키워드", required = true) @RequestParam @NotBlank String keyword,
            @Parameter(description = "결과 개수 제한") @RequestParam(defaultValue = "10") @Min(1) @Max(50) int limit) {
        
        log.debug("정비소 자동완성 검색 요청: 키워드={}, 제한={}", keyword, limit);
        
        List<ServiceCenterDto.SimpleResponse> responses = serviceCenterService.autocompleteServiceCenters(keyword, limit);
        
        return ResponseEntity.ok(ResponseUtils.success("자동완성 검색을 성공적으로 완료했습니다.", responses));
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
} 