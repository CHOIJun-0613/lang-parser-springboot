package com.carcare.domain.service.service;

import com.carcare.domain.service.entity.ServiceCenterOperatingHours;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 운영 상태 계산 전문 서비스
 * 복잡한 시간 계산, 상태 전환 로직, 다음 변경 시점 예측 등을 담당
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OperatingStatusCalculationService {

    private static final int FUTURE_DAYS_TO_CHECK = 30; // 미래 30일까지 확인

    /**
     * 정확한 운영 상태 계산
     */
    public OperatingStatusResult calculateOperatingStatus(ServiceCenterOperatingHours.OperatingHoursData data, 
                                                         LocalDateTime targetDateTime, String timezone) {
        log.debug("운영 상태 계산: 시간={}, 시간대={}", targetDateTime, timezone);

        try {
            ZoneId zoneId = ZoneId.of(timezone);
            LocalDateTime localDateTime = targetDateTime.atZone(ZoneId.systemDefault()).withZoneSameInstant(zoneId).toLocalDateTime();

            // 기본 설정 확인
            if (data.getDefaultSettings().isAlwaysOpen()) {
                return OperatingStatusResult.builder()
                    .status(ServiceCenterOperatingHours.OperatingStatus.OPEN)
                    .isDefinitive(true)
                    .reason("24시간 운영")
                    .nextChangeTime(null)
                    .build();
            }

            String dateStr = localDateTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String dayOfWeek = localDateTime.getDayOfWeek().toString();
            LocalTime currentTime = localDateTime.toLocalTime();

            // 1. 임시 휴무 확인
            Optional<ServiceCenterOperatingHours.TemporaryClosurePeriod> activeClosure = 
                findActiveTemporaryClosure(dateStr, data.getTemporaryClosures());
            if (activeClosure.isPresent()) {
                LocalDateTime nextOpen = findNextOpenTimeAfterClosure(activeClosure.get(), data, zoneId);
                return OperatingStatusResult.builder()
                    .status(ServiceCenterOperatingHours.OperatingStatus.TEMPORARILY_CLOSED)
                    .isDefinitive(true)
                    .reason("임시 휴업: " + activeClosure.get().getReason())
                    .nextChangeTime(nextOpen)
                    .build();
            }

            // 2. 특별 운영시간 확인 (공휴일 등)
            if (data.getSpecialDates().containsKey(dateStr)) {
                return calculateSpecialDateStatus(data.getSpecialDates().get(dateStr), currentTime, localDateTime, data, zoneId);
            }

            // 3. 정기 휴무일 확인
            if (data.getHolidays().contains(dateStr) || data.getRegularClosedDays().contains(dayOfWeek)) {
                LocalDateTime nextOpen = findNextRegularOpenTime(localDateTime, data, zoneId);
                return OperatingStatusResult.builder()
                    .status(ServiceCenterOperatingHours.OperatingStatus.HOLIDAY)
                    .isDefinitive(true)
                    .reason("정기 휴무일")
                    .nextChangeTime(nextOpen)
                    .build();
            }

            // 4. 일반 운영시간 확인
            if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
                return calculateRegularDayStatus(data.getWeeklySchedule().get(dayOfWeek), currentTime, localDateTime, data, zoneId);
            }

            // 5. 운영시간 정보 없음
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.CLOSED)
                .isDefinitive(false)
                .reason("운영시간 정보 없음")
                .nextChangeTime(null)
                .build();

        } catch (Exception e) {
            log.error("운영 상태 계산 중 오류 발생: {}", e.getMessage(), e);
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.UNKNOWN)
                .isDefinitive(false)
                .reason("계산 오류: " + e.getMessage())
                .nextChangeTime(null)
                .build();
        }
    }

    /**
     * 다음 상태 변경 시간 정확히 계산
     */
    public LocalDateTime findNextStatusChangeTime(ServiceCenterOperatingHours.OperatingHoursData data,
                                                  LocalDateTime fromDateTime, String timezone) {
        log.debug("다음 상태 변경 시간 계산: 시작시간={}", fromDateTime);

        try {
            ZoneId zoneId = ZoneId.of(timezone);
            LocalDateTime searchStart = fromDateTime.atZone(ZoneId.systemDefault()).withZoneSameInstant(zoneId).toLocalDateTime();

            if (data.getDefaultSettings().isAlwaysOpen()) {
                return null; // 24시간 운영이면 상태 변경 없음
            }

            // 현재 날짜부터 미래 30일간 확인
            for (int i = 0; i < FUTURE_DAYS_TO_CHECK; i++) {
                LocalDateTime checkDateTime = searchStart.plusDays(i);
                List<StatusChangePoint> changesInDay = findStatusChangesInDay(checkDateTime.toLocalDate(), data, zoneId);

                for (StatusChangePoint changePoint : changesInDay) {
                    if (changePoint.getChangeTime().isAfter(searchStart)) {
                        return changePoint.getChangeTime();
                    }
                }
            }

            return null; // 30일 내 변경점 없음

        } catch (Exception e) {
            log.error("다음 상태 변경 시간 계산 중 오류 발생: {}", e.getMessage(), e);
            return null;
        }
    }

    /**
     * 영업일 판단
     */
    public boolean isBusinessDay(LocalDate date, ServiceCenterOperatingHours.OperatingHoursData data) {
        String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        String dayOfWeek = date.getDayOfWeek().toString();

        // 기본 설정 확인
        if (data.getDefaultSettings().isAlwaysOpen()) {
            return true;
        }

        // 임시 휴무 확인
        if (findActiveTemporaryClosure(dateStr, data.getTemporaryClosures()).isPresent()) {
            return false;
        }

        // 정기 휴무 확인
        if (data.getHolidays().contains(dateStr) || data.getRegularClosedDays().contains(dayOfWeek)) {
            return false;
        }

        // 특별 운영시간 확인
        if (data.getSpecialDates().containsKey(dateStr)) {
            return data.getSpecialDates().get(dateStr).isOpen();
        }

        // 일반 운영시간 확인
        if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
            ServiceCenterOperatingHours.DayOperatingHours dayHours = data.getWeeklySchedule().get(dayOfWeek);
            return dayHours.isOpen() && !dayHours.getTimeSlots().isEmpty();
        }

        return false;
    }

    /**
     * 예약 가능한 시간 슬롯 생성
     */
    public List<ReservationSlot> generateReservationSlots(LocalDate date, 
                                                         ServiceCenterOperatingHours.OperatingHoursData data,
                                                         String timezone) {
        List<ReservationSlot> slots = new ArrayList<>();

        try {
            if (!isBusinessDay(date, data)) {
                return slots;
            }

            ZoneId zoneId = ZoneId.of(timezone);
            String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String dayOfWeek = date.getDayOfWeek().toString();

            List<ServiceCenterOperatingHours.TimeSlot> operatingSlots = new ArrayList<>();
            final List<ServiceCenterOperatingHours.TimeSlot> breakSlots = new ArrayList<>();

            // 운영 시간대 및 휴게 시간대 수집
            if (data.getSpecialDates().containsKey(dateStr)) {
                operatingSlots = data.getSpecialDates().get(dateStr).getTimeSlots();
                // 특별 운영일에는 일반적으로 휴게시간 없음
            } else if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
                ServiceCenterOperatingHours.DayOperatingHours dayHours = data.getWeeklySchedule().get(dayOfWeek);
                operatingSlots = dayHours.getTimeSlots();
                breakSlots.addAll(dayHours.getBreakTimes());
            }

            // 예약 슬롯 생성 설정
            int slotMinutes = data.getDefaultSettings().getReservationSlotMinutes();
            int lastReservationBefore = data.getDefaultSettings().getLastReservationMinutesBefore();

            // 각 운영 시간대에서 슬롯 생성
            for (ServiceCenterOperatingHours.TimeSlot operatingSlot : operatingSlots) {
                if (operatingSlot.getType() == ServiceCenterOperatingHours.TimeSlotType.OPERATING ||
                    operatingSlot.getType() == ServiceCenterOperatingHours.TimeSlotType.APPOINTMENT_ONLY) {
                    
                    List<ReservationSlot> slotsInRange = generateSlotsInTimeRange(
                        date, operatingSlot, slotMinutes, lastReservationBefore, zoneId
                    );
                    slots.addAll(slotsInRange);
                }
            }

            // 휴게시간 제거
            slots.removeIf(slot -> isInBreakTime(slot.getStartTime(), breakSlots));

            // 시간순 정렬
            slots.sort(Comparator.comparing(ReservationSlot::getStartTime));

            return slots;

        } catch (Exception e) {
            log.error("예약 슬롯 생성 중 오류 발생: 날짜={}, 오류={}", date, e.getMessage(), e);
            return Collections.emptyList();
        }
    }

    // === 내부 헬퍼 메서드들 ===

    private Optional<ServiceCenterOperatingHours.TemporaryClosurePeriod> findActiveTemporaryClosure(
            String dateStr, List<ServiceCenterOperatingHours.TemporaryClosurePeriod> closures) {
        LocalDate date = LocalDate.parse(dateStr);
        return closures.stream()
            .filter(closure -> {
                LocalDate start = LocalDate.parse(closure.getStartDate());
                LocalDate end = LocalDate.parse(closure.getEndDate());
                return !date.isBefore(start) && !date.isAfter(end);
            })
            .findFirst();
    }

    private OperatingStatusResult calculateSpecialDateStatus(ServiceCenterOperatingHours.SpecialOperatingHours specialHours,
                                                           LocalTime currentTime, LocalDateTime currentDateTime,
                                                           ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        if (!specialHours.isOpen()) {
            LocalDateTime nextOpen = findNextRegularOpenTime(currentDateTime, data, zoneId);
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.HOLIDAY)
                .isDefinitive(true)
                .reason("특별 휴무: " + specialHours.getReason())
                .nextChangeTime(nextOpen)
                .build();
        }

        return calculateTimeSlotStatus(specialHours.getTimeSlots(), currentTime, currentDateTime, data, zoneId);
    }

    private OperatingStatusResult calculateRegularDayStatus(ServiceCenterOperatingHours.DayOperatingHours dayHours,
                                                          LocalTime currentTime, LocalDateTime currentDateTime,
                                                          ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        if (!dayHours.isOpen()) {
            LocalDateTime nextOpen = findNextRegularOpenTime(currentDateTime, data, zoneId);
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.CLOSED)
                .isDefinitive(true)
                .reason("정기 휴무")
                .nextChangeTime(nextOpen)
                .build();
        }

        // 휴게시간 확인
        if (isInTimeSlots(dayHours.getBreakTimes(), currentTime)) {
            LocalDateTime nextOpen = findNextTimeAfterBreak(currentTime, currentDateTime, dayHours, data, zoneId);
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.BREAK_TIME)
                .isDefinitive(true)
                .reason("휴게시간")
                .nextChangeTime(nextOpen)
                .build();
        }

        return calculateTimeSlotStatus(dayHours.getTimeSlots(), currentTime, currentDateTime, data, zoneId);
    }

    private OperatingStatusResult calculateTimeSlotStatus(List<ServiceCenterOperatingHours.TimeSlot> timeSlots,
                                                        LocalTime currentTime, LocalDateTime currentDateTime,
                                                        ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        // 운영 시간대에 있는지 확인
        Optional<ServiceCenterOperatingHours.TimeSlot> currentSlot = timeSlots.stream()
            .filter(slot -> isTimeInSlot(currentTime, slot))
            .findFirst();

        if (currentSlot.isPresent()) {
            ServiceCenterOperatingHours.TimeSlot slot = currentSlot.get();
            LocalDateTime nextChange = findNextChangeAfterCurrentSlot(currentTime, currentDateTime, timeSlots, data, zoneId);
            
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.OPEN)
                .isDefinitive(true)
                .reason("운영시간 중")
                .nextChangeTime(nextChange)
                .build();
        } else {
            // 운영 시간대가 아님
            LocalDateTime nextOpen = findNextOpenTimeInDay(currentTime, currentDateTime, timeSlots, data, zoneId);
            if (nextOpen == null) {
                nextOpen = findNextRegularOpenTime(currentDateTime, data, zoneId);
            }
            
            return OperatingStatusResult.builder()
                .status(ServiceCenterOperatingHours.OperatingStatus.CLOSED)
                .isDefinitive(true)
                .reason("운영시간 외")
                .nextChangeTime(nextOpen)
                .build();
        }
    }

    private boolean isInTimeSlots(List<ServiceCenterOperatingHours.TimeSlot> timeSlots, LocalTime currentTime) {
        return timeSlots.stream().anyMatch(slot -> isTimeInSlot(currentTime, slot));
    }

    private boolean isTimeInSlot(LocalTime time, ServiceCenterOperatingHours.TimeSlot slot) {
        LocalTime start = LocalTime.parse(slot.getStartTime());
        LocalTime end = LocalTime.parse(slot.getEndTime());
        return !time.isBefore(start) && time.isBefore(end);
    }

    private List<StatusChangePoint> findStatusChangesInDay(LocalDate date, 
                                                          ServiceCenterOperatingHours.OperatingHoursData data,
                                                          ZoneId zoneId) {
        List<StatusChangePoint> changes = new ArrayList<>();
        
        String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        String dayOfWeek = date.getDayOfWeek().toString();

        // 해당 날짜의 시간대들 수집
        List<ServiceCenterOperatingHours.TimeSlot> allSlots = new ArrayList<>();
        
        if (data.getSpecialDates().containsKey(dateStr)) {
            allSlots.addAll(data.getSpecialDates().get(dateStr).getTimeSlots());
        } else if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
            ServiceCenterOperatingHours.DayOperatingHours dayHours = data.getWeeklySchedule().get(dayOfWeek);
            allSlots.addAll(dayHours.getTimeSlots());
            allSlots.addAll(dayHours.getBreakTimes());
        }

        // 각 시간대의 시작/종료 시점을 변경점으로 추가
        for (ServiceCenterOperatingHours.TimeSlot slot : allSlots) {
            LocalDateTime startDateTime = date.atTime(LocalTime.parse(slot.getStartTime()));
            LocalDateTime endDateTime = date.atTime(LocalTime.parse(slot.getEndTime()));
            
            changes.add(StatusChangePoint.builder()
                .changeTime(startDateTime)
                .fromStatus(ServiceCenterOperatingHours.OperatingStatus.CLOSED)
                .toStatus(getStatusFromSlotType(slot.getType()))
                .reason("시작: " + slot.getDescription())
                .build());
                
            changes.add(StatusChangePoint.builder()
                .changeTime(endDateTime)
                .fromStatus(getStatusFromSlotType(slot.getType()))
                .toStatus(ServiceCenterOperatingHours.OperatingStatus.CLOSED)
                .reason("종료: " + slot.getDescription())
                .build());
        }

        // 시간순 정렬
        changes.sort(Comparator.comparing(StatusChangePoint::getChangeTime));
        
        return changes;
    }

    private ServiceCenterOperatingHours.OperatingStatus getStatusFromSlotType(ServiceCenterOperatingHours.TimeSlotType type) {
        switch (type) {
            case OPERATING:
            case APPOINTMENT_ONLY:
            case LIMITED_SERVICE:
                return ServiceCenterOperatingHours.OperatingStatus.OPEN;
            case BREAK:
                return ServiceCenterOperatingHours.OperatingStatus.BREAK_TIME;
            default:
                return ServiceCenterOperatingHours.OperatingStatus.CLOSED;
        }
    }

    private LocalDateTime findNextOpenTimeAfterClosure(ServiceCenterOperatingHours.TemporaryClosurePeriod closure,
                                                      ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        LocalDate endDate = LocalDate.parse(closure.getEndDate());
        LocalDate nextDay = endDate.plusDays(1);
        
        // 휴무 종료 다음날부터 영업일 찾기
        for (int i = 0; i < 30; i++) {
            LocalDate checkDate = nextDay.plusDays(i);
            if (isBusinessDay(checkDate, data)) {
                // 해당 일의 첫 운영시간 찾기
                return findFirstOpenTimeInDay(checkDate, data, zoneId);
            }
        }
        
        return null;
    }

    private LocalDateTime findNextRegularOpenTime(LocalDateTime fromDateTime, 
                                                 ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        LocalDate startDate = fromDateTime.toLocalDate().plusDays(1); // 다음날부터 확인
        
        for (int i = 0; i < 30; i++) {
            LocalDate checkDate = startDate.plusDays(i);
            if (isBusinessDay(checkDate, data)) {
                return findFirstOpenTimeInDay(checkDate, data, zoneId);
            }
        }
        
        return null;
    }

    private LocalDateTime findFirstOpenTimeInDay(LocalDate date, 
                                               ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        String dayOfWeek = date.getDayOfWeek().toString();
        
        List<ServiceCenterOperatingHours.TimeSlot> timeSlots = new ArrayList<>();
        
        if (data.getSpecialDates().containsKey(dateStr)) {
            timeSlots = data.getSpecialDates().get(dateStr).getTimeSlots();
        } else if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
            timeSlots = data.getWeeklySchedule().get(dayOfWeek).getTimeSlots();
        }
        
        Optional<LocalTime> firstOpenTime = timeSlots.stream()
            .filter(slot -> slot.getType() == ServiceCenterOperatingHours.TimeSlotType.OPERATING ||
                           slot.getType() == ServiceCenterOperatingHours.TimeSlotType.APPOINTMENT_ONLY)
            .map(slot -> LocalTime.parse(slot.getStartTime()))
            .min(LocalTime::compareTo);
            
        return firstOpenTime.map(date::atTime).orElse(null);
    }

    private LocalDateTime findNextTimeAfterBreak(LocalTime currentTime, LocalDateTime currentDateTime,
                                                ServiceCenterOperatingHours.DayOperatingHours dayHours,
                                                ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        // 현재 휴게시간 종료 시간 찾기
        Optional<LocalTime> breakEndTime = dayHours.getBreakTimes().stream()
            .filter(slot -> isTimeInSlot(currentTime, slot))
            .map(slot -> LocalTime.parse(slot.getEndTime()))
            .findFirst();
            
        if (breakEndTime.isPresent()) {
            LocalDateTime endDateTime = currentDateTime.toLocalDate().atTime(breakEndTime.get());
            
            // 휴게시간 종료 후 운영시간이 있는지 확인
            if (dayHours.getTimeSlots().stream()
                .anyMatch(slot -> LocalTime.parse(slot.getStartTime()).equals(breakEndTime.get()) ||
                                LocalTime.parse(slot.getStartTime()).isAfter(breakEndTime.get()))) {
                return endDateTime;
            }
        }
        
        // 당일 운영시간 없으면 다음 영업일 찾기
        return findNextRegularOpenTime(currentDateTime, data, zoneId);
    }

    private LocalDateTime findNextChangeAfterCurrentSlot(LocalTime currentTime, LocalDateTime currentDateTime,
                                                        List<ServiceCenterOperatingHours.TimeSlot> timeSlots,
                                                        ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        // 현재 슬롯의 종료 시간
        Optional<LocalTime> currentSlotEnd = timeSlots.stream()
            .filter(slot -> isTimeInSlot(currentTime, slot))
            .map(slot -> LocalTime.parse(slot.getEndTime()))
            .findFirst();
            
        if (currentSlotEnd.isPresent()) {
            return currentDateTime.toLocalDate().atTime(currentSlotEnd.get());
        }
        
        return findNextRegularOpenTime(currentDateTime, data, zoneId);
    }

    private LocalDateTime findNextOpenTimeInDay(LocalTime currentTime, LocalDateTime currentDateTime,
                                              List<ServiceCenterOperatingHours.TimeSlot> timeSlots,
                                              ServiceCenterOperatingHours.OperatingHoursData data, ZoneId zoneId) {
        // 당일 현재 시간 이후의 운영시간 찾기
        Optional<LocalTime> nextOpenTime = timeSlots.stream()
            .filter(slot -> slot.getType() == ServiceCenterOperatingHours.TimeSlotType.OPERATING ||
                           slot.getType() == ServiceCenterOperatingHours.TimeSlotType.APPOINTMENT_ONLY)
            .map(slot -> LocalTime.parse(slot.getStartTime()))
            .filter(time -> time.isAfter(currentTime))
            .min(LocalTime::compareTo);
            
        return nextOpenTime.map(time -> currentDateTime.toLocalDate().atTime(time)).orElse(null);
    }

    private List<ReservationSlot> generateSlotsInTimeRange(LocalDate date, 
                                                          ServiceCenterOperatingHours.TimeSlot timeSlot,
                                                          int slotMinutes, int lastReservationBefore, ZoneId zoneId) {
        List<ReservationSlot> slots = new ArrayList<>();
        
        LocalTime start = LocalTime.parse(timeSlot.getStartTime());
        LocalTime end = LocalTime.parse(timeSlot.getEndTime()).minus(lastReservationBefore, ChronoUnit.MINUTES);
        
        LocalDateTime current = date.atTime(start);
        LocalDateTime endDateTime = date.atTime(end);
        
        while (!current.isAfter(endDateTime)) {
            slots.add(ReservationSlot.builder()
                .startTime(current)
                .endTime(current.plusMinutes(slotMinutes))
                .duration(slotMinutes)
                .slotType(timeSlot.getType())
                .isAvailable(true)
                .build());
                
            current = current.plusMinutes(slotMinutes);
        }
        
        return slots;
    }

    private boolean isInBreakTime(LocalDateTime slotTime, List<ServiceCenterOperatingHours.TimeSlot> breakSlots) {
        LocalTime time = slotTime.toLocalTime();
        return isInTimeSlots(breakSlots, time);
    }

    // === 결과 클래스들 ===

    @lombok.Data
    @lombok.Builder
    public static class OperatingStatusResult {
        private ServiceCenterOperatingHours.OperatingStatus status;
        private boolean isDefinitive; // 확실한 상태인지 여부
        private String reason;
        private LocalDateTime nextChangeTime;
    }

    @lombok.Data
    @lombok.Builder
    public static class StatusChangePoint {
        private LocalDateTime changeTime;
        private ServiceCenterOperatingHours.OperatingStatus fromStatus;
        private ServiceCenterOperatingHours.OperatingStatus toStatus;
        private String reason;
    }

    @lombok.Data
    @lombok.Builder
    public static class ReservationSlot {
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private int duration; // 분 단위
        private ServiceCenterOperatingHours.TimeSlotType slotType;
        private boolean isAvailable;
        private String note;
    }
} 