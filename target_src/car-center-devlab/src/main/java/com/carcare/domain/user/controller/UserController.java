package com.carcare.domain.user.controller;

import com.carcare.domain.user.dto.UserDto;
import com.carcare.domain.user.service.UserService;
import com.carcare.common.dto.ApiResponse;
import com.carcare.common.util.ResponseUtils;
import com.carcare.common.exception.BusinessException;
import com.carcare.config.JwtAuthenticationFilter.JwtUserPrincipal;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

import jakarta.validation.Valid;
import java.util.List;

/**
 * 사용자 관리 컨트롤러(재분석)
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
@Validated
@Tag(name = "User", description = "사용자 관리 API")
public class UserController {
    /**
	 * 사용자 관리 서비스 클래스 변수
	 */
	@Autowired
    private final UserService userService;
    
    /**
     * 현재 사용자 프로필 조회
     */
    @GetMapping("/profile")
    @Operation(summary = "내 프로필 조회", description = "현재 로그인한 사용자의 프로필 정보를 조회합니다.")
    @io.swagger.v3.oas.annotations.responses.ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "프로필 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "404", description = "사용자를 찾을 수 없음")
    })
    public ResponseEntity<ApiResponse<UserDto.ProfileResponse>> getMyProfile() {
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("사용자 프로필 조회 요청: userId={}", currentUser.getUserId());
        
        UserDto.ProfileResponse response = userService.getUserProfile(currentUser.getUserId());
        
        return ResponseEntity.ok(ResponseUtils.success("프로필을 성공적으로 조회했습니다.", response));
    }
    
    /**
     * 현재 사용자 프로필 수정
     */
    @PutMapping("/profile")
    @Operation(summary = "내 프로필 수정", description = "현재 로그인한 사용자의 프로필 정보를 수정합니다.")
    @io.swagger.v3.oas.annotations.responses.ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "프로필 수정 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "409", description = "중복된 전화번호")
    })
    public ResponseEntity<ApiResponse<UserDto.ProfileResponse>> updateMyProfile(
            @Valid @RequestBody UserDto.UpdateProfileRequest request) {
        
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("사용자 프로필 수정 요청: userId={}, name={}", currentUser.getUserId(), request.getName());
        
        UserDto.ProfileResponse response = userService.updateUserProfile(currentUser.getUserId(), request);
        
        return ResponseEntity.ok(ResponseUtils.success("프로필을 성공적으로 수정했습니다.", response));
    }
    
    /**
     * 비밀번호 변경
     */
    @PutMapping("/password")
    @Operation(summary = "비밀번호 변경", description = "현재 로그인한 사용자의 비밀번호를 변경합니다.")
    @io.swagger.v3.oas.annotations.responses.ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "비밀번호 변경 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "400", description = "잘못된 요청 데이터"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패")
    })
    public ResponseEntity<ApiResponse<Void>> changePassword(
            @Valid @RequestBody UserDto.ChangePasswordRequest request) {
        
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("비밀번호 변경 요청: userId={}", currentUser.getUserId());
        
        userService.changePassword(currentUser.getUserId(), request);
        
        return ResponseEntity.ok(ResponseUtils.success("비밀번호가 성공적으로 변경되었습니다.", null));
    }
    
    /**
     * 사용자 목록 조회 (관리자용)
     */
    @GetMapping
    @Operation(summary = "사용자 목록 조회", description = "등록된 사용자 목록을 조회합니다. (관리자 전용)")
    @io.swagger.v3.oas.annotations.responses.ApiResponses(value = {
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "200", description = "사용자 목록 조회 성공"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "401", description = "인증 실패"),
        @io.swagger.v3.oas.annotations.responses.ApiResponse(responseCode = "403", description = "관리자 권한 필요")
    })
    public ResponseEntity<ApiResponse<List<UserDto.ListResponse>>> getUserList(
            @Parameter(description = "페이지 번호 (0부터 시작)") @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "페이지 크기") @RequestParam(defaultValue = "20") int size) {
        
        JwtUserPrincipal currentUser = getCurrentUser();
        log.info("사용자 목록 조회 요청: userId={}, role={}, page={}, size={}", 
                currentUser.getUserId(), currentUser.getRole(), page, size);
        
        // 관리자 권한 확인
        if (!"SYSTEM_ADMIN".equals(currentUser.getRole())) {
            throw new BusinessException("시스템 관리자 권한이 필요합니다");
        }
        
        List<UserDto.ListResponse> users = userService.getUserList(page, size);
        long totalCount = userService.getUserCount();
        
        return ResponseEntity.ok(ResponseUtils.success(
                String.format("사용자 목록을 성공적으로 조회했습니다. (총 %d명)", totalCount), users));
    }
    
    /**
     * SecurityContext에서 현재 사용자 정보 추출
     */
    private JwtUserPrincipal getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof JwtUserPrincipal) {
            return (JwtUserPrincipal) authentication.getPrincipal();
        }
        throw new BusinessException("인증된 사용자 정보를 찾을 수 없습니다");
    }
} 