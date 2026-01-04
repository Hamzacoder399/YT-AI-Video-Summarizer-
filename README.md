# YouTube AI Video Summarizer & Q&A Chatbot

An AI-powered web application that summarizes long-form YouTube videos and allows users to ask follow-up questions using an integrated AI chatbot.

Built to demonstrate practical AI integration, clean frontend–backend interaction, and real-world usability.

---

## 🚀 Features

- **YouTube Video Summarization**
  - Extracts and summarizes long-form YouTube video transcripts
  - Produces concise, readable AI-generated summaries

- **AI-Powered Q&A Chatbot**
  - Ask contextual questions based on the generated summary
  - Maintains conversation relevance using the video summary
  - Prompt usage limit enforced (max 8 questions per video)

- **Spam & Abuse Protection**
  - Ask button disabled while a request is processing
  - Prevents multiple concurrent requests
  - Automatic disabling once prompt limit is reached

- **Clean UX**
  - Loading indicators for long operations
  - Clear error handling (missing transcript, network errors, limits reached)
  - Simple and responsive interface

- **Secure by Design**
  - Environment variables used for API keys
  - `.env` excluded from version control
    
---

## 🛠 Tech Stack

- **Frontend:** HTML, CSS, Vanilla JavaScript (Fetch API)
- **Backend:** Python, Flask
- **AI Model:** Mistral AI
- **Version Control:** Git & GitHub

---

## 📂 Project Structure
├── app.py
├── templates/
│ └── index.html
├── static/
│ └── design.css
├── .gitignore
└── README.md
