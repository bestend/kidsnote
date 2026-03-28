# kd - 키즈노트 앨범 다운로더

키즈노트 앨범 사진과 동영상을 한 번에 내려받는 CLI입니다.

## 설치

```bash
curl -fsSL https://raw.githubusercontent.com/bestend/kidsnote/main/install.sh | bash
```

## 사용 순서

```bash
kd login
kd config
kd list
kd fetch
kd download
```

### `kd login`

브라우저가 열리면 로그인한 뒤 아이별 앨범 화면을 한 번씩 열어 주세요.
브라우저를 닫으면 세션과 아이 정보가 저장됩니다.

### `kd config`

다운로드 폴더를 정합니다.

```bash
kd config
kd config --show
kd config --download-dir ~/Downloads/kidsnote
```

### `kd list`

저장된 아이 목록을 확인합니다.

```bash
kd list
```

### `kd fetch`

현재 앨범과 추억 앨범을 같이 가져옵니다.

```bash
kd fetch
kd fetch --index 0
```

### `kd download`

가져온 파일을 날짜별 폴더로 저장합니다.

```bash
kd download
kd download --index 0
kd download --output ~/Downloads/kidsnote
kd download --dry-run
```

## 저장 위치

설정과 세션:

```text
~/.config/kidsnote/
```

다운로드 기본 경로:

```text
~/Pictures/kidsnote
```

## 문제 있을 때

- 세션이 만료되면 `kd login`을 다시 실행하세요.
- 아이가 안 보이면 로그인 후 아이별 앨범 화면까지 들어가야 합니다.
- 다운로드 폴더를 바꾸려면 `kd config`를 실행하세요.

## License

MIT
