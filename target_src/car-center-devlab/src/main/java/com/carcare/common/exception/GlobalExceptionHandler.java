package com.carcare.common.exception;

import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.http.converter.HttpMessageNotReadableException;

import com.fasterxml.jackson.databind.exc.InvalidFormatException;
import com.fasterxml.jackson.databind.exc.MismatchedInputException;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * 전역 예외 처리기
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    /**
     * BusinessException 처리 - 404 Not Found
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<String>> handleBusinessException(BusinessException ex) {
        log.warn("Business exception occurred: {}", ex.getMessage());
        
        // 정비소를 찾을 수 없는 경우 404로 처리
        if (ex.getMessage().contains("정비소를 찾을 수 없습니다") || 
            ex.getMessage().contains("찾을 수 없습니다")) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ResponseUtils.error(ex.getMessage(), "RESOURCE_NOT_FOUND"));
        }
        
        // 중복 데이터 등의 경우 409 Conflict로 처리  
        if (ex.getMessage().contains("이미") || ex.getMessage().contains("중복")) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ResponseUtils.error(ex.getMessage(), "RESOURCE_CONFLICT"));
        }
        
        // 기타 비즈니스 예외는 400 Bad Request로 처리
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ResponseUtils.error(ex.getMessage(), "BUSINESS_ERROR"));
    }
    
    /**
     * Validation 예외 처리 - 400 Bad Request
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationException(MethodArgumentNotValidException ex) {
        log.warn("Validation exception occurred: {}", ex.getMessage());
        
        Map<String, Object> response = new HashMap<>();
        response.put("timestamp", java.time.LocalDateTime.now().toString().replace("T", " ").substring(0, 19));
        response.put("status", 400);
        response.put("error", "Bad Request");
        response.put("message", "Validation failed for object='" + ex.getBindingResult().getObjectName() + "'. Error count: " + ex.getBindingResult().getErrorCount());
        response.put("path", ""); // 실제 요청 path는 별도로 설정 필요
        
        response.put("errors", ex.getBindingResult().getFieldErrors().stream()
            .map(error -> {
                Map<String, Object> errorDetail = new HashMap<>();
                errorDetail.put("objectName", error.getObjectName());
                errorDetail.put("field", error.getField());
                errorDetail.put("rejectedValue", error.getRejectedValue());
                errorDetail.put("codes", error.getCodes());
                errorDetail.put("arguments", error.getArguments());
                errorDetail.put("defaultMessage", error.getDefaultMessage());
                errorDetail.put("bindingFailure", false);
                errorDetail.put("code", error.getCode());
                return errorDetail;
            })
            .toArray());
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
    }
    
    /**
     * ConstraintViolation 예외 처리 - 400 Bad Request
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ApiResponse<String>> handleConstraintViolationException(ConstraintViolationException ex) {
        log.warn("Constraint violation exception occurred: {}", ex.getMessage());
        
        StringBuilder message = new StringBuilder("입력값 검증 실패: ");
        Set<ConstraintViolation<?>> violations = ex.getConstraintViolations();
        for (ConstraintViolation<?> violation : violations) {
            message.append(violation.getPropertyPath()).append(" - ").append(violation.getMessage()).append("; ");
        }
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ResponseUtils.error(message.toString(), "VALIDATION_ERROR"));
    }
    
    /**
     * 타입 변환 예외 처리 - 400 Bad Request
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ApiResponse<String>> handleTypeMismatchException(MethodArgumentTypeMismatchException ex) {
        log.warn("Type mismatch exception occurred: {}", ex.getMessage());
        
        String message = String.format("잘못된 파라미터 타입입니다. '%s'는 %s 타입이어야 합니다.", 
            ex.getValue(), ex.getRequiredType().getSimpleName());
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ResponseUtils.error(message, "INVALID_PARAMETER_TYPE"));
    }
    
    /**
     * JSON 파싱 오류 처리 - 400 Bad Request
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiResponse<String>> handleHttpMessageNotReadableException(HttpMessageNotReadableException ex) {
        log.warn("JSON parsing error occurred: {}", ex.getMessage());
        
        String message = "잘못된 JSON 형식입니다.";
        
        // Jackson 관련 예외에서 더 구체적인 메시지 추출
        Throwable cause = ex.getCause();
        if (cause instanceof InvalidFormatException) {
            InvalidFormatException formatEx = (InvalidFormatException) cause;
            String fieldName = formatEx.getPath().isEmpty() ? "unknown" : 
                formatEx.getPath().get(formatEx.getPath().size() - 1).getFieldName();
            String invalidValue = formatEx.getValue() != null ? formatEx.getValue().toString() : "null";
            String targetType = formatEx.getTargetType().getSimpleName();
            
            message = String.format("필드 '%s'의 값 '%s'는 %s 타입으로 변환할 수 없습니다. 올바른 형식의 값을 입력해주세요.", 
                fieldName, invalidValue, targetType);
        } else if (cause instanceof MismatchedInputException) {
            MismatchedInputException mismatchEx = (MismatchedInputException) cause;
            String fieldName = mismatchEx.getPath().isEmpty() ? "unknown" : 
                mismatchEx.getPath().get(mismatchEx.getPath().size() - 1).getFieldName();
            String targetType = mismatchEx.getTargetType().getSimpleName();
            
            message = String.format("필드 '%s'의 값이 %s 타입과 일치하지 않습니다.", fieldName, targetType);
        }
        
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ResponseUtils.error(message, "INVALID_JSON_FORMAT"));
    }
    
    /**
     * HTTP 메서드 지원하지 않음 예외 처리 - 405 Method Not Allowed
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiResponse<String>> handleMethodNotSupportedException(HttpRequestMethodNotSupportedException ex) {
        log.warn("Method not supported exception occurred: {}", ex.getMessage());
        
        String message = String.format("지원되지 않는 HTTP 메서드입니다. 사용 가능한 메서드: %s", 
            String.join(", ", ex.getSupportedMethods()));
        
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
            .body(ResponseUtils.error(message, "METHOD_NOT_ALLOWED"));
    }
    
    /**
     * 인증 예외 처리 - 401 Unauthorized
     */
    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<ApiResponse<String>> handleAuthenticationException(AuthenticationException ex) {
        log.warn("Authentication exception occurred: {}", ex.getMessage());
        
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
            .body(ResponseUtils.error("인증이 필요합니다.", "UNAUTHORIZED"));
    }
    
    /**
     * 권한 예외 처리 - 403 Forbidden
     */
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<String>> handleAccessDeniedException(AccessDeniedException ex) {
        log.warn("Access denied exception occurred: {}", ex.getMessage());
        
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
            .body(ResponseUtils.error("접근 권한이 없습니다.", "FORBIDDEN"));
    }
    
    /**
     * 정적 리소스 찾을 수 없음 예외 처리 - 404 Not Found
     */
    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiResponse<String>> handleNoResourceFoundException(NoResourceFoundException ex) {
        log.debug("Static resource not found: {}", ex.getMessage());
        
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(ResponseUtils.error("요청한 리소스를 찾을 수 없습니다.", "RESOURCE_NOT_FOUND"));
    }
    
    /**
     * 기타 모든 예외 처리 - 500 Internal Server Error
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<String>> handleGeneralException(Exception ex) {
        log.error("Unexpected exception occurred: ", ex);
        
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ResponseUtils.error("서버 내부 오류가 발생했습니다.", "INTERNAL_SERVER_ERROR"));
    }
} 