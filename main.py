from kivy.app import App
import os
import urllib.parse
from bs4 import BeautifulSoup
import requests
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ListProperty
from kivy.animation import Animation

class MainLayout(FloatLayout):
    indicator_color = ListProperty([0.2, 0.2, 0.2, 1])

    def detect_captive_portal_url(self):
        """
        Attempts to detect the captive portal redirect URL by requesting
        standard HTTP connection-test endpoints.
        """
        test_urls = [
            "http://connectivitycheck.gstatic.com/generate_204",
            "http://www.msftconnecttest.com/connecttest.txt",
            "http://httpbin.org/status/200"
        ]
        
        print("Attempting to auto-detect captive portal URL...")
        for url in test_urls:
            try:
                # We allow redirects to trace where the portal sends the request
                response = requests.get(url, timeout=4, allow_redirects=True)
                
                # If there is a redirect history, the final URL is the portal login page
                if response.history:
                    detected_url = response.url
                    print(f"Redirect detected. Portal URL: {detected_url}")
                    return detected_url
                
                # If the URL changed from the original test URL, return it
                if url not in response.url:
                    print(f"URL changed. Portal URL: {response.url}")
                    return response.url
                    
            except Exception as e:
                print(f"Could not reach {url} for detection: {e}")
                
        # Fallback default gateway if auto-detection fails or if already logged in
        fallback_url = "http://192.168.180.1"
        print(f"Auto-detection unavailable. Falling back to: {fallback_url}")
        return fallback_url

    def on_round_button_click(self):
        # 1. Turn the indicator green to show action started
        self.indicator_color = [0, 0.8, 0, 1]
        
        # 2. Dynamically detect the Target URL
        TARGET_URL = self.detect_captive_portal_url()
        print(f"Target URL set to: {TARGET_URL}")

        # 3. Get the app's private directory
        app = App.get_running_app()
        OUTPUT_DIR = os.path.join(app.user_data_dir, "downloaded_site")
        print(f"Saving files to: {OUTPUT_DIR}")

        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 4. Downloading logic
        try:
            # Fetch the main HTML
            response = requests.get(TARGET_URL, timeout=10)
            response.raise_for_status()
            html_content = response.text

            # Save the main index.html
            with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
            print("Main HTML downloaded successfully.")

            # Parse the HTML to find assets
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Find all script (JS) and link (CSS) tags
            assets = []
            for script in soup.find_all("script"):
                src = script.get("src")
                if src:
                    assets.append(src)
                    
            for link in soup.find_all("link"):
                href = link.get("href")
                if href:
                    assets.append(href)

            # Download each asset
            for asset in assets:
                # Resolve relative URLs to absolute URLs
                absolute_url = urllib.parse.urljoin(TARGET_URL, asset)
                
                # Determine local filename and path
                parsed_url = urllib.parse.urlparse(absolute_url)
                local_filename = os.path.basename(parsed_url.path)
                
                if not local_filename:
                    continue
                    
                print(f"Downloading: {absolute_url}")
                try:
                    asset_response = requests.get(absolute_url, timeout=10)
                    asset_response.raise_for_status()
                    
                    with open(os.path.join(OUTPUT_DIR, local_filename), "wb") as f:
                        f.write(asset_response.content)
                except Exception as e:
                    print(f"Failed to download {asset}: {e}")

        except Exception as e:
            print(f"An error occurred during download: {e}")

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
