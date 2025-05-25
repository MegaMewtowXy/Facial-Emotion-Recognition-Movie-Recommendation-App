import os
import shutil
import requests
import pandas as pd
import cv2  # Ensure cv2 is imported
from fer import FER
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.gridlayout import GridLayout
from kivymd.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.resources import resource_find
from urllib.parse import urlparse
from kivy.core.window import Window
# Default genres for each emotion
default_emo_genres_map = {
    'anger': ['Action', 'Thriller', 'Crime'],
    'disgust': ['Horror', 'Drama', 'Crime'],
    'fear': ['Thriller', 'Horror', 'Mystery'],
    'happiness': ['Comedy', 'Romance', 'Animation'],
    'sadness': ['Drama', 'Romance', 'Biography'],
    'surprise': ['Sci-Fi', 'Adventure', 'Fantasy'],
    'neutral': ['Documentary', 'Drama', 'Biography']
}

# Load Movie Dataset
try:
    movies = pd.read_csv("cleanest_movie.csv")
except FileNotFoundError:
    movies = pd.DataFrame(columns=["Title", "Genre", "Poster"])  # Empty dataset fallback

# Kivy UI (KV Language)
KV = '''
ScreenManager:
    MenuScreen:
    CameraScreen:
    ResultsScreen:

<MenuScreen>:
    name: "menu"
    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(20)
        padding: dp(20)
        MDLabel:
            text: "Emotion-Based Movie Recommendation"
            font_style: "H5"
            halign: "center"
        MDRaisedButton:
            text: "Detect Emotion"
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "camera"

<CameraScreen>:
    name: "camera"
    BoxLayout:
        orientation: "vertical"
        Camera:
            id: camera
            play: True
        MDRaisedButton:
            text: "Capture & Analyze"
            pos_hint: {"center_x": 0.5}
            on_release: app.detect_emotion()

<ResultsScreen>:
    name: "results"
    MDBoxLayout:
        orientation: "vertical"
        MDLabel:
            id: emotion_label
            text: "Detected Emotion: "
            halign: "center"
            size_hint_y: None
            height: dp(30)
        ScrollView:
            MDGridLayout:
                id: movie_grid
                cols: 2
                padding: dp(10)
                spacing: dp(10)
                size_hint_y: None
                height: self.minimum_height
        MDRaisedButton:
            text: "Back to Menu"
            pos_hint: {"center_x": 0.5}
            on_release: app.root.current = "menu"
'''

class MenuScreen(Screen):
    pass

class CameraScreen(Screen):
    pass

class ResultsScreen(Screen):
    pass

class EmotionApp(MDApp):
    def build(self):
        Window.set_icon('icon.ico')
        return Builder.load_string(KV)

    def detect_emotion(self):
        cap = cv2.VideoCapture(0)
        emo_detector = FER(mtcnn=True)
        
        ret, frame = cap.read()
        if not ret:
            self.root.get_screen("results").ids.emotion_label.text = "Camera Error"
            return
        
        emotion_name = "neutral"
        emotions = emo_detector.detect_emotions(frame)
        if emotions:
            emotion_name, _ = emo_detector.top_emotion(frame)

        cap.release()

        # Set genres based on emotion
        emo_genres_map = {
            'anger': ['Action', 'Thriller', 'Crime'],
            'disgust': ['Horror', 'Drama', 'Crime'],
            'fear': ['Thriller', 'Horror', 'Mystery'],
            'happiness': ['Comedy', 'Romance', 'Animation'],
            'sadness': ['Drama', 'Romance', 'Biography'],
            'surprise': ['Sci-Fi', 'Adventure', 'Fantasy'],
            'neutral': ['Documentary', 'Drama', 'Biography']
        }
        selected_genres = emo_genres_map.get(emotion_name, [])
        self.recommend_movies(selected_genres)

        # Update UI
        result_screen = self.root.get_screen("results")
        result_screen.ids.emotion_label.text = f"Detected Emotion: {emotion_name.capitalize()}"

        self.root.current = "results"

    def recommend_movies(self, genres):
        filtered = movies[movies['Genre'].str.contains("|".join(genres), case=False, na=False)]
        filtered = filtered.sample(n=min(4, len(filtered)))  # Limit to 4 movies

        movie_grid = self.root.get_screen("results").ids.movie_grid
        movie_grid.clear_widgets()

        temp_image_paths = []

        for _, movie in filtered.iterrows():
            title = movie["Title"]
            poster_url = movie["Poster"]
            print(f"Checking poster URL: {poster_url}")  # Debugging: log the poster URL

            # Validate poster URL and download if valid
            if not poster_url or not self.is_valid_image(poster_url):
                print(f"Using default poster due to invalid URL: {poster_url}")  # Debugging: log fallback
                poster_url = resource_find('default_poster.jpg')  # Use the default image bundled with the APK
            else:
                # Download image and save it locally
                poster_url = self.download_image(poster_url)

            movie_item = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
            movie_item.height = dp(300)  # Adjusted height for bigger images

            movie_item.add_widget(Image(source=poster_url, size_hint_y=0.8))  # Display image above title
            movie_item.add_widget(MDLabel(text=title, halign="center", size_hint_y=None, height=dp(40)))

            movie_grid.add_widget(movie_item)

            # Add the image path to temp_image_paths for future deletion
            temp_image_paths.append(poster_url)

        self.temp_image_paths = temp_image_paths  # Store paths to delete later

    def is_valid_image(self, url):
        """Check if the image URL is valid and accessible."""
        try:
            response = requests.get(url, stream=True, timeout=5)
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.RequestException as e:
            print(f"Error checking image URL: {e}")
            return False

    def download_image(self, url):
        """Download image and return the local file path."""
        filename = os.path.join(self.get_temp_image_dir(), os.path.basename(urlparse(url).path))
        
        # Check if the file already exists
        if not os.path.exists(filename):
            try:
                response = requests.get(url, stream=True)
                with open(filename, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            except requests.RequestException as e:
                print(f"Error downloading image: {e}")
        
        return filename

    def get_temp_image_dir(self):
        """Ensure temporary image directory exists."""
        temp_dir = os.path.join(self.get_application_name(), "temp_images")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir

    def on_stop(self):
        """Override the on_stop method to delete temporary images when the app closes."""
        for temp_image in self.temp_image_paths:
            # Only delete images that are not the default image
            if temp_image != resource_find('default_poster.jpg') and os.path.exists(temp_image):
                os.remove(temp_image)
                print(f"Deleted temporary image: {temp_image}")

if __name__ == "__main__":
    EmotionApp().run()
