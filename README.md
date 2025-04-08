# Conversational Document and Video Chatbot

A Flask-based web application that leverages the LLaVA 7B model to create an interactive chatbot capable of processing text queries, images, PDFs, Word documents, CSVs, Excel files, and videos. The chatbot supports conversation history, a user-populated knowledge base, and real-time streaming responses, all wrapped in a visually appealing UI with animations.

## Features

- **Multi-Format Input Support**: Process text queries, images (JPG, PNG, JPEG), PDFs, Word documents (DOCX), CSVs, Excel files (XLSX), and videos (MP4).
- **Image Recognition**: Uses LLaVA 7B to describe image content in detail.
- **Video Analysis**: Extracts audio (speech-to-text) and visual content (frame-based descriptions) from videos.
- **Knowledge Base**: Users can add content to a simple in-memory knowledge base and retrieve relevant information based on queries.
- **Conversation History**: Maintains a rolling history of the last 3 interactions for context-aware responses.
- **Streaming Responses**: Real-time response streaming from the LLaVA model for a smooth user experience.
- **Responsive UI**: A modern, animated interface with gradient backgrounds, scrollable chat history, and file upload capabilities.

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally with the `llava:7b` model pulled (`ollama pull llava:7b`).
- A web browser (e.g., Chrome, Firefox) for accessing the UI.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/conversational-chatbot.git
   cd conversational-chatbot

## File Structure
![image](https://github.com/user-attachments/assets/549c6280-0913-4182-b85e-34dca5e469db)

## Dependencies

- **Flask**: Web framework for the backend.
- **requests**: For API calls to Ollama.
- **PyPDF2**: PDF text extraction.
- **python-docx**: Word document text extraction.
- **moviepy**: Video processing.
- **speechrecognition**: Audio-to-text conversion.
- **pandas**: CSV and Excel file handling.
- **openpyxl**: Excel file support.
- **difflib**: Keyword similarity matching for knowledge base retrieval.

## Notes

- **Ollama Configuration**: The app assumes Ollama is running locally at `http://localhost:11434`. Update `OLLAMA_API_URL` in `main.py` if your setup differs.
- **Temporary Files**: Video processing creates temporary files (`temp_video.mp4`, `temp_audio.wav`, `temp_frame_*.jpg`), which are cleaned up automatically.
- **Knowledge Base**: Stored in memory and resets on app restart. For persistence, consider integrating a database.
- **Uploads Directory**: Create `static/uploads/` manually if you plan to store uploaded files persistently (current code processes files in-memory).

## Limitations

- Video processing may fail for large files due to memory constraints or if dependencies (e.g., FFmpeg for `moviepy`) are not installed.
- Speech recognition relies on Google’s API and requires an internet connection.
- The knowledge base uses simple keyword matching; advanced NLP could improve retrieval accuracy.

## Acknowledgments

- Built with [LLaVA](https://github.com/haotian-liu/LLaVA) via [Ollama](https://ollama.ai/).
- Inspired by modern chatbot UIs and Flask tutorials.
