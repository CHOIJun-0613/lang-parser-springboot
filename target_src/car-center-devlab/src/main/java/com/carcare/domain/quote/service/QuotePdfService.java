package com.carcare.domain.quote.service;

import com.carcare.domain.quote.entity.Quote;
import com.carcare.domain.quote.entity.QuoteItem;
import com.carcare.domain.quote.repository.QuoteRepository;
import com.carcare.domain.quote.repository.QuoteItemRepository;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.math.BigDecimal;

/**
 * 견적서 PDF 생성 서비스
 * 견적서 템플릿을 기반으로 PDF 문서를 생성
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class QuotePdfService {

    private final QuoteRepository quoteRepository;
    private final QuoteItemRepository quoteItemRepository;
    private final QuoteCalculationService calculationService;

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy년 MM월 dd일 HH:mm");

    /**
     * 견적서 PDF 생성
     */
    public PdfGenerationResult generateQuotePdf(Long quoteId) {
        log.info("견적서 PDF 생성 시작: quoteId={}", quoteId);
        
        try {
            // 견적서 데이터 조회
            Quote quote = quoteRepository.findById(quoteId)
                .orElseThrow(() -> new BusinessException("견적서를 찾을 수 없습니다."));
            
            List<QuoteItem> items = quoteItemRepository.findByQuoteId(quoteId);
            
            // PDF 내용 생성
            String htmlContent = generateHtmlContent(quote, items);
            
            // HTML을 PDF로 변환 (실제 구현에서는 라이브러리 사용)
            byte[] pdfBytes = convertHtmlToPdf(htmlContent);
            
            String fileName = generateFileName(quote);
            
            PdfGenerationResult result = PdfGenerationResult.builder()
                .fileName(fileName)
                .contentType("application/pdf")
                .fileSize(pdfBytes.length)
                .resource(new ByteArrayResource(pdfBytes))
                .generatedAt(LocalDateTime.now())
                .build();
            
            log.info("견적서 PDF 생성 완료: quoteId={}, fileName={}, fileSize={}", 
                    quoteId, fileName, pdfBytes.length);
            
            return result;
            
        } catch (Exception e) {
            log.error("견적서 PDF 생성 실패: quoteId={}, error={}", quoteId, e.getMessage(), e);
            throw new BusinessException("견적서 PDF 생성에 실패했습니다: " + e.getMessage());
        }
    }

    /**
     * 견적서 HTML 템플릿 생성
     */
    private String generateHtmlContent(Quote quote, List<QuoteItem> items) {
        StringBuilder html = new StringBuilder();
        
        // HTML 헤더
        html.append("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>견적서</title>
                <style>
                    body { font-family: 'Malgun Gothic', sans-serif; margin: 20px; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .title { font-size: 24px; font-weight: bold; margin-bottom: 20px; }
                    .info-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                    .info-table th, .info-table td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                    .info-table th { background-color: #f0f0f0; font-weight: bold; }
                    .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                    .items-table th, .items-table td { border: 1px solid #ccc; padding: 8px; text-align: center; }
                    .items-table th { background-color: #f0f0f0; font-weight: bold; }
                    .items-table .desc { text-align: left; }
                    .total-section { margin-top: 20px; }
                    .total-table { width: 50%; border-collapse: collapse; margin-left: auto; }
                    .total-table th, .total-table td { border: 1px solid #ccc; padding: 8px; }
                    .total-table th { background-color: #f0f0f0; text-align: left; }
                    .total-table td { text-align: right; font-weight: bold; }
                    .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #666; }
                </style>
            </head>
            <body>
            """);
        
        // 견적서 제목
        html.append("<div class=\"header\">");
        html.append("<div class=\"title\">정비 견적서</div>");
        html.append("</div>");
        
        // 견적서 기본 정보
        html.append("<table class=\"info-table\">");
        html.append("<tr><th>견적서 번호</th><td>").append(quote.getQuoteUuid()).append("</td>");
        html.append("<th>작성일자</th><td>").append(quote.getCreatedAt().format(DATE_FORMATTER)).append("</td></tr>");
        html.append("<tr><th>예약 번호</th><td>").append(quote.getReservationId()).append("</td>");
        html.append("<th>유효기간</th><td>").append(
            quote.getValidUntil() != null ? quote.getValidUntil().format(DATE_FORMATTER) : "미설정"
        ).append("</td></tr>");
        html.append("<tr><th>상태</th><td>").append(quote.getStatus().getDescription()).append("</td>");
        html.append("<th>승인일자</th><td>").append(
            quote.getApprovedAt() != null ? quote.getApprovedAt().format(DATE_FORMATTER) : "-"
        ).append("</td></tr>");
        html.append("</table>");
        
        // 견적 항목 테이블
        if (!items.isEmpty()) {
            html.append("<table class=\"items-table\">");
            html.append("<thead>");
            html.append("<tr><th>순번</th><th>항목구분</th><th>설명</th><th>수량</th><th>단가</th><th>금액</th><th>보증기간</th></tr>");
            html.append("</thead>");
            html.append("<tbody>");
            
            int index = 1;
            for (QuoteItem item : items) {
                html.append("<tr>");
                html.append("<td>").append(index++).append("</td>");
                html.append("<td>").append(item.getItemType().getDescription()).append("</td>");
                html.append("<td class=\"desc\">").append(escapeHtml(item.getDescription())).append("</td>");
                html.append("<td>").append(item.getQuantity()).append("</td>");
                html.append("<td>").append(formatCurrency(item.getUnitPrice())).append("</td>");
                html.append("<td>").append(formatCurrency(item.getTotalPrice())).append("</td>");
                html.append("<td>").append(
                    item.getWarrantyPeriod() != null ? item.getWarrantyPeriod() + "개월" : "-"
                ).append("</td>");
                html.append("</tr>");
            }
            
            html.append("</tbody>");
            html.append("</table>");
        }
        
        // 총액 계산 섹션
        var calculation = calculationService.calculateQuoteTotal(quote.getId());
        
        html.append("<div class=\"total-section\">");
        html.append("<table class=\"total-table\">");
        html.append("<tr><th>공임비</th><td>").append(formatCurrency(calculation.getLaborCost())).append("</td></tr>");
        html.append("<tr><th>부품비</th><td>").append(formatCurrency(calculation.getPartsCost())).append("</td></tr>");
        html.append("<tr><th>소모품비</th><td>").append(formatCurrency(calculation.getMaterialCost())).append("</td></tr>");
        html.append("<tr><th>진단비</th><td>").append(formatCurrency(calculation.getDiagnosticCost())).append("</td></tr>");
        html.append("<tr><th>기타비용</th><td>").append(formatCurrency(calculation.getOtherCost())).append("</td></tr>");
        html.append("<tr><th>소계</th><td>").append(formatCurrency(calculation.getSubtotal())).append("</td></tr>");
        html.append("<tr><th>부가세</th><td>").append(formatCurrency(calculation.getTaxAmount())).append("</td></tr>");
        
        if (quote.getDiscountAmount() != null && quote.getDiscountAmount().compareTo(BigDecimal.ZERO) > 0) {
            html.append("<tr><th>할인금액</th><td>").append(formatCurrency(quote.getDiscountAmount())).append("</td></tr>");
        }
        
        html.append("<tr style=\"background-color: #e0e0e0;\"><th>총 견적금액</th><td>").append(formatCurrency(quote.getTotalAmount())).append("</td></tr>");
        html.append("</table>");
        html.append("</div>");
        
        // 메모
        if (quote.getNotes() != null && !quote.getNotes().trim().isEmpty()) {
            html.append("<div style=\"margin-top: 20px;\">");
            html.append("<h3>비고</h3>");
            html.append("<div style=\"border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9;\">");
            html.append(escapeHtml(quote.getNotes()).replace("\n", "<br>"));
            html.append("</div>");
            html.append("</div>");
        }
        
        // 푸터
        html.append("<div class=\"footer\">");
        html.append("<p>본 견적서는 카센터 관리 시스템에서 자동 생성되었습니다.</p>");
        html.append("<p>생성일시: ").append(LocalDateTime.now().format(DATE_FORMATTER)).append("</p>");
        html.append("</div>");
        
        html.append("</body></html>");
        
        return html.toString();
    }

    /**
     * HTML을 PDF로 변환
     * 실제 구현에서는 iText, Flying Saucer, wkhtmltopdf 등의 라이브러리 사용
     */
    private byte[] convertHtmlToPdf(String htmlContent) throws IOException {
        // 실제 구현에서는 PDF 라이브러리를 사용하여 변환
        // 여기서는 예시로 HTML 내용을 바이트 배열로 반환
        
        // PDF 생성 시뮬레이션
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            // PDF 헤더 (실제로는 PDF 라이브러리가 처리)
            String pdfHeader = "%PDF-1.4\n";
            baos.write(pdfHeader.getBytes());
            
            // HTML 내용을 PDF로 변환하는 로직
            // 실제 구현에서는 다음과 같은 라이브러리 사용:
            /*
            // iText 사용 예시:
            Document document = new Document();
            PdfWriter.getInstance(document, baos);
            document.open();
            XMLWorkerHelper.getInstance().parseXHtml(writer, document, 
                new ByteArrayInputStream(htmlContent.getBytes()));
            document.close();
            */
            
            // 현재는 HTML 내용을 그대로 바이트로 변환 (테스트용)
            baos.write(htmlContent.getBytes("UTF-8"));
            
            return baos.toByteArray();
        }
    }

    /**
     * 파일명 생성
     */
    private String generateFileName(Quote quote) {
        String dateStr = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        return String.format("견적서_%s_%s.pdf", quote.getQuoteUuid().toString().substring(0, 8), dateStr);
    }

    /**
     * HTML 이스케이프 처리
     */
    private String escapeHtml(String text) {
        if (text == null) return "";
        return text.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace("\"", "&quot;")
                  .replace("'", "&#39;");
    }

    /**
     * 통화 형식 포맷팅
     */
    private String formatCurrency(BigDecimal amount) {
        if (amount == null) return "0원";
        return String.format("%,d원", amount.longValue());
    }

    /**
     * PDF 생성 결과 클래스
     */
    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class PdfGenerationResult {
        private String fileName;            // 파일명
        private String contentType;         // 컨텐츠 타입
        private long fileSize;              // 파일 크기
        private Resource resource;          // 파일 리소스
        private LocalDateTime generatedAt;  // 생성 일시
    }
} 