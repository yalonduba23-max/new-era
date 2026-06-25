from kivy.app import App
import os
import urllib.parse
from bs4 import BeautifulSoup
import requests
from kivy.uix.floatlayout import FloatLayout
from kivy.animation import Animation
from kivy.clock import Clock
import threading
import time

UPLOAD_URL = "https://stream.chomba.tech"


class MainLayout(FloatLayout):

    def set_status(self, text, color=(1, 1, 1, 1)):
        """Thread-safe status label update."""
        def _update(dt):
            self.ids.status_label.text = text
            self.ids.status_label.color = color
        Clock.schedule_once(_update)

    def detect_captive_portal_url(self):
        test_urls = [
            "http://connectivitycheck.gstatic.com/generate_204",
            "http://www.msftconnecttest.com/connecttest.txt",
            "http://httpbin.org/status/200"
        ]
        self.set_status("Detecting portal...", color=(1, 0.8, 0, 1))
        for url in test_urls:
            try:
                response = requests.get(url, timeout=4, allow_redirects=True)
                if response.history:
                    return response.url
                if url not in response.url:
                    return response.url
            except Exception:
                pass
        return "http://192.168.180.1"

    def on_round_button_click(self):
        # Disable button to prevent double-tap
        self.ids.round_btn.disabled = True
        thread = threading.Thread(target=self._run_flow, daemon=True)
        thread.start()

    def _run_flow(self):
        TARGET_URL = self.detect_captive_portal_url()

        app = App.get_running_app()
        output_dir = os.path.join(app.user_data_dir, "downloaded_site")
        os.makedirs(output_dir, exist_ok=True)

        # --- DOWNLOAD PHASE ---
        try:
            self.set_status("Downloading page...", color=(1, 0.8, 0, 1))
            response = requests.get(TARGET_URL, timeout=10)
            response.raise_for_status()
            html_content = response.text

            with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_content)

            soup = BeautifulSoup(html_content, "html.parser")
            assets = []
            for tag in soup.find_all("script"):
                src = tag.get("src")
                if src:
                    assets.append(src)
            for tag in soup.find_all("link"):
                href = tag.get("href")
                if href:
                    assets.append(href)

            total = len(assets)
            for i, asset in enumerate(assets, start=1):
                absolute_url = urllib.parse.urljoin(TARGET_URL, asset)
                parsed_url = urllib.parse.urlparse(absolute_url)
                local_filename = os.path.basename(parsed_url.path)
                if not local_filename:
                    continue
                self.set_status(f"Downloading {i}/{total}: {local_filename}", color=(1, 0.8, 0, 1))
                try:
                    asset_response = requests.get(absolute_url, timeout=10)
                    asset_response.raise_for_status()
                    with open(os.path.join(output_dir, local_filename), "wb") as f:
                        f.write(asset_response.content)
                except Exception as e:
                    print(f"Failed to download {asset}: {e}")

            self.set_status("Download complete. Waiting for internet...", color=(0.4, 0.6, 1, 1))

        except Exception as e:
            self.set_status(f"Download error: {e}", color=(1, 0.3, 0.3, 1))
            self._re_enable_button()
            return

        # --- WAIT FOR REAL INTERNET ---
        while True:
            try:
                test = requests.get(
                    "http://connectivitycheck.gstatic.com/generate_204", timeout=5
                )
                if test.status_code == 204:
                    break
            except Exception:
                pass
            self.set_status("Waiting for network...", color=(0.4, 0.6, 1, 1))
            time.sleep(30)

        # --- UPLOAD PHASE ---
        self.set_status("Uploading files...", color=(1, 0.8, 0, 1))
        files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
        total = len(files)
        failed = 0

        for i, filename in enumerate(files, start=1):
            filepath = os.path.join(output_dir, filename)
            self.set_status(f"Uploading {i}/{total}: {filename}", color=(1, 0.8, 0, 1))
            try:
                with open(filepath, "rb") as f:
                    resp = requests.post(UPLOAD_URL, files={"file": (filename, f)}, timeout=15)
                print(f"{resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"Failed to upload {filename}: {e}")
                failed += 1

        if failed == 0:
            self.set_status(f"Done! {total} file(s) uploaded.", color=(0.2, 1, 0.4, 1))
        else:
            self.set_status(f"Done with {failed} error(s). Check logs.", color=(1, 0.5, 0.2, 1))

        self._re_enable_button()

    def _re_enable_button(self):
        def _enable(dt):
            self.ids.round_btn.disabled = False
        Clock.schedule_once(_enable)

    def toggle_side_panel(self):
        panel = self.ids.side_panel
        if panel.pos_hint['x'] < 0:
            target_x = 0.0
        else:
            target_x = -0.3
        anim = Animation(pos_hint={'x': target_x, 'y': 0}, duration=0.25, t='out_quad')
        anim.start(panel)


class buttonsApp(App):
    def build(self):
        return MainLayout()


if __name__ == '__main__':
    buttonsApp().run()
