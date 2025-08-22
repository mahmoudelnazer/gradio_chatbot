# 🤖 Conversational Assistant - Documentation

## Overview

The Conversational Assistant is a Python-based chatbot application built with Gradio that helps users schedule meetings and send emails through natural language conversations. The system uses Google's Gemini AI for intent classification and entity extraction, with fallback rule-based functionality when the API is unavailable.

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Architecture](#architecture)
6. [API Reference](#api-reference)
7. [File Structure](#file-structure)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## Features

- **Natural Language Processing**: Understands user intents and extracts relevant information
- **Conversation Memory**: Maintains context across multiple interactions
- **Multi-intent Support**: Handles meeting scheduling and email sending
- **Fallback System**: Works even without API access using rule-based approaches
- **Session Management**: Supports multiple conversation sessions
- **Data Persistence**: Saves conversations and actions to JSON files
- **Visual Interface**: Clean Gradio-based web UI with state visualization

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Steps

1. Clone or download the project files
2. Install required dependencies:

```bash
pip install gradio requests python-dotenv dateutil
```

3. Set up environment variables (optional):

```bash
# Create a .env file in the project root
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variable:

```
GEMINI_API_KEY=your_google_gemini_api_key_here
```

You can obtain a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### File Structure

The application creates the following directories automatically:

- `conversations/` - Stores conversation history JSON files
- `outbox/` - Stores executed actions (meetings and emails) as JSON files

## Usage

### Running the Application

```bash
pip install -r requirements.txt
python main.py
```

The application will start a web server accessible at:
- Local: http://0.0.0.0:7860
- Network: http://your-ip-address:7860

### How to Use

1. **Start a Conversation**: Type your request in natural language
2. **Provide Information**: The assistant will ask for any missing details
3. **Confirm Actions**: Review and confirm before execution
4. **View State**: Monitor the conversation state in the right panel

### Example Interactions

**Scheduling a Meeting:**
```
User: I want to schedule a meeting with John tomorrow at 3pm
Assistant: What should I call this meeting?
User: Project kickoff
Assistant: Do you want me to book 'Project kickoff' on 2023-12-15 at 3pm with john@example.com?
User: Yes
Assistant: ✅ Meeting 'Project kickoff' has been booked for 2023-12-15 at 3pm. Details saved to files.
```

**Sending an Email:**
```
User: I need to send an email to Sarah
Assistant: What should the email say?
User: Please review the quarterly report by Friday
Assistant: Do you want me to send an email to sarah@company.com saying: 'Please review the quarterly report by Friday'?
User: Yes
Assistant: ✅ Email sent to sarah@company.com. Details saved to files.
```

## Architecture

### Core Components

1. **GeminiAssistant Class**: Main logic for conversation processing
2. **Intent Classification**: Determines user goals (schedule_meeting, send_email, chitchat)
3. **Entity Extraction**: Identifies relevant information from user messages
4. **State Management**: Tracks conversation context and missing information
5. **Action Execution**: Performs the requested actions and saves results

### Workflow

1. User inputs a message
2. System classifies intent using Gemini AI or fallback rules
3. Entities are extracted with conversation context
4. Missing information is identified and requested
5. Once all information is gathered, confirmation is requested
6. Upon confirmation, the action is executed and saved

## API Reference

### GeminiAssistant Class

#### Methods

- `__init__()`: Initializes the assistant with API configuration
- `reset_session()`: Starts a new conversation session
- `save_conversation()`: Saves conversation to JSON file
- `get_conversation_history()`: Retrieves recent conversation history
- `save_action()`: Saves executed actions to JSON file
- `call_gemini()`: Calls the Gemini API with a prompt
- `classify_intent()`: Determines user intent from message
- `extract_entities_with_context()`: Extracts relevant information from message
- `process_message()`: Main method to process user input and generate response
- `execute_action()`: Executes the confirmed action (meeting or email)

### Key Functions

- `chat_function(message, history)`: Main chat function for Gradio interface
- `new_chat()`: Resets the conversation and starts a new session

## File Structure

```
project/
├── assistant.py          # Main application file
├── .env                  # Environment variables (optional)
├── conversations/        # Auto-created directory for conversation history
│   ├── actions.json      # All executed actions
│   └── conversations_*.json  # Individual conversation sessions
├── outbox/               # Auto-created directory for executed actions
│   ├── email_*.json      # Sent email details
│   └── meeting_*.json    # Scheduled meeting details
└── README.md             # This documentation
```

## Examples

### Example Inputs

1. "I want to schedule a meeting with John tomorrow at 3pm"
2. "Please send an email to sarah@example.com"
3. "Book a project review meeting for next Monday"
4. "Actually, I want to send an email instead"
5. "Hello there!"

### Output Files

**Meeting JSON:**
```json
{
  "type": "meeting",
  "title": "Project Review",
  "date": "2023-12-18",
  "time": "15:00",
  "participants": "john@example.com, sarah@example.com",
  "created_at": "2023-12-15T10:30:45.123456"
}
```

**Email JSON:**
```json
{
  "type": "email",
  "recipient": "sarah@example.com",
  "subject": "Project Update",
  "body": "Please review the latest project updates",
  "created_at": "2023-12-15T10:32:15.654321"
}
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Solution: Add your Gemini API key to the `.env` file or use the fallback mode

2. **Module Not Found Errors**
   - Solution: Install missing packages with `pip install package_name`

3. **Port Already in Use**
   - Solution: Change the port in the `demo.launch()` call or terminate other processes using port 7860

4. **Fallback Mode Activated**
   - Indication: "⚠️ No Gemini API key found. Using fallback mode." message
   - Solution: Add a valid API key or accept limited functionality

### Debugging

- Check the console for error messages
- Verify the `.env` file is in the correct location
- Ensure required directories have write permissions
- Review generated JSON files for data consistency

