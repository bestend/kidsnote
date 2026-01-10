# 키즈노트 앨범 다운로더

키즈노트에서 아이의 앨범 사진과 동영상을 일괄 다운로드하는 CLI 도구입니다.

## 특징

- 브라우저 자동화를 통한 간편한 로그인
- 여러 아이 지원 (자동 감지, 아이별 폴더 분리)
- 비동기 다운로드로 빠른 속도 (최대 20개 동시 다운로드)
- 날짜별 폴더 자동 정리 (`YYYY/MM/DD`)
- 이미 다운로드된 파일 자동 스킵

## 설치

```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 클론
git clone https://github.com/bestend/kidsnote.git
cd kidsnote

# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

## 사용법

### 1. 로그인

```bash
uv run main.py login
```

- 브라우저가 열리고 키즈노트 로그인 페이지로 이동합니다
- 로그인 후 **앨범 페이지**로 이동해주세요
- 여러 아이가 있다면 각 아이의 앨범을 한 번씩 방문해주세요
- **완료 후 브라우저를 닫으면** 세션과 아이 정보가 저장됩니다

### 2. 아이 목록 확인

```bash
uv run main.py list
```

저장된 아이 목록과 상태를 확인합니다:
```
저장된 아이 목록 (2명):

  [0] child=3354912 - fetch 필요
  [1] child=3354913 - 앨범 150개
```

### 3. 아이 이름 지정 (선택)

```bash
uv run main.py rename 0 "첫째"
uv run main.py rename 1 "둘째"
```

이름을 지정하면 다운로드 폴더에 이름이 사용됩니다:
- 이름 지정 전: `~/Pictures/kidsnote/3354912/`
- 이름 지정 후: `~/Pictures/kidsnote/첫째/`

### 4. 앨범 목록 가져오기

```bash
uv run main.py fetch
```

기본적으로 모든 아이의 앨범을 가져옵니다.

옵션:
- `-n, --index`: 특정 아이만 지정

```bash
# 모든 아이의 앨범 가져오기 (기본)
uv run main.py fetch

# 첫 번째 아이만
uv run main.py fetch --index 0
```

### 5. 다운로드

```bash
uv run main.py download
```

기본적으로 모든 아이의 앨범을 다운로드합니다.

옵션:
- `-n, --index`: 특정 아이만 지정
- `-o, --output`: 저장 폴더 (기본: `~/Pictures/kidsnote`)
- `-t, --timeout`: 파일당 타임아웃 초 (기본: 60)
- `-c, --concurrent`: 동시 다운로드 수 (기본: 20)
- `--dry-run`: 다운로드 없이 파일 목록만 출력

```bash
# 모든 아이 다운로드 (기본)
uv run main.py download

# 특정 아이만
uv run main.py download --index 0

# 다른 폴더에 저장
uv run main.py download --output ~/Downloads/kidsnote

# 파일 목록만 확인
uv run main.py download --dry-run
```

## 전체 워크플로우

```bash
# 1. 로그인 (최초 1회 또는 세션 만료 시)
uv run main.py login

# 2. 아이 목록 확인 및 이름 지정
uv run main.py list
uv run main.py rename 0 "첫째"

# 3. 앨범 목록 가져오기 (모든 아이)
uv run main.py fetch

# 4. 다운로드 (모든 아이)
uv run main.py download
```

## 폴더 구조

### 프로젝트 데이터 (`.kidsnote/`)

```
.kidsnote/
├── session.json              # 로그인 세션 (쿠키)
├── config.json               # 아이 정보 목록
└── children/
    ├── 3354912/              # 첫째 아이 (child_id)
    │   └── list.json         # 앨범 목록
    └── 3354913/              # 둘째 아이
        └── list.json
```

### 다운로드 폴더 (`~/Pictures/kidsnote/`)

```
~/Pictures/kidsnote/
├── 첫째/                     # 이름 지정한 경우
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── 15/
│   │   │   │   ├── 2024-01-15-0.jpg
│   │   │   │   ├── 2024-01-15-1.jpg
│   │   │   │   └── 2024-01-15.mp4
│   │   │   └── 20/
│   │   │       └── 2024-01-20-0.jpg
│   │   └── 02/
│   │       └── ...
│   └── 2023/
│       └── ...
└── 3354913/                  # 이름 미지정 시 child_id
    └── ...
```

## 추가 개선 기능 (TODO)

- [ ] `sync` 명령어: login + fetch + download 한 번에 실행
- [ ] 세션 만료 자동 감지 및 재로그인 프롬프트
- [ ] 아이 이름 자동 추출 (현재는 ID만 저장)
- [ ] 특정 날짜 범위만 다운로드 (`--from`, `--to` 옵션)
- [ ] 사진/동영상 필터링 (`--only-photo`, `--only-video`)
- [ ] 다운로드 재시도 옵션 (`--retry`)
- [ ] 진행 상황 저장 및 이어받기
- [ ] Docker 지원

## 문제 해결

### 로그인 세션이 만료됨

```bash
# 다시 로그인
uv run main.py login
```

### 아이 정보가 감지되지 않음

로그인 후 반드시 **앨범 페이지** (`/service/album`)를 방문해야 합니다.

### 다운로드가 느림

동시 다운로드 수를 조정해보세요:

```bash
uv run main.py download --concurrent 10
```

### 이미 다운로드된 파일

같은 경로에 파일이 존재하면 자동으로 스킵됩니다. 재다운로드하려면 해당 파일을 삭제하세요.

## 라이선스

MIT
