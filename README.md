# Logistics System

물류·재고·생산 업무를 하나의 데이터 흐름으로 연결한 통합 업무 관리 시스템입니다.

Excel과 개별 자료로 분산되기 쉬운 입출고, 재고, BOM, 생산계획, 승인, 검사, 불량 및 잔량 정보를 관계형 데이터로 관리합니다. 화면에서 버튼만 제한하는 방식이 아니라, 서버에서 현재 업무 단계와 처리 수량을 다시 검증해 데이터 정합성을 유지하도록 설계했습니다.

> 개인 프로젝트로 기획, 데이터 모델링, 백엔드, 서버 렌더링 화면 및 배포 구성을 직접 구현했습니다.

## 주요 기능

### 상태 기반 생산 워크플로우

- 구매 입고부터 품질, 자재, 생산, 포장 및 최종 확인까지 부서별 업무 흐름 관리
- 현재 단계와 담당 조직을 기준으로 요청·승인·검사·반려·완료 처리 제한
- 부분 승인, 불량 및 미처리 수량을 잔량 데이터로 분리
- 업무번호, 품목코드, LOT 기준 처리 이력 추적
- 단계 변경 시 다음 담당 조직 알림 생성
- 검사 성적서 등 첨부파일 등록·다운로드·삭제

### BOM·생산계획 기반 MRP

- BOM, 생산계획, 자재 마스터 Excel 업로드 및 정규화
- 생산계획과 현재고를 결합한 자재별 소요량·부족 수량 계산
- 기간, 품목 및 부족 여부별 결과 조회
- 주차별 소요량과 부족 품목 대시보드
- MOQ와 비고를 포함한 구매 검토 자료 생성

### 재고·이력 관리

- 제품, 자재, 반제품 및 대여 자산의 현재고 관리
- 입고, 출고, 이동 및 수량 조정 이력 저장
- 품목코드, LOT, REV, 창고, 등급 및 기간별 검색
- 선택 항목 일괄 처리와 Excel 업로드·다운로드
- 기간별 변동과 품목별 현황 대시보드

### 인증·접근제어

- bcrypt 기반 비밀번호 해싱과 세션 로그인
- 관리자, 일반 사용자, 조회 전용 사용자 역할 구분
- 구매, 품질, 자재, 생산 등 소속 조직별 변경 권한 제한
- 미사용 세션 만료 및 계정 유효성 재검증
- 로그인과 주요 데이터 변경 활동 기록

### AI Assistant

- 자연어 질문을 허용된 조회 도구와 인자로 변환
- LLM의 직접 SQL 실행 차단
- 서버 조회 함수에서 사용자 권한과 입력값 재검증
- Groq API와 Llama 3.3 70B 모델 연동

## 시스템 구조

```mermaid
flowchart TD
    A["Jinja2 · HTML · CSS · JavaScript"] --> B["FastAPI Router<br/>인증 · 입력 파싱 · 요청 처리"]
    B --> C["Domain Service<br/>재고 · MRP · Workflow · 검사 · 알림"]
    C --> D["SQLAlchemy ORM<br/>트랜잭션 · 변경 이력"]
    D --> E["SQLite (로컬) / PostgreSQL (운영)"]
    B --> F["AI Tool Router"]
    F --> C
```

모든 데이터 변경은 서버의 업무 규칙 검증과 권한 확인을 거친 뒤 저장됩니다. AI Assistant 역시 데이터베이스에 직접 접근하지 않고 등록된 조회 도구만 선택합니다.

## 기술 스택

| 영역 | 기술 | 활용 |
|---|---|---|
| Backend | Python, FastAPI | 라우팅, 인증, 업무 처리 및 서버 검증 |
| ORM / DB | SQLAlchemy, SQLite, PostgreSQL | 관계형 모델, 트랜잭션 및 이력 관리 |
| Frontend | Jinja2, JavaScript, CSS | 서버 렌더링 업무 화면과 사용자 인터랙션 |
| Data | Pandas, OpenPyXL | Excel 정규화, 검증 및 결과 파일 생성 |
| Security | Session, bcrypt, Passlib | 인증, 세션 및 역할·조직별 권한 관리 |
| AI | Groq, Llama 3.3 70B | 질문 해석과 허용된 조회 도구 선택 |

## 프로젝트 구조

```text
app/
├─ ai/                 # LLM 클라이언트와 응답 처리
├─ assistant/          # 도구 등록, 라우팅 및 조회 서비스
├─ models/             # 재고, BOM, MRP, 사용자 도메인 모델
├─ routers/            # 인증, 재고, MRP, 관리자 화면 라우터
├─ services/           # 업무 규칙과 서비스 로직
├─ templates/          # Jinja2 화면 템플릿
├─ workflow/           # 부서별 생산 워크플로우 도메인
└─ main.py             # 애플리케이션 진입점
```

## 로컬 실행

### 1. 저장소 복제 및 가상환경 생성

```bash
git clone https://github.com/hwihyunkim229/logistics-system.git
cd logistics-system
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt python-dotenv
```

### 3. 환경변수 설정

필수 환경변수:

```env
SECRET_KEY=충분히-긴-임의의-문자열
```

선택 환경변수:

```env
# 미설정 시 프로젝트 루트에 local.db를 생성합니다.
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME

# AI Assistant를 사용할 때만 설정합니다.
GROQ_API_KEY=your_api_key
```

### 4. 서버 실행

```bash
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`으로 접속합니다. 애플리케이션 시작 시 필요한 데이터베이스 테이블이 자동 생성됩니다.

> 보안을 위해 실제 운영 DB와 계정 데이터는 저장소에 포함하지 않았습니다. 로그인 기능을 시험하려면 로컬 DB에 관리자 계정을 별도로 생성해야 합니다.

## 설계 포인트

- **수량 정합성:** 승인·검사·출고 시 현재 수량과 요청 수량을 서버에서 비교합니다.
- **상태 무결성:** 현재 단계에서 허용된 처리만 실행해 단계 건너뛰기와 중복 처리를 방지합니다.
- **추적성:** 현재고와 변경 이력을 분리해 결과뿐 아니라 변경 원인도 확인할 수 있습니다.
- **권한 최소화:** 역할과 소속 조직을 함께 확인해 조회·수정 범위를 구분합니다.
- **AI 격리:** LLM은 SQL이 아닌 허용된 도구와 인자만 선택합니다.

## 향후 개선 계획

- pytest 기반 단위·통합·워크플로우 회귀 테스트 확충
- Alembic을 이용한 데이터베이스 마이그레이션 체계화
- Docker 및 CI/CD 기반 배포 자동화
- 비대해진 Router를 도메인 서비스 단위로 분리
- 운영 지표와 사용자 피드백을 활용한 UX 개선

## 개인정보 및 데이터 안내

이 저장소에는 실제 사용자 계정, 운영 데이터, 비밀번호, API 키 및 로컬 데이터베이스가 포함되지 않습니다. 공개 저장소에서 사용하는 데이터는 반드시 가상의 샘플 데이터로 구성해야 합니다.
