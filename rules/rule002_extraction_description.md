# Description Extraction Rules for Objects(Classe, Method)

## 1. Class(클래스)의 description 추출 규칙
- **description 위치**: Class 선언 위치의 상단에 **@Tag** annotation의 **description**의 문자열 값으로 기술되어 있음. 
- **description 값 저장**: DB(neo4j)의 **Class 노드의 'description' 속성에 저장**한다
- description 추출에 실패한 경우는 빈문자열("")을 리턴한다
- 예시 코드: 예시코드의 UserController 클래스의 description은 **'사용자 관리 API'** 임
```java
@Tag(name = "User", description = "사용자 관리 API")
public class UserController {
    /**
	 * 사용자 관리 서비스 클래스 변수
	 */
	@Autowired
    private final UserService userService;
    ...
}
```

## 2. Method(메서드)의 description 추출 규칙
- **description 위치**: Method 선언 위치의 상단에 **@Operation** annotation의 **description**의 문자열 값으로 기술되어 있음. 
- **description 값 저장**: DB(neo4j)의 **Method 노드의 'description' 속성에 저장**한다
- description 추출에 실패한 경우는 빈문자열("")을 리턴한다
- 예시 코드: 예시코드의 getMyProfile() Method의의 description은 **'현재 로그인한 사용자의 프로필 정보를 조회합니다.'** 임
```java
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
```


## 3. Class와 Method 외 노드의의 description은 빈문자열("")로 저장한다. 