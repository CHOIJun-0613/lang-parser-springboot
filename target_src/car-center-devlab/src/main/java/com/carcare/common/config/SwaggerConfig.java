package com.carcare.common.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.Components;

/**
 * Swagger OpenAPI 3.0 설정
 * 런타임에 현재 요청의 URL을 기반으로 서버 설정을 동적으로 처리
 */
@Configuration
public class SwaggerConfig {

    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Car Center Management System API")
                        .description("자동차 정비소 관리 시스템 REST API 문서")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("Car Center API Team")
                                .email("api@carcare.com")
                                .url("https://carcare.com"))
                        .license(new License()
                                .name("Apache 2.0")
                                .url("http://www.apache.org/licenses/LICENSE-2.0.html")))
                .addSecurityItem(new SecurityRequirement().addList("JWT"))
                .components(new Components()
                        .addSecuritySchemes("JWT", 
                                new SecurityScheme()
                                        .type(SecurityScheme.Type.HTTP)
                                        .scheme("bearer")
                                        .bearerFormat("JWT")
                                        .in(SecurityScheme.In.HEADER)
                                        .name("Authorization")));
        // 서버 설정은 제거 - Swagger UI가 현재 브라우저 URL을 자동으로 사용하도록 함
    }
} 