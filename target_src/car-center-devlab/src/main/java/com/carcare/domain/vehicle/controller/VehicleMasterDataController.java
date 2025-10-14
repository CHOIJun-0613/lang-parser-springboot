package com.carcare.domain.vehicle.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.carcare.domain.vehicle.entity.VehicleBrand;
import com.carcare.domain.vehicle.entity.VehicleModel;
import com.carcare.domain.vehicle.service.VehicleMasterDataService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;

import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.Map;

/**
 * 차량 마스터 데이터 컨트롤러 (공개 API)
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/vehicles/master")
@Tag(name = "Vehicle Master Data", description = "차량 제조사 및 모델 마스터 데이터 API")
public class VehicleMasterDataController {
    
    private final VehicleMasterDataService masterDataService;
    
    @Autowired
    public VehicleMasterDataController(VehicleMasterDataService masterDataService) {
        this.masterDataService = masterDataService;
    }
    
    /**
     * 모든 활성 제조사 목록 조회
     */
    @Operation(summary = "제조사 목록 조회", description = "모든 활성 제조사 목록을 조회합니다.")
    @GetMapping("/brands")
    public ResponseEntity<ApiResponse<List<VehicleBrand>>> getAllBrands() {
        log.info("Getting all active vehicle brands");
        
        List<VehicleBrand> brands = masterDataService.getAllActiveBrands();
        
        return ResponseEntity.ok(ResponseUtils.success("제조사 목록을 성공적으로 조회했습니다", brands));
    }
    
    /**
     * 원산지별 제조사 목록 조회
     */
    @Operation(summary = "원산지별 제조사 조회", description = "특정 원산지의 제조사 목록을 조회합니다.")
    @GetMapping("/brands/country/{country}")
    public ResponseEntity<ApiResponse<List<VehicleBrand>>> getBrandsByCountry(
            @Parameter(description = "원산지") @PathVariable String country) {
        
        log.info("Getting vehicle brands by country: {}", country);
        
        List<VehicleBrand> brands = masterDataService.getBrandsByCountry(country);
        
        return ResponseEntity.ok(ResponseUtils.success(
            String.format("%s 제조사 목록을 성공적으로 조회했습니다", country), brands));
    }
    
    /**
     * 제조사 검색
     */
    @Operation(summary = "제조사 검색", description = "제조사명으로 검색합니다.")
    @GetMapping("/brands/search")
    public ResponseEntity<ApiResponse<List<VehicleBrand>>> searchBrands(
            @Parameter(description = "검색 키워드") @RequestParam String keyword) {
        
        log.info("Searching vehicle brands with keyword: {}", keyword);
        
        List<VehicleBrand> brands = masterDataService.searchBrands(keyword);
        
        return ResponseEntity.ok(ResponseUtils.success("제조사 검색을 완료했습니다", brands));
    }
    
    /**
     * 제조사 상세 조회
     */
    @Operation(summary = "제조사 상세 조회", description = "제조사 상세 정보를 조회합니다.")
    @GetMapping("/brands/{brandId}")
    public ResponseEntity<ApiResponse<VehicleBrand>> getBrandById(
            @Parameter(description = "제조사 ID") @PathVariable Long brandId) {
        
        log.info("Getting vehicle brand by ID: {}", brandId);
        
        VehicleBrand brand = masterDataService.getBrandById(brandId);
        
        return ResponseEntity.ok(ResponseUtils.success("제조사 정보를 성공적으로 조회했습니다", brand));
    }
    
    /**
     * 제조사별 모델 목록 조회
     */
    @Operation(summary = "제조사별 모델 조회", description = "특정 제조사의 모든 모델 목록을 조회합니다.")
    @GetMapping("/brands/{brandId}/models")
    public ResponseEntity<ApiResponse<List<VehicleModel>>> getModelsByBrandId(
            @Parameter(description = "제조사 ID") @PathVariable Long brandId,
            @Parameter(description = "차종 필터") @RequestParam(required = false) String category) {
        
        log.info("Getting vehicle models by brand ID: {}, category: {}", brandId, category);
        
        List<VehicleModel> models;
        if (category != null && !category.trim().isEmpty()) {
            models = masterDataService.getModelsByBrandAndCategory(brandId, category);
        } else {
            models = masterDataService.getModelsByBrandId(brandId);
        }
        
        return ResponseEntity.ok(ResponseUtils.success("모델 목록을 성공적으로 조회했습니다", models));
    }
    
    /**
     * 모든 활성 모델 목록 조회 (제조사 정보 포함)
     */
    @Operation(summary = "전체 모델 조회", description = "모든 활성 모델 목록을 제조사 정보와 함께 조회합니다.")
    @GetMapping("/models")
    public ResponseEntity<ApiResponse<List<VehicleModel>>> getAllModels() {
        log.info("Getting all active vehicle models with brand information");
        
        List<VehicleModel> models = masterDataService.getAllActiveModelsWithBrand();
        
        return ResponseEntity.ok(ResponseUtils.success("전체 모델 목록을 성공적으로 조회했습니다", models));
    }
    
    /**
     * 차종별 모델 목록 조회
     */
    @Operation(summary = "차종별 모델 조회", description = "특정 차종의 모델 목록을 조회합니다.")
    @GetMapping("/models/category/{category}")
    public ResponseEntity<ApiResponse<List<VehicleModel>>> getModelsByCategory(
            @Parameter(description = "차종") @PathVariable String category) {
        
        log.info("Getting vehicle models by category: {}", category);
        
        List<VehicleModel> models = masterDataService.getModelsByCategory(category);
        
        return ResponseEntity.ok(ResponseUtils.success(
            String.format("%s 차종 모델 목록을 성공적으로 조회했습니다", category), models));
    }
    
    /**
     * 모델 검색
     */
    @Operation(summary = "모델 검색", description = "모델명으로 검색합니다.")
    @GetMapping("/models/search")
    public ResponseEntity<ApiResponse<List<VehicleModel>>> searchModels(
            @Parameter(description = "검색 키워드") @RequestParam String keyword) {
        
        log.info("Searching vehicle models with keyword: {}", keyword);
        
        List<VehicleModel> models = masterDataService.searchModels(keyword);
        
        return ResponseEntity.ok(ResponseUtils.success("모델 검색을 완료했습니다", models));
    }
    
    /**
     * 모델 상세 조회
     */
    @Operation(summary = "모델 상세 조회", description = "모델 상세 정보를 조회합니다.")
    @GetMapping("/models/{modelId}")
    public ResponseEntity<ApiResponse<VehicleModel>> getModelById(
            @Parameter(description = "모델 ID") @PathVariable Long modelId) {
        
        log.info("Getting vehicle model by ID: {}", modelId);
        
        VehicleModel model = masterDataService.getModelById(modelId);
        
        return ResponseEntity.ok(ResponseUtils.success("모델 정보를 성공적으로 조회했습니다", model));
    }
    
    /**
     * 모든 차종 목록 조회
     */
    @Operation(summary = "차종 목록 조회", description = "모든 차종 목록을 조회합니다.")
    @GetMapping("/categories")
    public ResponseEntity<ApiResponse<List<String>>> getAllCategories() {
        log.info("Getting all vehicle categories");
        
        List<String> categories = masterDataService.getAllCategories();
        
        return ResponseEntity.ok(ResponseUtils.success("차종 목록을 성공적으로 조회했습니다", categories));
    }
    
    /**
     * 제조사-모델 매핑 조회
     */
    @Operation(summary = "제조사-모델 매핑 조회", description = "모든 제조사와 해당 모델들의 매핑 정보를 조회합니다.")
    @GetMapping("/brand-model-mapping")
    public ResponseEntity<ApiResponse<Map<VehicleBrand, List<VehicleModel>>>> getBrandModelMapping() {
        log.info("Getting brand-model mapping");
        
        Map<VehicleBrand, List<VehicleModel>> mapping = masterDataService.getBrandModelMapping();
        
        return ResponseEntity.ok(ResponseUtils.success("제조사-모델 매핑을 성공적으로 조회했습니다", mapping));
    }
    
    /**
     * 마스터 데이터 통계 조회
     */
    @Operation(summary = "마스터 데이터 통계 조회", description = "제조사 및 모델 통계 정보를 조회합니다.")
    @GetMapping("/statistics")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getStatistics() {
        log.info("Getting master data statistics");
        
        Map<String, Object> statistics = masterDataService.getMasterDataStatistics();
        
        return ResponseEntity.ok(ResponseUtils.success("마스터 데이터 통계를 성공적으로 조회했습니다", statistics));
    }
    
    /**
     * 제조사별 모델 개수 조회
     */
    @Operation(summary = "제조사별 모델 개수 조회", description = "특정 제조사의 모델 개수를 조회합니다.")
    @GetMapping("/brands/{brandId}/model-count")
    public ResponseEntity<ApiResponse<Integer>> getModelCountByBrand(
            @Parameter(description = "제조사 ID") @PathVariable Long brandId) {
        
        log.info("Getting model count for brand ID: {}", brandId);
        
        int count = masterDataService.getModelCountByBrand(brandId);
        
        return ResponseEntity.ok(ResponseUtils.success("모델 개수를 성공적으로 조회했습니다", count));
    }
} 