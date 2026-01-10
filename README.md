# 키즈노트 앨범 다운로더

키즈노트에서 아이의 앨범 사진과 동영상을 일괄 다운로드하는 CLI 도구입니다.

## 특징

- 브라우저 자동화를 통한 간편한 로그인
- 여러 아이 지원 (자동 감지, 이름 자동 추출)
- 비동기 다운로드로 빠른 속도 (최대 20개 동시 다운로드)
- 날짜별 폴더 자동 정리 (`YYYY/MM/DD`)
- 이미 다운로드된 파일 자동 스킵
- 전역 설정 저장 (`~/.config/kidsnote/`)

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
- **완료 후 브라우저를 닫으면** 세션과 아이 정보(이름 포함)가 저장됩니다

### 2. 다운로드 경로 설정

```bash
uv run main.py config
```

- 현재 설정을 확인하고 다운로드 경로를 설정합니다
- 기본값: `~/Pictures/kidsnote`

```bash
# 설정만 확인
uv run main.py config --show

# 직접 경로 지정
uv run main.py config --download-dir ~/Downloads/kidsnote
```

### 3. 아이 목록 확인

```bash
uv run main.py list
```

저장된 아이 목록과 상태를 확인합니다:
```
저장된 아이 목록 (2명):

  [0] 홍길동 (child=1234567) - 앨범 150개, 미디어 5000개
  [1] 홍길순 (child=2345678) - 앨범 80개, 미디어 2500개
```

### 4. 앨범 목록 가져오기

```bash
uv run main.py fetch
```

기본적으로 모든 아이의 앨범을 가져옵니다.

```bash
# 특정 아이만
uv run main.py fetch --index 0
```

### 5. 다운로드

```bash
uv run main.py download
```

기본적으로 모든 아이의 앨범을 설정된 경로에 다운로드합니다.

옵션:
- `-n, --index`: 특정 아이만 지정
- `-o, --output`: 저장 폴더 (미지정 시 설정값 사용)
- `-t, --timeout`: 파일당 타임아웃 초 (기본: 60)
- `-c, --concurrent`: 동시 다운로드 수 (기본: 20)
- `--dry-run`: 다운로드 없이 파일 목록만 출력

```bash
# 모든 아이 다운로드 (기본)
uv run main.py download

# 특정 아이만
uv run main.py download --index 0

# 다른 폴더에 저장 (일회성)
uv run main.py download --output ~/Downloads/kidsnote

# 파일 목록만 확인
uv run main.py download --dry-run
```

## 전체 워크플로우

```bash
# 1. 로그인 (최초 1회 또는 세션 만료 시)
uv run main.py login

# 2. 다운로드 경로 설정
uv run main.py config

# 3. 아이 목록 확인
uv run main.py list

# 4. 앨범 목록 가져오기
uv run main.py fetch

# 5. 다운로드
uv run main.py download
```

## 폴더 구조

### 전역 설정 (`~/.config/kidsnote/`)

```
~/.config/kidsnote/
├── config.json               # 전역 설정 (다운로드 경로, 아이 정보)
├── session.json              # 로그인 세션 (쿠키)
├── download.log              # 다운로드 로그
└── children/
    ├── 1234567/              # 첫째 아이 (child_id)
    │   └── list.json         # 앨범 목록
    └── 2345678/              # 둘째 아이
        └── list.json
```

### 다운로드 폴더 (설정된 경로)

```
~/Pictures/kidsnote/          # 또는 설정한 경로
├── 홍길동/                   # 아이 이름 (자동 추출)
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
└── 2345678/                  # 이름 추출 실패 시 child_id
    └── ...
```

## config.json 형식

```json
{
  "download_dir": "/Users/username/Pictures/kidsnote",
  "children": [
    {
      "child_id": 1234567,
      "center": 12345,
      "cls": 123456,
      "name": "홍길동"
    }
  ]
}
```

## 문제 해결

### 로그인 세션이 만료됨

```bash
uv run main.py login
```

### 아이 정보가 감지되지 않음

로그인 후 반드시 **앨범 페이지** (`/service/album`)를 방문해야 합니다.

### 다운로드 경로가 없음

```bash
uv run main.py config
```

### 다운로드가 느림

동시 다운로드 수를 조정해보세요:

```bash
uv run main.py download --concurrent 10
```

### 이미 다운로드된 파일

같은 경로에 파일이 존재하면 자동으로 스킵됩니다. 재다운로드하려면 해당 파일을 삭제하세요.

## 라이선스

MIT
