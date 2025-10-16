# Python 가상환경 사용 가이드

## 🎯 가상환경 활성화

### ✅ 올바른 방법

```bash
# 방법 1: source 명령어 사용 (권장)
source runvenv.sh

# 방법 2: . (dot) 명령어 사용
. runvenv.sh

# 방법 3: 직접 활성화
source .venv/bin/activate
```

### ❌ 잘못된 방법

```bash
# 이렇게 하면 안 됩니다! (서브셸에서 실행되어 효과 없음)
bash runvenv.sh
./runvenv.sh
sh runvenv.sh
```

## 📋 주요 명령어

### 가상환경 활성화
```bash
source runvenv.sh
```

### 가상환경 비활성화
```bash
deactivate
```

### 가상환경 상태 확인
```bash
echo $VIRTUAL_ENV
which python
python --version
```

### 패키지 설치
```bash
# 가상환경 활성화 후
pip install -r requirements.txt
```

## 🔍 문제 해결

### 가상환경이 없는 경우
```bash
python3 -m venv .venv
source runvenv.sh
pip install -r requirements.txt
```

### 가상환경이 손상된 경우
```bash
rm -rf .venv
python3 -m venv .venv
source runvenv.sh
pip install -r requirements.txt
```

## 💡 왜 source를 사용해야 하나?

- `source` 또는 `.` 명령어는 **현재 셸**에서 스크립트를 실행합니다
- `bash runvenv.sh`는 **서브셸**에서 실행되어 환경 변수가 현재 셸에 적용되지 않습니다
- 가상환경 활성화는 환경 변수(`VIRTUAL_ENV`, `PATH`)를 변경하므로 반드시 현재 셸에서 실행해야 합니다

## 🎨 VSCode 통합

VSCode에서 Python 인터프리터를 선택하면 자동으로 가상환경이 활성화됩니다:

1. `Ctrl+Shift+P` (또는 `Cmd+Shift+P`)
2. "Python: Select Interpreter" 입력
3. `.venv/bin/python` 선택

## 📝 참고

- 가상환경 경로: `/workspace/lang-java-springboot/.venv`
- Python 버전: Python 3.x
- 패키지 목록: `requirements.txt`
