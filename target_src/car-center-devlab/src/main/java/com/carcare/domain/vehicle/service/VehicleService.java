package com.carcare.domain.vehicle.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.carcare.domain.vehicle.entity.Vehicle;
import com.carcare.domain.vehicle.dto.VehicleDto;
import com.carcare.domain.vehicle.repository.VehicleRepository;
import com.carcare.domain.vehicle.validator.VehicleValidator;
import com.carcare.domain.vehicle.service.VehicleBusinessRuleService;
import com.carcare.domain.vehicle.exception.VehicleNotFoundException;
import com.carcare.common.exception.BusinessException;

import lombok.extern.slf4j.Slf4j;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 차량 비즈니스 로직 서비스
 */
@Slf4j
@Service
@Transactional
public class VehicleService {
    
    private final VehicleRepository vehicleRepository;
    private final VehicleValidator vehicleValidator;
    private final VehicleBusinessRuleService businessRuleService;
    
    @Autowired
    public VehicleService(VehicleRepository vehicleRepository, VehicleValidator vehicleValidator, 
                         VehicleBusinessRuleService businessRuleService) {
        this.vehicleRepository = vehicleRepository;
        this.vehicleValidator = vehicleValidator;
        this.businessRuleService = businessRuleService;
    }
    
    /**
     * 차량 등록
     */
    public VehicleDto.Response registerVehicle(Long userId, VehicleDto.Request request) {
        log.info("Registering vehicle for user: {}, licensePlate: {}", userId, request.getLicensePlate());
        
        // 1. 사용자 차량 등록 한도 검증
        int currentVehicleCount = vehicleRepository.countByUserId(userId);
        businessRuleService.validateVehicleRegistrationLimit(userId, currentVehicleCount);
        
        // 2. 차량 등록 데이터 검증
        vehicleValidator.validateForRegistration(request);
        
        // 3. 엔티티 생성
        Vehicle vehicle = Vehicle.builder()
                .vehicleUuid(UUID.randomUUID())
                .userId(userId)
                .make(request.getMake())
                .model(request.getModel())
                .year(request.getYear())
                .licensePlate(request.getLicensePlate())
                .vin(request.getVin())
                .engineType(request.getEngineType())
                .fuelType(request.getFuelType())
                .mileage(request.getMileage() != null ? request.getMileage() : 0)
                .color(request.getColor())
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
        
        // 4. 데이터베이스 저장
        int result = vehicleRepository.insertVehicle(vehicle);
        if (result != 1) {
            throw new BusinessException("차량 등록에 실패했습니다");
        }
        
        log.info("Vehicle registered successfully: id={}, licensePlate={}", vehicle.getId(), vehicle.getLicensePlate());
        return convertToResponse(vehicle);
    }
    
    /**
     * 차량 정보 수정
     */
    public VehicleDto.Response updateVehicle(Long userId, Long vehicleId, VehicleDto.Request request) {
        log.info("Updating vehicle: id={}, userId={}", vehicleId, userId);
        
        // 1. 차량 존재 및 소유권 확인
        Vehicle vehicle = vehicleValidator.validateAndGetVehicle(vehicleId);
        vehicleValidator.validateOwnership(vehicleId, userId);
        
        // 2. 차량 수정 데이터 검증
        vehicleValidator.validateForUpdate(vehicleId, request);
        
        // 3. 엔티티 업데이트
        Vehicle updatedVehicle = Vehicle.builder()
                .id(vehicle.getId())
                .vehicleUuid(vehicle.getVehicleUuid())
                .userId(vehicle.getUserId())
                .make(request.getMake())
                .model(request.getModel())
                .year(request.getYear())
                .licensePlate(request.getLicensePlate())
                .vin(request.getVin())
                .engineType(request.getEngineType())
                .fuelType(request.getFuelType())
                .mileage(request.getMileage())
                .color(request.getColor())
                .isActive(vehicle.getIsActive())
                .createdAt(vehicle.getCreatedAt())
                .updatedAt(LocalDateTime.now())
                .build();
        
        // 4. 데이터베이스 업데이트
        int result = vehicleRepository.updateVehicle(updatedVehicle);
        if (result != 1) {
            throw new BusinessException("차량 정보 수정에 실패했습니다");
        }
        
        log.info("Vehicle updated successfully: id={}", vehicleId);
        return convertToResponse(updatedVehicle);
    }
    
    /**
     * 차량 삭제 (소프트 삭제)
     */
    public void deleteVehicle(Long userId, Long vehicleId) {
        log.info("Deleting vehicle: id={}, userId={}", vehicleId, userId);
        
        // 1. 차량 삭제 검증
        vehicleValidator.validateForDeletion(vehicleId, userId);
        
        // 2. 소프트 삭제 실행
        int result = vehicleRepository.deleteVehicle(vehicleId, userId);
        if (result != 1) {
            throw new BusinessException("차량 삭제에 실패했습니다");
        }
        
        log.info("Vehicle deleted successfully: id={}", vehicleId);
    }
    
    /**
     * 차량 상세 조회
     */
    @Transactional(readOnly = true)
    public VehicleDto.Response getVehicle(Long userId, Long vehicleId) {
        log.info("Getting vehicle: id={}, userId={}", vehicleId, userId);
        
        Vehicle vehicle = vehicleValidator.validateAndGetVehicle(vehicleId);
        vehicleValidator.validateOwnership(vehicleId, userId);
        
        return convertToResponse(vehicle);
    }
    
    /**
     * UUID로 차량 조회
     */
    @Transactional(readOnly = true)
    public VehicleDto.Response getVehicleByUuid(Long userId, UUID vehicleUuid) {
        log.info("Getting vehicle by UUID: {}, userId={}", vehicleUuid, userId);
        
        Vehicle vehicle = vehicleRepository.findByUuid(vehicleUuid)
                .orElseThrow(() -> new VehicleNotFoundException("UUID", vehicleUuid));
        
        vehicleValidator.validateOwnership(vehicle.getId(), userId);
        
        return convertToResponse(vehicle);
    }
    
    /**
     * 사용자의 차량 목록 조회
     */
    @Transactional(readOnly = true)
    public List<VehicleDto.Response> getUserVehicles(Long userId, Boolean activeOnly) {
        log.info("Getting user vehicles: userId={}, activeOnly={}", userId, activeOnly);
        
        List<Vehicle> vehicles;
        if (activeOnly != null && activeOnly) {
            vehicles = vehicleRepository.findActiveVehiclesByUserId(userId);
        } else {
            vehicles = vehicleRepository.findByUserId(userId);
        }
        
        return vehicles.stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
    }
    
    /**
     * 차량 검색 (페이징 포함)
     */
    @Transactional(readOnly = true)
    public VehicleDto.ListResponse searchVehicles(Long userId, VehicleDto.SearchCriteria criteria) {
        log.info("Searching vehicles: userId={}, criteria={}", userId, criteria);
        
        // 검색 조건 기본값 설정
        if (criteria.getPage() < 0) criteria.setPage(0);
        if (criteria.getSize() <= 0) criteria.setSize(10);
        if (criteria.getSortBy() == null) criteria.setSortBy("createdAt");
        if (criteria.getSortDirection() == null) criteria.setSortDirection("DESC");
        
        // 차량 목록 조회
        List<Vehicle> vehicles = vehicleRepository.searchVehicles(criteria, userId);
        
        // 총 개수 조회
        int totalCount = vehicleRepository.countSearchResults(criteria, userId);
        
        // 응답 DTO 변환
        List<VehicleDto.Response> vehicleResponses = vehicles.stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
        
        // 페이징 정보 계산
        int totalPages = (int) Math.ceil((double) totalCount / criteria.getSize());
        boolean hasNext = criteria.getPage() < totalPages - 1;
        boolean hasPrevious = criteria.getPage() > 0;
        
        return VehicleDto.ListResponse.builder()
                .vehicles(vehicleResponses)
                .totalCount(totalCount)
                .currentPage(criteria.getPage())
                .pageSize(criteria.getSize())
                .totalPages(totalPages)
                .hasNext(hasNext)
                .hasPrevious(hasPrevious)
                .build();
    }
    
    /**
     * 사용자의 차량 개수 조회
     */
    @Transactional(readOnly = true)
    public int getUserVehicleCount(Long userId) {
        return vehicleRepository.countByUserId(userId);
    }
    
    /**
     * 차량번호로 차량 존재 여부 확인
     */
    @Transactional(readOnly = true)
    public boolean isLicensePlateExists(String licensePlate) {
        return vehicleRepository.existsByLicensePlate(licensePlate);
    }
    
    // === Private Helper Methods ===
    
    /**
     * Entity를 Response DTO로 변환
     */
    private VehicleDto.Response convertToResponse(Vehicle vehicle) {
        return VehicleDto.Response.builder()
                .id(vehicle.getId())
                .vehicleUuid(vehicle.getVehicleUuid())
                .userId(vehicle.getUserId())
                .make(vehicle.getMake())
                .model(vehicle.getModel())
                .year(vehicle.getYear())
                .licensePlate(vehicle.getLicensePlate())
                .vin(vehicle.getVin())
                .engineType(vehicle.getEngineType())
                .fuelType(vehicle.getFuelType())
                .fuelTypeDescription(vehicle.getFuelType() != null ? vehicle.getFuelType().getDescription() : null)
                .mileage(vehicle.getMileage())
                .color(vehicle.getColor())
                .isActive(vehicle.getIsActive())
                .createdAt(vehicle.getCreatedAt())
                .updatedAt(vehicle.getUpdatedAt())
                .build();
    }
} 