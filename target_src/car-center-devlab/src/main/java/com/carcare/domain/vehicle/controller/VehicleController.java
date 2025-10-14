package com.carcare.domain.vehicle.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import com.carcare.domain.vehicle.dto.VehicleDto;
import com.carcare.domain.vehicle.entity.Vehicle;
import com.carcare.domain.vehicle.service.VehicleService;
import com.carcare.domain.vehicle.service.VehicleMasterDataService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;

import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 차량 관리 컨트롤러
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/vehicles")
@Tag(name = "Vehicle", description = "차량 관리 API")
@Validated
@SecurityRequirement(name = "bearerAuth")
public class VehicleController {
    
    private final VehicleService vehicleService;
    private final VehicleMasterDataService masterDataService;
    
    @Autowired
    public VehicleController(VehicleService vehicleService, VehicleMasterDataService masterDataService) {
        this.vehicleService = vehicleService;
        this.masterDataService = masterDataService;
    }
    
    /**
     * 차량 등록
     */
    @Operation(summary = "차량 등록", description = "새로운 차량을 등록합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "201", description = "차량 등록 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "차량번호 중복")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<VehicleDto.Response>> registerVehicle(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Valid @RequestBody VehicleDto.Request request) {
        
        log.info("Vehicle registration request from user: {}", userPrincipal.getUserId());
        
        VehicleDto.Response response = vehicleService.registerVehicle(userPrincipal.getUserId(), request);
        
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ResponseUtils.success("차량이 성공적으로 등록되었습니다", response));
    }
    
    /**
     * 사용자의 차량 목록 조회
     */
    @Operation(summary = "차량 목록 조회", description = "로그인한 사용자의 차량 목록을 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 목록 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패")
    })
    @GetMapping
    public ResponseEntity<ApiResponse<List<VehicleDto.Response>>> getUserVehicles(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "활성 차량만 조회 여부") @RequestParam(required = false) Boolean activeOnly) {
        
        log.info("Getting vehicles for user: {}", userPrincipal.getUserId());
        
        List<VehicleDto.Response> vehicles = vehicleService.getUserVehicles(userPrincipal.getUserId(), activeOnly);
        
        return ResponseEntity.ok(ResponseUtils.success("차량 목록을 성공적으로 조회했습니다", vehicles));
    }
    
    /**
     * 차량 검색 (페이징 포함)
     */
    @Operation(summary = "차량 검색", description = "다양한 조건으로 차량을 검색합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 검색 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패")
    })
    @GetMapping("/search")
    public ResponseEntity<ApiResponse<VehicleDto.ListResponse>> searchVehicles(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "검색 키워드 (차량번호, 제조사, 모델)") @RequestParam(required = false) String keyword,
            @Parameter(description = "제조사") @RequestParam(required = false) String make,
            @Parameter(description = "모델") @RequestParam(required = false) String model,
            @Parameter(description = "연식 시작") @RequestParam(required = false) Integer yearFrom,
            @Parameter(description = "연식 끝") @RequestParam(required = false) Integer yearTo,
            @Parameter(description = "연료 타입") @RequestParam(required = false) String fuelType,
            @Parameter(description = "색상") @RequestParam(required = false) String color,
            @Parameter(description = "활성 상태") @RequestParam(required = false) Boolean isActive,
            @Parameter(description = "정렬 기준 (createdAt, year, make, model)") @RequestParam(defaultValue = "createdAt") String sortBy,
            @Parameter(description = "정렬 방향 (ASC, DESC)") @RequestParam(defaultValue = "DESC") String sortDirection,
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") int size) {
        
        log.info("Searching vehicles for user: {}", userPrincipal.getUserId());
        
        VehicleDto.SearchCriteria criteria = VehicleDto.SearchCriteria.builder()
                .keyword(keyword)
                .make(make)
                .model(model)
                .yearFrom(yearFrom)
                .yearTo(yearTo)
                .fuelType(fuelType != null ? Vehicle.FuelType.valueOf(fuelType.toUpperCase()) : null)
                .color(color)
                .isActive(isActive)
                .sortBy(sortBy)
                .sortDirection(sortDirection)
                .page(page)
                .size(size)
                .build();
        
        VehicleDto.ListResponse response = vehicleService.searchVehicles(userPrincipal.getUserId(), criteria);
        
        return ResponseEntity.ok(ResponseUtils.success("차량 검색을 성공적으로 완료했습니다", response));
    }
    
    /**
     * 차량 상세 조회 (ID)
     */
    @Operation(summary = "차량 상세 조회", description = "차량 ID로 상세 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "권한 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "차량을 찾을 수 없음")
    })
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<VehicleDto.Response>> getVehicle(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "차량 ID") @PathVariable Long id) {
        
        log.info("Getting vehicle: id={}, userId={}", id, userPrincipal.getUserId());
        
        VehicleDto.Response vehicle = vehicleService.getVehicle(userPrincipal.getUserId(), id);
        
        return ResponseEntity.ok(ResponseUtils.success("차량 정보를 성공적으로 조회했습니다", vehicle));
    }
    
    /**
     * 차량 상세 조회 (UUID)
     */
    @Operation(summary = "차량 상세 조회 (UUID)", description = "차량 UUID로 상세 정보를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "권한 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "차량을 찾을 수 없음")
    })
    @GetMapping("/uuid/{uuid}")
    public ResponseEntity<ApiResponse<VehicleDto.Response>> getVehicleByUuid(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "차량 UUID") @PathVariable UUID uuid) {
        
        log.info("Getting vehicle by UUID: {}, userId={}", uuid, userPrincipal.getUserId());
        
        VehicleDto.Response vehicle = vehicleService.getVehicleByUuid(userPrincipal.getUserId(), uuid);
        
        return ResponseEntity.ok(ResponseUtils.success("차량 정보를 성공적으로 조회했습니다", vehicle));
    }
    
    /**
     * 차량 정보 수정
     */
    @Operation(summary = "차량 정보 수정", description = "차량 정보를 수정합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 수정 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "권한 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "차량을 찾을 수 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "차량번호 중복")
    })
    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<VehicleDto.Response>> updateVehicle(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "차량 ID") @PathVariable Long id,
            @Valid @RequestBody VehicleDto.Request request) {
        
        log.info("Updating vehicle: id={}, userId={}", id, userPrincipal.getUserId());
        
        VehicleDto.Response response = vehicleService.updateVehicle(userPrincipal.getUserId(), id, request);
        
        return ResponseEntity.ok(ResponseUtils.success("차량 정보가 성공적으로 수정되었습니다", response));
    }
    
    /**
     * 차량 삭제
     */
    @Operation(summary = "차량 삭제", description = "차량을 삭제합니다. (소프트 삭제)")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 삭제 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "권한 없음"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "차량을 찾을 수 없음")
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteVehicle(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "차량 ID") @PathVariable Long id) {
        
        log.info("Deleting vehicle: id={}, userId={}", id, userPrincipal.getUserId());
        
        vehicleService.deleteVehicle(userPrincipal.getUserId(), id);
        
        return ResponseEntity.ok(ResponseUtils.<Void>success("차량이 성공적으로 삭제되었습니다"));
    }
    
    /**
     * 차량번호 중복 확인
     */
    @Operation(summary = "차량번호 중복 확인", description = "차량번호의 중복 여부를 확인합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "중복 확인 완료"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패")
    })
    @GetMapping("/check-license-plate")
    public ResponseEntity<ApiResponse<Boolean>> checkLicensePlate(
            @Parameter(description = "확인할 차량번호") @RequestParam String licensePlate) {
        
        log.info("Checking license plate: {}", licensePlate);
        
        boolean exists = vehicleService.isLicensePlateExists(licensePlate);
        
        return ResponseEntity.ok(ResponseUtils.success(
            exists ? "이미 등록된 차량번호입니다" : "사용 가능한 차량번호입니다", 
            exists));
    }
    
    /**
     * 사용자 차량 개수 조회
     */
    @Operation(summary = "사용자 차량 개수 조회", description = "로그인한 사용자의 등록된 차량 개수를 조회합니다.")
    @ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "차량 개수 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패")
    })
    @GetMapping("/count")
    public ResponseEntity<ApiResponse<Integer>> getUserVehicleCount(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Getting vehicle count for user: {}", userPrincipal.getUserId());
        
        int count = vehicleService.getUserVehicleCount(userPrincipal.getUserId());
        
        return ResponseEntity.ok(ResponseUtils.success("차량 개수를 성공적으로 조회했습니다", count));
    }
    
    /**
     * 고급 차량 필터링 (제조사/모델 기반)
     */
    @Operation(summary = "고급 차량 필터링", description = "제조사/모델 마스터 데이터를 활용한 고급 필터링을 수행합니다.")
    @GetMapping("/advanced-search")
    public ResponseEntity<ApiResponse<VehicleDto.ListResponse>> advancedSearchVehicles(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal,
            @Parameter(description = "제조사 ID") @RequestParam(required = false) Long brandId,
            @Parameter(description = "모델 ID") @RequestParam(required = false) Long modelId,
            @Parameter(description = "원산지") @RequestParam(required = false) String country,
            @Parameter(description = "차종") @RequestParam(required = false) String category,
            @Parameter(description = "연료 타입") @RequestParam(required = false) String fuelType,
            @Parameter(description = "연식 시작") @RequestParam(required = false) Integer yearFrom,
            @Parameter(description = "연식 끝") @RequestParam(required = false) Integer yearTo,
            @Parameter(description = "주행거리 최소") @RequestParam(required = false) Integer mileageMin,
            @Parameter(description = "주행거리 최대") @RequestParam(required = false) Integer mileageMax,
            @Parameter(description = "검색 키워드") @RequestParam(required = false) String keyword,
            @Parameter(description = "정렬 기준") @RequestParam(defaultValue = "createdAt") String sortBy,
            @Parameter(description = "정렬 방향") @RequestParam(defaultValue = "DESC") String sortDirection,
            @Parameter(description = "페이지 번호") @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "10") int size) {
        
        log.info("Advanced search for vehicles: brandId={}, modelId={}, country={}", brandId, modelId, country);
        
        // 마스터 데이터 기반 필터링 로직
        String resolvedMake = null;
        String resolvedModel = null;
        
        if (brandId != null) {
            var brand = masterDataService.getBrandById(brandId);
            resolvedMake = brand.getName();
        }
        
        if (modelId != null) {
            var model = masterDataService.getModelById(modelId);
            resolvedModel = model.getName();
            // 모델이 지정된 경우, 해당 모델의 제조사로 자동 설정
            if (resolvedMake == null) {
                var brand = masterDataService.getBrandById(model.getBrandId());
                resolvedMake = brand.getName();
            }
        }
        
        // 검색 조건 구성
        VehicleDto.SearchCriteria criteria = VehicleDto.SearchCriteria.builder()
                .keyword(keyword)
                .make(resolvedMake)
                .model(resolvedModel)
                .yearFrom(yearFrom)
                .yearTo(yearTo)
                .fuelType(fuelType != null ? Vehicle.FuelType.valueOf(fuelType.toUpperCase()) : null)
                .sortBy(sortBy)
                .sortDirection(sortDirection)
                .page(page)
                .size(size)
                .build();
        
        VehicleDto.ListResponse response = vehicleService.searchVehicles(userPrincipal.getUserId(), criteria);
        
        return ResponseEntity.ok(ResponseUtils.success("고급 차량 검색을 성공적으로 완료했습니다", response));
    }
    
    /**
     * 사용자 차량 통계 조회
     */
    @Operation(summary = "사용자 차량 통계", description = "사용자의 차량 통계 정보를 조회합니다.")
    @GetMapping("/statistics")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getUserVehicleStatistics(
            @AuthenticationPrincipal JwtUserPrincipal userPrincipal) {
        
        log.info("Getting vehicle statistics for user: {}", userPrincipal.getUserId());
        
        List<VehicleDto.Response> userVehicles = vehicleService.getUserVehicles(userPrincipal.getUserId(), Boolean.TRUE);
        
        // 통계 계산
        Map<String, Object> statistics = Map.of(
            "totalVehicles", userVehicles.size(),
            "brandDistribution", userVehicles.stream()
                .collect(Collectors.groupingBy(VehicleDto.Response::getMake, 
                        Collectors.counting())),
            "fuelTypeDistribution", userVehicles.stream()
                .collect(Collectors.groupingBy(VehicleDto.Response::getFuelType, 
                        Collectors.counting())),
            "averageAge", userVehicles.stream()
                .mapToInt(v -> java.time.LocalDateTime.now().getYear() - v.getYear())
                .average().orElse(0.0),
            "totalMileage", userVehicles.stream()
                .mapToInt(v -> v.getMileage() != null ? v.getMileage() : 0)
                .sum()
        );
        
        return ResponseEntity.ok(ResponseUtils.success("차량 통계를 성공적으로 조회했습니다", statistics));
    }
} 