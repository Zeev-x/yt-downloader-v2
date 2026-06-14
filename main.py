from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

import subprocess
import threading
import os
import json
import glob
import imageio_ffmpeg


class MainLayout(BoxLayout):

    def add_log(self, text):
        def update(dt):
            self.ids.log.text += text + "\n"
        Clock.schedule_once(update)

    def clear_log(self):
        self.ids.log.text = ""

    def get_formats(self):
        threading.Thread(target=self._get_formats, daemon=True).start()

    def _get_formats(self):
        url = self.ids.url.text.strip()

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        self.add_log("")
        self.add_log("=== MENGAMBIL DAFTAR KUALITAS ===")

        result = subprocess.run(
            ["yt-dlp", "-J", url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        if result.returncode != 0:
            self.add_log("❌ Gagal mengambil informasi video")
            self.add_log(result.stderr)
            return

        try:
            data = json.loads(result.stdout)
            qualities = set()

            for fmt in data.get("formats", []):
                height = fmt.get("height")
                if height:
                    qualities.add(f"{height}p")

            qualities = sorted(
                list(qualities),
                key=lambda x: int(x[:-1])
            )

            if not qualities:
                self.add_log("❌ Tidak ada kualitas ditemukan")
                return

            def update(dt):
                self.ids.quality.values = qualities
                self.ids.quality.text = qualities[-1]

            Clock.schedule_once(update)

            self.add_log("✅ Kualitas ditemukan:")
            for q in qualities:
                self.add_log("  • " + q)

        except Exception as e:
            self.add_log(f"❌ Error: {e}")

    def download_mp3(self):
        threading.Thread(target=self._download_mp3, daemon=True).start()

    def download_mp4(self):
        threading.Thread(target=self._download_mp4, daemon=True).start()

    def _download_mp3(self):
        url = self.ids.url.text.strip()

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        os.makedirs("downloads/audio", exist_ok=True)

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        if not os.path.exists(ffmpeg_path):
            self.add_log("❌ FFmpeg tidak ditemukan")
            return

        self.add_log(f"FFmpeg: {ffmpeg_path}")
        self.add_log("=== DOWNLOAD MP3 ===")

        cmd = [
            "yt-dlp",
            "--ffmpeg-location",
            ffmpeg_path,
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            "downloads/audio/%(title)s.%(ext)s",
            url
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        for line in process.stdout:
            self.add_log(line.strip())

        process.wait()

        if process.returncode == 0:
            self.add_log("✅ Download MP3 selesai")
        else:
            self.add_log("❌ Download MP3 gagal")

    def _download_mp4(self):
        url = self.ids.url.text.strip()

        if not url:
            self.add_log("❌ Masukkan URL terlebih dahulu!")
            return

        quality = self.ids.quality.text

        os.makedirs("downloads/video", exist_ok=True)
        os.makedirs("downloads/temp", exist_ok=True)

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        if not os.path.exists(ffmpeg_path):
            self.add_log("❌ FFmpeg tidak ditemukan")
            return

        self.add_log(f"FFmpeg: {ffmpeg_path}")

        if quality.endswith("p"):
            height = quality[:-1]
            format_code = (
                f"bestvideo[height<={height}]"
                f"+bestaudio/"
                f"best[height<={height}]"
            )
        else:
            format_code = "bv*+ba/b"

        temp_template = "downloads/temp/%(title)s.%(ext)s"

        self.add_log("")
        self.add_log(f"=== DOWNLOAD MP4 {quality} ===")

        cmd = [
            "yt-dlp",
            "--ffmpeg-location",
            ffmpeg_path,
            "-f",
            format_code,
            "--merge-output-format",
            "mp4",
            "-o",
            temp_template,
            url
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        for line in process.stdout:
            self.add_log(line.strip())

        process.wait()

        if process.returncode != 0:
            self.add_log("❌ Download gagal")
            return

        files = glob.glob("downloads/temp/*.mp4")

        if not files:
            self.add_log("❌ File hasil download tidak ditemukan")
            return

        source_file = max(files, key=os.path.getmtime)
        filename = os.path.basename(source_file)
        output_file = os.path.join("downloads/video", filename)

        self.add_log("")
        self.add_log("=== KONVERSI KE H.264 + AAC ===")

        convert_cmd = [
            ffmpeg_path,
            "-y",
            "-i", source_file,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_file
        ]

        convert = subprocess.Popen(
            convert_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        for line in convert.stdout:
            self.add_log(line.strip())

        convert.wait()

        if convert.returncode == 0:
            try:
                os.remove(source_file)
            except Exception:
                pass

            self.add_log("")
            self.add_log("✅ Video berhasil dikonversi")
            self.add_log("Codec Video : H.264")
            self.add_log("Codec Audio : AAC")
            self.add_log(f"File : {output_file}")
        else:
            self.add_log("❌ Gagal konversi H.264")


class ReyetteApp(App):
    pass


if __name__ == "__main__":
    ReyetteApp().run()
