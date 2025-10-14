package com.carcare.domain.service.entity;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.*;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 정비소 운영시간 엔티티
 * JSON 기반으로 유연한 운영시간 관리
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceCenterOperatingHours {
    
    private Long id;
    
    @NotNull(message = "정비소 ID는 필수입니다")
    private Long serviceCenterId;
    
    // JSON으로 저장되는 운영시간 데이터
    @NotNull(message = "운영시간 정보는 필수입니다")
    private String operatingHoursJson;
    
    // 현재 운영 상태 (캐시된 값)
    private OperatingStatus currentStatus;
    
    // 다음 상태 변경 시간 (캐시된 값)
    private LocalDateTime nextStatusChangeAt;
    
    // 운영 상태 마지막 업데이트 시간
    private LocalDateTime statusUpdatedAt;
    
    // 기본 시간대 설정
    @Builder.Default
    private String timezone = "Asia/Seoul";
    
    // 자동 상태 업데이트 활성화 여부
    @Builder.Default
    private Boolean autoStatusUpdate = true;
    
    // 메타데이터
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
    
    /**
     * 운영 상태 열거형
     */
    public enum OperatingStatus {
        @JsonProperty("OPEN")
        OPEN("영업 중"),
        
        @JsonProperty("CLOSED")
        CLOSED("영업 종료"),
        
        @JsonProperty("BREAK_TIME")
        BREAK_TIME("휴게시간"),
        
        @JsonProperty("HOLIDAY")
        HOLIDAY("휴무일"),
        
        @JsonProperty("TEMPORARILY_CLOSED")
        TEMPORARILY_CLOSED("임시 휴업"),
        
        @JsonProperty("UNKNOWN")
        UNKNOWN("상태 불명");
        
        private final String description;
        
        OperatingStatus(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
        
        public boolean isOpen() {
            return this == OPEN;
        }
        
        public boolean isClosed() {
            return this == CLOSED || this == HOLIDAY || this == TEMPORARILY_CLOSED;
        }
    }
    
    /**
     * 운영시간 데이터 구조 (JSON으로 저장)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OperatingHoursData {
        
        // 기본 운영시간 (요일별)
        @Builder.Default
        private Map<String, DayOperatingHours> weeklySchedule = new HashMap<>();
        
        // 특별 운영시간 (특정 날짜)
        @Builder.Default
        private Map<String, SpecialOperatingHours> specialDates = new HashMap<>();
        
        // 휴무일 설정
        @Builder.Default
        private List<String> holidays = new ArrayList<>();
        
        // 정기 휴무 설정 (매주 특정 요일)
        @Builder.Default
        private List<String> regularClosedDays = new ArrayList<>();
        
        // 임시 휴무 기간
        @Builder.Default
        private List<TemporaryClosurePeriod> temporaryClosures = new ArrayList<>();
        
        // 기본 설정
        @Builder.Default
        private DefaultSettings defaultSettings = new DefaultSettings();
    }
    
    /**
     * 요일별 운영시간
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DayOperatingHours {
        
        // 영업 여부
        @Builder.Default
        private boolean isOpen = true;
        
        // 운영 시간대 (여러 구간 가능)
        @Builder.Default
        private List<TimeSlot> timeSlots = new ArrayList<>();
        
        // 휴게 시간대
        @Builder.Default
        private List<TimeSlot> breakTimes = new ArrayList<>();
        
        // 특별 메모
        private String note;
    }
    
    /**
     * 시간대 정보
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TimeSlot {
        
        @NotNull(message = "시작 시간은 필수입니다")
        private String startTime; // "09:00" 형식
        
        @NotNull(message = "종료 시간은 필수입니다")
        private String endTime;   // "18:00" 형식
        
        // 시간대 타입 (운영, 휴게 등)
        @Builder.Default
        private TimeSlotType type = TimeSlotType.OPERATING;
        
        private String description;
    }
    
    /**
     * 시간대 타입
     */
    public enum TimeSlotType {
        @JsonProperty("OPERATING")
        OPERATING("운영시간"),
        
        @JsonProperty("BREAK")
        BREAK("휴게시간"),
        
        @JsonProperty("APPOINTMENT_ONLY")
        APPOINTMENT_ONLY("예약제"),
        
        @JsonProperty("LIMITED_SERVICE")
        LIMITED_SERVICE("제한 서비스");
        
        private final String description;
        
        TimeSlotType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    /**
     * 특별 운영시간
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SpecialOperatingHours {
        
        @NotNull(message = "날짜는 필수입니다")
        private String date; // "2024-01-01" 형식
        
        @Builder.Default
        private boolean isOpen = false;
        
        @Builder.Default
        private List<TimeSlot> timeSlots = new ArrayList<>();
        
        private String reason; // 공휴일, 특별 운영 등
        private String note;
    }
    
    /**
     * 임시 휴무 기간
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TemporaryClosurePeriod {
        
        @NotNull(message = "시작 날짜는 필수입니다")
        private String startDate; // "2024-01-01" 형식
        
        @NotNull(message = "종료 날짜는 필수입니다")
        private String endDate;   // "2024-01-07" 형식
        
        @NotNull(message = "휴무 사유는 필수입니다")
        private String reason;
        
        private String note;
    }
    
    /**
     * 기본 설정
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DefaultSettings {
        
        // 기본 시간대
        @Builder.Default
        private String timezone = "Asia/Seoul";
        
        // 기본 운영시간 (새로운 요일 추가시 사용)
        @Builder.Default
        private String defaultOpenTime = "09:00";
        
        @Builder.Default
        private String defaultCloseTime = "18:00";
        
        // 예약 가능 시간 (분 단위)
        @Builder.Default
        private int reservationSlotMinutes = 30;
        
        // 마지막 예약 가능 시간 (영업 종료 전 몇 분)
        @Builder.Default
        private int lastReservationMinutesBefore = 60;
        
        // 24시간 영업 여부
        @Builder.Default
        private boolean is24Hours = false;
        
        // 무휴 영업 여부
        @Builder.Default
        private boolean isAlwaysOpen = false;
    }
    
    // === JSON 처리 메서드들 ===
    
    /**
     * JSON 문자열을 OperatingHoursData 객체로 변환
     */
    @JsonIgnore
    public OperatingHoursData getOperatingHoursData() {
        if (operatingHoursJson == null || operatingHoursJson.trim().isEmpty()) {
            return OperatingHoursData.builder().build();
        }
        
        try {
            ObjectMapper mapper = new ObjectMapper();
            mapper.registerModule(new JavaTimeModule());
            return mapper.readValue(operatingHoursJson, OperatingHoursData.class);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("운영시간 JSON 파싱 오류: " + e.getMessage(), e);
        }
    }
    
    /**
     * OperatingHoursData 객체를 JSON 문자열로 변환하여 저장
     */
    @JsonIgnore
    public void setOperatingHoursData(OperatingHoursData data) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            mapper.registerModule(new JavaTimeModule());
            this.operatingHoursJson = mapper.writeValueAsString(data);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("운영시간 JSON 직렬화 오류: " + e.getMessage(), e);
        }
    }
    
    // === 비즈니스 로직 메서드들 ===
    
    /**
     * 현재 시간 기준 운영 상태 확인
     */
    @JsonIgnore
    public OperatingStatus getCurrentOperatingStatus() {
        return getCurrentOperatingStatus(LocalDateTime.now(ZoneId.of(timezone)));
    }
    
    /**
     * 특정 시간 기준 운영 상태 확인
     */
    @JsonIgnore
    public OperatingStatus getCurrentOperatingStatus(LocalDateTime dateTime) {
        try {
            OperatingHoursData data = getOperatingHoursData();
            
            // 기본 설정 확인
            if (data.getDefaultSettings().isAlwaysOpen()) {
                return OperatingStatus.OPEN;
            }
            
            String dateStr = dateTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String dayOfWeek = dateTime.getDayOfWeek().toString();
            LocalTime currentTime = dateTime.toLocalTime();
            
            // 1. 임시 휴무 확인
            if (isTemporarilyClosed(dateStr, data.getTemporaryClosures())) {
                return OperatingStatus.TEMPORARILY_CLOSED;
            }
            
            // 2. 특별 운영시간 확인 (공휴일 등)
            if (data.getSpecialDates().containsKey(dateStr)) {
                return getStatusFromSpecialHours(data.getSpecialDates().get(dateStr), currentTime);
            }
            
            // 3. 휴무일 확인
            if (data.getHolidays().contains(dateStr) || data.getRegularClosedDays().contains(dayOfWeek)) {
                return OperatingStatus.HOLIDAY;
            }
            
            // 4. 일반 운영시간 확인
            if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
                return getStatusFromDayHours(data.getWeeklySchedule().get(dayOfWeek), currentTime);
            }
            
            return OperatingStatus.CLOSED;
            
        } catch (Exception e) {
            return OperatingStatus.UNKNOWN;
        }
    }
    
    /**
     * 다음 상태 변경 시간 계산
     */
    @JsonIgnore
    public LocalDateTime getNextStatusChangeTime() {
        return getNextStatusChangeTime(LocalDateTime.now(ZoneId.of(timezone)));
    }
    
    /**
     * 특정 시간 기준 다음 상태 변경 시간 계산
     */
    @JsonIgnore
    public LocalDateTime getNextStatusChangeTime(LocalDateTime fromDateTime) {
        try {
            OperatingHoursData data = getOperatingHoursData();
            
            if (data.getDefaultSettings().isAlwaysOpen()) {
                return null; // 24시간 운영이면 상태 변경 없음
            }
            
            // 향후 7일간 확인
            for (int i = 0; i < 7; i++) {
                LocalDateTime checkDate = fromDateTime.plusDays(i);
                LocalDateTime nextChange = findNextChangeInDay(checkDate, data);
                if (nextChange != null) {
                    return nextChange;
                }
            }
            
            return null; // 7일 내 상태 변경 없음
            
        } catch (Exception e) {
            return null;
        }
    }
    
    /**
     * 영업일 여부 확인
     */
    @JsonIgnore
    public boolean isBusinessDay(LocalDate date) {
        try {
            OperatingHoursData data = getOperatingHoursData();
            String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String dayOfWeek = date.getDayOfWeek().toString();
            
            // 임시 휴무 확인
            if (isTemporarilyClosed(dateStr, data.getTemporaryClosures())) {
                return false;
            }
            
            // 휴무일 확인
            if (data.getHolidays().contains(dateStr) || data.getRegularClosedDays().contains(dayOfWeek)) {
                return false;
            }
            
            // 특별 운영시간 확인
            if (data.getSpecialDates().containsKey(dateStr)) {
                return data.getSpecialDates().get(dateStr).isOpen();
            }
            
            // 일반 운영시간 확인
            if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
                return data.getWeeklySchedule().get(dayOfWeek).isOpen();
            }
            
            return false;
            
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * 예약 가능한 시간대 목록 조회
     */
    @JsonIgnore
    public List<LocalDateTime> getAvailableReservationSlots(LocalDate date) {
        List<LocalDateTime> slots = new ArrayList<>();
        
        try {
            if (!isBusinessDay(date)) {
                return slots;
            }
            
            OperatingHoursData data = getOperatingHoursData();
            String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            String dayOfWeek = date.getDayOfWeek().toString();
            
            List<TimeSlot> operatingSlots = new ArrayList<>();
            
            // 특별 운영시간 또는 일반 운영시간 확인
            if (data.getSpecialDates().containsKey(dateStr)) {
                operatingSlots = data.getSpecialDates().get(dateStr).getTimeSlots();
            } else if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
                operatingSlots = data.getWeeklySchedule().get(dayOfWeek).getTimeSlots();
            }
            
            // 각 운영 시간대에서 예약 슬롯 생성
            int slotMinutes = data.getDefaultSettings().getReservationSlotMinutes();
            int lastReservationBefore = data.getDefaultSettings().getLastReservationMinutesBefore();
            
            for (TimeSlot slot : operatingSlots) {
                if (slot.getType() == TimeSlotType.OPERATING || slot.getType() == TimeSlotType.APPOINTMENT_ONLY) {
                    slots.addAll(generateSlotsInRange(date, slot.getStartTime(), slot.getEndTime(), 
                                                    slotMinutes, lastReservationBefore));
                }
            }
            
            // 휴게시간 제외
            List<TimeSlot> breakTimes = getBreakTimesForDate(date, data);
            slots.removeIf(slotTime -> isInBreakTime(slotTime, breakTimes));
            
        } catch (Exception e) {
            // 오류 발생시 빈 목록 반환
        }
        
        return slots;
    }
    
    // === 내부 헬퍼 메서드들 ===
    
    private boolean isTemporarilyClosed(String dateStr, List<TemporaryClosurePeriod> closures) {
        LocalDate date = LocalDate.parse(dateStr);
        return closures.stream()
            .anyMatch(closure -> {
                LocalDate start = LocalDate.parse(closure.getStartDate());
                LocalDate end = LocalDate.parse(closure.getEndDate());
                return !date.isBefore(start) && !date.isAfter(end);
            });
    }
    
    private OperatingStatus getStatusFromSpecialHours(SpecialOperatingHours specialHours, LocalTime currentTime) {
        if (!specialHours.isOpen()) {
            return OperatingStatus.HOLIDAY;
        }
        
        return getStatusFromTimeSlots(specialHours.getTimeSlots(), currentTime);
    }
    
    private OperatingStatus getStatusFromDayHours(DayOperatingHours dayHours, LocalTime currentTime) {
        if (!dayHours.isOpen()) {
            return OperatingStatus.CLOSED;
        }
        
        // 휴게시간 확인
        if (isInTimeSlots(dayHours.getBreakTimes(), currentTime)) {
            return OperatingStatus.BREAK_TIME;
        }
        
        return getStatusFromTimeSlots(dayHours.getTimeSlots(), currentTime);
    }
    
    private OperatingStatus getStatusFromTimeSlots(List<TimeSlot> timeSlots, LocalTime currentTime) {
        boolean isInOperatingTime = isInTimeSlots(timeSlots.stream()
            .filter(slot -> slot.getType() == TimeSlotType.OPERATING || slot.getType() == TimeSlotType.APPOINTMENT_ONLY)
            .toList(), currentTime);
        
        return isInOperatingTime ? OperatingStatus.OPEN : OperatingStatus.CLOSED;
    }
    
    private boolean isInTimeSlots(List<TimeSlot> timeSlots, LocalTime currentTime) {
        return timeSlots.stream()
            .anyMatch(slot -> {
                LocalTime start = LocalTime.parse(slot.getStartTime());
                LocalTime end = LocalTime.parse(slot.getEndTime());
                return !currentTime.isBefore(start) && currentTime.isBefore(end);
            });
    }
    
    private LocalDateTime findNextChangeInDay(LocalDateTime checkDate, OperatingHoursData data) {
        // 복잡한 로직이므로 기본 구현만 제공
        // 실제 구현에서는 모든 시간 변경점을 계산해야 함
        return null;
    }
    
    private List<TimeSlot> getBreakTimesForDate(LocalDate date, OperatingHoursData data) {
        String dateStr = date.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        String dayOfWeek = date.getDayOfWeek().toString();
        
        if (data.getSpecialDates().containsKey(dateStr)) {
            return Collections.emptyList(); // 특별 운영일에는 휴게시간 없음
        }
        
        if (data.getWeeklySchedule().containsKey(dayOfWeek)) {
            return data.getWeeklySchedule().get(dayOfWeek).getBreakTimes();
        }
        
        return Collections.emptyList();
    }
    
    private boolean isInBreakTime(LocalDateTime slotTime, List<TimeSlot> breakTimes) {
        LocalTime time = slotTime.toLocalTime();
        return isInTimeSlots(breakTimes, time);
    }
    
    private List<LocalDateTime> generateSlotsInRange(LocalDate date, String startTime, String endTime, 
                                                   int slotMinutes, int lastReservationBefore) {
        List<LocalDateTime> slots = new ArrayList<>();
        
        LocalTime start = LocalTime.parse(startTime);
        LocalTime end = LocalTime.parse(endTime).minusMinutes(lastReservationBefore);
        
        LocalDateTime current = date.atTime(start);
        LocalDateTime endDateTime = date.atTime(end);
        
        while (!current.isAfter(endDateTime)) {
            slots.add(current);
            current = current.plusMinutes(slotMinutes);
        }
        
        return slots;
    }
    
    /**
     * 운영시간 요약 정보 조회
     */
    @JsonIgnore
    public String getOperatingHoursSummary() {
        try {
            OperatingHoursData data = getOperatingHoursData();
            
            if (data.getDefaultSettings().isAlwaysOpen()) {
                return "24시간 운영";
            }
            
            StringBuilder summary = new StringBuilder();
            
            // 주간 운영시간 요약
            Map<String, DayOperatingHours> weeklySchedule = data.getWeeklySchedule();
            if (!weeklySchedule.isEmpty()) {
                summary.append("평일: ");
                weeklySchedule.entrySet().stream()
                    .filter(entry -> !entry.getValue().getTimeSlots().isEmpty())
                    .findFirst()
                    .ifPresent(entry -> {
                        TimeSlot firstSlot = entry.getValue().getTimeSlots().get(0);
                        summary.append(firstSlot.getStartTime())
                               .append(" - ")
                               .append(firstSlot.getEndTime());
                    });
            }
            
            // 휴무일 정보
            if (!data.getRegularClosedDays().isEmpty()) {
                summary.append(" (").append(String.join(", ", data.getRegularClosedDays())).append(" 휴무)");
            }
            
            return summary.toString();
            
        } catch (Exception e) {
            return "운영시간 정보 없음";
        }
    }
} 