# DineUp

DineUp is a web-based application that provides personalized recipe recommendations and health tracking features. The system uses Firebase for user management, OpenAI for AI-driven suggestions, and Streamlit for the web interface.

## Features

- **User Login and Signup**: Secure authentication using Firebase.
- **Recipe Recommendations**: Suggests recipes based on user mood, available ingredients, and preferences.
- **Health Tracking**: Tracks daily nutritional intake (calories, proteins, carbs, and fats).
- **Health Insights**: Generates detailed health reports and recommendations for a healthier lifestyle.
- **Graphical Visualization**: Displays daily intake vs. ideal intake in an easy-to-read graph.

---

## Prerequisites

Before running the application, ensure the following:

1. **Python 3.8 or higher** installed on your system.
2. Required Python libraries (see `requirements.txt`).

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-repo/DineUp.git
cd DineUp
```

### Step 2: Create and Activate a Virtual Environment

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Add the `.env` File  
Place the `.env` file (containing the API key you received from us) in the same directory as your project code. This file is essential to access the API key in the application.

---

## Running the Application

1. **Start the Streamlit server**:  
   Run the following command to start the application.  
   ```bash
   streamlit run app.py
   ```

2. **Open the application in your web browser**:  
   Once the server starts, Streamlit will provide a local URL, typically:  
   ```
   http://localhost:8501
   ```

3. **Log in and navigate the application**:  
   - When the app opens, you'll see a **Log In page**.  
   - **Mark the "New User" checkbox** to create an account. Enter your email and password, then press **Submit** to register.  
   - After creating an account, **unmark the "New User" checkbox** to log in using your newly created credentials.  
   - **Important:** You need to press the **Submit** button twice:  
     - First, when you log in.  
     - Second, after you're logged in to fully remove the login page (this is a known bug).  

4. **Explore the Home Page**:  
   - After logging in, you'll arrive at the **Home Page**, where random recipes are displayed.  
   - You can **add recipes to your favorites** by clicking the corresponding buttons.

5. **Navigate the menu**:  
   On the left side of the screen, you'll find a navigation menu with the following pages:  

   - **Find Recipes**:  
     Enter your mood, available ingredients, or dietary goals to get three tailored recipes for **breakfast, lunch, and dinner**. Each recipe includes detailed **nutritional information**.

   - **Daily Intake**:  
     Log your daily intake of **calories, carbs, fat, and protein** for a specific day.

   - **Health Report**:  
     View an **overall report of your health and diet**, including a daily breakdown of your intake.
     
---

## Project Structure

```
AI_DineUp/
├── app.py                # Main application file
├── .env                  # The API key 
├── requirements.txt      # Dependencies
├── recipes.csv           # Recipe dataset
├── images/               # Recipe images
└── README.md             # Documentation
```

---

## Usage

1. **Login or Sign Up**:
   - Use the login page to create an account or sign in.

2. **Navigate the App**:
   - **Home Page**: Explore random recipe suggestions.
   - **Find Recipe**: Input your mood and available ingredients to get tailored recipes.
   - **Daily Intake**: Log your nutritional intake for the day.
   - **Health Insights**: View detailed reports and download summaries.

---

## Notes

- Ensure the `recipes.csv` file and recipe images are present in the project directory.
- Known Bug: After refreshing the page, the user will be logged out, and they will need to log in again. This issue occurs due to the use of Streamlit, which does not retain session states across page reloads. For further development we will need to address this problem in the future.


---

## Troubleshooting

- **Missing Dependencies**: Run `pip install -r requirements.txt`.

---
