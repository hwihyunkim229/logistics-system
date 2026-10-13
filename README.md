# Logistics System

사내 물류 업무를 정리하면서 만든 웹 애플리케이션입니다. 입출고와 재고 이력부터 BOM, 생산계획, 부서별 생산 진행 상황까지 한곳에서 관리하는 것을 목표로 합니다.

처음에는 재고 조회와 Excel 업로드 기능으로 시작했고, 실제 업무 흐름에 맞춰 생산 요청, 승인, 검사, 잔량 관리 기능을 추가했습니다. 화면은 FastAPI와 Jinja2로 구성했으며, 별도의 프런트엔드 빌드 과정 없이 실행할 수 있습니다.

## 구현된 기능

- 품목·LOT·창고별 재고 조회 및 입출고 이력 관리
- 제품, 자재, 반제품, 대여 자산 관리
- Excel을 이용한 품목·BOM·생산계획 등록과 결과 다운로드
- 생산계획과 현재고를 기준으로 한 자재 소요량 및 부족 수량 계산
- 구매 입고 → 품질 검사 → 자재 확인 → 생산 → 포장으로 이어지는 작업 흐름
- 부분 승인, 불량, 미처리 수량에 대한 잔량 관리
- 역할과 소속 부서에 따른 화면 조회·수정 권한 설정
- 로그인, 데이터 변경, 주요 화면 접근 기록
- 재고와 생산 현황 대시보드
- 등록된 조회 기능만 호출하도록 제한한 자연어 조회 도우미
- Android 앱을 통한 QR·바코드 스캔, 재고 검색, 입출고 및 원자재 LOT 등록

처리 단계와 수량은 화면뿐 아니라 서버에서도 다시 확인합니다. 예를 들어 이미 완료된 요청을 다시 승인하거나, 남은 수량보다 많은 수량을 처리하는 요청은 저장되지 않습니다.

## 기술 구성

- Python, FastAPI, SQLAlchemy
- Jinja2, JavaScript, CSS
- SQLite(로컬), PostgreSQL(운영 환경)
- Pandas, OpenPyXL
- bcrypt, Passlib, 세션 인증
- Groq API(선택 사항)

주요 코드는 다음과 같이 나뉘어 있습니다.

```text
app/
├─ models/       데이터베이스 모델
├─ routers/      재고, MRP, 관리자 등 일반 화면
├─ services/     조회 및 업무 처리 로직
├─ templates/    Jinja2 템플릿
├─ workflow/     구매·품질·자재·생산 업무 흐름
├─ assistant/    자연어 조회 도구와 라우팅
└─ main.py       애플리케이션 진입점
android-app/      현장 재고 처리를 위한 Android 앱
```

## 로컬에서 실행하기

Python 3.11 이상 환경을 권장합니다.

```bash
git clone https://github.com/hwihyunkim229/logistics-system.git
cd logistics-system
python -m venv .venv
```

가상환경을 활성화합니다.

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

실행 전에 세션 암호화에 사용할 `SECRET_KEY`를 환경변수로 설정합니다.

```powershell
# Windows PowerShell
$env:SECRET_KEY="임의의-긴-문자열"
uvicorn app.main:app --reload
```

```bash
# macOS / Linux
export SECRET_KEY="임의의-긴-문자열"
uvicorn app.main:app --reload
```

서버가 시작되면 [http://127.0.0.1:8000](http://127.0.0.1:8000)에서 접속할 수 있습니다. 별도의 `DATABASE_URL`을 지정하지 않으면 프로젝트 루트에 `local.db`가 생성되고 필요한 테이블도 함께 만들어집니다.

회원가입 화면은 열려 있지 않습니다. 처음 사용할 때는 로컬 데이터베이스에 관리자 계정을 직접 추가해야 하며, 이후 계정은 관리자 화면에서 만들 수 있습니다.

## 선택 환경변수

PostgreSQL을 사용할 때:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
```

자연어 조회 도우미를 사용할 때:

```env
GROQ_API_KEY=your_api_key
```

`GROQ_API_KEY`가 없어도 재고, MRP, 생산 워크플로우 등 나머지 기능은 사용할 수 있습니다.

## Android 앱

`android-app`에는 현장에서 재고를 처리할 수 있는 Android 앱이 들어 있습니다. Kotlin과 Jetpack Compose로 작성했으며, 웹 서버와 별도의 데이터를 사용하지 않고 FastAPI API에 로그인해 같은 재고와 처리 이력을 공유합니다.

앱에서는 다음 작업을 할 수 있습니다.

- 웹 계정으로 로그인하고 로그인 세션 유지
- 품목코드, 품목명, LOT를 이용한 재고 검색
- 카메라로 QR 코드와 바코드 스캔
- 선택한 품목의 입고·출고 처리
- QR 코드에서 읽은 LOT, 검사원, 최초 입고일자를 이용한 원자재 LOT 등록
- 본인이 처리한 최근 입출고 이력 확인

Android Studio에서 `android-app` 폴더를 열거나, 프로젝트 루트에서 Gradle Wrapper로 개발용 APK를 빌드할 수 있습니다.

```powershell
# Windows
cd android-app
.\gradlew.bat assembleDevDebug
```

```bash
# macOS / Linux
cd android-app
./gradlew assembleDevDebug
```

개발용 앱은 로그인 화면에서 테스트 서버 주소를 바꿀 수 있습니다. 휴대전화에서 로컬 서버에 접속하려면 컴퓨터와 같은 네트워크에 연결한 뒤 `http://컴퓨터-IP:포트` 형식으로 입력해야 합니다. 운영용 빌드는 앱에 설정된 배포 서버로 연결되며 서버 주소를 화면에서 변경할 수 없습니다.

앱은 Android 6.0(API 23) 이상을 지원하고, 빌드에는 JDK 17과 Android SDK 35가 필요합니다. 카메라 스캔을 사용하려면 카메라 권한을 허용해야 합니다.

## 테스트

```bash
pytest
```

테스트는 재고 처리, 다중 필터, 대시보드 데이터, 모바일 재고 API 등 주요 기능을 중심으로 작성되어 있습니다.

## 참고

저장소에는 운영 환경의 계정, API 키, 첨부파일, Excel 원본 및 데이터베이스를 포함하지 않습니다. 로컬에서 만든 `.env`, `*.db`, `*.xlsx` 파일도 Git 추적 대상에서 제외됩니다.
