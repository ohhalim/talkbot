# Data AI Assistant - 시작하기

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd data-ai-assistant

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 OpenAI API 키 설정
```

### 2. Docker로 실행 (권장)

```bash
# 개발 환경 시작
make dev-up

# 또는 docker-compose 직접 사용
docker-compose -f docker-compose.dev.yml up -d
```

### 3. 로컬 개발 환경 설정

#### 백엔드 설정
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 프론트엔드 설정
```bash
cd frontend
npm install
npm start
```

## 📋 사용법

### 1. 로그인
- URL: http://localhost:3000
- 사용자명: `admin`
- 비밀번호: `password`

### 2. 지식 베이스 초기화
로그인 후 자동으로 지식 베이스가 초기화됩니다.

### 3. 질문하기
다음과 같은 질문을 해보세요:
- "모든 고객 목록을 보여주세요"
- "총 주문 금액이 가장 높은 고객은 누구인가요?"
- "카테고리별 제품 수를 알려주세요"
- "재고가 부족한 제품을 찾아주세요"

## 🔧 API 문서

백엔드 서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 주요 기능

### 1. 자연어 질의
사용자가 자연어로 질문하면 AI가 SQL로 변환하여 데이터베이스에서 답변을 찾습니다.

### 2. RAG (Retrieval-Augmented Generation)
- 테이블 스키마 정보
- 비즈니스 용어 사전
- SQL 예시 패턴

### 3. 결과 시각화
- 테이블 형태로 결과 표시
- SQL 쿼리 표시
- 신뢰도 점수 표시

## 🛠 개발 명령어

```bash
# 도움말
make help

# 개발 환경 시작
make dev-up

# 로그 확인
make dev-logs

# 환경 정리
make clean
```

## 🐛 문제 해결

### 1. OpenAI API 키 오류
`.env` 파일에 올바른 OpenAI API 키가 설정되어 있는지 확인하세요.

### 2. 데이터베이스 연결 오류
PostgreSQL 컨테이너가 정상적으로 실행되고 있는지 확인하세요:
```bash
docker-compose -f docker-compose.dev.yml logs postgres
```

### 3. 프론트엔드 빌드 오류
Node.js 의존성을 다시 설치해보세요:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 📈 다음 단계

1. **사용자 피드백 시스템** 구현
2. **쿼리 캐싱** 최적화
3. **더 복잡한 SQL 패턴** 지원
4. **시각화 차트** 추가
5. **사용자 권한 관리** 강화

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 라이선스

MIT License