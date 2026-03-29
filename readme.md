# 🤖 Rasa Project – Clean & Scalable Setup

This is a well-structured Rasa project designed to make development easier, faster, and more manageable.
It provides a clean foundation for building and maintaining conversational AI applications efficiently.

---

## 🚀 What This Project Offers

* Organized project structure for better readability
* Easy setup for quick development
* Scalable design for real-world chatbot applications
* Ready-to-use Rasa configuration

---

## 📁 Project Structure

```
.
├── actions/           # Custom actions
├── data/              # NLU & stories
├── models/            # Trained models (ignored in git)
├── domain.yml         # Bot responses & intents
├── config.yml         # Pipeline & policies
├── endpoints.yml      # Action server config
└── actions.py         # Custom logic
```

---

## ⚙️ Installation

### 1️⃣ Create Virtual Environment

```bash
python -m venv env
```

### 2️⃣ Activate Environment

```bash
# Windows
env\Scripts\activate

# Linux / Mac
source env/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip install rasa
```

---

## 🏗️ Initialize Project (If Starting Fresh)

```bash
rasa init
```

---

## 🧠 Train the Model

```bash
rasa train
```

---

## 💬 Run the Chatbot

```bash
rasa shell
```

---

## ⚡ Run Action Server (If Using Custom Actions)

```bash
rasa run actions
```

---

## 🌐 Run API Server (Optional)

```bash
rasa run --enable-api --cors "*"
```

---

## 🧠 How It Works

```
User Message
   ↓
NLU (Intent + Entities)
   ↓
Stories / Rules
   ↓
Actions (Custom Logic)
   ↓
Response to User
```

---

## 🔧 Customization

* Add intents → `data/nlu.yml`
* Add stories → `data/stories.yml`
* Update responses → `domain.yml`
* Add logic → `actions.py`

---

## ⚠️ Important Notes

* `models/` folder is ignored (auto-generated)
* `.env` should never be committed
* Use Python 3.10 for best compatibility

---

## 🚀 Future Improvements

* Integrate with Flask backend
* Add database connectivity
* Build API-based chatbot
* Deploy using Docker

---

## 🤝 Contribution

Feel free to contribute by improving structure, adding features, or optimizing performance.

---

## 📄 License

This project is open-source and available for learning and development purposes.

---
