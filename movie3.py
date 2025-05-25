import sys
import cv2
import pandas as pd
from fer import FER
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QGridLayout, QStackedWidget, QSizePolicy, QGroupBox, QScrollArea, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QUrl, QThread, pyqtSignal, Qt
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

import os


class EmotionMovieApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emotion-Based Movie Recommender")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setGeometry(100, 100, 1000, 800)
        self.emo_detector = FER(mtcnn=True)
        self.movies = pd.read_csv("cleanest_movie.csv")
        self.network_manager = QNetworkAccessManager()
        self.user_preferences = {}  # Stores user-selected genres for each emotion
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.page_stack = QStackedWidget()

        self.btn_setup = QPushButton("Set Preferences")
        self.btn_recommend = QPushButton("Recommendations")
        self.btn_setup.clicked.connect(lambda: self.page_stack.setCurrentIndex(0))
        self.btn_recommend.clicked.connect(lambda: self.page_stack.setCurrentIndex(1))

        layout.addWidget(self.btn_setup)
        layout.addWidget(self.btn_recommend)
        layout.addWidget(self.page_stack)

        # Preferences Page
        self.setup_page = QWidget()
        self.setup_layout = QVBoxLayout(self.setup_page)

        self.genre_choices = [
            'Animation', 'Adventure', 'Comedy', 'Action', 'Family', 'Romance',
            'Drama', 'Crime', 'Thriller', 'Fantasy', 'Horror', 'Biography',
            'History', 'Mystery', 'Sci-Fi', 'War', 'Sport', 'Music',
            'Documentary', 'Musical', 'Western', 'Short', 'Film-Noir',
            'Talk-Show', 'News', 'Adult', 'Reality-TV', 'Game-Show'
        ]

        self.emotions = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
        self.genre_lists = {}

        for emotion in self.emotions:
            group_box = QGroupBox(emotion.capitalize())
            group_layout = QVBoxLayout()
            genre_list = QListWidget()
            genre_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            genre_list.addItems(self.genre_choices)
            genre_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            group_layout.addWidget(genre_list)
            group_box.setLayout(group_layout)
            self.setup_layout.addWidget(group_box)
            self.genre_lists[emotion] = genre_list

        self.capture_btn = QPushButton("Detect Emotion")
        self.capture_btn.clicked.connect(self.detect_emotion)
        self.setup_layout.addWidget(self.capture_btn)

        self.result_label = QLabel("")
        self.setup_layout.addWidget(self.result_label)
        self.page_stack.addWidget(self.setup_page)

        # Recommendations Page
        self.recommend_page = QWidget()
        self.recommend_layout = QVBoxLayout(self.recommend_page)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.movie_grid_container = QWidget()
        self.movie_grid = QGridLayout(self.movie_grid_container)

        self.scroll_area.setWidget(self.movie_grid_container)
        self.recommend_layout.addWidget(QLabel("Recommended Movies:"))
        self.recommend_layout.addWidget(self.scroll_area)

        self.page_stack.addWidget(self.recommend_page)

        self.setLayout(layout)

    def detect_emotion(self):
        self.save_preferences()  # Save selected genres before detecting emotion
        self.thread = EmotionDetectionThread(self.emo_detector)
        self.thread.emotion_detected.connect(self.on_emotion_detected)
        self.thread.start()

    def save_preferences(self):
        """Store selected genres for each emotion."""
        for emotion in self.emotions:
            selected_genres = [item.text() for item in self.genre_lists[emotion].selectedItems()]
            self.user_preferences[emotion] = selected_genres

    def on_emotion_detected(self, emotion_name):
        self.result_label.setText(f"Detected Emotion: {emotion_name.capitalize()}")
        self.show_recommendations(emotion_name)

    def show_recommendations(self, emotion_name):
        # Default genres if the user didn't select any
        default_emo_genres_map = {
            'angry': ['Action', 'Thriller', 'Crime'],
            'disgust': ['Horror', 'Drama'],
            'fear': ['Thriller', 'Horror', 'Mystery'],
            'happy': ['Comedy', 'Romance', 'Animation'],
            'sad': ['Drama', 'Romance', 'Biography'],
            'surprise': ['Sci-Fi', 'Adventure', 'Fantasy'],
            'neutral': ['Documentary', 'Drama']
        }

        selected_genres = self.user_preferences.get(emotion_name, [])
        if not selected_genres:
            selected_genres = default_emo_genres_map.get(emotion_name, ['Drama'])

        filtered_movies = self.movies[self.movies['Genre'].apply(lambda x: any(genre in x for genre in selected_genres))]

        # Clear previous recommendations
        for i in reversed(range(self.movie_grid.count())):
            self.movie_grid.itemAt(i).widget().setParent(None)

        # Adjust grid layout based on screen size
        screen_width = self.frameGeometry().width()
        columns = 4 if screen_width > 1000 else 3  # Number of columns based on window width
        row = 0
        column = 0

        for i in range(min(16, len(filtered_movies))):
            title = filtered_movies['Title'].iloc[i]
            poster_url = filtered_movies['Poster'].iloc[i]

            movie_label = QLabel(title)
            movie_img = QLabel()

            if not poster_url or not poster_url.startswith("http"):
                poster_url = "default_poster.jpg"

            request = QNetworkRequest(QUrl(poster_url))
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda r=reply, img_label=movie_img: self.load_image(r, img_label))

            # Add widgets to grid layout dynamically based on window size
            self.movie_grid.addWidget(movie_label, row, column * 2)
            self.movie_grid.addWidget(movie_img, row, column * 2 + 1)

            column += 1
            if column >= columns:
                column = 0
                row += 1

        self.page_stack.setCurrentIndex(1)

    def load_image(self, reply, img_label):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            img_label.setPixmap(QPixmap("default_poster.jpg").scaled(150, 200, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()):
                img_label.setPixmap(pixmap.scaled(150, 200, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                img_label.setPixmap(QPixmap("default_poster.jpg").scaled(150, 200, Qt.AspectRatioMode.KeepAspectRatio))

    def closeEvent(self, event):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.stop_thread()
        event.accept()


class EmotionDetectionThread(QThread):
    emotion_detected = pyqtSignal(str)

    def __init__(self, emo_detector):
        super().__init__()
        self.emo_detector = emo_detector
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.emotion_detected.emit('neutral')
            return

        emotion_name = 'neutral'
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Detecting Emotion...", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
            emotions = self.emo_detector.detect_emotions(frame)
            if emotions:
                emotion_name, _ = self.emo_detector.top_emotion(frame)
                break

        cap.release()
        cv2.destroyAllWindows()
        self.emotion_detected.emit(emotion_name)

    def stop_thread(self):
        self.running = False
        self.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmotionMovieApp()
    window.show()
    sys.exit(app.exec())
