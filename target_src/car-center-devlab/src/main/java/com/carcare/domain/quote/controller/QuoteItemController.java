package com.carcare.domain.quote.controller;

import com.carcare.domain.quote.service.QuoteItemService;
import com.carcare.domain.quote.dto.QuoteItemDto;
import com.carcare.domain.quote.entity.QuoteItem;
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
import java.util.List;

/**
 * 견적 항목 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/quotes/{quoteId}/items")
@Tag(name = "Quote Item", description = "견적 항목 관리 API")
@RequiredArgsConstructor
@Slf4j
public class QuoteItemController {
    
    private final QuoteItemService quoteItemService;

    /**
     * 견적 항목 생성
     */
    @PostMapping
    @Operation(summary = "견적 항목 생성", description = "견적서에 새로운 항목을 추가합니다.")
    public ResponseEntity<ApiResponse<QuoteItemDto.Response>> createQuoteItem(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Valid @RequestBody QuoteItemDto.CreateRequest request) {
        
        log.info("견적 항목 생성 API 호출: quoteId={}, itemType={}", quoteId, request.getItemType());
        
        QuoteItemDto.Response response = quoteItemService.createQuoteItem(quoteId, request);
        
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(ResponseUtils.success("견적 항목이 성공적으로 생성되었습니다.", response));
    }

    /**
     * 견적 항목 조회
     */
    @GetMapping("/{itemId}")
    @Operation(summary = "견적 항목 조회", description = "견적 항목 ID로 항목을 조회합니다.")
    public ResponseEntity<ApiResponse<QuoteItemDto.Response>> getQuoteItem(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "견적 항목 ID", example = "1")
            @PathVariable Long itemId) {
        
        log.info("견적 항목 조회 API 호출: quoteId={}, itemId={}", quoteId, itemId);
        
        QuoteItemDto.Response response = quoteItemService.findQuoteItemById(itemId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목 조회가 완료되었습니다.", response));
    }

    /**
     * 견적서별 모든 항목 조회
     */
    @GetMapping
    @Operation(summary = "견적서별 항목 목록 조회", description = "견적서의 모든 항목을 조회합니다.")
    public ResponseEntity<ApiResponse<List<QuoteItemDto.Response>>> getQuoteItems(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId) {
        
        log.info("견적서별 항목 목록 조회 API 호출: quoteId={}", quoteId);
        
        List<QuoteItemDto.Response> response = quoteItemService.findQuoteItemsByQuoteId(quoteId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목 목록 조회가 완료되었습니다.", response));
    }

    /**
     * 견적서별 특정 타입 항목 조회
     */
    @GetMapping("/type/{itemType}")
    @Operation(summary = "견적서별 특정 타입 항목 조회", description = "견적서의 특정 타입 항목만 조회합니다.")
    public ResponseEntity<ApiResponse<List<QuoteItemDto.Response>>> getQuoteItemsByType(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "항목 타입", example = "LABOR")
            @PathVariable QuoteItem.QuoteItemType itemType) {
        
        log.info("견적서별 타입별 항목 조회 API 호출: quoteId={}, itemType={}", quoteId, itemType);
        
        List<QuoteItemDto.Response> response = quoteItemService.findQuoteItemsByQuoteIdAndType(quoteId, itemType);
        
        return ResponseEntity.ok(ResponseUtils.success("타입별 견적 항목 목록 조회가 완료되었습니다.", response));
    }

    /**
     * 견적 항목 수정
     */
    @PutMapping("/{itemId}")
    @Operation(summary = "견적 항목 수정", description = "견적 항목 정보를 수정합니다.")
    public ResponseEntity<ApiResponse<QuoteItemDto.Response>> updateQuoteItem(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "견적 항목 ID", example = "1")
            @PathVariable Long itemId,
            @Valid @RequestBody QuoteItemDto.UpdateRequest request) {
        
        log.info("견적 항목 수정 API 호출: quoteId={}, itemId={}", quoteId, itemId);
        
        QuoteItemDto.Response response = quoteItemService.updateQuoteItem(itemId, request);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목이 성공적으로 수정되었습니다.", response));
    }

    /**
     * 견적 항목 삭제
     */
    @DeleteMapping("/{itemId}")
    @Operation(summary = "견적 항목 삭제", description = "견적 항목을 삭제합니다.")
    public ResponseEntity<ApiResponse<Void>> deleteQuoteItem(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Parameter(description = "견적 항목 ID", example = "1")
            @PathVariable Long itemId) {
        
        log.info("견적 항목 삭제 API 호출: quoteId={}, itemId={}", quoteId, itemId);
        
        quoteItemService.deleteQuoteItem(itemId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목이 성공적으로 삭제되었습니다."));
    }

    /**
     * 견적 항목 일괄 생성
     */
    @PostMapping("/batch")
    @Operation(summary = "견적 항목 일괄 생성", description = "견적서에 여러 항목을 일괄로 추가합니다.")
    public ResponseEntity<ApiResponse<List<QuoteItemDto.Response>>> createQuoteItems(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Valid @RequestBody List<QuoteItemDto.CreateRequest> requests) {
        
        log.info("견적 항목 일괄 생성 API 호출: quoteId={}, 항목 수={}", quoteId, requests.size());
        
        List<QuoteItemDto.Response> response = quoteItemService.createQuoteItems(quoteId, requests);
        
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(ResponseUtils.success("견적 항목들이 성공적으로 생성되었습니다.", response));
    }

    /**
     * 견적 항목 일괄 교체
     */
    @PutMapping("/batch")
    @Operation(summary = "견적 항목 일괄 교체", description = "견적서의 모든 항목을 삭제하고 새로운 항목들로 교체합니다.")
    public ResponseEntity<ApiResponse<List<QuoteItemDto.Response>>> replaceQuoteItems(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId,
            @Valid @RequestBody List<QuoteItemDto.CreateRequest> requests) {
        
        log.info("견적 항목 일괄 교체 API 호출: quoteId={}, 항목 수={}", quoteId, requests.size());
        
        List<QuoteItemDto.Response> response = quoteItemService.replaceQuoteItems(quoteId, requests);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목들이 성공적으로 교체되었습니다.", response));
    }

    /**
     * 견적서의 모든 항목 삭제
     */
    @DeleteMapping
    @Operation(summary = "견적서 모든 항목 삭제", description = "견적서의 모든 항목을 삭제합니다.")
    public ResponseEntity<ApiResponse<Void>> deleteAllQuoteItems(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId) {
        
        log.info("견적서 모든 항목 삭제 API 호출: quoteId={}", quoteId);
        
        quoteItemService.deleteQuoteItemsByQuoteId(quoteId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적서의 모든 항목이 성공적으로 삭제되었습니다."));
    }

    /**
     * 견적 항목 개수 조회
     */
    @GetMapping("/count")
    @Operation(summary = "견적 항목 개수 조회", description = "견적서의 총 항목 개수를 조회합니다.")
    public ResponseEntity<ApiResponse<Long>> getQuoteItemCount(
            @Parameter(description = "견적서 ID", example = "1")
            @PathVariable Long quoteId) {
        
        log.info("견적 항목 개수 조회 API 호출: quoteId={}", quoteId);
        
        long count = quoteItemService.countQuoteItemsByQuoteId(quoteId);
        
        return ResponseEntity.ok(ResponseUtils.success("견적 항목 개수 조회가 완료되었습니다.", count));
    }
} 