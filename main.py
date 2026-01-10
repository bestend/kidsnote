import json
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiohttp
import aiofiles
import typer
from loguru import logger
from tqdm.asyncio import tqdm

logger.add("kidsnote_download.log", rotation="10 MB")

app = typer.Typer(help="키즈노트 앨범 미디어 다운로더")


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


class Downloader:
    def __init__(self, config: DownloadConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def download(self, session: aiohttp.ClientSession, item: MediaItem) -> bool:
        filepath = self.config.output_dir / item.path
        if filepath.exists():
            return True

        filepath.parent.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with session.get(item.url, timeout=timeout) as resp:
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


async def async_main(items: list[MediaItem], config: DownloadConfig) -> tuple[int, int]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    return await Downloader(config).run(items)


@app.command()
def download(
    input_file: Annotated[
        Path, typer.Option("--input", "-i", help="입력 JSON 파일 경로")
    ] = Path("list.json"),
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
    output_path = output_dir.expanduser()

    try:
        with open(input_file, encoding="utf-8") as f:
            items = parse_media_items(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"입력 파일 로드 실패: {e}")
        raise typer.Exit(1)

    if not items:
        logger.warning("다운로드할 파일이 없습니다")
        raise typer.Exit(0)

    logger.info(f"총 {len(items)}개 파일 발견")

    if dry_run:
        for item in items:
            typer.echo(f"  {output_path / item.path}")
        raise typer.Exit(0)

    config = DownloadConfig(output_path, timeout, concurrent)
    success, failed = asyncio.run(async_main(items, config))

    logger.info(f"완료: {success}개 성공, {failed}개 실패")
    raise typer.Exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    app()
