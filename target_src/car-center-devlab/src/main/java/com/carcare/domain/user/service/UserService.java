package com.carcare.domain.user.service;

import com.carcare.domain.user.entity.User;
import com.carcare.domain.user.dto.UserDto;
import com.carcare.domain.user.mapper.UserMapper;
import com.carcare.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 사용자 비즈니스 로직 서비스
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {
    
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    
    /**
     * 사용자 프로필 조회
     */
    @Transactional(readOnly = true)
    public UserDto.ProfileResponse getUserProfile(Long userId) {
        log.info("사용자 프로필 조회 요청: userId={}", userId);
        
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException("사용자를 찾을 수 없습니다"));
        
        return convertToProfileResponse(user);
    }
    
    /**
     * 사용자 프로필 수정
     */
    @Transactional
    public UserDto.ProfileResponse updateUserProfile(Long userId, UserDto.UpdateProfileRequest request) {
        log.info("사용자 프로필 수정 요청: userId={}, name={}", userId, request.getName());
        
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException("사용자를 찾을 수 없습니다"));
        
        // 전화번호 중복 확인 (기존 번호와 다른 경우에만)
        if (request.getPhone() != null && !request.getPhone().equals(user.getPhone())) {
            if (userMapper.existsByPhone(request.getPhone())) {
                throw new BusinessException("이미 사용 중인 전화번호입니다");
            }
        }
        
        // 사용자 정보 업데이트
        user.setName(request.getName());
        user.setPhone(request.getPhone());
        user.setUpdatedAt(LocalDateTime.now());
        
        int updated = userMapper.updateUser(user);
        if (updated == 0) {
            throw new BusinessException("사용자 정보 수정에 실패했습니다");
        }
        
        log.info("사용자 프로필 수정 완료: userId={}", userId);
        
        return convertToProfileResponse(user);
    }
    
    /**
     * 비밀번호 변경
     */
    @Transactional
    public void changePassword(Long userId, UserDto.ChangePasswordRequest request) {
        log.info("비밀번호 변경 요청: userId={}", userId);
        
        User user = userMapper.findById(userId)
                .orElseThrow(() -> new BusinessException("사용자를 찾을 수 없습니다"));
        
        // 현재 비밀번호 확인
        if (!passwordEncoder.matches(request.getCurrentPassword(), user.getPassword())) {
            throw new BusinessException("현재 비밀번호가 올바르지 않습니다");
        }
        
        // 새 비밀번호 확인
        if (!request.getNewPassword().equals(request.getConfirmNewPassword())) {
            throw new BusinessException("새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다");
        }
        
        // 비밀번호 업데이트
        user.setPassword(passwordEncoder.encode(request.getNewPassword()));
        user.setUpdatedAt(LocalDateTime.now());
        
        int updated = userMapper.updateUser(user);
        if (updated == 0) {
            throw new BusinessException("비밀번호 변경에 실패했습니다");
        }
        
        log.info("비밀번호 변경 완료: userId={}", userId);
    }
    
    /**
     * 사용자 목록 조회 (관리자용)
     */
    @Transactional(readOnly = true)
    public List<UserDto.ListResponse> getUserList(int page, int size) {
        log.info("사용자 목록 조회 요청: page={}, size={}", page, size);
        
        int offset = page * size;
        List<User> users = userMapper.findUsersWithPaging(offset, size);
        
        return users.stream()
                .map(this::convertToListResponse)
                .collect(Collectors.toList());
    }
    
    /**
     * 사용자 수 조회
     */
    @Transactional(readOnly = true)
    public long getUserCount() {
        return userMapper.countUsers();
    }
    
    /**
     * Entity를 ProfileResponse DTO로 변환
     */
    private UserDto.ProfileResponse convertToProfileResponse(User user) {
        return UserDto.ProfileResponse.builder()
                .id(user.getId())
                .userUuid(user.getUserUuid())
                .email(user.getEmail())
                .name(user.getName())
                .phone(user.getPhone())
                .role(user.getRole())
                .isActive(user.getIsActive())
                .emailVerified(user.getEmailVerified())
                .lastLoginAt(user.getLastLoginAt())
                .createdAt(user.getCreatedAt())
                .updatedAt(user.getUpdatedAt())
                .build();
    }
    
    /**
     * Entity를 ListResponse DTO로 변환
     */
    private UserDto.ListResponse convertToListResponse(User user) {
        return UserDto.ListResponse.builder()
                .id(user.getId())
                .userUuid(user.getUserUuid())
                .email(user.getEmail())
                .name(user.getName())
                .phone(user.getPhone())
                .role(user.getRole())
                .isActive(user.getIsActive())
                .emailVerified(user.getEmailVerified())
                .createdAt(user.getCreatedAt())
                .lastLoginAt(user.getLastLoginAt())
                .build();
    }
} 