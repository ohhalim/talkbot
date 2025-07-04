# Data AI Assistant MVP

물어보세 스타일의 데이터 AI 어시스턴트 MVP 구현

## 🎯 프로젝트 개요

자연어로 데이터베이스에 질의하고 답변을 받을 수 있는 AI 어시스턴트입니다. 사용자가 "고객 목록을 보여주세요"와 같이 자연어로 질문하면, AI가 이를 SQL로 변환하여 데이터베이스에서 결과를 가져와 사용자에게 제공합니다.

## 🏗 아키텍처

```
[사용자] → [웹 인터페이스] → [API Gateway] → [Question Router] 
                                                      ↓
[Vector DB] ← [RAG Engine] ← [LLM Service] ← [Query Processor]
     ↓              ↓
[Embedding]    [SQL Executor] → [Database]
```

## 🛠 기술 스택

### 백엔드
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (메인), ChromaDB (벡터)
- **LLM**: OpenAI GPT-4 API
- **Embedding**: OpenAI text-embedding-ada-002
- **Cache**: Redis
- **AI Framework**: LangChain, LangGraph, LangServe

### 프론트엔드
- **Framework**: React + TypeScript
- **UI Library**: Material-UI
- **State Management**: Zustand
- **HTTP Client**: Axios

### 인프라
- **Containerization**: Docker + Docker Compose
- **Development**: Hot reload 지원

## 🚀 빠른 시작

### 1. 저장소 클론 및 환경 설정
```bash
git clone <repository-url>
cd data-ai-assistant
cp .env.example .env
# .env 파일에 OpenAI API 키 설정
```

### 2. Docker로 실행 (권장)
```bash
# 개발 환경 시작
make dev-up

# 또는
docker-compose -f docker-compose.dev.yml up -d
```

### 3. 애플리케이션 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **LangServe 엔드포인트**:
  - LangGraph 에이전트: http://localhost:8000/agent
  - RAG 체인: http://localhost:8000/rag
  - SQL 체인: http://localhost:8000/sql
  - 채팅 체인: http://localhost:8000/chat

### 4. 로그인 정보 (MVP 테스트용)
- **사용자명**: admin
- **비밀번호**: password

## 📋 주요 기능

### 1. 🤖 다중 AI 엔진 지원
- **LangGraph 에이전트**: 스마트한 단계별 추론과 도구 사용
- **LangChain SQL**: 강력한 SQL 체인 기반 처리  
- **기본 엔진**: 빠른 응답과 간단한 질의 처리
- 실시간 엔진 선택 및 비교

### 2. 🗣 자연어 질의
- 자연어로 데이터베이스 질의
- 실시간 채팅 인터페이스
- 질의 히스토리 관리
- 중간 처리 단계 시각화

### 3. 🔄 Text-to-SQL 변환
- GPT-4 기반 자연어 → SQL 변환
- SQL 쿼리 검증 및 안전성 검사
- 읽기 전용 쿼리만 허용
- LangGraph를 통한 스마트 쿼리 생성

### 4. 🧠 RAG (Retrieval-Augmented Generation)
- 테이블 스키마 정보 벡터 검색
- 비즈니스 용어 사전 활용
- SQL 예시 패턴 학습
- LangChain 기반 고급 문서 검색

### 5. 📊 결과 시각화
- 테이블 형태 결과 표시
- 생성된 SQL 쿼리 표시
- 신뢰도 점수 표시
- 처리 단계별 상세 정보
- 오류 메시지 처리

### 6. 🔗 LangServe API
- RESTful API 엔드포인트
- 스트리밍 응답 지원
- 배치 처리 지원
- 타입 안전성 보장

### 7. 🔒 보안 기능
- JWT 기반 인증
- SQL 인젝션 방지
- 안전한 쿼리만 실행

## 💡 사용 예시

### 샘플 질문들
```
1. "모든 고객 목록을 보여주세요"
   → SELECT * FROM customers ORDER BY created_at DESC;

2. "총 주문 금액이 가장 높은 고객은 누구인가요?"
   → 고객별 총 주문 금액을 계산하여 최상위 고객 반환

3. "카테고리별 제품 수를 알려주세요"
   → SELECT category, COUNT(*) FROM products GROUP BY category;

4. "재고가 부족한 제품을 찾아주세요"
   → SELECT * FROM products WHERE stock_quantity < 10;
```

## 🔧 개발 명령어

```bash
# 도움말 확인
make help

# 개발 환경 관리
make dev-up        # 개발 환경 시작
make dev-down      # 개발 환경 중지
make dev-logs      # 로그 확인
make clean         # 환경 정리

# 데이터베이스 관리
make init-db       # 데이터베이스 초기화

# 로컬 개발
make install-backend   # 백엔드 의존성 설치
make install-frontend  # 프론트엔드 의존성 설치
```

## 📂 프로젝트 구조

```
data-ai-assistant/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── core/           # 설정, 보안, DB
│   │   ├── models/         # 데이터 모델
│   │   ├── services/       # 비즈니스 로직
│   │   ├── api/           # API 엔드포인트
│   │   └── utils/         # 유틸리티
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React 프론트엔드
│   ├── src/
│   │   ├── components/    # 재사용 컴포넌트
│   │   ├── pages/         # 페이지 컴포넌트
│   │   ├── services/      # API 클라이언트
│   │   └── store/         # 상태 관리
│   ├── package.json
│   └── Dockerfile
├── docs/                   # 문서
├── docker-compose.yml     # 프로덕션 설정
├── docker-compose.dev.yml # 개발 설정
├── Makefile              # 개발 명령어
└── README.md
```

## 🎛 환경 변수

```bash
# .env 파일 예시
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/dataai
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your_jwt_secret_key_here
ENVIRONMENT=development
```

## 🐛 문제 해결

### OpenAI API 키 오류
```bash
# .env 파일에 올바른 API 키 설정 확인
cat .env | grep OPENAI_API_KEY
```

### 데이터베이스 연결 오류
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose -f docker-compose.dev.yml logs postgres
```

### 포트 충돌
기본 포트가 사용 중인 경우 docker-compose.dev.yml에서 포트 변경

## 🚀 배포

### Docker Compose 사용
```bash
# 프로덕션 환경 실행
docker-compose up -d
```

### 클라우드 배포
- AWS ECS, GCP Cloud Run, Azure Container Instances 지원
- Kubernetes 매니페스트 파일 추가 예정

## 📈 로드맵

### Phase 1 - MVP 완료 ✅
- [x] 기본 Text-to-SQL 기능
- [x] 웹 인터페이스
- [x] RAG 기반 컨텍스트 검색
- [x] Docker 컨테이너화
- [x] LangChain, LangGraph, LangServe 통합
- [x] 다중 AI 엔진 지원
- [x] 스마트 에이전트 시스템

### Phase 2 - 기능 강화 (예정)
- [ ] 사용자 피드백 시스템
- [ ] 쿼리 결과 캐싱
- [ ] 더 복잡한 SQL 패턴 지원
- [ ] 시각화 차트 추가

### Phase 3 - 운영 최적화 (예정)
- [ ] 성능 모니터링
- [ ] 사용자 권한 관리
- [ ] 다중 데이터베이스 지원
- [ ] API 사용량 제한

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

문제가 발생하면 [Issues](https://github.com/your-org/data-ai-assistant/issues)에 등록해주세요.

---

**주의**: 이것은 MVP 버전입니다. 프로덕션 환경에서 사용하기 전에 추가적인 보안 검토와 테스트가 필요합니다.