# 🚀 Hieu's Hub - Backend Server

This is the Backend system (API Server) for the **Hieu's Hub** project - An English vocabulary learning and test preparation application integrated with an AI Assistant. 
The system is built with **Python (Flask)**, processes data from Google Sheets using **Pandas**, and integrates the power of the **Google Gemini API**.

## 🛠️ Technologies Used
* **Framework:** Python / Flask
* **Cross-Origin:** Flask-CORS (Secure communication between FE and BE)
* **Data Processing:** Pandas
* **Artificial Intelligence:** Google Generative AI (`gemini-3.6-flash`)
* **Deploy / Hosting:** Gunicorn / Render.com

---

## 📂 API Structure (Endpoints)

The system provides 3 main APIs for the Frontend to communicate with:

1. `POST /api/get-data`: Fetches and synchronizes data from Google Sheets to the system.
2. `POST /api/generate-quiz`: Processes data and automatically generates 8 different types of multiple-choice and fill-in-the-blank exercises.
3. `POST /api/ask-ai`: Communication portal with the AI Assistant (Gemini) to answer grammar and vocabulary queries.

---

## 💻 Local Setup Instructions

### Step 1: Install Dependencies
Ensure you have Python installed. Open your Terminal in the project directory and run the following command:
```bash
pip install -r requirements.txt
