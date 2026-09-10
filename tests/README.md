# 조회 필터·활동 로그·로그인 UI 검증

프로젝트 루트에서 가상환경 Python으로 실행합니다. 테스트는 메모리 SQLite DB만 사용합니다.

```text
python -m unittest discover -s tests -p "test_*.py" -v
python tests/render_multi_filter_fixtures.py
node tests/multi_filter_browser.cjs
node tests/sidebar_login_browser.cjs
node tests/dashboard_products_browser.cjs
```

브라우저 검증에는 Playwright와 Microsoft Edge가 필요합니다. Playwright 모듈 경로를 두 번째 명령행 인자로 지정하거나 `PLAYWRIGHT_MODULE` 환경변수로 설정할 수 있습니다. 브라우저 채널은 `PLAYWRIGHT_CHANNEL`로 변경할 수 있습니다. 화면과 스크린샷은 `work/multi-filter/`에 저장됩니다. 네트워크 요청은 테스트 화면과 로컬 정적 파일로 대체합니다.

대시보드 검증용 화면은 `test_dashboard_products.py` 실행 시 메모리 DB의 가상 제품 분류로 생성됩니다. 브라우저 검증에서는 차트 라이브러리를 테스트 대역으로 대체해 전달된 제품별 데이터와 필터 옵션을 확인합니다.
