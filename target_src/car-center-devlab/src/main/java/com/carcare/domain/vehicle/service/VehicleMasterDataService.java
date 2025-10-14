package com.carcare.domain.vehicle.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.carcare.domain.vehicle.entity.VehicleBrand;
import com.carcare.domain.vehicle.entity.VehicleModel;
import com.carcare.domain.vehicle.repository.VehicleBrandRepository;
import com.carcare.domain.vehicle.repository.VehicleModelRepository;
import com.carcare.domain.vehicle.exception.VehicleNotFoundException;
import com.carcare.domain.vehicle.exception.InvalidVehicleDataException;

import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 차량 마스터 데이터 관리 서비스
 */
@Slf4j
@Service
@Transactional
public class VehicleMasterDataService {
    
    private final VehicleBrandRepository brandRepository;
    private final VehicleModelRepository modelRepository;
    
    @Autowired
    public VehicleMasterDataService(VehicleBrandRepository brandRepository, VehicleModelRepository modelRepository) {
        this.brandRepository = brandRepository;
        this.modelRepository = modelRepository;
    }
    
    // === Brand Management ===
    
    /**
     * 모든 활성 제조사 목록 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleBrands", key = "'all-active'")
    @Transactional(readOnly = true)
    public List<VehicleBrand> getAllActiveBrands() {
        log.info("Fetching all active vehicle brands");
        return brandRepository.findAllActive();
    }
    
    /**
     * 원산지별 제조사 목록 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleBrands", key = "'country-' + #country")
    @Transactional(readOnly = true)
    public List<VehicleBrand> getBrandsByCountry(String country) {
        log.info("Fetching vehicle brands by country: {}", country);
        return brandRepository.findByCountry(country);
    }
    
    /**
     * 제조사 검색
     */
    @Transactional(readOnly = true)
    public List<VehicleBrand> searchBrands(String keyword) {
        log.info("Searching vehicle brands with keyword: {}", keyword);
        return brandRepository.searchByName(keyword);
    }
    
    /**
     * 제조사 상세 조회
     */
    @Transactional(readOnly = true)
    public VehicleBrand getBrandById(Long brandId) {
        log.info("Fetching vehicle brand by ID: {}", brandId);
        return brandRepository.findById(brandId)
                .orElseThrow(() -> new VehicleNotFoundException("제조사", brandId));
    }
    
    /**
     * 제조사 등록 (관리자용)
     */
    @CacheEvict(value = "vehicleBrands", allEntries = true)
    public VehicleBrand createBrand(VehicleBrand brand) {
        log.info("Creating new vehicle brand: {}", brand.getName());
        
        // 중복 검사
        if (brandRepository.existsByName(brand.getName())) {
            throw new InvalidVehicleDataException("이미 존재하는 제조사명입니다: " + brand.getName());
        }
        
        if (brand.getCode() != null && brandRepository.existsByCode(brand.getCode())) {
            throw new InvalidVehicleDataException("이미 존재하는 제조사 코드입니다: " + brand.getCode());
        }
        
        int result = brandRepository.insertBrand(brand);
        if (result != 1) {
            throw new InvalidVehicleDataException("제조사 등록에 실패했습니다");
        }
        
        log.info("Vehicle brand created successfully: ID={}", brand.getId());
        return brand;
    }
    
    // === Model Management ===
    
    /**
     * 제조사별 모든 활성 모델 목록 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleModels", key = "'brand-' + #brandId")
    @Transactional(readOnly = true)
    public List<VehicleModel> getModelsByBrandId(Long brandId) {
        log.info("Fetching vehicle models by brand ID: {}", brandId);
        return modelRepository.findActiveByBrandId(brandId);
    }
    
    /**
     * 제조사별 차종 필터링된 모델 목록 조회
     */
    @Cacheable(value = "vehicleModels", key = "'brand-' + #brandId + '-category-' + #category")
    @Transactional(readOnly = true)
    public List<VehicleModel> getModelsByBrandAndCategory(Long brandId, String category) {
        log.info("Fetching vehicle models by brand ID: {} and category: {}", brandId, category);
        return modelRepository.findByBrandIdAndCategory(brandId, category);
    }
    
    /**
     * 모든 활성 모델 목록 조회 (제조사 정보 포함, 캐시 적용)
     */
    @Cacheable(value = "vehicleModels", key = "'all-active-with-brand'")
    @Transactional(readOnly = true)
    public List<VehicleModel> getAllActiveModelsWithBrand() {
        log.info("Fetching all active vehicle models with brand information");
        return modelRepository.findAllActiveWithBrand();
    }
    
    /**
     * 차종별 모델 목록 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleModels", key = "'category-' + #category")
    @Transactional(readOnly = true)
    public List<VehicleModel> getModelsByCategory(String category) {
        log.info("Fetching vehicle models by category: {}", category);
        return modelRepository.findByCategory(category);
    }
    
    /**
     * 모델 검색
     */
    @Transactional(readOnly = true)
    public List<VehicleModel> searchModels(String keyword) {
        log.info("Searching vehicle models with keyword: {}", keyword);
        return modelRepository.searchByName(keyword);
    }
    
    /**
     * 모델 상세 조회
     */
    @Transactional(readOnly = true)
    public VehicleModel getModelById(Long modelId) {
        log.info("Fetching vehicle model by ID: {}", modelId);
        return modelRepository.findById(modelId)
                .orElseThrow(() -> new VehicleNotFoundException("모델", modelId));
    }
    
    /**
     * 모델 등록 (관리자용)
     */
    @CacheEvict(value = {"vehicleModels", "vehicleBrands"}, allEntries = true)
    public VehicleModel createModel(VehicleModel model) {
        log.info("Creating new vehicle model: {} for brand ID: {}", model.getName(), model.getBrandId());
        
        // 제조사 존재 확인
        if (!brandRepository.findById(model.getBrandId()).isPresent()) {
            throw new VehicleNotFoundException("제조사", model.getBrandId());
        }
        
        // 중복 검사
        if (modelRepository.existsByBrandIdAndName(model.getBrandId(), model.getName())) {
            throw new InvalidVehicleDataException("해당 제조사에 이미 존재하는 모델명입니다: " + model.getName());
        }
        
        if (model.getCode() != null && modelRepository.existsByCode(model.getCode())) {
            throw new InvalidVehicleDataException("이미 존재하는 모델 코드입니다: " + model.getCode());
        }
        
        int result = modelRepository.insertModel(model);
        if (result != 1) {
            throw new InvalidVehicleDataException("모델 등록에 실패했습니다");
        }
        
        log.info("Vehicle model created successfully: ID={}", model.getId());
        return model;
    }
    
    // === Utility Methods ===
    
    /**
     * 모든 차종 목록 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleCategories", key = "'all'")
    @Transactional(readOnly = true)
    public List<String> getAllCategories() {
        log.info("Fetching all vehicle categories");
        return modelRepository.findAllCategories();
    }
    
    /**
     * 제조사별 브랜드-모델 매핑 조회 (캐시 적용)
     */
    @Cacheable(value = "vehicleBrandModelMap", key = "'all'")
    @Transactional(readOnly = true)
    public Map<VehicleBrand, List<VehicleModel>> getBrandModelMapping() {
        log.info("Fetching brand-model mapping");
        
        List<VehicleBrand> brands = brandRepository.findAllActive();
        
        return brands.stream()
                .collect(Collectors.toMap(
                    brand -> brand,
                    brand -> modelRepository.findActiveByBrandId(brand.getId())
                ));
    }
    
    /**
     * 마스터 데이터 통계 조회
     */
    @Transactional(readOnly = true)
    public Map<String, Object> getMasterDataStatistics() {
        log.info("Fetching master data statistics");
        
        int totalBrands = brandRepository.countAll();
        int activeBrands = brandRepository.countActive();
        
        Map<String, Integer> modelCountByCategory = modelRepository.findAllCategories()
                .stream()
                .collect(Collectors.toMap(
                    category -> category,
                    category -> modelRepository.countByCategory(category)
                ));
        
        return Map.of(
            "totalBrands", totalBrands,
            "activeBrands", activeBrands,
            "modelCountByCategory", modelCountByCategory,
            "totalCategories", modelCountByCategory.size()
        );
    }
    
    /**
     * 제조사별 모델 개수 조회
     */
    @Transactional(readOnly = true)
    public int getModelCountByBrand(Long brandId) {
        return modelRepository.countByBrandId(brandId);
    }
    
    /**
     * 모든 캐시 초기화 (관리자용)
     */
    @CacheEvict(value = {"vehicleBrands", "vehicleModels", "vehicleCategories", "vehicleBrandModelMap"}, allEntries = true)
    public void clearAllCaches() {
        log.info("Clearing all vehicle master data caches");
    }
} 