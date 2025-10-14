package com.carcare.domain.service.controller;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * 정비 서비스 관리 컨트롤러
 */
@RestController
@RequestMapping("/api/v1/services")
@Tag(name = "Service", description = "정비 서비스 관리 API")
public class ServiceController {
    
    // TODO: 정비 서비스 관련 API 구현
} 