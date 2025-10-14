# car-center-devlab 프로젝트 논리명 추출 규칙

## 1. Class(클래스)의 logical name(논리명) 추출 규칙
- **논리명(logical name) 위치**: Class 선언 위치의 상단에 코멘트로 기술되어 있음. '/**\n * {local_name}\n */'의 형태로 기술되어 있음.
- **논리명 저장**: DB(neo4j)의 **Class 노드의 'logical_name' 속성에 저장**한다
- 예시 코드: 예시코드의 UserController클래스의 logical name(논리명)은 **'사용자 관리 컨트롤러'** 임
```java
    /**
     * 사용자 관리 컨트롤러
     */
    @Slf4j
    @RestController
    public class UserController {
        ...
    }
```

## 2. Method(메서드)의 논리명 추출 규칙
- **논리명(logical name) 위치**: Method 선언 위치의 상단에 코멘트로 기술되어 있음. '/**\n * {local name}\n */'의 형태로 기술되어 있음
- **논리명 저장**: DB(neo4j)의 **Method 노드의 'logical_name' 속성에 저장**한다
- 예시 코드: 예시코드의 changePassword() Method의의 logical name(논리명)은 **'비밀번호 변경'** 임
```java
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
```

## 3. MyBatis Mapper XML의 논리명 추출 규칙
- **논리명(logical name) 위치**: `<mapper>` 태그의 `namespace` 속성 위의 주석
- **논리명 저장**: DB(neo4j)의 **MyBatisMapper 노드의 'logical_name' 속성에 저장**한다
- **형식**: `<!-- {logical_name} -->`
- 예시 코드: 예시코드의 UserMapper의 logical name(논리명)은 **'사용자 데이터 매퍼'** 임
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<!-- 사용자 데이터 매퍼 -->
<mapper namespace="com.carcare.domain.user.mapper.UserMapper">
    ...
</mapper>
```

## 4. SQL 문의 논리명 추출 규칙
- **논리명(logical name) 위치**: 각 SQL 태그(`<select>`, `<insert>`, `<update>`, `<delete>`) 위의 주석
- **논리명 저장**: DB(neo4j)의 **SqlStatement 노드의 'logical_name' 속성에 저장**한다
- **형식**: `<!-- {logical_name} -->`
- 예시 코드: 예시코드의 findUserById SQL의 logical name(논리명)은 **'사용자 ID로 조회'** 임
```xml
    <!-- 사용자 ID로 조회 -->
    <select id="findUserById" parameterType="Long" resultType="User">
        SELECT 
            user_id,
            username,
            email,
            created_at
        FROM users 
        WHERE user_id = #{userId}
    </select>
```
