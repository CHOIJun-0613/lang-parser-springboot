package com.carcare.domain.reservation.repository;

import com.carcare.domain.reservation.entity.Reservation;
import com.carcare.domain.reservation.dto.ReservationDto;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * 예약 데이터 접근 인터페이스
 */
@Mapper
public interface ReservationRepository {

    /**
     * 예약 등록
     */
    int insertReservation(Reservation reservation);

    /**
     * 예약 정보 수정
     */
    int updateReservation(Reservation reservation);

    /**
     * 예약 삭제 (소프트 삭제)
     */
    int deleteReservation(@Param("id") Long id, @Param("reason") String reason);

    /**
     * 예약 조회 (ID)
     */
    Optional<Reservation> findById(Long id);

    /**
     * 예약 상세 조회 (조인)
     */
    Optional<ReservationDto.Response> findDetailById(Long id);

    /**
     * UUID로 예약 조회
     */
    Optional<Reservation> findByUuid(String uuid);

    /**
     * 예약 검색
     */
    List<ReservationDto.Response> searchReservations(SearchCriteria criteria);

    /**
     * 예약 검색 결과 총 개수
     */
    long countSearchReservations(SearchCriteria criteria);

    /**
     * 사용자별 예약 목록
     */
    List<ReservationDto.Response> findByUserId(Long userId);

    /**
     * 정비소별 예약 목록
     */
    List<ReservationDto.Response> findByServiceCenterId(Long serviceCenterId);

    /**
     * 상태별 예약 목록
     */
    List<ReservationDto.Response> findByStatus(String status);

    /**
     * 오늘 예약 목록
     */
    List<ReservationDto.Response> findTodayReservations();

    /**
     * 예약 통계 조회
     */
    ReservationDto.Statistics getReservationStatistics(@Param("serviceCenterId") Long serviceCenterId);

    /**
     * 정비소별 예약 통계
     */
    ReservationDto.Statistics getServiceCenterStatistics(Long serviceCenterId);

    /**
     * 중복 예약 체크
     */
    boolean checkDuplicateReservation(@Param("serviceCenterId") Long serviceCenterId, 
                                    @Param("scheduledDate") LocalDateTime scheduledDate,
                                    @Param("excludeId") Long excludeId);

    /**
     * 예약 시간 충돌 체크
     */
    boolean checkTimeConflict(@Param("serviceCenterId") Long serviceCenterId,
                            @Param("startTime") LocalDateTime startTime,
                            @Param("endTime") LocalDateTime endTime,
                            @Param("excludeId") Long excludeId);

    /**
     * 검색 조건 클래스
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchCriteria {
        
        /**
         * 고객 ID
         */
        private Long userId;
        
        /**
         * 정비소 ID
         */
        private Long serviceCenterId;
        
        /**
         * 차량 ID
         */
        private Long vehicleId;
        
        /**
         * 예약 상태
         */
        private Reservation.ReservationStatus status;
        
        /**
         * 검색 시작 날짜
         */
        private LocalDateTime startDate;
        
        /**
         * 검색 종료 날짜
         */
        private LocalDateTime endDate;
        
        /**
         * 정렬 기준 (scheduledDate, createdAt, status)
         */
        private String sortBy = "scheduledDate";
        
        /**
         * 정렬 방향 (ASC, DESC)
         */
        private String sortDirection = "ASC";
        
        /**
         * 페이지 번호
         */
        private Integer page = 0;
        
        /**
         * 페이지 크기
         */
        private Integer size = 10;
        
        /**
         * 오프셋 계산
         */
        public Integer getOffset() {
            return page * size;
        }
    }
} 