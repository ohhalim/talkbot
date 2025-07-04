.PHONY: help build up down logs clean dev-up dev-down init-db

help: ## 사용 가능한 명령어 표시
	@echo "사용 가능한 명령어:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Docker 이미지 빌드
	docker-compose build

up: ## 프로덕션 환경 시작
	docker-compose up -d

down: ## 서비스 중지
	docker-compose down

logs: ## 로그 확인
	docker-compose logs -f

clean: ## 모든 컨테이너와 볼륨 제거
	docker-compose down -v
	docker system prune -f

dev-up: ## 개발 환경 시작
	docker-compose -f docker-compose.dev.yml up -d

dev-down: ## 개발 환경 중지
	docker-compose -f docker-compose.dev.yml down

dev-build: ## 개발 환경 빌드
	docker-compose -f docker-compose.dev.yml build

dev-logs: ## 개발 환경 로그 확인
	docker-compose -f docker-compose.dev.yml logs -f

init-db: ## 데이터베이스 초기화
	docker-compose -f docker-compose.dev.yml run --rm init-db

install-backend: ## 백엔드 의존성 설치
	cd backend && pip install -r requirements.txt

install-frontend: ## 프론트엔드 의존성 설치
	cd frontend && npm install

test-backend: ## 백엔드 테스트 실행
	cd backend && python -m pytest

lint-backend: ## 백엔드 코드 린트
	cd backend && python -m flake8 app/

setup-env: ## 환경 변수 파일 설정
	cp .env.example .env
	@echo "Please edit .env file with your configuration"