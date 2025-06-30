import asyncio
import logging
import re
import shlex
import subprocess
from typing import Optional, Tuple

from .exceptions import YtDlpError
from .ffmpeg import cleanup_commands
from .types.raw import VideoParameters

py_logger = logging.getLogger('pytgcalls')


class YtDlp:
    YOUTUBE_REGX = re.compile(
        r'^((?:https?:)?//)?((?:www|m)\.)?'
        r'(youtube(-nocookie)?\.com|youtu\.be)'
        r'(/(?:[\w\-]+\?v=|embed/|live/|v/)?)'
        r'([\w\-]+)(\S+)?$'
    )

    @staticmethod
    def is_valid(link: str) -> bool:
        return bool(YtDlp.YOUTUBE_REGX.match(link))

    @staticmethod
    async def extract(
        link: Optional[str],
        video_parameters: VideoParameters,
        add_commands: Optional[str] = None,
        use_cookies: bool = True,  # default aktifkan cookies
        cookies_path: str = 'storage/cookies/cookies.txt',
    ) -> Tuple[Optional[str], Optional[str]]:
        if not link:
            return None, None

        commands = [
            'yt-dlp',
            '-g',
            '-f',
            "bestvideo[vcodec~='(vp09|avc1)']+m4a/best",
            '-S',
            f"res:{min(video_parameters.width, video_parameters.height)}",
            '--no-warnings',
        ]

        # Tambahkan file cookies jika diset untuk digunakan
        if use_cookies:
            commands += ['--cookies', cookies_path]

        # Tambahkan perintah tambahan dari argumen
        if add_commands:
            commands += await cleanup_commands(
                shlex.split(add_commands),
                'yt-dlp',
                ['-f', '-g', '--no-warnings'],
            )

        commands.append(link)

        py_logger.debug(f'Running yt-dlp with command: {" ".join(commands)}')

        loop = asyncio.get_running_loop()
        try:
            proc_res = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ['yt-dlp', '-g', '-f', 'bestaudio', '--no-warnings', '--cookies', 'storage/cookies/cookies.txt', url],
                    commands,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=20,
                ),
            )

            if proc_res.returncode != 0:
                raise YtDlpError(f"yt-dlp error: {proc_res.stderr.strip()}")

            data = proc_res.stdout.strip().split('\n')
            if data:
                return data[0], data[1] if len(data) >= 2 else data[0]
            else:
                raise YtDlpError('No video URLs found in yt-dlp output')

        except FileNotFoundError:
            raise YtDlpError('yt-dlp is not installed on your system')
        except asyncio.TimeoutError:
            raise YtDlpError('yt-dlp command timed out')
            
