import cv2
import streamlit as st
import numpy as np
from fer import FER
import pandas as pd
import random
genre_choices=['Animation', 'Adventure', 'Comedy', 'Action', 'Family', 'Romance',
       'Drama', 'Crime', 'Thriller', 'Fantasy', 'Horror', 'Biography',
       'History', 'Mystery', 'Sci-Fi', 'War', 'Sport', 'Music',
       'Documentary', 'Musical', 'Western', 'Short', 'Film-Noir',
       'Talk-Show', 'News', 'Adult', 'Reality-TV', 'Game-Show']
emotions =['anger','disgust','fear','happiness','sadness','surprise','neutral']
page=st.sidebar.radio("Select Page",["Set Up Preferances","Recommendations"])
if page == "Set Up Preferances":
    with st.form(key="user-form"):
        anger_genres=st.multiselect("Anger",genre_choices)
        disgust_genres=st.multiselect("Disgust",genre_choices)
        fear_genres=st.multiselect("Fear",genre_choices)
        happiness_genres=st.multiselect("Happiness",genre_choices)
        sad_genres=st.multiselect("Sadness",genre_choices)
        surprise_genres=st.multiselect("Surprise",genre_choices)
        neutral_genres=st.multiselect("Neutral",genre_choices)
        st.text("Please wait until completed is shown")
        submit=st.form_submit_button()
    if submit:
        emo_detector=FER(mtcnn=True)
        cap=cv2.VideoCapture(0)
        if cap.isOpened():
            result,image=cap.read()
        else:
            result=False
        while result:
            result,image=cap.read()
            cv2.imshow("testing",image)
            if len(emo_detector.detect_emotions(image))>0:
                emotion_name,score=emo_detector.top_emotion(image)
                break
            if(cv2.waitKey(10)==27):
                break
        cap.release()
        cv2.destroyWindow("testing")
        st.write(f"You Are Feeling {emotion_name}, we'll show you movies for that.")
        if emotion_name == 'angry':
            emo_genres=anger_genres
        if emotion_name == 'disgust':
            emo_genres=disgust_genres
        if emotion_name == 'fear':
            emo_genres=fear_genres
        if emotion_name == 'happy':
            emo_genres=happiness_genres
        if emotion_name == 'sad':
            emo_genres=sad_genres
        if emotion_name == 'surprise':
            emo_genres=surprise_genres
        if emotion_name == 'neutral':
            emo_genres=neutral_genres
        if "emo_genres" not in st.session_state:
            st.session_state.emo_genres = emo_genres
        st.success("Completed")
elif page == 'Recommendations':
    if "emo_genres" not in st.session_state:
        st.header("PLS SETUP RECOMMENDATIONS")
    else:
        st.header("Recommendations")
        movies=pd.read_csv("cleanest_movie.csv")
        def filter_movs(dataframe,gen_list):
            i=0
            for gen in gen_list:
                if gen in dataframe:
                    return True
                i+=1
                if i==len(gen_list):
                    return False     
        recomm_movs=movies[movies['Genre'].apply(lambda x:filter_movs(x,st.session_state.emo_genres))]
        print(recomm_movs.sample(10))
        [col1,col2,col3,col4]=st.columns(4)
        [col5,col6,col7,col8]=st.columns(4)
        [col9,col10,col11,col12]=st.columns(4)
        [col13,col14,col15,col16]=st.columns(4)
        col_grp1=[col1,col2,col3,col4]
        col_grp2=[col5,col6,col7,col8]
        col_grp3=[col9,col10,col11,col12]
        col_grp4=[col13,col14,col15,col16]
        cols=[col_grp1,col_grp2,col_grp3,col_grp4]
        i=random.randint(0,10)
        for grps in cols:
            with st.container():
                for x in grps:
                    with x:
                        st.write(recomm_movs['Title'].iloc[i])
                        st.image(recomm_movs['Poster'].iloc[i])
                        i+=random.randint(1,100)
        del st.session_state.emo_genres



            

