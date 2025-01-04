import streamlit as st
import pyrebase
import openai
import logging
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import re
import os
import zipfile
import io
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Firebase configuration
firebase_config = {
    "apiKey": "AIzaSyBVDFnvFMKxu-_AN4gSkG3eA86inL7SakA",
    "authDomain": "dineup-1712d.firebaseapp.com",
    "databaseURL": "https://dineup-1712d-default-rtdb.europe-west1.firebasedatabase.app",
    "projectId": "dineup-1712d",
    "storageBucket": "dineup-1712d.appspot.com",
    "messagingSenderId": "852265792411",
    "appId": "1:852265792411:web:912b19f2296e88c8c0273e",
    "measurementId": "G-1D1EEFQV0C"
}

# Initialize Firebase and OpenAI
firebase = pyrebase.initialize_app(firebase_config)
database = firebase.database()
auth = firebase.auth()

# Load the .env file
load_dotenv()

# Access the API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load recipe dataset
@st.cache_data
def load_dataset():
    return pd.read_csv("recipes.csv") 

recipe_df = load_dataset()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = None

# Helper Functions

def fetch_user_preferences(user_uid):
    try:
        preferences = database.child("users").child(user_uid).child("preferences").get().val()
        liked_ingredients = preferences.get("liked_ingredients", []) if preferences else []
        disliked_ingredients = preferences.get("disliked_ingredients", []) if preferences else []
        liked_recipes = preferences.get("liked_recipes", []) if preferences else []
        return liked_ingredients, disliked_ingredients, liked_recipes
    except Exception as e:
        st.error(f"Failed to fetch user preferences: {e}")
        return [], [], []


def add_to_favorites(user_id, recipe_title):
    try:
        preferences = database.child("users").child(user_id).child("preferences").get().val() or {}
        liked_recipes = preferences.get("liked_recipes", [])

        if recipe_title not in liked_recipes:
            liked_recipes.append(recipe_title)
            database.child("users").child(user_id).child("preferences").update({"liked_recipes": liked_recipes})
            st.success(f"Added '{recipe_title}' to favorites!")
        else:
            st.info(f"'{recipe_title}' is already in favorites.")
    except Exception as e:
        logging.error(f"Error adding to favorites: {e}")
        st.error("Failed to add recipe to favorites.")


def parse_recipe_recommendations(response):
    """
    Parse the response from OpenAI to extract recipe details, including ingredients, instructions, and nutritional information.
    """

    recipes = []
    current_recipe = ""   
    for line in response.split("\n"):
        if "Recipe:" in line:
            if current_recipe:
                recipes.append(current_recipe.strip())
            current_recipe = line.strip() + "\n" 
        else:
            current_recipe += line.strip() + "\n"  

    if current_recipe:  
        recipes.append(current_recipe.strip())

    logging.debug(recipes)
    return recipes


def generate_recipe_recommendations(mood, ingredients, dietary_goals, data):
    """
    Generate recipe recommendations using OpenAI's chat models.
    """

    prompt = (
        f"Based on the mood '{mood}' and the following ingredients: {', '.join(ingredients)}, and the dietary goals of the user '{dietary_goals}'"
        f"and on the user´s liked recioes'{data}' "
        f"provide three recipes: one for breakfast recipe, one for lunch recipe, and one for dinner recipe. "
        f"Each recipe should include a name, a list of ingredients, and step-by-step instructions."
        f"Each recipe should include nutritional information (calories, proteins, carbs, and fats)"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant skilled in recipe suggestions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,
            temperature=0.7
        )
        return parse_recipe_recommendations(response['choices'][0]['message']['content'].strip())
    except Exception as e:
        logging.error(f"Error generating recipe recommendations: {e}")
        st.error("Unable to generate recipe recommendations. Please try again later.")
        return []


def save_daily_intake(user_id, date, intake_data):
    """Save daily nutritional intake to Firebase."""
    try:
        database.child("users").child(user_id).child("health_intake").child(date).set(intake_data)
        st.success("Your daily intake has been saved!")
    except Exception as e:
        logging.error(f"Error saving daily intake: {e}")
        st.error("Unable to save daily intake. Please try again later.")


def fetch_independent_data(user_id):
    """Fetch independent data (name, gender, age, health_intake) from Firebase."""
    try:
        name = database.child("users").child(user_id).child("name").get().val()
        gender = database.child("users").child(user_id).child("gender").get().val()
        age = database.child("users").child(user_id).child("age").get().val()
        weight = database.child("users").child(user_id).child("weight").get().val()
        health_data = database.child("users").child(user_id).child("health_intake").get().val()

        return {
            "name": name or "User",
            "gender": gender or "Unknown",
            "age": age or "Unknown",
            "weight": weight or "Unknown",
            "health_data": health_data or {}
        }
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        st.error("Unable to fetch user data.")
        return None


def get_ideal_intake_from_openai(user_info):
    
    name = user_info.get("name", "User")
    gender = user_info.get("gender", "Unknown")
    age = user_info.get("age", "Unknown")
    weight = user_info.get("weight", "Unknown")


    prompt = (
        f"Provide the ideal daily nutrient intake (calories, proteins, carbs, and fats) for the user with the name {name}"        
        f"Based on the user's age: {age}, gender: {gender}, and weight: {weight}."
        f"Provide it as a list with no extra text or explanations"
        f"Provide one value for each , i.e no ranges"
    )

    try:
        ideal_values_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7
        )
        ideal_values_str = ideal_values_response['choices'][0]['message']['content'].strip()

        ideal_intake = {}

        for line in ideal_values_str.split('\n'):
            if not line.strip():
                continue
                
            nutrient, amount = line.split(":")
            clean_nutrient = nutrient.strip().lstrip("-").lower()  
            clean_amount = amount.strip().replace('g', '').strip()

            clean_amount = clean_amount.replace(',', '')

            try:
                ideal_intake[clean_nutrient] = float(clean_amount)
            except ValueError as e:
                logging.error(f"Error converting amount '{clean_amount}' for nutrient '{clean_nutrient}': {e}")

        ideal_intake = {key.strip(): value for key, value in ideal_intake.items()}

        logging.debug(f"Ideal Intake: {ideal_intake}")
        return ideal_intake


    except Exception as e:
        print(f"Error fetching data from OpenAI: {e}")
        return {}


def generate_health_report_with_openai_v2(user_info):
    """
    Generate a health report and recommendations using OpenAI based on the user's health data.
    """

    name = user_info.get("name", "User")
    gender = user_info.get("gender", "Unknown")
    age = user_info.get("age", "Unknown")
    weight = user_info.get("weight", "Unknown")
    health_data = user_info.get("health_data", {})

    user = user_info

    health_summary = "\n".join(
        [f"{date}: Calories: {data.get('calories', 0)}, Proteins: {data.get('proteins', 0)}g, "
         f"Carbs: {data.get('carbs', 0)}g, Fats: {data.get('fats', 0)}g"
         for date, data in sorted(health_data.items())]
    )

    summary_prompt = (
        f"The user is a {age}-year-old {gender.lower()} named {name} and weighs {weight}. Based on their health data:\n"
        f"{health_summary}\n\n"
        f"Generate a detailed health report for {name}, including a summary of their nutritional habits, areas of improvement, "
        f"and personalized recommendations for a healthier diet and lifestyle. "
        f"Provide specific suggestions for meals, exercises, and other health tips tailored to their age, gender, and weight."
    )

    daily_prompt = (
        f"The user is a {age}-year-old {gender.lower()} named {name} and weighs {weight}. Based on their health data for today "
        f"({datetime.now().strftime('%Y-%m-%d')}):\n"
        f"{health_summary}\n\n"
        f"Generate a daily report, including an analysis of their nutritional intake (calories, proteins, carbs, and fats) "
        f"compared to ideal intake for their age, weight, and activity level. "
        f"Explain areas where their intake deviates from the ideal and suggest improvements."
    )

    try:
        # Generate the summary report
        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=800,
            temperature=0.7
        )
        summary_report = summary_response['choices'][0]['message']['content'].strip()

        # Generate the daily report
        daily_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": daily_prompt}],
            max_tokens=800,
            temperature=0.7
        )
        daily_report = daily_response['choices'][0]['message']['content'].strip()

        # Generate a visual graph comparing intake to ideal values
        ideal_intake = get_ideal_intake_from_openai(user)
        today_data = health_data.get(datetime.now().strftime('%Y-%m-%d'), {})
        actual_intake = {
            "calories": today_data.get('calories', 0),
            "proteins": today_data.get('proteins', 0),
            "carbs": today_data.get('carbs', 0),
            "fats": today_data.get('fats', 0)
        }

        labels = ['Calories', 'Proteins', 'Carbs', 'Fats']

        ideal_values = [ideal_intake.get(label.lower().strip(), 0) for label in labels]

        logging.debug(f"Ideal Values: {ideal_values}")

        actual_values = [actual_intake.get(label.lower().strip(), 0) for label in labels]

        logging.debug(f"Actual Values: {actual_values}")

        plt.figure(figsize=(8, 6))
        x = range(len(labels))
        plt.bar(x, ideal_values, width=0.4, label='Ideal Intake', align='center')
        plt.bar([p + 0.4 for p in x], actual_values, width=0.4, label='Actual Intake', align='center')
        plt.xticks([p + 0.2 for p in x], labels)
        plt.ylabel("Amount")
        plt.title("Daily Intake vs. Ideal Intake")
        plt.legend()

        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)

        return summary_report, daily_report, buffer

    except Exception as e:
        logging.error(f"Error generating reports and graph: {e}")
        st.error("Unable to generate reports and graph. Please try again later.")
        return None, None, None


def login_logic():
    """Handle login and signup logic."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.user_name = None

    if not st.session_state.logged_in:
        st.header("Login or Sign Up")

        # Toggle between login and signup
        is_new_user = st.checkbox("New User? Sign Up", value=False)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        name = st.text_input("Name") if is_new_user else None        
        gender = st.text_input("Gender") if is_new_user else None
        age = st.text_input("Age") if is_new_user else None
        weight = st.text_input("Weight") if is_new_user else None

        error = st.empty()

        if st.button("Submit"):
            try:
                if is_new_user:
                    user = auth.create_user_with_email_and_password(email, password)
                    user_id = user['localId']
                    database.child("users").child(user_id).set({
                        "name": name,
                        "gender": gender,
                        "age": age,
                        "weight": weight,
                        "email": email,
                        "createdAt": datetime.now().isoformat(),
                    })
                    st.success("Account created successfully!")
                else:
                    user = auth.sign_in_with_email_and_password(email, password)
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    user_uid = user['localId']
                    user_data = database.child("users").child(user_uid).get()
                    st.session_state.user_name = user_data.val().get("name", "User")
                    st.success("Logged in successfully!")
            except Exception as e:
                error.error(f"Error: {str(e)}")
   

# Home page with hardcoded ingredients to like or dislike
def home_page():
    st.header("Home Page")

    current_time = datetime.now()

    # Check if 30 seconds have passed since the last refresh
    if st.session_state.last_refresh_time is None or (current_time - st.session_state.last_refresh_time).total_seconds() >= 30:
        st.session_state.last_refresh_time = current_time
        st.session_state.random_recipes = recipe_df.sample(n=3).to_dict(orient="records")
        all_ingredients = recipe_df['Ingredients'].dropna().str.split(', ').explode().unique()
        st.session_state.random_ingredients = list(pd.Series(all_ingredients).sample(n=3))

    # Display random recipes
    st.subheader("Random Recipe Recommendations")
    for index, recipe in enumerate(st.session_state.random_recipes):
        st.markdown(f"### {recipe['Title']}")
        image_path = os.path.abspath(f"images/{recipe['Image_Name']}.jpg")

        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.warning(f"Image not found: {recipe['Image_Name']}")

        st.write(f"**Ingredients:** {recipe['Ingredients']}")
        st.write(f"**Instructions:** {recipe['Instructions']}\n")

        if st.button(f"Add '{recipe['Title']}' to Favorites", key=f"add_recipe_{index}"):
            if st.session_state.user:
                add_to_favorites(st.session_state.user['localId'], recipe['Title'])
                st.session_state.random_recipes[index]['added_to_favorites'] = True
            else:
                st.error("You must be logged in to add recipes to favorites.")

        if st.session_state.random_recipes[index].get('added_to_favorites'):
            st.info(f"'{recipe['Title']}' is already added to favorites.")


# Main function updated to include navigation
def main():
    # Login logic and navigation
    login_logic()
    if st.session_state.logged_in:
        st.sidebar.header(f"Welcome, {st.session_state.user_name}!")
        if st.sidebar.button("Home"):
            st.session_state.current_page = "Home"
        if st.sidebar.button("Find Recipe"):
            st.session_state.current_page = "Find Recipe"
        if st.sidebar.button("Daily Intake"):
            st.session_state.current_page = "Daily Intake"
        if st.sidebar.button("Health Insights"):
            st.session_state.current_page = "Health Insights"
        if st.sidebar.button("Log Out"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.user_name = None
            st.session_state.current_page = "Login"
            st.success("Logged out successfully.")

        # Page rendering based on navigation
        if st.session_state.current_page == "Home":
            st.title("Find Recipe Page with Health Tracking")
            home_page()
        elif st.session_state.current_page == "Find Recipe":
            with st.form("recipe_form"):
                mood = st.text_input("Enter your mood (e.g., happy, tired, adventurous):")
                ingredients = st.text_area("List the ingredients you have (comma-separated):")
                dietary_goals = st.text_area("Enter your dietary goals (e.g., low-carb, under 500 calories, high-protein):")
                submit = st.form_submit_button("Find Recipes")

            if submit:
                if not mood or not ingredients:
                    st.warning("Please fill out all fields.")
                else: 
                    data = fetch_user_preferences(st.session_state.user['localId'])
                    ingredients_list = [item.strip() for item in ingredients.split(",")]
                    st.session_state.recommendations = generate_recipe_recommendations(mood, ingredients_list, dietary_goals, data)
                    if st.session_state.recommendations:
                        logging.debug(st.session_state.recommendations)

                        intro_text = st.session_state.recommendations[0]
                        st.write(intro_text)

                        st.subheader("Recommended Recipes")

                        # Loop through and display each recipe
                        for index, recipe in enumerate(st.session_state.recommendations[1:], start=1):
                            st.write(f"### Recipe {index}:")
                            
                            sections = recipe.split("\n\n")
                            
                            for section in sections:
                                if section.startswith("**"):
                                    st.markdown(section)
                                else:
                                    st.write(section)

                            st.markdown("---")

        elif st.session_state.current_page == "Daily Intake":
            st.subheader("Daily Intake")
            with st.form("intake_form"):
                date = st.date_input("Date").isoformat()
                calories = st.number_input("Calories (kcal)", min_value=0)
                proteins = st.number_input("Proteins (g)", min_value=0)
                carbs = st.number_input("Carbs (g)", min_value=0)
                fats = st.number_input("Fats (g)", min_value=0)
                save_intake = st.form_submit_button("Save Daily Intake")

                if save_intake:
                    intake_data = {
                        "calories": calories,
                        "proteins": proteins,
                        "carbs": carbs,
                        "fats": fats
                    }
                    save_daily_intake(st.session_state.user['localId'], date, intake_data)

        elif st.session_state.current_page == "Health Insights":
            st.subheader("Health Insights")
            if st.button("Generate Health Reports"):
                user_id = st.session_state.user['localId']
                user_info = fetch_independent_data(user_id)
                if user_info:
                    summary_report, daily_report, graph_buffer = generate_health_report_with_openai_v2(user_info)
                    if summary_report and daily_report:
                        # Display the summary report
                        st.markdown("### Summary Report")
                        st.text_area("Summary Report", summary_report, height=300)

                        # Display the daily report
                        st.markdown("### Daily Report")
                        st.text_area("Daily Report", daily_report, height=300)

                        # Display the graph
                        st.markdown("### Daily Intake vs. Ideal Intake")
                        st.image(graph_buffer, use_column_width=True)

                        # Extract bytes from the BytesIO buffer
                        graph_buffer.seek(0)
                        graph_bytes = graph_buffer.read()

                        # Create a ZIP file containing all three items
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                            zip_file.writestr("summary_report.txt", summary_report)
                            zip_file.writestr("daily_report.txt", daily_report)
                            zip_file.writestr("daily_intake_graph.png", graph_bytes)
                        zip_buffer.seek(0)

                        # Add a download button for the ZIP file
                        st.download_button(
                            label="Download All Reports and Graph",
                            data=zip_buffer.getvalue(),
                            file_name="health_reports_and_graph.zip",
                            mime="application/zip"
                        )

if __name__ == "__main__":
    main()
