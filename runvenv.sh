#!/bin/bash
# Python 가상환경 활성화 스크립트
# 사용법: source runvenv.sh 또는 . runvenv.sh

if [ ! -d ".venv" ]; then
    echo "❌ 가상환경이 존재하지 않습니다."
    echo "다음 명령어로 가상환경을 생성하세요:"
    echo "  python3 -m venv .venv"
    return 1 2>/dev/null || exit 1
fi

source .venv/bin/activate

if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ 가상환경 활성화 완료: $VIRTUAL_ENV"
    echo "Python: $(which python)"
    echo "비활성화: deactivate"
else
    echo "❌ 가상환경 활성화 실패"
    return 1 2>/dev/null || exit 1
fi
