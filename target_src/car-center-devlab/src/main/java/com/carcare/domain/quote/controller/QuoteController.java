package com.carcare.domain.quote.controller;

import com.carcare.domain.quote.service.QuoteService;
import com.carcare.domain.quote.service.QuotePdfService;
import com.carcare.domain.quote.dto.QuoteDto;
import com.carcare.domain.quote.entity.Quote;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

/**
 * 견적서 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/quotes")
@Tag(name = "Quote", description = "견적서 관리 API")
@RequiredArgsConstructor
@Slf4j
public class QuoteController {
    
    private final QuoteService quoteService;
    private final QuotePdfService quotePdfService;

    /**
     * 견적서 생성
     */
    @PostMapping
    @Operation(summary = "견적서 생성", description = "새로운 견적서를 생성합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> createQuote(
            @Valid @RequestBody QuoteDto.CreateRequest request) {
        
        log.info("견적서 생성 API 호출: reservationId={}", request.getReservationId());
        
        QuoteDto.Response response = quoteService.createQuote(request);
        
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(ResponseUtils.success("견적서가 성공적으로 생성되었습니다.", response));
    }

    /**
     * 견적서 조회 (ID)
     */
    @GetMapping("/{id}")
    @Operation(summary = "견적서 조회", description = "견적서 ID로 견적서를 조회합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> getQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id) {
        
        log.info("견적서 조회 API 호출: quoteId={}", id);
        
        QuoteDto.Response response = quoteService.findQuoteById(id);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서 조회가 완료되었습니다.", response));
    }

    /**
     * 견적서 조회 (UUID)
     */
    @GetMapping("/uuid/{uuid}")
    @Operation(summary = "견적서 조회 (UUID)", description = "견적서 UUID로 견적서를 조회합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> getQuoteByUuid(
            @Parameter(description = "견적서 UUID", example = "550e8400-e29b-41d4-a716-446655440000")
            @PathVariable UUID uuid) {
        
        log.info("견적서 UUID 조회 API 호출: uuid={}", uuid);
        
        QuoteDto.Response response = quoteService.findQuoteByUuid(uuid);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서 조회가 완료되었습니다.", response));
    }

    /**
     * 예약별 견적서 조회
     */
    @GetMapping("/reservation/{reservationId}")
    @Operation(summary = "예약별 견적서 조회", description = "예약 ID로 견적서를 조회합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> getQuoteByReservation(
            @Parameter(description = "예약 ID", example = "1")
            @PathVariable Long reservationId) {
        
        log.info("예약별 견적서 조회 API 호출: reservationId={}", reservationId);
        
        QuoteDto.Response response = quoteService.findQuoteByReservationId(reservationId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서 조회가 완료되었습니다.", response));
    }

    /**
     * 견적서 수정
     */
    @PutMapping("/{id}")
    @Operation(summary = "견적서 수정", description = "견적서 정보를 수정합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> updateQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id,
            @Valid @RequestBody QuoteDto.UpdateRequest request) {
        
        log.info("견적서 수정 API 호출: quoteId={}", id);
        
        QuoteDto.Response response = quoteService.updateQuote(id, request);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서가 성공적으로 수정되었습니다.", response));
    }

    /**
     * 견적서 삭제
     */
    @DeleteMapping("/{id}")
    @Operation(summary = "견적서 삭제", description = "견적서를 삭제합니다.")
    public ResponseEntity<ApiResponse<Void>> deleteQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id) {
        
        log.info("견적서 삭제 API 호출: quoteId={}", id);
        
        quoteService.deleteQuote(id);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서가 성공적으로 삭제되었습니다."));
    }

    /**
     * 견적서 발송
     */
    @PostMapping("/{id}/send")
    @Operation(summary = "견적서 발송", description = "견적서를 고객에게 발송합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> sendQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id) {
        
        log.info("견적서 발송 API 호출: quoteId={}", id);
        
        QuoteDto.Response response = quoteService.sendQuote(id);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서가 성공적으로 발송되었습니다.", response));
    }

    /**
     * 견적서 승인
     */
    @PostMapping("/{id}/approve")
    @Operation(summary = "견적서 승인", description = "견적서를 승인합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> approveQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id) {
        
        log.info("견적서 승인 API 호출: quoteId={}", id);
        
        QuoteDto.Response response = quoteService.approveQuote(id);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서가 성공적으로 승인되었습니다.", response));
    }

    /**
     * 견적서 거절
     */
    @PostMapping("/{id}/reject")
    @Operation(summary = "견적서 거절", description = "견적서를 거절합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.Response>> rejectQuote(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id,
            @Valid @RequestBody QuoteDto.StatusChangeRequest request) {
        
        log.info("견적서 거절 API 호출: quoteId={}", id);
        
        QuoteDto.Response response = quoteService.rejectQuote(id, request);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서가 성공적으로 거절되었습니다.", response));
    }

    /**
     * 견적서 목록 조회 (페이징)
     */
    @GetMapping
    @Operation(summary = "견적서 목록 조회", description = "견적서 목록을 페이징하여 조회합니다.")
    public ResponseEntity<ApiResponse<QuoteDto.ListResponse>> getQuotes(
            @Parameter(description = "페이지 번호 (0부터 시작)", example = "0")
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "페이지 크기", example = "10")
            @RequestParam(defaultValue = "10") int size) {
        
        log.info("견적서 목록 조회 API 호출: page={}, size={}", page, size);
        
        QuoteDto.ListResponse response = quoteService.findQuotes(page, size);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서 목록 조회가 완료되었습니다.", response));
    }

    /**
     * 상태별 견적서 조회
     */
    @GetMapping("/status/{status}")
    @Operation(summary = "상태별 견적서 조회", description = "특정 상태의 견적서 목록을 조회합니다.")
    public ResponseEntity<ApiResponse<List<QuoteDto.Response>>> getQuotesByStatus(
            @Parameter(description = "견적서 상태", example = "PENDING")
            @PathVariable Quote.QuoteStatus status) {
        
        log.info("상태별 견적서 조회 API 호출: status={}", status);
        
        List<QuoteDto.Response> response = quoteService.findQuotesByStatus(status);
        
        return ResponseEntity.ok(ResponseUtils.success("상태별 견적서 목록 조회가 완료되었습니다.", response));
    }

    /**
     * 견적서 PDF 다운로드
     */
    @GetMapping("/{id}/pdf")
    @Operation(summary = "견적서 PDF 다운로드", description = "견적서를 PDF 파일로 다운로드합니다.")
    public ResponseEntity<org.springframework.core.io.Resource> downloadQuotePdf(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long id) {
        
        log.info("견적서 PDF 다운로드 API 호출: quoteId={}", id);
        
        QuotePdfService.PdfGenerationResult pdfResult = quotePdfService.generateQuotePdf(id);
        
        // 한글 파일명을 위한 RFC 5987 인코딩
        String encodedFileName = encodeFileName(pdfResult.getFileName());
        
        return ResponseEntity.ok()
            .header("Content-Disposition", "attachment; " + encodedFileName)
            .header("Content-Type", pdfResult.getContentType())
            .header("Content-Length", String.valueOf(pdfResult.getFileSize()))
            .body(pdfResult.getResource());
    }
    
    /**
     * 파일명 인코딩 (한글 지원을 위한 RFC 5987 표준)
     */
    private String encodeFileName(String fileName) {
        try {
            // ASCII 파일명과 UTF-8 인코딩된 파일명 모두 제공
            String encodedName = java.net.URLEncoder.encode(fileName, "UTF-8")
                .replace("+", "%20"); // 공백을 %20으로 변경
            
            return String.format("filename=\"%s\"; filename*=UTF-8''%s", 
                fileName.replaceAll("[^\\x00-\\x7F]", "_"), // ASCII 문자만 남기고 나머지는 _ 로 치환
                encodedName);
        } catch (Exception e) {
            log.warn("파일명 인코딩 실패, 기본 파일명 사용: {}", e.getMessage());
            return "filename=\"quote.pdf\"";
        }
    }
    
    /**
     * 견적 계산 (생성 전 미리보기)
     */
    @PostMapping("/calculate")
    @Operation(summary = "견적 계산", description = "견적 항목들의 총 금액을 계산합니다.")
    public ResponseEntity<ApiResponse<QuoteCalculationResponse>> calculateQuote(
            @Valid @RequestBody QuoteCalculationRequest request) {
        
        log.info("견적 계산 API 호출: items={}", request.getItems().size());
        
        // 소계 계산
        BigDecimal subtotal = request.getItems().stream()
            .map(item -> item.getUnitPrice().multiply(BigDecimal.valueOf(item.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        // 할인 금액 계산
        BigDecimal discountAmount = subtotal.multiply(request.getDiscountRate());
        
        // 할인 후 금액
        BigDecimal afterDiscount = subtotal.subtract(discountAmount);
        
        // 세금 계산
        BigDecimal taxAmount = afterDiscount.multiply(request.getTaxRate());
        
        // 총액 계산
        BigDecimal totalAmount = afterDiscount.add(taxAmount);
        
        QuoteCalculationResponse response = new QuoteCalculationResponse(
            subtotal, discountAmount, taxAmount, totalAmount);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 계산이 완료되었습니다.", response));
    }
    
    /**
     * 견적 계산 요청 DTO
     */
    public static class QuoteCalculationRequest {
        
        @NotNull(message = "견적 항목은 필수입니다")
        private List<CalculationItem> items;
        
        @DecimalMin(value = "0.0", message = "할인율은 0 이상이어야 합니다")
        private BigDecimal discountRate = BigDecimal.ZERO;
        
        @DecimalMin(value = "0.0", message = "세율은 0 이상이어야 합니다")
        private BigDecimal taxRate = new BigDecimal("0.1");
        
        // getters and setters
        public List<CalculationItem> getItems() { return items; }
        public void setItems(List<CalculationItem> items) { this.items = items; }
        public BigDecimal getDiscountRate() { return discountRate; }
        public void setDiscountRate(BigDecimal discountRate) { this.discountRate = discountRate; }
        public BigDecimal getTaxRate() { return taxRate; }
        public void setTaxRate(BigDecimal taxRate) { this.taxRate = taxRate; }
        
        public static class CalculationItem {
            @NotNull(message = "수량은 필수입니다")
            private Integer quantity;
            
            @NotNull(message = "단가는 필수입니다")
            @DecimalMin(value = "0.0", message = "단가는 0 이상이어야 합니다")
            private BigDecimal unitPrice;
            
            // getters and setters
            public Integer getQuantity() { return quantity; }
            public void setQuantity(Integer quantity) { this.quantity = quantity; }
            public BigDecimal getUnitPrice() { return unitPrice; }
            public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
        }
    }
    
    /**
     * 견적 계산 응답 DTO
     */
    public static class QuoteCalculationResponse {
        private BigDecimal subtotal;      // 소계
        private BigDecimal discountAmount; // 할인금액
        private BigDecimal taxAmount;     // 세금
        private BigDecimal totalAmount;   // 총액
        
        public QuoteCalculationResponse(BigDecimal subtotal, BigDecimal discountAmount, 
                                      BigDecimal taxAmount, BigDecimal totalAmount) {
            this.subtotal = subtotal;
            this.discountAmount = discountAmount;
            this.taxAmount = taxAmount;
            this.totalAmount = totalAmount;
        }
        
        // getters
        public BigDecimal getSubtotal() { return subtotal; }
        public BigDecimal getDiscountAmount() { return discountAmount; }
        public BigDecimal getTaxAmount() { return taxAmount; }
        public BigDecimal getTotalAmount() { return totalAmount; }
    }
} 