import os
import shutil
import subprocess
import threading


class FfmpegEncoder:
    def __init__(self, channel_id, rtmp_url, bitrate=6000):
        self.channel_id = channel_id
        self.rtmp_url = rtmp_url
        self.bitrate = max(300, min(51000, int(bitrate or 6000)))
        self.process = None
        self.lock = threading.Lock()
        self.logs = []

    def _log(self, message):
        self.logs.append(message)
        self.logs = self.logs[-30:]

    def start(self):
        if self.process and self.process.poll() is None:
            return
        ffmpeg = os.getenv('FFMPEG_BIN', 'ffmpeg')
        if not shutil.which(ffmpeg) and not os.path.isfile(ffmpeg):
            raise RuntimeError('FFmpeg is not installed on the Nexus server.')

        bitrate = f'{self.bitrate}k'
        command = [
            ffmpeg, '-hide_banner', '-loglevel', 'error',
            '-f', 'webm', '-i', 'pipe:0',
            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p', '-b:v', bitrate, '-maxrate', bitrate,
            '-bufsize', f'{self.bitrate * 2}k',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '48000',
            '-f', 'flv', self.rtmp_url,
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self._log('FFmpeg encoder started.')
        threading.Thread(target=self._read_errors, daemon=True).start()

    def _read_errors(self):
        if not self.process or not self.process.stderr:
            return
        for raw_line in iter(self.process.stderr.readline, b''):
            line = raw_line.decode('utf-8', errors='replace').strip()
            if line:
                self._log(line)

    def write(self, chunk):
        with self.lock:
            if not self.process or self.process.poll() is not None or not self.process.stdin:
                raise RuntimeError('FFmpeg encoder is not running.')
            try:
                self.process.stdin.write(chunk)
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                self._log(f'FFmpeg input stopped: {exc}')
                raise RuntimeError('FFmpeg stopped while receiving media.') from exc

    def stop(self):
        with self.lock:
            if not self.process:
                return
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
            self._log('FFmpeg encoder stopped.')
            self.process = None

    def status(self):
        running = bool(self.process and self.process.poll() is None)
        return {'running': running, 'channel_id': self.channel_id, 'logs': list(self.logs)}


class EncoderManager:
    def __init__(self):
        self.encoders = {}
        self.lock = threading.Lock()

    def start(self, channel_id, rtmp_url, bitrate):
        with self.lock:
            self.stop(channel_id)
            encoder = FfmpegEncoder(channel_id, rtmp_url, bitrate)
            encoder.start()
            self.encoders[channel_id] = encoder
            return encoder.status()

    def write(self, channel_id, chunk):
        with self.lock:
            encoder = self.encoders.get(channel_id)
            if not encoder:
                raise RuntimeError('Encoder is not running.')
            encoder.write(chunk)

    def stop(self, channel_id):
        encoder = self.encoders.pop(channel_id, None)
        if encoder:
            encoder.stop()

    def status(self, channel_id):
        encoder = self.encoders.get(channel_id)
        return encoder.status() if encoder else {'running': False, 'channel_id': channel_id, 'logs': []}


encoder_manager = EncoderManager()