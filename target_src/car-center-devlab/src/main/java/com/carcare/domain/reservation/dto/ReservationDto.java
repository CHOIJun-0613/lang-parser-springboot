package com.carcare.domain.reservation.dto;

import com.carcare.domain.reservation.entity.Reservation;
import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 예약 관련 DTO 클래스
 */
public class ReservationDto {

    /**
     * 예약 생성 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 생성 요청")
    public static class CreateRequest {
        
        @NotNull(message = "차량 ID는 필수입니다")
        @Schema(description = "차량 ID", example = "1")
        private Long vehicleId;
        
        @NotNull(message = "정비소 ID는 필수입니다")
        @Schema(description = "정비소 ID", example = "1")
        private Long serviceCenterId;
        
        @NotNull(message = "서비스 유형 ID는 필수입니다")
        @Schema(description = "서비스 유형 ID", example = "1")
        private Long serviceTypeId;
        
        @NotNull(message = "예약 일시는 필수입니다")
        @Future(message = "예약 일시는 현재 시간보다 이후여야 합니다")
        @Schema(description = "예약 일시", example = "2024-12-25T14:30:00")
        private LocalDateTime scheduledDate;
        
        @Min(value = 30, message = "예상 소요시간은 최소 30분입니다")
        @Max(value = 480, message = "예상 소요시간은 최대 8시간입니다")
        @Schema(description = "예상 소요시간(분)", example = "120")
        private Integer estimatedDuration;
        
        @Size(max = 1000, message = "고객 요청사항은 1000자를 초과할 수 없습니다")
        @Schema(description = "고객 요청사항", example = "엔진 소음이 있어서 점검 부탁드립니다.")
        private String customerNotes;
    }

    /**
     * 예약 수정 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 수정 요청")
    public static class UpdateRequest {
        
        @Future(message = "예약 일시는 현재 시간보다 이후여야 합니다")
        @Schema(description = "예약 일시", example = "2024-12-25T15:30:00")
        private LocalDateTime scheduledDate;
        
        @Min(value = 30, message = "예상 소요시간은 최소 30분입니다")
        @Max(value = 480, message = "예상 소요시간은 최대 8시간입니다")
        @Schema(description = "예상 소요시간(분)", example = "150")
        private Integer estimatedDuration;
        
        @Size(max = 1000, message = "고객 요청사항은 1000자를 초과할 수 없습니다")
        @Schema(description = "고객 요청사항", example = "수정된 요청사항입니다.")
        private String customerNotes;
    }

    /**
     * 예약 상태 변경 요청 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 상태 변경 요청")
    public static class StatusUpdateRequest {
        
        @NotNull(message = "상태는 필수입니다")
        @Schema(description = "예약 상태", example = "CONFIRMED")
        private Reservation.ReservationStatus status;
        
        @Size(max = 500, message = "정비사 메모는 500자를 초과할 수 없습니다")
        @Schema(description = "정비사 메모", example = "차량 점검 완료, 추가 정비 필요 없음")
        private String mechanicNotes;
        
        @Schema(description = "취소 사유", example = "고객 요청에 의한 취소")
        private String cancellationReason;
    }

    /**
     * 예약 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 응답")
    public static class Response {
        
        @Schema(description = "예약 ID", example = "1")
        private Long id;
        
        @Schema(description = "예약 UUID")
        private UUID reservationUuid;
        
        @Schema(description = "고객 ID", example = "1")
        private Long userId;
        
        @Schema(description = "고객 이름", example = "김철수")
        private String userName;
        
        @Schema(description = "차량 ID", example = "1")
        private Long vehicleId;
        
        @Schema(description = "차량 정보", example = "현대 소나타 (12가1234)")
        private String vehicleInfo;
        
        @Schema(description = "정비소 ID", example = "1")
        private Long serviceCenterId;
        
        @Schema(description = "정비소 이름", example = "ABC 정비소")
        private String serviceCenterName;
        
        @Schema(description = "서비스 유형 ID", example = "1")
        private Long serviceTypeId;
        
        @Schema(description = "서비스 유형 이름", example = "정기점검")
        private String serviceTypeName;
        
        @Schema(description = "예약 상태")
        private Reservation.ReservationStatus status;
        
        @Schema(description = "예약 상태 설명", example = "확정")
        private String statusDescription;
        
        @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss")
        @Schema(description = "예약 일시", example = "2024-12-25T14:30:00")
        private LocalDateTime scheduledDate;
        
        @Schema(description = "예상 소요시간(분)", example = "120")
        private Integer estimatedDuration;
        
        @Schema(description = "고객 요청사항")
        private String customerNotes;
        
        @Schema(description = "정비사 메모")
        private String mechanicNotes;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "확정 시간")
        private LocalDateTime confirmedAt;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "시작 시간")
        private LocalDateTime startedAt;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "완료 시간")
        private LocalDateTime completedAt;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "취소 시간")
        private LocalDateTime cancelledAt;
        
        @Schema(description = "취소 사유")
        private String cancellationReason;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "생성 시간")
        private LocalDateTime createdAt;
        
        @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
        @Schema(description = "수정 시간")
        private LocalDateTime updatedAt;
    }

    /**
     * 예약 목록 응답 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 목록 응답")
    public static class ListResponse {
        
        @Schema(description = "예약 목록")
        private List<Response> reservations;
        
        @Schema(description = "전체 개수", example = "25")
        private Long totalCount;
        
        @Schema(description = "현재 페이지", example = "0")
        private Integer currentPage;
        
        @Schema(description = "페이지 크기", example = "10")
        private Integer pageSize;
        
        @Schema(description = "전체 페이지 수", example = "3")
        private Integer totalPages;
    }

    /**
     * 예약 검색 조건 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 검색 조건")
    public static class SearchCriteria {
        
        @Schema(description = "고객 ID", example = "1")
        private Long userId;
        
        @Schema(description = "정비소 ID", example = "1")
        private Long serviceCenterId;
        
        @Schema(description = "차량 ID", example = "1")
        private Long vehicleId;
        
        @Schema(description = "예약 상태")
        private Reservation.ReservationStatus status;
        
        @JsonFormat(pattern = "yyyy-MM-dd")
        @Schema(description = "검색 시작 날짜", example = "2024-12-01")
        private LocalDateTime startDate;
        
        @JsonFormat(pattern = "yyyy-MM-dd")
        @Schema(description = "검색 종료 날짜", example = "2024-12-31")
        private LocalDateTime endDate;
        
        @Schema(description = "정렬 기준", example = "scheduledDate", 
                allowableValues = {"scheduledDate", "createdAt", "status"})
        private String sortBy = "scheduledDate";
        
        @Schema(description = "정렬 방향", example = "ASC", 
                allowableValues = {"ASC", "DESC"})
        private String sortDirection = "ASC";
        
        @Min(0)
        @Schema(description = "페이지 번호", example = "0")
        private Integer page = 0;
        
        @Min(1)
        @Max(100)
        @Schema(description = "페이지 크기", example = "10")
        private Integer size = 10;
        
        // 계산된 필드들
        public Integer getOffset() {
            return page * size;
        }
    }

    /**
     * 예약 통계 DTO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "예약 통계")
    public static class Statistics {
        
        @Schema(description = "전체 예약 수", example = "150")
        private Long totalReservations;
        
        @Schema(description = "대기 중인 예약 수", example = "5")
        private Long pendingReservations;
        
        @Schema(description = "확정된 예약 수", example = "10")
        private Long confirmedReservations;
        
        @Schema(description = "진행 중인 예약 수", example = "3")
        private Long inProgressReservations;
        
        @Schema(description = "완료된 예약 수", example = "120")
        private Long completedReservations;
        
        @Schema(description = "취소된 예약 수", example = "12")
        private Long cancelledReservations;
        
        @Schema(description = "금일 예약 수", example = "8")
        private Long todayReservations;
        
        @Schema(description = "이번 주 예약 수", example = "25")
        private Long thisWeekReservations;
        
        @Schema(description = "이번 달 예약 수", example = "85")
        private Long thisMonthReservations;
    }
} 