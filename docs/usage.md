# 상세 사용법

## 설치

```bash
curl -fsSL https://raw.githubusercontent.com/bestend/kidsnote/main/install.sh | bash
```

수동 설치:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install git+https://github.com/bestend/kidsnote.git
uv tool run --from git+https://github.com/bestend/kidsnote.git playwright install chromium
```

## 기본 흐름

```bash
kd login
kd config
kd list
kd fetch
kd download
```

## 명령어

### `kd login`

- 브라우저를 열고 로그인합니다.
- 로그인 후 아이별 앨범 화면을 한 번씩 방문하면 세션과 아이 정보가 저장됩니다.

### `kd config`

```bash
kd config --show
kd config --download-dir ~/Downloads/kidsnote
```

### `kd list`

저장된 아이 목록과 fetch 상태를 보여줍니다.

### `kd fetch`

```bash
kd fetch
kd fetch --index 0
```

- 아이별로 현재 앨범과 추억 앨범을 모두 확인합니다.
- 중복 항목은 병합해서 `list.json`에 저장합니다.

### `kd download`

```bash
kd download
kd download --index 0
kd download --output ~/Downloads/kidsnote
kd download --dry-run
kd download --concurrent 10
```

옵션:

- `-n, --index`: 특정 아이만 다운로드
- `-o, --output`: 저장 폴더 지정
- `-t, --timeout`: 파일당 타임아웃 초
- `-c, --concurrent`: 최대 동시 다운로드 수
- `--dry-run`: 다운로드 없이 파일 목록만 출력

## 저장 위치

전역 설정:

```text
~/.config/kidsnote/
├── config.json
├── session.json
├── download.log
└── children/
    └── <child_id>/
        └── list.json
```

다운로드 폴더:

```text
~/Pictures/kidsnote/
└── <아이이름 또는 child_id>/
    └── YYYY/MM/DD/
```

## 문제 해결

### 세션이 만료된 경우

```bash
kd login
```

### 아이 정보가 안 잡히는 경우

- 로그인 후 앨범 화면까지 이동해야 합니다.
- 여러 아이가 있으면 각 아이의 앨범을 한 번씩 방문해야 합니다.

### 다운로드 경로를 바꾸고 싶은 경우

```bash
kd config
```

### `kd` 명령어를 찾지 못하는 경우

```bash
export PATH="$HOME/.local/bin:$PATH"
```
