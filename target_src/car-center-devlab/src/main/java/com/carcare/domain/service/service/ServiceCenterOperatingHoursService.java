package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterOperatingHours;
import com.carcare.domain.service.entity.ServiceCenter;
import com.carcare.domain.service.repository.ServiceCenterRepository;
import com.carcare.domain.service.repository.ServiceCenterOperatingHoursRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.factory.annotation.Value;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 정비소 운영시간 관리 서비스
 * 운영시간 CRUD, 상태 계산, JSON 데이터 처리 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ServiceCenterOperatingHoursService {

    private final ServiceCenterRepository serviceCenterRepository;
    private final ServiceCenterOperatingHoursRepository operatingHoursRepository;
    
    @Value("${spring.datasource.url:}")
    private String datasourceUrl;

    /**
     * 기본 운영시간 생성
     */
    @Transactional
    public OperatingHoursResult createDefaultOperatingHours(Long serviceCenterId, Long createdBy) {
        log.info("기본 운영시간 생성: 정비소ID={}", serviceCenterId);

        try {
            // 서비스 센터 존재 확인
            ServiceCenter serviceCenter = serviceCenterRepository.findById(serviceCenterId)
                .orElseThrow(() -> new BusinessException("정비소를 찾을 수 없습니다: " + serviceCenterId));

            // 기존 운영시간 확인
            if (operatingHoursRepository.existsByServiceCenterId(serviceCenterId)) {
                throw new BusinessException("이미 운영시간이 설정되어 있습니다");
            }

            // 기본 운영시간 데이터 생성
            ServiceCenterOperatingHours.OperatingHoursData defaultData = createDefaultOperatingHoursData();

            ServiceCenterOperatingHours operatingHours = ServiceCenterOperatingHours.builder()
                .serviceCenterId(serviceCenterId)
                .currentStatus(ServiceCenterOperatingHours.OperatingStatus.UNKNOWN)
                .autoStatusUpdate(true)
                .timezone("Asia/Seoul")
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .createdBy(createdBy)
                .updatedBy(createdBy)
                .build();

            operatingHours.setOperatingHoursData(defaultData);

            // 현재 상태 계산 및 업데이트
            updateOperatingStatus(operatingHours);

            // 데이터베이스에 저장
            Long savedId = saveOperatingHours(operatingHours);

            log.info("기본 운영시간 생성 완료: 정비소ID={}, 운영시간ID={}", serviceCenterId, savedId);

            return OperatingHoursResult.builder()
                .success(true)
                .operatingHoursId(savedId)
                .currentStatus(operatingHours.getCurrentStatus())
                .message("기본 운영시간이 설정되었습니다")
                .summary(operatingHours.getOperatingHoursSummary())
                .build();

        } catch (Exception e) {
            log.error("기본 운영시간 생성 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return OperatingHoursResult.builder()
                .success(false)
                .errorMessage("운영시간 생성 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 운영시간 업데이트
     */
    @Transactional
    public OperatingHoursResult updateOperatingHours(Long serviceCenterId, OperatingHoursUpdateRequest request, Long updatedBy) {
        log.info("운영시간 업데이트: 정비소ID={}", serviceCenterId);

        try {
            ServiceCenterOperatingHours operatingHours = operatingHoursRepository.findByServiceCenterId(serviceCenterId)
                .orElseThrow(() -> new BusinessException("운영시간 정보를 찾을 수 없습니다: " + serviceCenterId));

            // 기존 데이터 로드
            ServiceCenterOperatingHours.OperatingHoursData currentData = operatingHours.getOperatingHoursData();

            // 요청에 따라 데이터 업데이트
            if (request.getWeeklySchedule() != null) {
                currentData.setWeeklySchedule(request.getWeeklySchedule());
            }

            if (request.getSpecialDates() != null) {
                currentData.getSpecialDates().putAll(request.getSpecialDates());
            }

            if (request.getHolidays() != null) {
                currentData.setHolidays(request.getHolidays());
            }

            if (request.getRegularClosedDays() != null) {
                currentData.setRegularClosedDays(request.getRegularClosedDays());
            }

            if (request.getTemporaryClosures() != null) {
                currentData.setTemporaryClosures(request.getTemporaryClosures());
            }

            if (request.getDefaultSettings() != null) {
                currentData.setDefaultSettings(request.getDefaultSettings());
            }

            // 데이터 검증
            ValidationResult validation = validateOperatingHoursData(currentData);
            if (!validation.isValid()) {
                return OperatingHoursResult.builder()
                    .success(false)
                    .errorMessage("운영시간 데이터 검증 실패: " + validation.getErrorMessage())
                    .build();
            }

            // 업데이트된 데이터 저장
            operatingHours.setOperatingHoursData(currentData);
            operatingHours.setUpdatedAt(LocalDateTime.now());
            operatingHours.setUpdatedBy(updatedBy);

            // 현재 상태 재계산
            updateOperatingStatus(operatingHours);

            // 데이터베이스 업데이트
            operatingHoursRepository.update(operatingHours);

            log.info("운영시간 업데이트 완료: 정비소ID={}", serviceCenterId);

            return OperatingHoursResult.builder()
                .success(true)
                .operatingHoursId(operatingHours.getId())
                .currentStatus(operatingHours.getCurrentStatus())
                .message("운영시간이 업데이트되었습니다")
                .summary(operatingHours.getOperatingHoursSummary())
                .nextStatusChangeAt(operatingHours.getNextStatusChangeAt())
                .build();

        } catch (Exception e) {
            log.error("운영시간 업데이트 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return OperatingHoursResult.builder()
                .success(false)
                .errorMessage("운영시간 업데이트 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 운영시간 조회
     */
    public OperatingHoursDetailResult getOperatingHours(Long serviceCenterId) {
        log.debug("운영시간 조회: 정비소ID={}", serviceCenterId);

        try {
            Optional<ServiceCenterOperatingHours> operatingHoursOpt = operatingHoursRepository.findByServiceCenterId(serviceCenterId);

            if (operatingHoursOpt.isEmpty()) {
                return OperatingHoursDetailResult.builder()
                    .serviceCenterId(serviceCenterId)
                    .hasOperatingHours(false)
                    .message("운영시간이 설정되지 않았습니다")
                    .build();
            }

            ServiceCenterOperatingHours operatingHours = operatingHoursOpt.get();

            // 현재 상태가 오래된 경우 업데이트
            if (needsStatusUpdate(operatingHours)) {
                updateOperatingStatus(operatingHours);
                // TODO: 실제 구현에서는 상태만 업데이트
            }

            return OperatingHoursDetailResult.builder()
                .serviceCenterId(serviceCenterId)
                .operatingHoursId(operatingHours.getId())
                .hasOperatingHours(true)
                .currentStatus(operatingHours.getCurrentStatus())
                .operatingHoursData(operatingHours.getOperatingHoursData())
                .summary(operatingHours.getOperatingHoursSummary())
                .nextStatusChangeAt(operatingHours.getNextStatusChangeAt())
                .statusUpdatedAt(operatingHours.getStatusUpdatedAt())
                .timezone(operatingHours.getTimezone())
                .autoStatusUpdate(operatingHours.getAutoStatusUpdate())
                .build();

        } catch (Exception e) {
            log.error("운영시간 조회 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return OperatingHoursDetailResult.builder()
                .serviceCenterId(serviceCenterId)
                .hasOperatingHours(false)
                .errorMessage("운영시간 조회 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 현재 운영 상태 조회
     */
    public OperatingStatusResult getCurrentOperatingStatus(Long serviceCenterId) {
        log.debug("현재 운영 상태 조회: 정비소ID={}", serviceCenterId);

        try {
            Optional<ServiceCenterOperatingHours> operatingHoursOpt = operatingHoursRepository.findByServiceCenterId(serviceCenterId);

            if (operatingHoursOpt.isEmpty()) {
                return OperatingStatusResult.builder()
                    .serviceCenterId(serviceCenterId)
                    .status(ServiceCenterOperatingHours.OperatingStatus.UNKNOWN)
                    .message("운영시간 정보가 없습니다")
                    .build();
            }

            ServiceCenterOperatingHours operatingHours = operatingHoursOpt.get();
            ServiceCenterOperatingHours.OperatingStatus currentStatus = operatingHours.getCurrentOperatingStatus();

            // 상태 변경이 필요한 경우 업데이트
            if (currentStatus != operatingHours.getCurrentStatus()) {
                operatingHours.setCurrentStatus(currentStatus);
                operatingHours.setStatusUpdatedAt(LocalDateTime.now());
                operatingHours.setNextStatusChangeAt(operatingHours.getNextStatusChangeTime());
                // TODO: 실제 구현에서는 상태만 업데이트
            }

            return OperatingStatusResult.builder()
                .serviceCenterId(serviceCenterId)
                .status(currentStatus)
                .statusDescription(currentStatus.getDescription())
                .isOpen(currentStatus.isOpen())
                .nextStatusChangeAt(operatingHours.getNextStatusChangeTime())
                .lastUpdatedAt(operatingHours.getStatusUpdatedAt())
                .message("운영 상태 조회 완료")
                .build();

        } catch (Exception e) {
            log.error("운영 상태 조회 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return OperatingStatusResult.builder()
                .serviceCenterId(serviceCenterId)
                .status(ServiceCenterOperatingHours.OperatingStatus.UNKNOWN)
                .errorMessage("운영 상태 조회 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 예약 가능한 시간대 조회
     */
    public ReservationSlotsResult getAvailableReservationSlots(Long serviceCenterId, LocalDate date) {
        log.debug("예약 가능 시간대 조회: 정비소ID={}, 날짜={}", serviceCenterId, date);

        try {
            Optional<ServiceCenterOperatingHours> operatingHoursOpt = operatingHoursRepository.findByServiceCenterId(serviceCenterId);

            if (operatingHoursOpt.isEmpty()) {
                return ReservationSlotsResult.builder()
                    .serviceCenterId(serviceCenterId)
                    .date(date)
                    .isBusinessDay(false)
                    .availableSlots(Collections.emptyList())
                    .message("운영시간 정보가 없습니다")
                    .build();
            }

            ServiceCenterOperatingHours operatingHours = operatingHoursOpt.get();
            boolean isBusinessDay = operatingHours.isBusinessDay(date);
            List<LocalDateTime> availableSlots = operatingHours.getAvailableReservationSlots(date);

            return ReservationSlotsResult.builder()
                .serviceCenterId(serviceCenterId)
                .date(date)
                .isBusinessDay(isBusinessDay)
                .availableSlots(availableSlots)
                .totalSlots(availableSlots.size())
                .message("예약 가능 시간대 조회 완료")
                .build();

        } catch (Exception e) {
            log.error("예약 가능 시간대 조회 중 오류 발생: 정비소ID={}, 날짜={}, 오류={}", serviceCenterId, date, e.getMessage(), e);
            return ReservationSlotsResult.builder()
                .serviceCenterId(serviceCenterId)
                .date(date)
                .isBusinessDay(false)
                .availableSlots(Collections.emptyList())
                .errorMessage("예약 가능 시간대 조회 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 운영 중인 정비소 목록 조회
     */
    public List<Long> getCurrentlyOpenServiceCenters() {
        log.debug("현재 운영 중인 정비소 목록 조회");

        try {
            // 데이터베이스에서 모든 운영시간 조회
            List<ServiceCenterOperatingHours> allOperatingHours = operatingHoursRepository.findAll();

            return allOperatingHours.stream()
                .filter(hours -> hours.getCurrentOperatingStatus().isOpen())
                .map(ServiceCenterOperatingHours::getServiceCenterId)
                .collect(Collectors.toList());

        } catch (Exception e) {
            log.error("운영 중인 정비소 목록 조회 중 오류 발생: {}", e.getMessage(), e);
            return Collections.emptyList();
        }
    }

    /**
     * 일괄 운영 상태 업데이트
     */
    @Transactional
    public BatchUpdateResult batchUpdateOperatingStatus() {
        log.info("일괄 운영 상태 업데이트 시작");

        try {
            List<ServiceCenterOperatingHours> allOperatingHours = operatingHoursRepository.findAll();
            int totalCount = allOperatingHours.size();
            int updatedCount = 0;

            for (ServiceCenterOperatingHours operatingHours : allOperatingHours) {
                if (operatingHours.getAutoStatusUpdate()) {
                    try {
                        updateOperatingStatus(operatingHours);
                        // TODO: 실제 구현에서는 상태만 업데이트
                        updatedCount++;
                    } catch (Exception e) {
                        log.warn("운영시간 상태 업데이트 실패: 정비소ID={}, 오류={}", 
                               operatingHours.getServiceCenterId(), e.getMessage());
                    }
                }
            }

            log.info("일괄 운영 상태 업데이트 완료: 전체={}, 업데이트={}", totalCount, updatedCount);

            return BatchUpdateResult.builder()
                .success(true)
                .totalCount(totalCount)
                .updatedCount(updatedCount)
                .message("일괄 운영 상태 업데이트가 완료되었습니다")
                .build();

        } catch (Exception e) {
            log.error("일괄 운영 상태 업데이트 중 오류 발생: {}", e.getMessage(), e);
            return BatchUpdateResult.builder()
                .success(false)
                .errorMessage("일괄 업데이트 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    // === 내부 메서드들 ===

    private ServiceCenterOperatingHours.OperatingHoursData createDefaultOperatingHoursData() {
        Map<String, ServiceCenterOperatingHours.DayOperatingHours> weeklySchedule = new HashMap<>();

        // 평일 기본 운영시간 (월-금)
        List<String> weekdays = Arrays.asList("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY");
        for (String day : weekdays) {
            weeklySchedule.put(day, ServiceCenterOperatingHours.DayOperatingHours.builder()
                .isOpen(true)
                .timeSlots(Arrays.asList(
                    ServiceCenterOperatingHours.TimeSlot.builder()
                        .startTime("09:00")
                        .endTime("18:00")
                        .type(ServiceCenterOperatingHours.TimeSlotType.OPERATING)
                        .description("정상 영업시간")
                        .build()
                ))
                .breakTimes(Arrays.asList(
                    ServiceCenterOperatingHours.TimeSlot.builder()
                        .startTime("12:00")
                        .endTime("13:00")
                        .type(ServiceCenterOperatingHours.TimeSlotType.BREAK)
                        .description("점심시간")
                        .build()
                ))
                .note("평일 운영")
                .build());
        }

        // 토요일 단축 운영
        weeklySchedule.put("SATURDAY", ServiceCenterOperatingHours.DayOperatingHours.builder()
            .isOpen(true)
            .timeSlots(Arrays.asList(
                ServiceCenterOperatingHours.TimeSlot.builder()
                    .startTime("09:00")
                    .endTime("14:00")
                    .type(ServiceCenterOperatingHours.TimeSlotType.OPERATING)
                    .description("토요일 단축 운영")
                    .build()
            ))
            .note("토요일 단축 운영")
            .build());

        // 일요일 휴무
        weeklySchedule.put("SUNDAY", ServiceCenterOperatingHours.DayOperatingHours.builder()
            .isOpen(false)
            .note("정기 휴무")
            .build());

        return ServiceCenterOperatingHours.OperatingHoursData.builder()
            .weeklySchedule(weeklySchedule)
            .regularClosedDays(Arrays.asList("SUNDAY"))
            .defaultSettings(ServiceCenterOperatingHours.DefaultSettings.builder()
                .timezone("Asia/Seoul")
                .defaultOpenTime("09:00")
                .defaultCloseTime("18:00")
                .reservationSlotMinutes(30)
                .lastReservationMinutesBefore(60)
                .is24Hours(false)
                .isAlwaysOpen(false)
                .build())
            .build();
    }

    private ValidationResult validateOperatingHoursData(ServiceCenterOperatingHours.OperatingHoursData data) {
        try {
            // 시간 형식 검증
            for (ServiceCenterOperatingHours.DayOperatingHours dayHours : data.getWeeklySchedule().values()) {
                for (ServiceCenterOperatingHours.TimeSlot slot : dayHours.getTimeSlots()) {
                    if (!isValidTimeFormat(slot.getStartTime()) || !isValidTimeFormat(slot.getEndTime())) {
                        return ValidationResult.builder()
                            .isValid(false)
                            .errorMessage("시간 형식이 올바르지 않습니다 (HH:mm 형식 사용)")
                            .build();
                    }

                    if (LocalTime.parse(slot.getStartTime()).isAfter(LocalTime.parse(slot.getEndTime()))) {
                        return ValidationResult.builder()
                            .isValid(false)
                            .errorMessage("시작 시간이 종료 시간보다 늦을 수 없습니다")
                            .build();
                    }
                }
            }

            // 날짜 형식 검증
            for (String dateStr : data.getHolidays()) {
                if (!isValidDateFormat(dateStr)) {
                    return ValidationResult.builder()
                        .isValid(false)
                        .errorMessage("날짜 형식이 올바르지 않습니다 (yyyy-MM-dd 형식 사용)")
                        .build();
                }
            }

            return ValidationResult.builder()
                .isValid(true)
                .build();

        } catch (Exception e) {
            return ValidationResult.builder()
                .isValid(false)
                .errorMessage("데이터 검증 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    private boolean isValidTimeFormat(String timeStr) {
        try {
            LocalTime.parse(timeStr);
            return true;
        } catch (DateTimeParseException e) {
            return false;
        }
    }

    private boolean isValidDateFormat(String dateStr) {
        try {
            LocalDate.parse(dateStr, DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            return true;
        } catch (DateTimeParseException e) {
            return false;
        }
    }

    private void updateOperatingStatus(ServiceCenterOperatingHours operatingHours) {
        ServiceCenterOperatingHours.OperatingStatus newStatus = operatingHours.getCurrentOperatingStatus();
        LocalDateTime nextChange = operatingHours.getNextStatusChangeTime();

        operatingHours.setCurrentStatus(newStatus);
        operatingHours.setNextStatusChangeAt(nextChange);
        operatingHours.setStatusUpdatedAt(LocalDateTime.now());
    }

    private boolean needsStatusUpdate(ServiceCenterOperatingHours operatingHours) {
        if (operatingHours.getStatusUpdatedAt() == null) {
            return true;
        }

        // 5분 이상 오래된 상태는 업데이트 필요
        return operatingHours.getStatusUpdatedAt().isBefore(LocalDateTime.now().minusMinutes(5));
    }

    // Repository 메서드로 대체됨 - 더 이상 필요하지 않음

    private Long saveOperatingHours(ServiceCenterOperatingHours operatingHours) {
        // H2 또는 PostgreSQL에 따라 다른 메서드 사용
        if (datasourceUrl.contains("h2")) {
            operatingHoursRepository.saveH2(operatingHours);
        } else {
            operatingHoursRepository.save(operatingHours);
        }
        return operatingHours.getId();
    }

    // updateOperatingHours 메서드는 이미 Repository를 직접 호출하도록 수정됨

    // === 요청/응답 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class OperatingHoursUpdateRequest {
        private Map<String, ServiceCenterOperatingHours.DayOperatingHours> weeklySchedule;
        private Map<String, ServiceCenterOperatingHours.SpecialOperatingHours> specialDates;
        private List<String> holidays;
        private List<String> regularClosedDays;
        private List<ServiceCenterOperatingHours.TemporaryClosurePeriod> temporaryClosures;
        private ServiceCenterOperatingHours.DefaultSettings defaultSettings;
    }

    @lombok.Data
    @lombok.Builder
    public static class OperatingHoursResult {
        private boolean success;
        private Long operatingHoursId;
        private ServiceCenterOperatingHours.OperatingStatus currentStatus;
        private String summary;
        private LocalDateTime nextStatusChangeAt;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class OperatingHoursDetailResult {
        private Long serviceCenterId;
        private Long operatingHoursId;
        private boolean hasOperatingHours;
        private ServiceCenterOperatingHours.OperatingStatus currentStatus;
        private ServiceCenterOperatingHours.OperatingHoursData operatingHoursData;
        private String summary;
        private LocalDateTime nextStatusChangeAt;
        private LocalDateTime statusUpdatedAt;
        private String timezone;
        private Boolean autoStatusUpdate;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class OperatingStatusResult {
        private Long serviceCenterId;
        private ServiceCenterOperatingHours.OperatingStatus status;
        private String statusDescription;
        private boolean isOpen;
        private LocalDateTime nextStatusChangeAt;
        private LocalDateTime lastUpdatedAt;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class ReservationSlotsResult {
        private Long serviceCenterId;
        private LocalDate date;
        private boolean isBusinessDay;
        private List<LocalDateTime> availableSlots;
        private int totalSlots;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class BatchUpdateResult {
        private boolean success;
        private int totalCount;
        private int updatedCount;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class ValidationResult {
        private boolean isValid;
        private String errorMessage;
    }
} 