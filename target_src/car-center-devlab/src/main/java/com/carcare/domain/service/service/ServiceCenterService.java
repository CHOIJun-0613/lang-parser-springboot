package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenter;
import com.carcare.domain.service.dto.ServiceCenterDto;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import com.carcare.common.exception.BusinessException;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.math.BigDecimal;

/**
 * 정비소 비즈니스 로직 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ServiceCenterService {

    private final ServiceCenterRepository serviceCenterRepository;

    /**
     * 정비소 등록
     */
    @Transactional
    public ServiceCenterDto.Response createServiceCenter(ServiceCenterDto.Request request, Long createdBy) {
        log.info("정비소 등록 시작: {}", request.getName());

        // 사업자등록번호 중복 검사
        if (serviceCenterRepository.existsByBusinessNumber(request.getBusinessNumber())) {
            throw new BusinessException("이미 등록된 사업자등록번호입니다: " + request.getBusinessNumber());
        }

        // 같은 위치에 이미 정비소가 있는지 검사 (반경 100m 이내)
        List<ServiceCenter> nearbyServiceCenters = serviceCenterRepository.findByLocation(
            request.getLatitude(), request.getLongitude(), 0.1 // 100m
        );
        if (!nearbyServiceCenters.isEmpty()) {
            log.warn("같은 위치에 이미 정비소가 존재합니다: 위도={}, 경도={}", request.getLatitude(), request.getLongitude());
        }

        ServiceCenter serviceCenter = ServiceCenter.builder()
            .name(request.getName())
            .description(request.getDescription())
            .address(request.getAddress())
            .addressDetail(request.getAddressDetail())
            .phoneNumber(request.getPhoneNumber())
            .email(request.getEmail())
            .businessNumber(request.getBusinessNumber())
            .ownerName(request.getOwnerName())
            .latitude(request.getLatitude())
            .longitude(request.getLongitude())
            .website(request.getWebsite())
            .specializedServices(request.getSpecializedServices())
            .facilities(request.getFacilities())
            .averageRating(BigDecimal.ZERO)
            .reviewCount(0)
            .verificationStatus(ServiceCenter.VerificationStatus.PENDING) // 기본값은 대기중
            .isActive(request.getIsActive() != null ? request.getIsActive() : true)
            .isOperating(request.getIsOperating() != null ? request.getIsOperating() : true)
            .createdBy(createdBy)
            .updatedBy(createdBy)
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();

        int result = serviceCenterRepository.insertServiceCenter(serviceCenter);
        if (result == 0) {
            throw new BusinessException("정비소 등록에 실패했습니다");
        }

        log.info("정비소 등록 완료: ID={}, 이름={}", serviceCenter.getId(), serviceCenter.getName());
        return convertToResponse(serviceCenter);
    }

    /**
     * 정비소 정보 수정
     */
    @Transactional
    public ServiceCenterDto.Response updateServiceCenter(Long id, ServiceCenterDto.Request request, Long updatedBy) {
        log.info("정비소 정보 수정 시작: ID={}", id);

        ServiceCenter existingServiceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        // 사업자등록번호 중복 검사 (자신 제외)
        log.debug("사업자등록번호 중복 체크 - 기존: '{}', 요청: '{}'", 
                 existingServiceCenter.getBusinessNumber(), request.getBusinessNumber());
        
        if (!existingServiceCenter.getBusinessNumber().equals(request.getBusinessNumber())) {
            log.debug("사업자등록번호가 변경되었으므로 중복 체크를 수행합니다");
            if (serviceCenterRepository.existsByBusinessNumber(request.getBusinessNumber())) {
                throw new BusinessException("이미 등록된 사업자등록번호입니다: " + request.getBusinessNumber());
            }
        } else {
            log.debug("사업자등록번호가 동일하므로 중복 체크를 건너뜁니다");
        }

        ServiceCenter serviceCenter = ServiceCenter.builder()
            .id(id)
            .name(request.getName())
            .description(request.getDescription())
            .address(request.getAddress())
            .addressDetail(request.getAddressDetail())
            .phoneNumber(request.getPhoneNumber())
            .email(request.getEmail())
            .businessNumber(request.getBusinessNumber())
            .ownerName(request.getOwnerName())
            .latitude(request.getLatitude())
            .longitude(request.getLongitude())
            .website(request.getWebsite())
            .specializedServices(request.getSpecializedServices())
            .facilities(request.getFacilities())
            .averageRating(existingServiceCenter.getAverageRating())
            .reviewCount(existingServiceCenter.getReviewCount())
            .verificationStatus(existingServiceCenter.getVerificationStatus())
            .isActive(request.getIsActive() != null ? request.getIsActive() : existingServiceCenter.getIsActive())
            .isOperating(request.getIsOperating() != null ? request.getIsOperating() : existingServiceCenter.getIsOperating())
            .createdBy(existingServiceCenter.getCreatedBy())
            .createdAt(existingServiceCenter.getCreatedAt())
            .updatedBy(updatedBy)
            .updatedAt(LocalDateTime.now())
            .build();

        int result = serviceCenterRepository.updateServiceCenter(serviceCenter);
        if (result == 0) {
            throw new BusinessException("정비소 정보 수정에 실패했습니다");
        }

        log.info("정비소 정보 수정 완료: ID={}", id);
        return convertToResponse(serviceCenter);
    }

    /**
     * 정비소 삭제 (소프트 삭제)
     */
    @Transactional
    public void deleteServiceCenter(Long id, Long updatedBy) {
        log.info("정비소 삭제 시작: ID={}", id);

        ServiceCenter serviceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        int result = serviceCenterRepository.deleteServiceCenter(id, updatedBy);
        if (result == 0) {
            throw new BusinessException("정비소 삭제에 실패했습니다");
        }

        log.info("정비소 삭제 완료: ID={}", id);
    }

    /**
     * 정비소 상세 조회
     */
    public ServiceCenterDto.Response getServiceCenter(Long id) {
        log.debug("정비소 상세 조회: ID={}", id);

        ServiceCenter serviceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        return convertToResponse(serviceCenter);
    }

    /**
     * 정비소 검색 (페이징 포함)
     */
    public ServiceCenterDto.ListResponse searchServiceCenters(ServiceCenterDto.SearchCriteria criteria) {
        log.debug("정비소 검색: 키워드={}, 페이지={}, 크기={}", criteria.getKeyword(), criteria.getPage(), criteria.getSize());

        // DTO를 Repository용 SearchCriteria로 변환
        ServiceCenterRepository.SearchCriteria repositoryCriteria = convertToRepositoryCriteria(criteria);
        
        // 검색 결과 조회
        List<ServiceCenter> serviceCenters = serviceCenterRepository.searchServiceCenters(repositoryCriteria);
        
        // 총 개수 조회
        int totalCount = serviceCenterRepository.countSearchResults(repositoryCriteria);

        // DTO 변환
        List<ServiceCenterDto.Response> responses = serviceCenters.stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());

        // 페이징 정보 계산
        int totalPages = (int) Math.ceil((double) totalCount / criteria.getSize());
        boolean hasNext = criteria.getPage() < totalPages - 1;
        boolean hasPrevious = criteria.getPage() > 0;

        // 검색 통계 계산
        Double averageDistance = responses.stream()
            .filter(r -> r.getDistance() != null)
            .mapToDouble(ServiceCenterDto.Response::getDistance)
            .average()
            .orElse(0.0);

        Integer verifiedCount = (int) responses.stream()
            .filter(r -> Boolean.TRUE.equals(r.getIsVerified()))
            .count();

        Integer operatingCount = (int) responses.stream()
            .filter(r -> Boolean.TRUE.equals(r.getIsOperating()))
            .count();

        return ServiceCenterDto.ListResponse.builder()
            .serviceCenters(responses)
            .currentPage(criteria.getPage())
            .totalPages(totalPages)
            .pageSize(criteria.getSize())
            .totalElements(totalCount)
            .hasNext(hasNext)
            .hasPrevious(hasPrevious)
            .averageDistance(averageDistance)
            .verifiedCount(verifiedCount)
            .operatingCount(operatingCount)
            .build();
    }

    /**
     * 위치 기반 정비소 검색
     */
    public ServiceCenterDto.ListResponse findServiceCentersByLocation(ServiceCenterDto.LocationRequest locationRequest) {
        log.debug("위치 기반 정비소 검색: 위도={}, 경도={}, 반경={}km", 
            locationRequest.getLatitude(), locationRequest.getLongitude(), locationRequest.getRadius());

        List<ServiceCenter> serviceCenters = serviceCenterRepository.findByLocation(
            locationRequest.getLatitude(), locationRequest.getLongitude(), locationRequest.getRadius()
        );

        List<ServiceCenterDto.Response> responses = serviceCenters.stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());

        return ServiceCenterDto.ListResponse.builder()
            .serviceCenters(responses)
            .currentPage(0)
            .totalPages(1)
            .pageSize(responses.size())
            .totalElements(responses.size())
            .hasNext(false)
            .hasPrevious(false)
            .averageDistance(responses.stream()
                .filter(r -> r.getDistance() != null)
                .mapToDouble(ServiceCenterDto.Response::getDistance)
                .average()
                .orElse(0.0))
            .verifiedCount((int) responses.stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsVerified()))
                .count())
            .operatingCount((int) responses.stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsOperating()))
                .count())
            .build();
    }

    /**
     * 평점별 정비소 검색
     */
    public ServiceCenterDto.ListResponse findServiceCentersByRating(BigDecimal minRating, BigDecimal maxRating) {
        log.debug("평점별 정비소 검색: 최소평점={}, 최대평점={}", minRating, maxRating);

        List<ServiceCenter> serviceCenters = serviceCenterRepository.findByRatingRange(minRating, maxRating);

        List<ServiceCenterDto.Response> responses = serviceCenters.stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());

        return ServiceCenterDto.ListResponse.builder()
            .serviceCenters(responses)
            .currentPage(0)
            .totalPages(1)
            .pageSize(responses.size())
            .totalElements(responses.size())
            .hasNext(false)
            .hasPrevious(false)
            .verifiedCount((int) responses.stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsVerified()))
                .count())
            .operatingCount((int) responses.stream()
                .filter(r -> Boolean.TRUE.equals(r.getIsOperating()))
                .count())
            .build();
    }

    /**
     * 정비소 상태 변경 (활성/비활성)
     */
    @Transactional
    public void updateServiceCenterStatus(Long id, Boolean isActive, Long updatedBy) {
        log.info("정비소 상태 변경: ID={}, 활성={}", id, isActive);

        ServiceCenter serviceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        int result = serviceCenterRepository.updateStatus(id, isActive, updatedBy);
        if (result == 0) {
            throw new BusinessException("정비소 상태 변경에 실패했습니다");
        }

        log.info("정비소 상태 변경 완료: ID={}", id);
    }

    /**
     * 정비소 운영 상태 변경
     */
    @Transactional
    public void updateOperatingStatus(Long id, Boolean isOperating, Long updatedBy) {
        log.info("정비소 운영 상태 변경: ID={}, 운영중={}", id, isOperating);

        ServiceCenter serviceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        int result = serviceCenterRepository.updateOperatingStatus(id, isOperating, updatedBy);
        if (result == 0) {
            throw new BusinessException("정비소 운영 상태 변경에 실패했습니다");
        }

        log.info("정비소 운영 상태 변경 완료: ID={}", id);
    }

    /**
     * 정비소 인증 상태 변경
     */
    @Transactional
    public void updateVerificationStatus(Long id, Boolean isVerified, Long updatedBy) {
        log.info("정비소 인증 상태 변경: ID={}, 인증={}", id, isVerified);

        ServiceCenter serviceCenter = serviceCenterRepository.findById(id)
            .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + id));

        int result = serviceCenterRepository.updateVerificationStatus(id, isVerified, updatedBy);
        if (result == 0) {
            throw new BusinessException("정비소 인증 상태 변경에 실패했습니다");
        }

        log.info("정비소 인증 상태 변경 완료: ID={}", id);
    }

    /**
     * 정비소 평점 업데이트
     */
    @Transactional
    public void updateServiceCenterRating(Long id, BigDecimal newRating, Integer newReviewCount) {
        log.debug("정비소 평점 업데이트: ID={}, 평점={}, 리뷰수={}", id, newRating, newReviewCount);

        int result = serviceCenterRepository.updateRating(id, newRating, newReviewCount);
        if (result == 0) {
            throw new BusinessException("정비소 평점 업데이트에 실패했습니다");
        }
    }

    /**
     * 정비소 통계 조회
     */
    public ServiceCenterDto.Statistics getServiceCenterStatistics() {
        log.debug("정비소 통계 조회");

        return serviceCenterRepository.getStatistics();
    }

    /**
     * 정비소 자동완성 검색
     */
    public List<ServiceCenterDto.SimpleResponse> autocompleteServiceCenters(String keyword, int limit) {
        log.debug("정비소 자동완성 검색: 키워드={}, 제한={}", keyword, limit);

        List<ServiceCenter> serviceCenters = serviceCenterRepository.findForAutocomplete(keyword, limit);

        return serviceCenters.stream()
            .map(this::convertToSimpleResponse)
            .collect(Collectors.toList());
    }

    /**
     * Entity를 Response DTO로 변환
     */
    private ServiceCenterDto.Response convertToResponse(ServiceCenter serviceCenter) {
        return ServiceCenterDto.Response.builder()
            .id(serviceCenter.getId())
            .name(serviceCenter.getName())
            .description(serviceCenter.getDescription())
            .address(serviceCenter.getAddress())
            .addressDetail(serviceCenter.getAddressDetail())
            .phoneNumber(serviceCenter.getPhoneNumber())
            .email(serviceCenter.getEmail())
            .businessNumber(serviceCenter.getBusinessNumber())
            .ownerName(serviceCenter.getOwnerName())
            .latitude(serviceCenter.getLatitude())
            .longitude(serviceCenter.getLongitude())
            .website(serviceCenter.getWebsite())
            .specializedServices(serviceCenter.getSpecializedServices())
            .facilities(serviceCenter.getFacilities())
            .averageRating(serviceCenter.getAverageRating())
            .reviewCount(serviceCenter.getReviewCount())
            .isVerified(serviceCenter.getIsVerified())
            .isActive(serviceCenter.getIsActive())
            .isOperating(serviceCenter.getIsOperating())
            .createdAt(serviceCenter.getCreatedAt())
            .updatedAt(serviceCenter.getUpdatedAt())
            .createdBy(serviceCenter.getCreatedBy() != null ? serviceCenter.getCreatedBy().toString() : null)
            .updatedBy(serviceCenter.getUpdatedBy() != null ? serviceCenter.getUpdatedBy().toString() : null)
            .build();
    }

    /**
     * Entity를 SimpleResponse DTO로 변환
     */
    private ServiceCenterDto.SimpleResponse convertToSimpleResponse(ServiceCenter serviceCenter) {
        return ServiceCenterDto.SimpleResponse.builder()
            .id(serviceCenter.getId())
            .name(serviceCenter.getName())
            .address(serviceCenter.getAddress())
            .phoneNumber(serviceCenter.getPhoneNumber())
            .averageRating(serviceCenter.getAverageRating())
            .isVerified(serviceCenter.getIsVerified())
            .isOperating(serviceCenter.getIsOperating())
            .build();
    }
    
    /**
     * DTO SearchCriteria를 Repository SearchCriteria로 변환
     */
    private ServiceCenterRepository.SearchCriteria convertToRepositoryCriteria(ServiceCenterDto.SearchCriteria dto) {
        ServiceCenterRepository.SearchCriteria criteria = new ServiceCenterRepository.SearchCriteria();
        criteria.setKeyword(dto.getKeyword());
        criteria.setAddress(dto.getAddress());
        criteria.setLatitude(dto.getLatitude());
        criteria.setLongitude(dto.getLongitude());
        criteria.setRadiusKm(dto.getRadius());
        criteria.setMinRating(dto.getMinRating());
        criteria.setMaxRating(dto.getMaxRating());
        
        // Boolean isVerified를 VerificationStatus로 변환
        if (dto.getIsVerified() != null) {
            criteria.setVerificationStatus(dto.getIsVerified() ? 
                ServiceCenter.VerificationStatus.VERIFIED : 
                ServiceCenter.VerificationStatus.PENDING);
        }
        
        criteria.setIsActive(dto.getIsActive());
        criteria.setIsOperating(dto.getIsOperating());
        criteria.setSortBy(dto.getSortBy());
        criteria.setSortDirection(dto.getSortDirection());
        criteria.setPage(dto.getPage());
        criteria.setSize(dto.getSize());
        
        return criteria;
    }
} 