# Codex Philippines: AI-Powered Legal Research Platform

Codex Philippines is a next-generation legal research tool designed to modernize access to Philippine laws and jurisprudence. It combines a high-performance React frontend with a Python-based backend and advanced AI data pipelines to deliver a seamless, interlinked legal database.

## 🚀 Key Features

*   **LexCode**: A dedicated, distraction-free interface for reading Codals (e.g., Revised Penal Code, Civil Code) with integrated case references.
*   **AI-Driven Linking**: Automatically discovers semantic connections between specific legal provisions and Supreme Court decisions using Gemini AI.
*   **Smart Search**: Full-text search across thousands of cases and statutes.
*   **Responsive Design**: Modern UI built with React and Tailwind CSS.

## 📂 Project Structure

The project is organized into three main components:

### 1. Frontend (`src/frontend`)
*   **Tech Stack**: React, Vite, Tailwind CSS.
*   **Role**: Delivers the user interface, including LexCode, Case Reader, and Search.
*   **Key Components**: `LexCodeViewer.jsx`, `CaseReader.jsx`, `LexCodeStream.jsx`.

### 2. Backend API (`api/`)
*   **Tech Stack**: Python (Azure Functions model).
*   **Role**: Serves data to the frontend.
*   **Key Endpoints**:
    *   `/api/codex/rpc`: Fetches Revised Penal Code data.
    *   `/api/cases`: Search and retrieve Supreme Court decisions.

### 3. Data Pipeline (`LexCode/`)
*   **Tech Stack**: Python, PostgreSQL, Gemini AI.
*   **Role**: The engine room for data ingestion and processing.
*   **Key Pipelines**:
    *   **Ingestion**: Scrapes, parses, and structures raw legal text (`LexCode/pipelines/`).
    *   **Linking**: `LexCode/linker/universal_rpc_linker.py` orchestrates the AI linking process.

## 🛠️ Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   PostgreSQL (Local or Cloud)
*   Google Gemini API Key

### Running the Application

The project includes a master script to start both the frontend and backend services:

```powershell
./start_all.ps1
```

This will:
1.  Start the Python Backend API (Port 7071).
2.  Start the React Frontend (Port 5300).
3.  Launch the application in your default browser.

## 📖 Developer Documentation

For detailed instructions on adding new legal codes or managing the data pipeline, refer to the **[Codex Ingestion Blueprint](file:///c:/Users/rnlar/.gemini/antigravity/brain/118b2014-cc53-449a-971e-116bbcc9f742/codex_ingestion_blueprint.md)**.

## 🧹 Maintenance

The project structure is kept clean by concentrating active development logic in specific directories. 
*   **Core Scripts**: Found in `LexCode/` (including `LexCode/linker/universal_rpc_linker.py`).
*   **Cleanup**: Use `scripts/cleanup_clutter.py` (if available) or manual removal for temporary debug scripts.
