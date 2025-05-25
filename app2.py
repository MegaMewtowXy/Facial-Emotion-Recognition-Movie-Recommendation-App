import cv2
import streamlit as st
import pandas as pd
import random
import requests
from fer import FER

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

# Genre choices
genre_choices = ['Animation', 'Adventure', 'Comedy', 'Action', 'Family', 'Romance',
                 'Drama', 'Crime', 'Thriller', 'Fantasy', 'Horror', 'Biography',
                 'History', 'Mystery', 'Sci-Fi', 'War', 'Sport', 'Music',
                 'Documentary', 'Musical', 'Western', 'Short', 'Film-Noir',
                 'Talk-Show', 'News', 'Adult', 'Reality-TV', 'Game-Show']

# Emotion to emoji mapping
emotion_emoji_map = {
    'angry': '😡',
    'disgust': '🤢',
    'fear': '😨',
    'happy': '😊',
    'sad': '😢',
    'surprise': '😲',
    'neutral': '😐'
}

# Sidebar for page selection
page = st.sidebar.radio("Select Page", ["Set Up Preferences", "Recommendations"])

# Function to validate image URL
def is_valid_image(url):
    """Check if the image URL is valid and accessible."""
    try:
        response = requests.get(url, stream=True, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

if page == "Set Up Preferences":
    with st.form(key="user-form"):
        anger_genres = st.multiselect("Anger", genre_choices)
        disgust_genres = st.multiselect("Disgust", genre_choices)
        fear_genres = st.multiselect("Fear", genre_choices)
        happiness_genres = st.multiselect("Happiness", genre_choices)
        sad_genres = st.multiselect("Sadness", genre_choices)
        surprise_genres = st.multiselect("Surprise", genre_choices)
        neutral_genres = st.multiselect("Neutral", genre_choices)
        st.text("Please wait until completed is shown")
        submit = st.form_submit_button()
    if submit:
        emo_detector = FER(mtcnn=True)
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Unable to access webcam. Please ensure the camera is connected.")
            st.stop()
        result, image = cap.read()
        emotion_name = 'neutral'  # Default emotion
        while result:
            result, image = cap.read()
            if len(emo_detector.detect_emotions(image)) > 0:
                emotion_name, score = emo_detector.top_emotion(image)
                break
            if cv2.waitKey(1) == 27:  # Exit on ESC key
                break
        cap.release()
        if emotion_name == 'neutral':
            st.warning("Unable to detect emotion, defaulting to 'Neutral'.")
        
        # Display emotion and emoji
        emotion_emoji = emotion_emoji_map.get(emotion_name, '😐')
        st.write(f"You Are Feeling **{emotion_name.capitalize()}** {emotion_emoji}, we'll show you movies for that.")

        # Set emotion genres based on the detected emotion
        emo_genres_map = {
            'anger': anger_genres,
            'disgust': disgust_genres,
            'fear': fear_genres,
            'happiness': happiness_genres,
            'sadness': sad_genres,
            'surprise': surprise_genres,
            'neutral': neutral_genres
        }
        emo_genres = emo_genres_map.get(emotion_name, [])

        # If no genres are selected, revert to default genres
        if not emo_genres:
            emo_genres = default_emo_genres_map.get(emotion_name, [])

        # Store the genres in session state
        st.session_state.emo_genres = emo_genres
        st.session_state.emotion_detected = True

        st.success("Emotion Detected, You can now view recommendations.")

elif page == 'Recommendations':
    if not st.session_state.get('emotion_detected', False):
        st.warning("Please detect your emotion first in the 'Set Up Preferences' page.")
    else:
        st.header("Recommendations")
        try:
            movies = pd.read_csv("cleanest_movie.csv")  # Load the movie dataset
        except FileNotFoundError:
            st.error("Movie dataset not found. Please ensure 'cleanest_movie.csv' is available.")
            st.stop()

        # Validate dataset columns
        if 'Genre' not in movies.columns or 'Title' not in movies.columns or 'Poster' not in movies.columns:
            st.error("CSV file does not contain required columns.")
            st.stop()

        # Optimized movie filtering function (shows movies containing ANY of the selected genres)
        def filter_movs(dataframe, gen_list):
            """Filters movies that contain at least one of the selected genres."""
            pattern = '|'.join(gen_list)  # Create regex OR pattern
            return dataframe[dataframe['Genre'].str.contains(pattern, case=False, na=False)]

        # Filter recommendations based on selected genres
        recomm_movs = filter_movs(movies, st.session_state.emo_genres)

        # Check if any movies match the selected genres
        if recomm_movs.empty:
            st.warning("No movies found for the selected genres.")
        else:
            recomm_movs = recomm_movs.sample(frac=1).reset_index(drop=True)  # Shuffle results
            recomm_movs = recomm_movs.head(16)  # Limit recommendations to 16 movies
            num_cols = 4  # Number of columns per row
            num_movies = len(recomm_movs)  # Total recommended movies

            # Display movies in a dynamic grid
            for i in range(0, num_movies, num_cols):
                cols = st.columns(num_cols)  # Create a new row with 4 columns
                for j in range(num_cols):
                    if i + j < num_movies:  # Ensure we don't go out of bounds
                        with cols[j]:
                            movie = recomm_movs.iloc[i + j]
                            st.write(f"**{movie['Title']}**")
                            # Validate poster URL
                            poster_url = movie['Poster']
                            default_poster = "default_poster.jpg"  # Path to default image
                            if not poster_url or not is_valid_image(poster_url):
                                poster_url = default_poster
                            st.image(poster_url, use_container_width=True)

            # Clean up session state after showing recommendations
            del st.session_state.emo_genres
