package com.carcare.domain.reservation.service;

import com.carcare.domain.reservation.entity.Reservation;
import com.carcare.domain.reservation.dto.ReservationDto;
import com.carcare.domain.reservation.repository.ReservationRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 예약 비즈니스 로직 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ReservationService {

    private final ReservationRepository reservationRepository;
    private final ReservationNotificationService notificationService;

    /**
     * 예약 생성
     */
    @Transactional
    public ReservationDto.Response createReservation(ReservationDto.CreateRequest request, Long userId) {
        log.info("예약 생성 시작: 사용자={}, 정비소={}", userId, request.getServiceCenterId());

        // 예약 시간 검증
        validateReservationTime(request.getScheduledDate(), request.getEstimatedDuration());

        // 시간 충돌 체크
        checkTimeConflict(request.getServiceCenterId(), request.getScheduledDate(), 
                         request.getEstimatedDuration(), null);

        // 예약 엔티티 생성
        Reservation reservation = Reservation.builder()
            .reservationUuid(UUID.randomUUID())
            .userId(userId)
            .vehicleId(request.getVehicleId())
            .serviceCenterId(request.getServiceCenterId())
            .serviceTypeId(request.getServiceTypeId())
            .status(Reservation.ReservationStatus.PENDING)
            .scheduledDate(request.getScheduledDate())
            .estimatedDuration(request.getEstimatedDuration())
            .customerNotes(request.getCustomerNotes())
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();

        // 예약 저장
        int result = reservationRepository.insertReservation(reservation);
        if (result == 0) {
            throw new BusinessException("예약 생성에 실패했습니다.");
        }

        log.info("예약 생성 완료: ID={}", reservation.getId());

        // 상세 정보 조회 후 반환
        ReservationDto.Response response = reservationRepository.findDetailById(reservation.getId())
            .orElseThrow(() -> new BusinessException("생성된 예약을 찾을 수 없습니다."));

        // 예약 생성 알림 발송
        notificationService.notifyReservationCreated(response);

        return response;
    }

    /**
     * 예약 수정
     */
    @Transactional
    public ReservationDto.Response updateReservation(Long id, ReservationDto.UpdateRequest request, Long userId) {
        log.info("예약 수정 시작: ID={}, 사용자={}", id, userId);

        // 기존 예약 조회
        Reservation reservation = reservationRepository.findById(id)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + id));

        // 권한 확인 (본인 예약만 수정 가능)
        if (!reservation.getUserId().equals(userId)) {
            throw new BusinessException("본인의 예약만 수정할 수 있습니다.");
        }

        // 수정 가능한 상태 확인
        if (!reservation.isCancellable()) {
            throw new BusinessException("수정할 수 없는 예약 상태입니다: " + reservation.getStatus().getDescription());
        }

        // 수정할 필드가 있는지 확인
        boolean hasChanges = false;

        if (request.getScheduledDate() != null && !request.getScheduledDate().equals(reservation.getScheduledDate())) {
            validateReservationTime(request.getScheduledDate(), 
                request.getEstimatedDuration() != null ? request.getEstimatedDuration() : reservation.getEstimatedDuration());
            
            checkTimeConflict(reservation.getServiceCenterId(), request.getScheduledDate(), 
                request.getEstimatedDuration() != null ? request.getEstimatedDuration() : reservation.getEstimatedDuration(), 
                reservation.getId());
            
            reservation.setScheduledDate(request.getScheduledDate());
            hasChanges = true;
        }

        if (request.getEstimatedDuration() != null && !request.getEstimatedDuration().equals(reservation.getEstimatedDuration())) {
            checkTimeConflict(reservation.getServiceCenterId(), 
                request.getScheduledDate() != null ? request.getScheduledDate() : reservation.getScheduledDate(),
                request.getEstimatedDuration(), reservation.getId());
            
            reservation.setEstimatedDuration(request.getEstimatedDuration());
            hasChanges = true;
        }

        if (request.getCustomerNotes() != null && !request.getCustomerNotes().equals(reservation.getCustomerNotes())) {
            reservation.setCustomerNotes(request.getCustomerNotes());
            hasChanges = true;
        }

        if (!hasChanges) {
            log.info("수정할 내용이 없음: ID={}", id);
            return reservationRepository.findDetailById(id)
                .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다."));
        }

        reservation.setUpdatedAt(LocalDateTime.now());

        // 예약 수정
        int result = reservationRepository.updateReservation(reservation);
        if (result == 0) {
            throw new BusinessException("예약 수정에 실패했습니다.");
        }

        log.info("예약 수정 완료: ID={}", id);

        return reservationRepository.findDetailById(id)
            .orElseThrow(() -> new BusinessException("수정된 예약을 찾을 수 없습니다."));
    }

    /**
     * 예약 상태 변경 (ID)
     */
    @Transactional
    public ReservationDto.Response updateReservationStatus(Long id, ReservationDto.StatusUpdateRequest request) {
        log.info("예약 상태 변경 시작: ID={}, 상태={}", id, request.getStatus());

        Reservation reservation = reservationRepository.findById(id)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + id));

        return performStatusUpdate(reservation, request);
    }

    /**
     * 예약 상태 변경 (UUID)
     */
    @Transactional
    public ReservationDto.Response updateReservationStatusByUuid(String uuid, ReservationDto.StatusUpdateRequest request) {
        log.info("예약 상태 변경 시작: UUID={}, 상태={}", uuid, request.getStatus());

        Reservation reservation = reservationRepository.findByUuid(uuid)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + uuid));

        return performStatusUpdate(reservation, request);
    }

    /**
     * 예약 상태 변경 공통 로직
     */
    private ReservationDto.Response performStatusUpdate(Reservation reservation, ReservationDto.StatusUpdateRequest request) {
        // 상태 변경 로직
        try {
            switch (request.getStatus()) {
                case CONFIRMED:
                    reservation.confirm();
                    break;
                case IN_PROGRESS:
                    reservation.start();
                    break;
                case COMPLETED:
                    reservation.complete();
                    break;
                case CANCELLED:
                    reservation.cancel(request.getCancellationReason());
                    break;
                default:
                    throw new BusinessException("지원하지 않는 상태 변경입니다: " + request.getStatus());
            }
        } catch (IllegalStateException e) {
            throw new BusinessException(e.getMessage());
        }

        // 정비사 메모 추가
        if (request.getMechanicNotes() != null) {
            reservation.setMechanicNotes(request.getMechanicNotes());
        }

        reservation.setUpdatedAt(LocalDateTime.now());

        // 예약 상태 저장
        int result = reservationRepository.updateReservation(reservation);
        if (result == 0) {
            throw new BusinessException("예약 상태 변경에 실패했습니다.");
        }

        log.info("예약 상태 변경 완료: ID={}, 상태={}", reservation.getId(), request.getStatus());

        ReservationDto.Response response = reservationRepository.findDetailById(reservation.getId())
            .orElseThrow(() -> new BusinessException("상태가 변경된 예약을 찾을 수 없습니다."));

        // 상태 변경 알림 발송  
        notificationService.notifyReservationStatusChanged(response, 
            reservationRepository.findById(reservation.getId()).map(Reservation::getStatus).orElse(null));

        return response;
    }

    /**
     * 예약 취소
     */
    @Transactional
    public void cancelReservation(Long id, String reason, Long userId) {
        log.info("예약 취소 시작: ID={}, 사용자={}", id, userId);

        Reservation reservation = reservationRepository.findById(id)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + id));

        // 권한 확인 (본인 예약만 취소 가능)
        if (!reservation.getUserId().equals(userId)) {
            throw new BusinessException("본인의 예약만 취소할 수 있습니다.");
        }

        // 취소 가능한 상태 확인
        if (!reservation.isCancellable()) {
            throw new BusinessException("취소할 수 없는 예약 상태입니다: " + reservation.getStatus().getDescription());
        }

        // 예약 취소
        reservation.cancel(reason);
        reservation.setUpdatedAt(LocalDateTime.now());

        int result = reservationRepository.updateReservation(reservation);
        if (result == 0) {
            throw new BusinessException("예약 취소에 실패했습니다.");
        }

        // 취소 알림 발송
        ReservationDto.Response response = reservationRepository.findDetailById(id)
            .orElseThrow(() -> new BusinessException("취소된 예약을 찾을 수 없습니다."));
        notificationService.notifyReservationCancelled(response, reason);

        log.info("예약 취소 완료: ID={}", id);
    }

    /**
     * 예약 조회 (상세)
     */
    public ReservationDto.Response getReservation(Long id) {
        log.debug("예약 상세 조회: ID={}", id);

        return reservationRepository.findDetailById(id)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + id));
    }

    /**
     * 예약 조회 (UUID)
     */
    public ReservationDto.Response getReservationByUuid(String uuid) {
        log.debug("예약 상세 조회: UUID={}", uuid);

        // UUID로 예약 엔티티 조회
        Reservation reservation = reservationRepository.findByUuid(uuid)
            .orElseThrow(() -> new BusinessException("예약을 찾을 수 없습니다: " + uuid));

        // ID로 상세 정보 조회
        return reservationRepository.findDetailById(reservation.getId())
            .orElseThrow(() -> new BusinessException("예약 상세 정보를 찾을 수 없습니다: " + uuid));
    }

    /**
     * 예약 검색
     */
    public ReservationDto.ListResponse searchReservations(ReservationDto.SearchCriteria criteria) {
        log.debug("예약 검색: 조건={}", criteria);

        // DTO를 Repository용 SearchCriteria로 변환
        ReservationRepository.SearchCriteria repositoryCriteria = convertToRepositoryCriteria(criteria);

        // 검색 결과 조회
        List<ReservationDto.Response> reservations = reservationRepository.searchReservations(repositoryCriteria);
        
        // 총 개수 조회
        long totalCount = reservationRepository.countSearchReservations(repositoryCriteria);
        
        // 페이지 계산
        int totalPages = (int) Math.ceil((double) totalCount / criteria.getSize());

        return ReservationDto.ListResponse.builder()
            .reservations(reservations)
            .totalCount(totalCount)
            .currentPage(criteria.getPage())
            .pageSize(criteria.getSize())
            .totalPages(totalPages)
            .build();
    }

    /**
     * 사용자별 예약 목록
     */
    public List<ReservationDto.Response> getUserReservations(Long userId) {
        log.debug("사용자별 예약 목록 조회: 사용자={}", userId);
        return reservationRepository.findByUserId(userId);
    }

    /**
     * 정비소별 예약 목록
     */
    public List<ReservationDto.Response> getServiceCenterReservations(Long serviceCenterId) {
        log.debug("정비소별 예약 목록 조회: 정비소={}", serviceCenterId);
        return reservationRepository.findByServiceCenterId(serviceCenterId);
    }

    /**
     * 오늘 예약 목록
     */
    public List<ReservationDto.Response> getTodayReservations() {
        log.debug("오늘 예약 목록 조회");
        return reservationRepository.findTodayReservations();
    }

    /**
     * 예약 통계
     */
    public ReservationDto.Statistics getReservationStatistics(Long serviceCenterId) {
        log.debug("예약 통계 조회: 정비소={}", serviceCenterId);
        return reservationRepository.getReservationStatistics(serviceCenterId);
    }

    /**
     * 예약 시간 검증
     */
    private void validateReservationTime(LocalDateTime scheduledDate, Integer estimatedDuration) {
        // 과거 시간 체크
        if (scheduledDate.isBefore(LocalDateTime.now())) {
            throw new BusinessException("과거 시간으로 예약할 수 없습니다.");
        }

        // 너무 먼 미래 체크 (1년 이후)
        if (scheduledDate.isAfter(LocalDateTime.now().plusYears(1))) {
            throw new BusinessException("1년 이후로는 예약할 수 없습니다.");
        }

        // 영업시간 체크 (예: 평일 9-18시)
        int hour = scheduledDate.getHour();
        int dayOfWeek = scheduledDate.getDayOfWeek().getValue(); // 1=월요일, 7=일요일
        
        if (dayOfWeek == 7) { // 일요일
            throw new BusinessException("일요일은 예약할 수 없습니다.");
        }
        
        if (hour < 9 || hour >= 18) {
            throw new BusinessException("영업시간(09:00-18:00) 내에만 예약 가능합니다.");
        }

        // 소요시간 체크
        if (estimatedDuration != null) {
            LocalDateTime endTime = scheduledDate.plusMinutes(estimatedDuration);
            if (endTime.getHour() > 18) {
                throw new BusinessException("예약 종료 시간이 영업시간을 초과합니다.");
            }
        }
    }

    /**
     * 시간 충돌 체크
     */
    private void checkTimeConflict(Long serviceCenterId, LocalDateTime scheduledDate, 
                                 Integer estimatedDuration, Long excludeId) {
        if (estimatedDuration == null) {
            estimatedDuration = 60; // 기본 1시간
        }

        LocalDateTime startTime = scheduledDate;
        LocalDateTime endTime = scheduledDate.plusMinutes(estimatedDuration);

        boolean hasConflict = reservationRepository.checkTimeConflict(
            serviceCenterId, startTime, endTime, excludeId);

        if (hasConflict) {
            throw new BusinessException("해당 시간에 이미 다른 예약이 있습니다.");
        }
    }

    /**
     * DTO를 Repository용 SearchCriteria로 변환
     */
    private ReservationRepository.SearchCriteria convertToRepositoryCriteria(ReservationDto.SearchCriteria criteria) {
        return ReservationRepository.SearchCriteria.builder()
            .userId(criteria.getUserId())
            .serviceCenterId(criteria.getServiceCenterId())
            .vehicleId(criteria.getVehicleId())
            .status(criteria.getStatus())
            .startDate(criteria.getStartDate())
            .endDate(criteria.getEndDate())
            .sortBy(criteria.getSortBy())
            .sortDirection(criteria.getSortDirection())
            .page(criteria.getPage())
            .size(criteria.getSize())
            .build();
    }
} 