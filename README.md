# 🤖 Voice AI Assistant

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) 
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi) 
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white) 
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

A powerful Voice AI assistant that can answer questions about your documents, summarize text, and generate reports using AI. Driven by a robust Retrieval-Augmented Generation (RAG) architecture and fully containerized for seamless cross-platform deployment.

## ✨ Features

- 🎤 **Voice Input**: Speak directly to the AI via integrated interfaces.
- 🧠 **RAG Architecture**: Intelligently retrieves relevant information from your specific documents.
- 📝 **Summarization**: Condenses long-form texts into concise, actionable key points.
- 📊 **Report Generation**: Automatically creates structured reports from complex data.
- 💬 **Chat Interface**: Have a natural, contextual conversation with the AI assistant.
- 🐳 **Automated CI/CD**: Fully containerized and automated with GitHub Actions, pushing directly to Docker Hub upon every code change.

## 🛠️ Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python 3.11, FastAPI
- **AI/ML**: Sentence Transformers, ChromaDB, OpenAI API
- **Deployment & DevOps**: Docker, Docker Compose, GitHub Actions
- **Infrastructure**: MongoDB, ngrok (for local tunneling)

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed on your machine:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Git
- An OpenAI API Key 

### Installation & Running Locally

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Voice_AI
   ```

2. **Set up environment variables**
   Create a `.env` file in the `backend` directory using the provided example:
   ```bash
   cp backend/.env.example backend/.env
   ```
   *Make sure to open `backend/.env` and add your valid `OPENAI_API_KEY` and other necessary credentials.*

3. **Build and start the application using Docker**
   Because this project is fully containerized, you can simply pull the image or build it from scratch!
   
   **Option A: Pull the automated image from Docker Hub (Fastest)**
   ```bash
   docker pull sanketrautel45/voice_ai:latest
   docker run -p 8000:8000 --env-file backend/.env sanketrautel45/voice_ai:latest
   ```

   **Option B: Build locally**
   ```bash
   docker build -t voice-ai .
   docker run -p 8000:8000 --env-file backend/.env voice-ai
   ```

4. **Access the application**
   - **Frontend UI / API:** Open your browser and navigate to `http://localhost:8000`
   - **Interactive API Docs:** Navigate to `http://localhost:8000/docs` to see the FastAPI Swagger UI.

## ⚙️ CI/CD & Automation

This project follows modern DevOps practices. A dedicated GitHub Actions workflow is set up to automatically test, build, and push a slim, optimized Docker image straight to Docker Hub on every push to the `main` branch.

- **Docker Image Repository**: [`sanketrautel45/voice_ai:latest`](https://hub.docker.com/r/sanketrautel45/voice_ai)
- **Workflow configuration**: Located in `.github/workflows/publish.yml`
