from flask import Flask, render_template, request, Response
import requests
import base64
from collections import deque
import json
import PyPDF2
from docx import Document
import moviepy
import speech_recognition as sr
import os
import io
import pandas as pd
import difflib

app = Flask(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"

conversation_history = deque(maxlen=3)
last_image_context = None

# Initialize an empty knowledge base that will be populated by user input
# This will reset with each run of main.py
KNOWLEDGE_BASE = []

# Function to add a document to the knowledge base
def add_to_knowledge_base(content):
    # Generate keywords by splitting the content into words and filtering out short words
    words = content.lower().split()
    keywords = [word for word in words if len(word) > 3]  # Simple keyword extraction (words longer than 3 characters)
    doc = {
        "id": len(KNOWLEDGE_BASE) + 1,  # Assign a unique ID
        "content": content,
        "keywords": keywords
    }
    KNOWLEDGE_BASE.append(doc)
    return f"Added to knowledge base: {content}"

# Function to retrieve relevant documents from the knowledge base
def retrieve_relevant_documents(query, top_k=2):
    if not KNOWLEDGE_BASE:
        return []  # Return empty list if knowledge base is empty
    
    # Simple keyword-based retrieval using string similarity
    query_words = query.lower().split()
    scores = []
    
    for doc in KNOWLEDGE_BASE:
        doc_keywords = doc["keywords"]
        score = sum(difflib.SequenceMatcher(None, word, keyword).ratio() for word in query_words for keyword in doc_keywords)
        scores.append((score, doc))
    
    # Sort documents by score and return the top_k
    scores.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for _, doc in scores[:top_k]]
    return top_docs

# Function to log processed data to a file
def log_processed_data(filename, content):
    with open("processed_data.txt", "a", encoding="utf-8") as output_file:
        output_file.write(f"--- File: {filename} ---\n")
        output_file.write(f"Extracted Content:\n{content}\n\n")

# Helper functions to extract text from different file types
def extract_text_from_pdf(file):
    file.seek(0)
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    file.seek(0)
    doc = Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_csv(file):
    file.seek(0)
    df = pd.read_csv(file)
    text = df.to_string()
    return text

def extract_text_from_xlsx(file):
    file.seek(0)
    df = pd.read_excel(file, engine='openpyxl')
    text = df.to_string()
    return text

def extract_text_from_video(file):
    try:
        file.seek(0)
        with open("temp_video.mp4", "wb") as f:
            f.write(file.read())

        if not os.path.exists("temp_video.mp4"):
            return "Error: Failed to save the video file."

        try:
            video = moviepy.VideoFileClip("temp_video.mp4")
        except Exception as e:
            return f"Error: Failed to process video with moviepy: {str(e)}"

        # Extract audio if available
        audio_text = "No audio detected."
        if video.audio:
            audio_path = "temp_audio.wav"
            try:
                video.audio.write_audiofile(audio_path)
                recognizer = sr.Recognizer()
                with sr.AudioFile(audio_path) as source:
                    audio = recognizer.record(source)
                    audio_text = recognizer.recognize_google(audio)
            except sr.RequestError as e:
                audio_text = f"Speech recognition failed (network issue): {str(e)}"
            except sr.UnknownValueError:
                audio_text = "Could not understand the audio."
            except Exception as e:
                audio_text = f"Speech recognition failed: {str(e)}"
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

        # Extract frames at 0.5-second intervals
        duration = video.duration
        interval = 0.5  # Extract a frame every 0.5 seconds
        timestamps = [i * interval for i in range(int(duration // interval) + 1)]
        
        # Ensure timestamps don't exceed the video duration
        timestamps = [min(t, duration) for t in timestamps if t <= duration]
        
        # Process all timestamps as extracted
        if not timestamps:
            timestamps = [duration / 2 if duration > 0 else 0.0]  # Fallback for very short videos

        visual_texts = []
        for i, t in enumerate(timestamps):
            if t <= duration:  # Double-check to avoid exceeding duration
                frame_path = f"temp_frame_{i}.jpg"
                try:
                    video.save_frame(frame_path, t=t)
                    with open(frame_path, "rb") as image_file:
                        image_data = image_file.read()
                        image_base64 = base64.b64encode(image_data).decode("utf-8")
                        response = requests.post(
                            OLLAMA_API_URL,
                            json={
                                "model": "llava:7b",
                                "prompt": "Describe the content of this image in detail, including the setting, characters, actions, and any text or objects visible.",
                                "images": [image_base64],
                                "stream": False
                            }
                        )
                        response.raise_for_status()
                        visual_text = response.json().get("response", "Error processing image.")
                        # Highlight the last frame as the most important
                        if i == len(timestamps) - 1:
                            visual_texts.append(f"Final Frame at {t:.1f} seconds (most relevant for identifying the main subject): {visual_text}")
                        else:
                            visual_texts.append(f"Frame at {t:.1f} seconds: {visual_text}")
                except Exception as e:
                    visual_texts.append(f"Frame at {t:.1f} seconds: Error processing frame: {str(e)}")
                finally:
                    if os.path.exists(frame_path):
                        os.remove(frame_path)

        video.close()
        if os.path.exists("temp_video.mp4"):
            os.remove("temp_video.mp4")

        visual_description = "\n".join(visual_texts) if visual_texts else "No visual content extracted."
        return f"Audio Content: {audio_text}\nVisual Content:\n{visual_description}"
    except Exception as e:
        return f"Error processing video: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    global last_image_context
    query = request.form.get("query")
    file = request.files.get("file")

    # Check if the query is a command to add to the knowledge base
    if query.lower().startswith("add to knowledge base:"):
        content = query[len("add to knowledge base:"):].strip()
        if content:
            response = add_to_knowledge_base(content)
            conversation_history.append(f"User: {query}")
            conversation_history.append(f"Bot: {response}")
            return Response(response, mimetype="text/plain")
        else:
            response = "Error: No content provided to add to the knowledge base."
            conversation_history.append(f"User: {query}")
            conversation_history.append(f"Bot: {response}")
            return Response(response, mimetype="text/plain")

    conversation_history.append(f"User: {query}")

    file_content = None
    image_base64 = None
    if file and file.filename != '':
        filename = file.filename.lower()
        if filename.endswith((".jpg", ".jpeg", ".png")):
            file_data = file.read()
            image_base64 = base64.b64encode(file_data).decode("utf-8")
            file_content = "Image uploaded."
            log_processed_data(filename, file_content)
        elif filename.endswith(".pdf"):
            file_content = extract_text_from_pdf(file)
            conversation_history.append(f"Bot: Extracted text from PDF:\n{file_content}")
            log_processed_data(filename, file_content)
        elif filename.endswith(".docx"):
            file_content = extract_text_from_docx(file)
            conversation_history.append(f"Bot: Extracted text from DOCX:\n{file_content}")
            log_processed_data(filename, file_content)
        elif filename.endswith(".csv"):
            file_content = extract_text_from_csv(file)
            conversation_history.append(f"Bot: Extracted text from CSV:\n{file_content}")
            log_processed_data(filename, file_content)
        elif filename.endswith(".xlsx"):
            file_content = extract_text_from_xlsx(file)
            conversation_history.append(f"Bot: Extracted text from XLSX:\n{file_content}")
            log_processed_data(filename, file_content)
        elif filename.endswith(".mp4"):
            file_content = extract_text_from_video(file)
            audio_content = ""
            visual_content = ""
            for line in file_content.split("\n"):
                if line.startswith("Audio Content:"):
                    audio_content = line.replace("Audio Content:", "").strip()
                elif line.startswith("Visual Content:") or visual_content:
                    visual_content += line + "\n"
            conversation_history.append(f"Bot: Extracted content from video:\nAudio: {audio_content}\n{visual_content}")
            log_processed_data(filename, file_content)
        else:
            file_content = f"Unsupported file format: {filename}"
            conversation_history.append(f"Bot: {file_content}")
            log_processed_data(filename, file_content)

    def generate_response():
        global last_image_context

        # Retrieve relevant documents from the user-created knowledge base
        retrieved_docs = retrieve_relevant_documents(query, top_k=2)
        retrieved_context = "\n".join([f"Retrieved Document {doc['id']}: {doc['content']}" for doc in retrieved_docs]) if retrieved_docs else "No relevant documents found in the knowledge base."

        # Build the prompt with conversation history, retrieved context, and extracted file content
        context = "\n".join(conversation_history) if conversation_history else ""
        if image_base64:
            prompt = (
                f"{context}\n"
                f"[Image Context: The previous image is part of this conversation.]\n"
                f"Additional Context from Knowledge Base:\n{retrieved_context}\n"
                f"Query: {query}\n"
                f"Answer: If this is a video, provide a concise summary of its overall content, focusing on the main theme, key elements (like settings, characters, actions, and objects), and identify the company being advertised if it’s an ad. Use the retrieved context to provide additional information if relevant. Do not mention frame-by-frame analysis or specific frame details."
            )
            payload = {
                "model": "llava:7b",
                "prompt": prompt,
                "images": [image_base64],
                "stream": True
            }
        else:
            if last_image_context:
                prompt = (
                    f"{context}\n"
                    f"[Context: {last_image_context}]\n"
                    f"Additional Context from Knowledge Base:\n{retrieved_context}\n"
                    f"Query: {query}\n"
                    f"Answer: If this is a video, provide a concise summary of its overall content, focusing on the main theme, key elements (like settings, characters, actions, and objects), and identify the company being advertised if it’s an ad. Use the retrieved context to provide additional information if relevant. Do not mention frame-by-frame analysis or specific frame details."
                )
            else:
                prompt = (
                    f"{context}\n"
                    f"Additional Context from Knowledge Base:\n{retrieved_context}\n"
                    f"Query: {query}\n"
                    f"Answer: If this is a video, provide a concise summary of its overall content, focusing on the main theme, key elements (like settings, characters, actions, and objects), and identify the company being advertised if it’s an ad. Use the retrieved context to provide additional information if relevant. Do not mention frame-by-frame analysis or specific frame details."
                )
            payload = {
                "model": "llava:7b",
                "prompt": prompt,
                "stream": True
            }

        try:
            response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    chunk = data.get("response", "")
                    full_response += chunk
                    yield chunk

            last_image_context = full_response if image_base64 else last_image_context
            conversation_history.append(f"Bot: {full_response}")

        except requests.exceptions.RequestException as e:
            error_message = f"Error: {str(e)}"
            yield error_message
            conversation_history.append(f"Bot: {error_message}")

    return Response(generate_response(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)