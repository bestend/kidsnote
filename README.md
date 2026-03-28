# kd - 키즈노트 앨범 다운로더

키즈노트에서 아이의 앨범 사진과 동영상을 일괄 다운로드하는 CLI 도구입니다.

## 설치

```bash
curl -fsSL https://raw.githubusercontent.com/bestend/kidsnote/main/install.sh | bash
```

## 핵심 흐름

```bash
kd login
kd config
kd list
kd fetch
kd download
```

- `kd login`: 로그인하고 아이 정보를 저장
- `kd fetch`: 현재 앨범과 추억 앨범을 함께 가져와 병합
- `kd download`: 날짜별 폴더로 미디어 다운로드

상세 사용법, 옵션, 저장 구조, 문제 해결은 [docs/usage.md](/Users/bestend/tech/kidsnote/docs/usage.md)를 참고하세요.

## License

MIT
