import json
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, parse_qs

import aiohttp
import aiofiles
import typer
from loguru import logger
from playwright.async_api import async_playwright, Request
from tqdm.asyncio import tqdm

logger.add("kidsnote_download.log", rotation="10 MB")

app = typer.Typer(help="키즈노트 앨범 미디어 다운로더")

KIDSNOTE_LOGIN_URL = "https://www.kidsnote.com/login"
KIDSNOTE_ALBUM_API = "https://www.kidsnote.com/api/v1_3/children/{child_id}/albums/"

# 설정 폴더 구조
DATA_DIR = Path(".kidsnote")
SESSION_FILE = DATA_DIR / "session.json"
CONFIG_FILE = DATA_DIR / "config.json"


@dataclass
class ChildConfig:
    child_id: int
    center: int
    cls: int
    name: str = ""

    def to_dict(self) -> dict:
        return {
            "child_id": self.child_id,
            "center": self.center,
            "cls": self.cls,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChildConfig":
        return cls(data["child_id"], data["center"], data["cls"], data.get("name", ""))


@dataclass
class MediaItem:
    filename: str
    url: str
    folder: str

    @property
    def path(self) -> Path:
        return Path(self.folder) / self.filename


@dataclass
class DownloadConfig:
    output_dir: Path
    timeout: int = 60
    max_concurrent: int = 20


def parse_media_items(json_data: dict) -> list[MediaItem]:
    items = []
    for entry in json_data.get("results", []):
        try:
            created_at = datetime.fromisoformat(entry["created"].rstrip("Z"))
        except (ValueError, KeyError):
            continue

        date_str = created_at.strftime("%Y-%m-%d")
        folder = created_at.strftime("%Y/%m/%d")

        for idx, img in enumerate(entry.get("attached_images", [])):
            if url := img.get("original"):
                items.append(MediaItem(f"{date_str}-{idx}.jpg", url, folder))

        if (video := entry.get("attached_video")) and (url := video.get("high")):
            items.append(MediaItem(f"{date_str}.mp4", url, folder))

    return items


class KidsnoteAuth:
    def __init__(self):
        self._cookies: list[dict] = []
        self._child_configs: list[ChildConfig] = []

    async def login_interactive(self) -> tuple[list[dict], list[ChildConfig]]:
        """브라우저를 열어 로그인하고 아이 정보를 자동 감지합니다."""
        logger.info("브라우저를 열어 로그인을 진행합니다...")
        logger.info("로그인 후 아이를 선택하고 앨범 페이지로 이동해주세요.")

        captured_configs: list[ChildConfig] = []

        async def handle_request(request: Request):
            url = request.url
            if "/api/v1_3/children/" in url and "/albums/" in url:
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)

                match = re.search(r"/children/(\d+)/albums/", url)
                if match:
                    child_id = int(match.group(1))
                    center = int(qs.get("center", [0])[0])
                    cls = int(qs.get("cls", [0])[0])

                    config = ChildConfig(child_id, center, cls)
                    if config not in captured_configs:
                        captured_configs.append(config)
                        logger.info(
                            f"아이 정보 감지됨: child={child_id}, center={center}, cls={cls}"
                        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            page.on("request", handle_request)

            await page.goto(KIDSNOTE_LOGIN_URL)

            logger.info(
                "앨범 페이지(/service/album)로 이동하면 자동으로 정보를 저장합니다."
            )
            logger.info("여러 아이가 있다면 각 아이의 앨범을 한 번씩 방문해주세요.")
            logger.info("완료 후 브라우저를 닫으면 저장됩니다.")

            try:
                await page.wait_for_event("close", timeout=600000)
            except Exception:
                pass

            self._cookies = await context.cookies()
            await browser.close()

        self._child_configs = captured_configs
        self._save_session()
        self._save_config()

        return self._cookies, self._child_configs

    def _save_session(self):
        DATA_DIR.mkdir(exist_ok=True)
        SESSION_FILE.write_text(json.dumps(self._cookies, ensure_ascii=False, indent=2))
        logger.info(f"세션 저장됨: {SESSION_FILE}")

    def _save_config(self):
        DATA_DIR.mkdir(exist_ok=True)
        data = [c.to_dict() for c in self._child_configs]
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"아이 설정 저장됨: {CONFIG_FILE} ({len(data)}명)")

    def load_session(self) -> list[dict] | None:
        if not SESSION_FILE.exists():
            return None
        try:
            self._cookies = json.loads(SESSION_FILE.read_text())
            return self._cookies
        except (json.JSONDecodeError, IOError):
            return None

    def load_config(self) -> list[ChildConfig]:
        if not CONFIG_FILE.exists():
            return []
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return [ChildConfig.from_dict(c) for c in data]
        except (json.JSONDecodeError, IOError):
            return []


class KidsnoteClient:
    def __init__(self, cookies: list[dict]):
        self._cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    async def fetch_albums(self, config: ChildConfig, page_size: int = 10000) -> dict:
        url = KIDSNOTE_ALBUM_API.format(child_id=config.child_id)
        params = {
            "tz": "Asia/Seoul",
            "page_size": page_size,
            "center": config.center,
            "cls": config.cls,
            "child": config.child_id,
        }
        headers = {"Cookie": self._cookie_header}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()


class Downloader:
    def __init__(self, config: DownloadConfig, cookies: list[dict] | None = None):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._cookie_header = ""
        if cookies:
            self._cookie_header = "; ".join(
                f"{c['name']}={c['value']}" for c in cookies
            )

    async def download(self, session: aiohttp.ClientSession, item: MediaItem) -> bool:
        filepath = self.config.output_dir / item.path
        if filepath.exists():
            return True

        filepath.parent.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                headers = {"Cookie": self._cookie_header} if self._cookie_header else {}
                async with session.get(
                    item.url, timeout=timeout, headers=headers
                ) as resp:
                    resp.raise_for_status()
                    expected_size = int(resp.headers.get("content-length", 0))

                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            await f.write(chunk)

                    if expected_size > 0 and filepath.stat().st_size != expected_size:
                        filepath.unlink(missing_ok=True)
                        return False
                    return True

            except (asyncio.TimeoutError, aiohttp.ClientError, IOError) as e:
                logger.error(f"다운로드 실패: {item.url} - {e}")
                filepath.unlink(missing_ok=True)
                return False

    async def run(self, items: list[MediaItem]) -> tuple[int, int]:
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrent,
            limit_per_host=10,
        )
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.download(session, item) for item in items]
            results = await tqdm.gather(*tasks, desc="다운로드 중", unit="파일")

        success = sum(results)
        return success, len(results) - success


@app.command()
def login():
    """브라우저를 열어 키즈노트에 로그인하고 아이 정보를 자동 감지합니다."""
    auth = KidsnoteAuth()
    cookies, configs = asyncio.run(auth.login_interactive())

    if not cookies:
        logger.error("로그인 실패")
        raise typer.Exit(1)

    if configs:
        logger.info(f"로그인 완료! {len(configs)}명의 아이 정보가 저장되었습니다.")
        for i, c in enumerate(configs):
            logger.info(f"  [{i}] child={c.child_id}, center={c.center}, cls={c.cls}")
    else:
        logger.warning(
            "아이 정보를 감지하지 못했습니다. 앨범 페이지를 방문했는지 확인하세요."
        )


def get_child_data_dir(child_id: int) -> Path:
    """아이별 데이터 폴더 경로를 반환합니다."""
    return DATA_DIR / "children" / str(child_id)


def get_child_label(config: ChildConfig, index: int) -> str:
    """아이 표시 라벨을 반환합니다."""
    if config.name:
        return f"[{index}] {config.name} (child={config.child_id})"
    return f"[{index}] child={config.child_id}"


@app.command(name="list")
def list_children():
    """저장된 아이 목록을 표시합니다."""
    auth = KidsnoteAuth()
    configs = auth.load_config()

    if not configs:
        logger.warning("저장된 아이 정보가 없습니다. login을 먼저 실행하세요.")
        raise typer.Exit(1)

    typer.echo(f"\n저장된 아이 목록 ({len(configs)}명):\n")
    for i, c in enumerate(configs):
        child_dir = get_child_data_dir(c.child_id)
        list_file = child_dir / "list.json"

        status = ""
        if list_file.exists():
            try:
                data = json.loads(list_file.read_text())
                results = data.get("results", [])
                # 미디어 개수 계산
                media_count = sum(
                    len(r.get("attached_images", []))
                    + (1 if r.get("attached_video") else 0)
                    for r in results
                )
                status = f" - 앨범 {len(results)}개, 미디어 {media_count}개"
            except (json.JSONDecodeError, IOError):
                status = " - list.json 오류"
        else:
            status = " - fetch 필요"

        label = get_child_label(c, i)
        typer.echo(f"  {label}{status}")

    typer.echo(f"\n사용법: uv run python main.py fetch --index <번호>")
    typer.echo(f"        uv run python main.py download --index <번호>")
    typer.echo(f"        또는 --all 옵션으로 모든 아이 처리\n")


@app.command(name="rename")
def rename_child(
    child_index: Annotated[int, typer.Argument(help="아이 인덱스")],
    name: Annotated[str, typer.Argument(help="아이 이름")],
):
    """아이에게 이름을 지정합니다."""
    auth = KidsnoteAuth()
    configs = auth.load_config()

    if not configs:
        logger.error("저장된 아이 정보가 없습니다.")
        raise typer.Exit(1)

    if child_index >= len(configs):
        logger.error(f"잘못된 인덱스입니다. 0~{len(configs) - 1} 사이로 지정하세요.")
        raise typer.Exit(1)

    configs[child_index].name = name

    # 직접 저장
    DATA_DIR.mkdir(exist_ok=True)
    data = [c.to_dict() for c in configs]
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    logger.info(f"아이 [{child_index}]의 이름을 '{name}'으로 설정했습니다.")


def get_album_stats(data: dict) -> str:
    """앨범 데이터에서 통계 문자열을 반환합니다."""
    results = data.get("results", [])
    if not results:
        return "0개"

    media_count = sum(
        len(r.get("attached_images", [])) + (1 if r.get("attached_video") else 0)
        for r in results
    )

    # 날짜 범위 계산
    dates = []
    for r in results:
        try:
            created = r.get("created", "")
            if created:
                dates.append(datetime.fromisoformat(created.rstrip("Z")))
        except ValueError:
            pass

    if dates:
        oldest = min(dates).strftime("%Y-%m-%d")
        newest = max(dates).strftime("%Y-%m-%d")
        return f"앨범 {len(results)}개, 미디어 {media_count}개 ({oldest} ~ {newest})"

    return f"앨범 {len(results)}개, 미디어 {media_count}개"


@app.command()
def fetch(
    child_index: Annotated[
        int, typer.Option("--index", "-n", help="특정 아이 인덱스 (-1: 전체)")
    ] = -1,
):
    """저장된 아이 정보로 앨범 목록을 가져와 JSON으로 저장합니다."""
    auth = KidsnoteAuth()
    cookies = auth.load_session()
    if not cookies:
        logger.error("저장된 세션이 없습니다. 먼저 login 명령어를 실행하세요.")
        raise typer.Exit(1)

    configs = auth.load_config()
    if not configs:
        logger.error("저장된 아이 정보가 없습니다. login 후 앨범 페이지를 방문하세요.")
        raise typer.Exit(1)

    # --index 미지정(-1) 시 전체, 지정 시 해당 아이만
    if child_index == -1:
        targets_with_index = list(enumerate(configs))
    elif child_index < len(configs):
        targets_with_index = [(child_index, configs[child_index])]
    else:
        logger.error(f"잘못된 인덱스입니다. 0~{len(configs) - 1} 사이로 지정하세요.")
        raise typer.Exit(1)

    client = KidsnoteClient(cookies)

    for idx, config in targets_with_index:
        label = get_child_label(config, idx)
        logger.info(f"{label} 앨범 가져오는 중...")

        async def _fetch():
            return await client.fetch_albums(config)

        try:
            data = asyncio.run(_fetch())
            child_dir = get_child_data_dir(config.child_id)
            child_dir.mkdir(parents=True, exist_ok=True)
            output = child_dir / "list.json"
            output.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            logger.info(f"앨범 목록 저장됨: {output} ({get_album_stats(data)})")
        except aiohttp.ClientError as e:
            logger.error(f"API 호출 실패: {e}")
            raise typer.Exit(1)


@app.command()
def download(
    child_index: Annotated[
        int, typer.Option("--index", "-n", help="특정 아이 인덱스 (-1: 전체)")
    ] = -1,
    output_dir: Annotated[
        Path, typer.Option("--output", "-o", help="다운로드 저장 폴더")
    ] = Path("~/Pictures/kidsnote"),
    timeout: Annotated[
        int, typer.Option("--timeout", "-t", help="파일당 타임아웃 (초)")
    ] = 60,
    concurrent: Annotated[
        int, typer.Option("--concurrent", "-c", help="최대 동시 다운로드 수")
    ] = 20,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="다운로드 없이 파일 목록만 출력")
    ] = False,
):
    """앨범 미디어를 다운로드합니다."""
    auth = KidsnoteAuth()
    cookies = auth.load_session()
    configs = auth.load_config()

    if not configs:
        logger.error("저장된 아이 정보가 없습니다. login 후 앨범 페이지를 방문하세요.")
        raise typer.Exit(1)

    # --index 미지정(-1) 시 전체, 지정 시 해당 아이만
    if child_index == -1:
        targets_with_index = list(enumerate(configs))
    elif child_index < len(configs):
        targets_with_index = [(child_index, configs[child_index])]
    else:
        logger.error(f"잘못된 인덱스입니다. 0~{len(configs) - 1} 사이로 지정하세요.")
        raise typer.Exit(1)

    output_base = output_dir.expanduser()
    total_success, total_failed = 0, 0

    for idx, config in targets_with_index:
        label = get_child_label(config, idx)
        child_dir = get_child_data_dir(config.child_id)
        input_file = child_dir / "list.json"

        if not input_file.exists():
            logger.warning(f"{label} list.json이 없습니다. fetch를 먼저 실행하세요.")
            continue

        try:
            with open(input_file, encoding="utf-8") as f:
                items = parse_media_items(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"입력 파일 로드 실패: {e}")
            continue

        if not items:
            logger.warning(f"{label} 다운로드할 파일이 없습니다")
            continue

        logger.info(f"{label} 총 {len(items)}개 파일 발견")

        # 아이별 폴더로 다운로드 (이름이 있으면 이름 사용)
        folder_name = config.name if config.name else str(config.child_id)
        child_output = output_base / folder_name

        if dry_run:
            for item in items:
                typer.echo(f"  {child_output / item.path}")
            continue

        dl_config = DownloadConfig(child_output, timeout, concurrent)

        async def _download():
            dl_config.output_dir.mkdir(parents=True, exist_ok=True)
            return await Downloader(dl_config, cookies).run(items)

        success, failed = asyncio.run(_download())
        total_success += success
        total_failed += failed

        logger.info(f"{label} 완료: {success}개 성공, {failed}개 실패")

    if not dry_run:
        logger.info(f"전체 완료: {total_success}개 성공, {total_failed}개 실패")

    raise typer.Exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    app()
