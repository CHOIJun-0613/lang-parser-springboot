package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterOperatingHours;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoField;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 특별 운영시간 및 휴무일 관리 서비스
 * 공휴일 자동 계산, 임시 휴무 관리, 특별 이벤트 운영시간 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SpecialOperatingHoursManagementService {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    /**
     * 한국 공휴일 자동 계산 및 적용
     */
    public HolidayManagementResult applyKoreanHolidays(Long serviceCenterId, int year, boolean replaceExisting) {
        log.info("한국 공휴일 적용: 정비소ID={}, 연도={}, 기존교체={}", serviceCenterId, year, replaceExisting);

        try {
            List<HolidayInfo> koreanHolidays = calculateKoreanHolidays(year);
            
            // TODO: 실제 구현에서는 기존 운영시간 데이터 로드
            ServiceCenterOperatingHours.OperatingHoursData data = loadOperatingHoursData(serviceCenterId);

            if (replaceExisting) {
                // 해당 연도의 기존 공휴일 제거
                data.getHolidays().removeIf(holidayDate -> holidayDate.startsWith(String.valueOf(year)));
                data.getSpecialDates().entrySet().removeIf(entry -> 
                    entry.getKey().startsWith(String.valueOf(year)) && 
                    entry.getValue().getReason() != null && 
                    entry.getValue().getReason().contains("공휴일"));
            }

            int addedCount = 0;
            for (HolidayInfo holiday : koreanHolidays) {
                String dateStr = holiday.getDate().format(DATE_FORMATTER);
                
                if (!data.getHolidays().contains(dateStr)) {
                    data.getHolidays().add(dateStr);
                    
                    // 특별 운영시간으로도 등록 (휴무)
                    data.getSpecialDates().put(dateStr, 
                        ServiceCenterOperatingHours.SpecialOperatingHours.builder()
                            .date(dateStr)
                            .isOpen(false)
                            .reason("공휴일: " + holiday.getName())
                            .note(holiday.getDescription())
                            .build());
                    
                    addedCount++;
                }
            }

            // TODO: 실제 구현에서는 데이터베이스 업데이트
            saveOperatingHoursData(serviceCenterId, data);

            log.info("한국 공휴일 적용 완료: 정비소ID={}, 추가됨={}", serviceCenterId, addedCount);

            return HolidayManagementResult.builder()
                .success(true)
                .serviceCenterId(serviceCenterId)
                .year(year)
                .addedHolidays(koreanHolidays)
                .addedCount(addedCount)
                .message(String.format("%d년 한국 공휴일 %d개가 적용되었습니다", year, addedCount))
                .build();

        } catch (Exception e) {
            log.error("한국 공휴일 적용 중 오류 발생: 정비소ID={}, 연도={}, 오류={}", 
                     serviceCenterId, year, e.getMessage(), e);
            return HolidayManagementResult.builder()
                .success(false)
                .serviceCenterId(serviceCenterId)
                .year(year)
                .errorMessage("공휴일 적용 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 임시 휴무 등록
     */
    public TemporaryClosureResult addTemporaryClosure(Long serviceCenterId, TemporaryClosureRequest request) {
        log.info("임시 휴무 등록: 정비소ID={}, 기간={} ~ {}", 
                serviceCenterId, request.getStartDate(), request.getEndDate());

        try {
            // 날짜 유효성 검증
            ValidationResult validation = validateDateRange(request.getStartDate(), request.getEndDate());
            if (!validation.isValid()) {
                return TemporaryClosureResult.builder()
                    .success(false)
                    .errorMessage(validation.getErrorMessage())
                    .build();
            }

            ServiceCenterOperatingHours.OperatingHoursData data = loadOperatingHoursData(serviceCenterId);

            // 중복 기간 확인
            List<ServiceCenterOperatingHours.TemporaryClosurePeriod> overlappingPeriods = 
                findOverlappingClosurePeriods(data.getTemporaryClosures(), request.getStartDate(), request.getEndDate());

            if (!overlappingPeriods.isEmpty() && !request.isAllowOverlap()) {
                return TemporaryClosureResult.builder()
                    .success(false)
                    .errorMessage("지정된 기간과 겹치는 임시 휴무가 이미 존재합니다")
                    .overlappingPeriods(overlappingPeriods)
                    .build();
            }

            // 새 임시 휴무 기간 추가
            ServiceCenterOperatingHours.TemporaryClosurePeriod newClosure = 
                ServiceCenterOperatingHours.TemporaryClosurePeriod.builder()
                    .startDate(request.getStartDate().format(DATE_FORMATTER))
                    .endDate(request.getEndDate().format(DATE_FORMATTER))
                    .reason(request.getReason())
                    .note(request.getNote())
                    .build();

            data.getTemporaryClosures().add(newClosure);

            // 해당 기간의 특별 운영시간도 휴무로 설정
            LocalDate current = request.getStartDate();
            int affectedDays = 0;
            while (!current.isAfter(request.getEndDate())) {
                String dateStr = current.format(DATE_FORMATTER);
                data.getSpecialDates().put(dateStr,
                    ServiceCenterOperatingHours.SpecialOperatingHours.builder()
                        .date(dateStr)
                        .isOpen(false)
                        .reason("임시 휴무: " + request.getReason())
                        .note(request.getNote())
                        .build());
                current = current.plusDays(1);
                affectedDays++;
            }

            saveOperatingHoursData(serviceCenterId, data);

            log.info("임시 휴무 등록 완료: 정비소ID={}, 영향받은 일수={}", serviceCenterId, affectedDays);

            return TemporaryClosureResult.builder()
                .success(true)
                .serviceCenterId(serviceCenterId)
                .addedClosure(newClosure)
                .affectedDays(affectedDays)
                .message("임시 휴무가 등록되었습니다")
                .build();

        } catch (Exception e) {
            log.error("임시 휴무 등록 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return TemporaryClosureResult.builder()
                .success(false)
                .serviceCenterId(serviceCenterId)
                .errorMessage("임시 휴무 등록 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 특별 운영시간 등록
     */
    public SpecialHoursResult addSpecialOperatingHours(Long serviceCenterId, SpecialHoursRequest request) {
        log.info("특별 운영시간 등록: 정비소ID={}, 날짜={}", serviceCenterId, request.getDate());

        try {
            ServiceCenterOperatingHours.OperatingHoursData data = loadOperatingHoursData(serviceCenterId);

            String dateStr = request.getDate().format(DATE_FORMATTER);

            // 기존 특별 운영시간 확인
            if (data.getSpecialDates().containsKey(dateStr) && !request.isReplaceExisting()) {
                return SpecialHoursResult.builder()
                    .success(false)
                    .errorMessage("해당 날짜에 이미 특별 운영시간이 설정되어 있습니다")
                    .build();
            }

            // 시간대 유효성 검증
            if (request.isOpen() && (request.getTimeSlots() == null || request.getTimeSlots().isEmpty())) {
                return SpecialHoursResult.builder()
                    .success(false)
                    .errorMessage("운영시간이 설정된 경우 시간대 정보는 필수입니다")
                    .build();
            }

            // 새 특별 운영시간 생성
            ServiceCenterOperatingHours.SpecialOperatingHours specialHours = 
                ServiceCenterOperatingHours.SpecialOperatingHours.builder()
                    .date(dateStr)
                    .isOpen(request.isOpen())
                    .timeSlots(request.getTimeSlots() != null ? request.getTimeSlots() : new ArrayList<>())
                    .reason(request.getReason())
                    .note(request.getNote())
                    .build();

            data.getSpecialDates().put(dateStr, specialHours);

            // 공휴일 목록에서도 관리 (휴무인 경우 추가, 운영인 경우 제거)
            if (!request.isOpen()) {
                if (!data.getHolidays().contains(dateStr)) {
                    data.getHolidays().add(dateStr);
                }
            } else {
                data.getHolidays().remove(dateStr);
            }

            saveOperatingHoursData(serviceCenterId, data);

            log.info("특별 운영시간 등록 완료: 정비소ID={}, 날짜={}, 운영={}", 
                    serviceCenterId, dateStr, request.isOpen());

            return SpecialHoursResult.builder()
                .success(true)
                .serviceCenterId(serviceCenterId)
                .date(request.getDate())
                .specialHours(specialHours)
                .message("특별 운영시간이 등록되었습니다")
                .build();

        } catch (Exception e) {
            log.error("특별 운영시간 등록 중 오류 발생: 정비소ID={}, 날짜={}, 오류={}", 
                     serviceCenterId, request.getDate(), e.getMessage(), e);
            return SpecialHoursResult.builder()
                .success(false)
                .serviceCenterId(serviceCenterId)
                .date(request.getDate())
                .errorMessage("특별 운영시간 등록 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 임시 휴무 제거
     */
    public TemporaryClosureResult removeTemporaryClosure(Long serviceCenterId, LocalDate startDate, LocalDate endDate) {
        log.info("임시 휴무 제거: 정비소ID={}, 기간={} ~ {}", serviceCenterId, startDate, endDate);

        try {
            ServiceCenterOperatingHours.OperatingHoursData data = loadOperatingHoursData(serviceCenterId);

            String startDateStr = startDate.format(DATE_FORMATTER);
            String endDateStr = endDate.format(DATE_FORMATTER);

            // 해당 기간의 임시 휴무 찾기 및 제거
            List<ServiceCenterOperatingHours.TemporaryClosurePeriod> toRemove = data.getTemporaryClosures().stream()
                .filter(closure -> closure.getStartDate().equals(startDateStr) && closure.getEndDate().equals(endDateStr))
                .collect(Collectors.toList());

            if (toRemove.isEmpty()) {
                return TemporaryClosureResult.builder()
                    .success(false)
                    .errorMessage("지정된 기간의 임시 휴무를 찾을 수 없습니다")
                    .build();
            }

            data.getTemporaryClosures().removeAll(toRemove);

            // 해당 기간의 특별 운영시간에서 임시 휴무 관련 항목 제거
            LocalDate current = startDate;
            int affectedDays = 0;
            while (!current.isAfter(endDate)) {
                String dateStr = current.format(DATE_FORMATTER);
                ServiceCenterOperatingHours.SpecialOperatingHours existing = data.getSpecialDates().get(dateStr);
                
                if (existing != null && existing.getReason() != null && 
                    existing.getReason().startsWith("임시 휴무")) {
                    data.getSpecialDates().remove(dateStr);
                    affectedDays++;
                }
                
                current = current.plusDays(1);
            }

            saveOperatingHoursData(serviceCenterId, data);

            log.info("임시 휴무 제거 완료: 정비소ID={}, 제거된 기간={}, 영향받은 일수={}", 
                    serviceCenterId, toRemove.size(), affectedDays);

            return TemporaryClosureResult.builder()
                .success(true)
                .serviceCenterId(serviceCenterId)
                .affectedDays(affectedDays)
                .message("임시 휴무가 제거되었습니다")
                .build();

        } catch (Exception e) {
            log.error("임시 휴무 제거 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return TemporaryClosureResult.builder()
                .success(false)
                .serviceCenterId(serviceCenterId)
                .errorMessage("임시 휴무 제거 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    /**
     * 특별 운영시간 목록 조회
     */
    public SpecialHoursListResult getSpecialOperatingHours(Long serviceCenterId, LocalDate fromDate, LocalDate toDate) {
        log.debug("특별 운영시간 목록 조회: 정비소ID={}, 기간={} ~ {}", serviceCenterId, fromDate, toDate);

        try {
            ServiceCenterOperatingHours.OperatingHoursData data = loadOperatingHoursData(serviceCenterId);

            List<SpecialHoursInfo> specialHoursList = new ArrayList<>();
            List<HolidayInfo> holidaysList = new ArrayList<>();
            List<ServiceCenterOperatingHours.TemporaryClosurePeriod> activePeriods = new ArrayList<>();

            // 특별 운영시간 수집
            LocalDate current = fromDate;
            while (!current.isAfter(toDate)) {
                String dateStr = current.format(DATE_FORMATTER);
                
                if (data.getSpecialDates().containsKey(dateStr)) {
                    ServiceCenterOperatingHours.SpecialOperatingHours specialHours = data.getSpecialDates().get(dateStr);
                    specialHoursList.add(SpecialHoursInfo.builder()
                        .date(current)
                        .isOpen(specialHours.isOpen())
                        .timeSlots(specialHours.getTimeSlots())
                        .reason(specialHours.getReason())
                        .note(specialHours.getNote())
                        .build());
                }

                if (data.getHolidays().contains(dateStr)) {
                    holidaysList.add(HolidayInfo.builder()
                        .date(current)
                        .name(getHolidayName(current))
                        .isNationalHoliday(isNationalHoliday(current))
                        .build());
                }

                current = current.plusDays(1);
            }

            // 활성 임시 휴무 기간 수집
            activePeriods = data.getTemporaryClosures().stream()
                .filter(closure -> {
                    LocalDate start = LocalDate.parse(closure.getStartDate());
                    LocalDate end = LocalDate.parse(closure.getEndDate());
                    return !(end.isBefore(fromDate) || start.isAfter(toDate));
                })
                .collect(Collectors.toList());

            return SpecialHoursListResult.builder()
                .success(true)
                .serviceCenterId(serviceCenterId)
                .fromDate(fromDate)
                .toDate(toDate)
                .specialHours(specialHoursList)
                .holidays(holidaysList)
                .temporaryClosures(activePeriods)
                .totalSpecialDays(specialHoursList.size())
                .totalHolidays(holidaysList.size())
                .totalClosurePeriods(activePeriods.size())
                .message("특별 운영시간 목록 조회가 완료되었습니다")
                .build();

        } catch (Exception e) {
            log.error("특별 운영시간 목록 조회 중 오류 발생: 정비소ID={}, 오류={}", serviceCenterId, e.getMessage(), e);
            return SpecialHoursListResult.builder()
                .success(false)
                .serviceCenterId(serviceCenterId)
                .fromDate(fromDate)
                .toDate(toDate)
                .errorMessage("특별 운영시간 목록 조회 중 오류가 발생했습니다: " + e.getMessage())
                .build();
        }
    }

    // === 내부 메서드들 ===

    /**
     * 한국 공휴일 계산
     */
    private List<HolidayInfo> calculateKoreanHolidays(int year) {
        List<HolidayInfo> holidays = new ArrayList<>();

        // 고정 공휴일
        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 1, 1))
            .name("신정")
            .isNationalHoliday(true)
            .description("새해 첫날")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 3, 1))
            .name("삼일절")
            .isNationalHoliday(true)
            .description("3·1 운동 기념일")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 5, 5))
            .name("어린이날")
            .isNationalHoliday(true)
            .description("어린이를 위한 날")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 6, 6))
            .name("현충일")
            .isNationalHoliday(true)
            .description("호국영령을 추모하는 날")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 8, 15))
            .name("광복절")
            .isNationalHoliday(true)
            .description("일제강점기로부터의 해방 기념일")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 10, 3))
            .name("개천절")
            .isNationalHoliday(true)
            .description("단군왕검이 고조선을 건국한 날")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 10, 9))
            .name("한글날")
            .isNationalHoliday(true)
            .description("한글 창제를 기념하는 날")
            .build());

        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 12, 25))
            .name("크리스마스")
            .isNationalHoliday(true)
            .description("예수 그리스도의 탄생을 기념하는 날")
            .build());

        // 음력 기반 공휴일 (근사치 계산)
        // 실제 구현에서는 정확한 음력-양력 변환 라이브러리 사용 필요
        holidays.addAll(calculateLunarHolidays(year));

        // 어버이날 (5월 8일)
        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 5, 8))
            .name("어버이날")
            .isNationalHoliday(false)
            .description("부모님의 은혜에 감사하는 날")
            .build());

        // 스승의 날 (5월 15일)
        holidays.add(HolidayInfo.builder()
            .date(LocalDate.of(year, 5, 15))
            .name("스승의날")
            .isNationalHoliday(false)
            .description("선생님의 은혜에 감사하는 날")
            .build());

        return holidays.stream()
            .sorted(Comparator.comparing(HolidayInfo::getDate))
            .collect(Collectors.toList());
    }

    /**
     * 음력 기반 공휴일 근사치 계산
     */
    private List<HolidayInfo> calculateLunarHolidays(int year) {
        List<HolidayInfo> lunarHolidays = new ArrayList<>();

        // 실제 구현에서는 정확한 음력-양력 변환이 필요
        // 여기서는 대략적인 날짜로 시뮬레이션

        // 설날 (대략 1월 말 ~ 2월 중순)
        LocalDate seollal = estimateLunarNewYear(year);
        lunarHolidays.add(HolidayInfo.builder()
            .date(seollal.minusDays(1))
            .name("설날 연휴")
            .isNationalHoliday(true)
            .description("설날 전날")
            .build());
        lunarHolidays.add(HolidayInfo.builder()
            .date(seollal)
            .name("설날")
            .isNationalHoliday(true)
            .description("음력 새해 첫날")
            .build());
        lunarHolidays.add(HolidayInfo.builder()
            .date(seollal.plusDays(1))
            .name("설날 연휴")
            .isNationalHoliday(true)
            .description("설날 다음날")
            .build());

        // 부처님 오신 날 (대략 5월)
        LocalDate buddhasBirthday = estimateBuddhasBirthday(year);
        lunarHolidays.add(HolidayInfo.builder()
            .date(buddhasBirthday)
            .name("부처님오신날")
            .isNationalHoliday(true)
            .description("석가탄신일")
            .build());

        // 추석 (대략 9월 ~ 10월)
        LocalDate chuseok = estimateChuseok(year);
        lunarHolidays.add(HolidayInfo.builder()
            .date(chuseok.minusDays(1))
            .name("추석 연휴")
            .isNationalHoliday(true)
            .description("추석 전날")
            .build());
        lunarHolidays.add(HolidayInfo.builder()
            .date(chuseok)
            .name("추석")
            .isNationalHoliday(true)
            .description("한가위, 중추절")
            .build());
        lunarHolidays.add(HolidayInfo.builder()
            .date(chuseok.plusDays(1))
            .name("추석 연휴")
            .isNationalHoliday(true)
            .description("추석 다음날")
            .build());

        return lunarHolidays;
    }

    // 음력 공휴일 근사 계산 (실제로는 정확한 계산 필요)
    private LocalDate estimateLunarNewYear(int year) {
        // 근사치: 1월 21일 ~ 2월 20일 사이
        return LocalDate.of(year, 2, 1); // 임시값
    }

    private LocalDate estimateBuddhasBirthday(int year) {
        // 근사치: 5월 중순
        return LocalDate.of(year, 5, 15); // 임시값
    }

    private LocalDate estimateChuseok(int year) {
        // 근사치: 9월 중순 ~ 10월 초
        return LocalDate.of(year, 9, 15); // 임시값
    }

    private ValidationResult validateDateRange(LocalDate startDate, LocalDate endDate) {
        if (startDate.isAfter(endDate)) {
            return ValidationResult.builder()
                .isValid(false)
                .errorMessage("시작 날짜가 종료 날짜보다 늦을 수 없습니다")
                .build();
        }

        if (startDate.isBefore(LocalDate.now())) {
            return ValidationResult.builder()
                .isValid(false)
                .errorMessage("과거 날짜로는 임시 휴무를 설정할 수 없습니다")
                .build();
        }

        if (ChronoUnit.DAYS.between(startDate, endDate) > 365) {
            return ValidationResult.builder()
                .isValid(false)
                .errorMessage("임시 휴무 기간은 1년을 초과할 수 없습니다")
                .build();
        }

        return ValidationResult.builder()
            .isValid(true)
            .build();
    }

    private List<ServiceCenterOperatingHours.TemporaryClosurePeriod> findOverlappingClosurePeriods(
            List<ServiceCenterOperatingHours.TemporaryClosurePeriod> existingPeriods,
            LocalDate startDate, LocalDate endDate) {
        
        return existingPeriods.stream()
            .filter(period -> {
                LocalDate existingStart = LocalDate.parse(period.getStartDate());
                LocalDate existingEnd = LocalDate.parse(period.getEndDate());
                
                // 겹치는 조건: 새 시작일이 기존 기간 내에 있거나, 새 종료일이 기존 기간 내에 있거나,
                // 새 기간이 기존 기간을 완전히 포함하는 경우
                return !(endDate.isBefore(existingStart) || startDate.isAfter(existingEnd));
            })
            .collect(Collectors.toList());
    }

    private String getHolidayName(LocalDate date) {
        // 실제 구현에서는 공휴일 데이터베이스나 설정에서 조회
        return "공휴일";
    }

    private boolean isNationalHoliday(LocalDate date) {
        // 실제 구현에서는 국경일 여부 확인 로직
        return true;
    }

    // TODO: 실제 구현에서는 Repository 메서드로 대체
    private ServiceCenterOperatingHours.OperatingHoursData loadOperatingHoursData(Long serviceCenterId) {
        return ServiceCenterOperatingHours.OperatingHoursData.builder().build(); // 임시 구현
    }

    private void saveOperatingHoursData(Long serviceCenterId, ServiceCenterOperatingHours.OperatingHoursData data) {
        // 임시 구현
    }

    // === 요청/응답 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class TemporaryClosureRequest {
        private LocalDate startDate;
        private LocalDate endDate;
        private String reason;
        private String note;
        private boolean allowOverlap = false;
    }

    @lombok.Data
    @lombok.Builder
    public static class SpecialHoursRequest {
        private LocalDate date;
        private boolean isOpen;
        private List<ServiceCenterOperatingHours.TimeSlot> timeSlots;
        private String reason;
        private String note;
        private boolean replaceExisting = false;
    }

    @lombok.Data
    @lombok.Builder
    public static class HolidayManagementResult {
        private boolean success;
        private Long serviceCenterId;
        private int year;
        private List<HolidayInfo> addedHolidays;
        private int addedCount;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class TemporaryClosureResult {
        private boolean success;
        private Long serviceCenterId;
        private ServiceCenterOperatingHours.TemporaryClosurePeriod addedClosure;
        private List<ServiceCenterOperatingHours.TemporaryClosurePeriod> overlappingPeriods;
        private int affectedDays;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class SpecialHoursResult {
        private boolean success;
        private Long serviceCenterId;
        private LocalDate date;
        private ServiceCenterOperatingHours.SpecialOperatingHours specialHours;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class SpecialHoursListResult {
        private boolean success;
        private Long serviceCenterId;
        private LocalDate fromDate;
        private LocalDate toDate;
        private List<SpecialHoursInfo> specialHours;
        private List<HolidayInfo> holidays;
        private List<ServiceCenterOperatingHours.TemporaryClosurePeriod> temporaryClosures;
        private int totalSpecialDays;
        private int totalHolidays;
        private int totalClosurePeriods;
        private String message;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class ValidationResult {
        private boolean isValid;
        private String errorMessage;
    }

    @lombok.Data
    @lombok.Builder
    public static class HolidayInfo {
        private LocalDate date;
        private String name;
        private boolean isNationalHoliday;
        private String description;
    }

    @lombok.Data
    @lombok.Builder
    public static class SpecialHoursInfo {
        private LocalDate date;
        private boolean isOpen;
        private List<ServiceCenterOperatingHours.TimeSlot> timeSlots;
        private String reason;
        private String note;
    }
} 