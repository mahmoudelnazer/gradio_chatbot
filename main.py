import gradio as gr
import json
import os
from datetime import datetime, timedelta
import re
import requests
from typing import Dict, Any, Optional, Tuple, List
import dateutil.parser
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class GeminiAssistant:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.api_url = GEMINI_API_URL
        self.session_id = str(uuid.uuid4())
        self.conversation_file = f"conversations_{self.session_id[:8]}.json"
        
        if self.api_key:
            print(f"✅ Gemini API key loaded successfully")
            self._test_api_connection()
        else:
            print("⚠️  No Gemini API key found. Using fallback mode.")
        
        self.conversation_state = {
            "intent": None,
            "entities": {},
            "awaiting_confirmation": False,
            "pending_action": None,
            "conversation_context": [],
            "gathering_info": False,
            "missing_fields": []
        }
        
        # Ensure directories exist
        os.makedirs("outbox", exist_ok=True)
        os.makedirs("conversations", exist_ok=True)
    
    def reset_session(self):
        """Start a new chat session"""
        self.session_id = str(uuid.uuid4())
        self.conversation_file = f"conversations_{self.session_id[:8]}.json"
        self.conversation_state = {
            "intent": None,
            "entities": {},
            "awaiting_confirmation": False,
            "pending_action": None,
            "conversation_context": [],
            "gathering_info": False,
            "missing_fields": []
        }
        print(f"🔄 New chat session started: {self.session_id[:8]}")
    
    def save_conversation(self, user_message: str, assistant_response: str, intent: str = None, entities: dict = None, awaiting_confirmation: bool = False):
        """Save conversation to JSON file"""
        try:
            conversation_data = {
                "session_id": self.session_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "intent": intent,
                "entities": entities or {},
                "awaiting_confirmation": awaiting_confirmation,
                "timestamp": datetime.now().isoformat()
            }
            
            # Read existing conversations
            conversation_path = f"conversations/{self.conversation_file}"
            conversations = []
            if os.path.exists(conversation_path):
                with open(conversation_path, 'r') as f:
                    conversations = json.load(f)
            
            # Add new conversation
            conversations.append(conversation_data)
            
            # Save back to file
            with open(conversation_path, 'w') as f:
                json.dump(conversations, f, indent=2)
                
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history from JSON file"""
        try:
            conversation_path = f"conversations/{self.conversation_file}"
            if not os.path.exists(conversation_path):
                return []
            
            with open(conversation_path, 'r') as f:
                conversations = json.load(f)
            
            # Return recent conversations
            return conversations[-limit:] if conversations else []
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def save_action(self, action_type: str, action_data: dict, executed: bool = False):
        """Save executed action to JSON file"""
        try:
            action_data_full = {
                "session_id": self.session_id,
                "action_type": action_type,
                "action_data": action_data,
                "executed": executed,
                "timestamp": datetime.now().isoformat()
            }
            
            # Read existing actions
            actions_path = "conversations/actions.json"
            actions = []
            if os.path.exists(actions_path):
                with open(actions_path, 'r') as f:
                    actions = json.load(f)
            
            # Add new action
            actions.append(action_data_full)
            
            # Save back to file
            with open(actions_path, 'w') as f:
                json.dump(actions, f, indent=2)
                
        except Exception as e:
            print(f"Error saving action: {e}")
    
    def _test_api_connection(self):
        """Test if the API key works"""
        try:
            response = self.call_gemini("Hello")
            if response and not response.startswith("ERROR"):
                print("✅ Gemini API connection successful")
            else:
                print("❌ Gemini API connection failed")
        except Exception as e:
            print(f"❌ Failed to connect to Gemini API: {e}")
    
    def call_gemini(self, prompt: str) -> str:
        """Call Gemini API using REST endpoint"""
        if not self.api_key:
            return self._fallback_response(prompt)
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500
            }
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content.strip()
                else:
                    print("No content in Gemini response")
                    return self._fallback_response(prompt)
            else:
                print(f"Gemini API error: {response.status_code} - {response.text}")
                return self._fallback_response(prompt)
                
        except requests.exceptions.Timeout:
            print("Gemini API timeout")
            return self._fallback_response(prompt)
        except requests.exceptions.RequestException as e:
            print(f"Gemini API request error: {e}")
            return self._fallback_response(prompt)
        except Exception as e:
            print(f"Unexpected error calling Gemini API: {e}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Rule-based fallback when Gemini is not available"""
        user_input = prompt.split("User input:")[-1].strip() if "User input:" in prompt else prompt
        
        # Intent classification
        if any(word in user_input.lower() for word in ["book", "schedule", "meeting", "appointment"]):
            return "INTENT: schedule_meeting"
        elif any(word in user_input.lower() for word in ["send", "email", "mail", "message"]):
            return "INTENT: send_email"
        else:
            return "INTENT: chitchat"
    
    def detect_intent_change(self, user_input: str, current_intent: str) -> bool:
        """Detect if user wants to switch to a different task"""
        if not current_intent:
            return False
        
        # Keywords for different intents
        meeting_keywords = ["book", "schedule", "meeting", "appointment", "call"]
        email_keywords = ["send", "email", "mail", "message"]
        
        # Check if user is switching tasks
        if current_intent == "send_email" and any(word in user_input.lower() for word in meeting_keywords):
            return True
        elif current_intent == "schedule_meeting" and any(word in user_input.lower() for word in email_keywords):
            return True
        
        # Also check with Gemini for more nuanced detection
        if self.api_key:
            prompt = f"""
            Current task: {current_intent}
            User input: "{user_input}"
            
            Is the user trying to switch to a different task? Consider:
            - If they were scheduling a meeting but now want to send an email
            - If they were sending an email but now want to schedule a meeting
            - Phrases like "actually", "instead", "no", "sorry", "wait"
            
            Answer only: YES or NO
            """
            
            response = self.call_gemini(prompt)
            if "yes" in response.lower():
                return True
        
        return False
    
    def classify_intent(self, user_input: str) -> str:
        """Classify user intent using Gemini with context"""
        # Get conversation history for context
        history = self.get_conversation_history(5)
        context = ""
        if history:
            context = "\n\nRecent conversation context:\n"
            for conv in history[-3:]:  # Last 3 exchanges
                context += f"User: {conv['user_message']}\n"
                context += f"Assistant: {conv['assistant_response']}\n"
        
        prompt = f"""
        Classify the following user input into one of these intents:
        1. schedule_meeting - user wants to book/schedule a meeting
        2. send_email - user wants to send an email
        3. chitchat - general conversation, greetings, or other topics
        
        Consider the conversation context to understand if the user is providing missing information for a previous request.
        Also look for intent switching - if they were doing one task but now want to do another.
        {context}
        
        Current user input: {user_input}
        
        Respond with only the intent name (schedule_meeting, send_email, or chitchat).
        """
        
        response = self.call_gemini(prompt)
        
        # Extract intent from response
        if "schedule_meeting" in response.lower():
            return "schedule_meeting"
        elif "send_email" in response.lower():
            return "send_email"
        else:
            return "chitchat"
    
    def extract_entities_with_context(self, user_input: str, intent: str) -> Dict[str, Any]:
        """Extract entities with conversation context"""
        # Get conversation history
        history = self.get_conversation_history(5)
        
        # Build context from previous conversations for the SAME intent
        previous_entities = {}
        context_info = ""
        
        if history:
            context_info = "\n\nPrevious conversation context:\n"
            for conv in history:
                if conv['intent'] == intent and conv['entities']:  # Only use entities from same intent
                    for key, value in conv['entities'].items():
                        if value and value != "N/A" and value.strip():
                            previous_entities[key] = value
                    context_info += f"User: {conv['user_message']}\n"
                    context_info += f"Previous entities: {conv['entities']}\n"
        
        if intent == "schedule_meeting":
            entities = self._extract_meeting_entities_with_context(user_input, context_info, previous_entities)
        elif intent == "send_email":
            entities = self._extract_email_entities_with_context(user_input, context_info, previous_entities)
        else:
            entities = {}
        
        # Merge with previous entities (current input takes precedence)
        merged_entities = previous_entities.copy()
        merged_entities.update(entities)
        
        return merged_entities
    
    def _extract_meeting_entities_with_context(self, user_input: str, context: str, previous_entities: dict) -> Dict[str, Any]:
        """Extract meeting entities with context"""
        prompt = f"""
        Extract meeting information from the current user input, considering the conversation context.
        
        {context}
        
        Current user input: "{user_input}"
        Previous entities found: {json.dumps(previous_entities, indent=2)}
        
        Look for:
        - Title/subject of the meeting
        - Date (today, tomorrow, specific dates, days of week)
        - Time (3pm, 15:00, etc.)
        - Participants/attendees (names, email addresses)
        
        If the user is just providing a missing piece of information (like just an email address or just a time), 
        extract only that new information. Don't repeat information that was already provided.
        
        Return in this exact format:
        TITLE: [meeting title if mentioned, or leave empty]
        DATE: [date if mentioned, or leave empty]
        TIME: [time if mentioned, or leave empty]
        PARTICIPANTS: [participants if mentioned, or leave empty]
        """
        
        response = self.call_gemini(prompt)
        entities = {}
        
        # Parse response or use regex fallback
        if self.api_key and not response.startswith("INTENT:"):
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('TITLE:') and line.split('TITLE:')[1].strip():
                    entities['title'] = line.split('TITLE:')[1].strip()
                elif line.startswith('DATE:') and line.split('DATE:')[1].strip():
                    entities['date'] = line.split('DATE:')[1].strip()
                elif line.startswith('TIME:') and line.split('TIME:')[1].strip():
                    entities['time'] = line.split('TIME:')[1].strip()
                elif line.startswith('PARTICIPANTS:') and line.split('PARTICIPANTS:')[1].strip():
                    entities['participants'] = line.split('PARTICIPANTS:')[1].strip()
        else:
            # Regex fallback
            entities = self._regex_extract_meeting(user_input)
        
        # Process date
        if 'date' in entities:
            entities['date'] = self._parse_date(entities['date'])
        
        return entities
    
    def _extract_email_entities_with_context(self, user_input: str, context: str, previous_entities: dict) -> Dict[str, Any]:
        """Extract email entities with context"""
        prompt = f"""
        Extract email information from the current user input, considering the conversation context.
        
        {context}
        
        Current user input: "{user_input}"
        Previous entities found: {json.dumps(previous_entities, indent=2)}
        
        Look for:
        - Recipient email address or name
        - Email body/message content
        - Subject (optional)
        
        If the user is just providing a missing piece of information (like just an email address or just a message), 
        extract only that new information. Don't repeat information that was already provided.
        
        Return in this exact format:
        RECIPIENT: [email address or name if mentioned, or leave empty]
        SUBJECT: [subject line if mentioned, or leave empty]
        BODY: [email content/message if mentioned, or leave empty]
        """
        
        response = self.call_gemini(prompt)
        entities = {}
        
        # Parse response or use regex fallback
        if self.api_key and not response.startswith("INTENT:"):
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('RECIPIENT:') and line.split('RECIPIENT:')[1].strip():
                    entities['recipient'] = line.split('RECIPIENT:')[1].strip()
                elif line.startswith('SUBJECT:') and line.split('SUBJECT:')[1].strip():
                    entities['subject'] = line.split('SUBJECT:')[1].strip()
                elif line.startswith('BODY:') and line.split('BODY:')[1].strip():
                    entities['body'] = line.split('BODY:')[1].strip()
        else:
            # Regex fallback
            entities = self._regex_extract_email(user_input)
        
        return entities
    
    def _regex_extract_meeting(self, text: str) -> Dict[str, Any]:
        """Regex-based meeting entity extraction"""
        entities = {}
        
        # Extract email addresses for participants
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if emails:
            entities['participants'] = ', '.join(emails)
        
        # Extract time patterns
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b',
            r'\b(\d{1,2})\s*(am|pm|AM|PM)\b',
            r'\b(\d{1,2}):(\d{2})\b'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                entities['time'] = match.group(0)
                break
        
        # Extract date patterns
        if 'tomorrow' in text.lower():
            entities['date'] = 'tomorrow'
        elif 'today' in text.lower():
            entities['date'] = 'today'
        elif 'next week' in text.lower():
            entities['date'] = 'next week'
        
        # Extract meeting title
        title_match = re.search(r'(?:book|schedule)\s+(?:a\s+)?(?:meeting\s+)?(?:with\s+)?([^.]+?)(?:\s+tomorrow|\s+today|\s+at|\s+with|\s*$)', text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if title and not any(word in title.lower() for word in ['tomorrow', 'today', 'at', 'with']):
                entities['title'] = title
        
        return entities
    
    def _regex_extract_email(self, text: str) -> Dict[str, Any]:
        """Regex-based email entity extraction"""
        entities = {}
        
        # Extract email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if emails:
            entities['recipient'] = emails[0]
        
        # Extract message content after "saying" or similar
        message_patterns = [
            r'saying\s+(.+)',
            r'that\s+(.+)',
            r'message\s*:\s*(.+)',
            r'email\s+(.+?)(?:\s+to|\s*$)'
        ]
        
        for pattern in message_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities['body'] = match.group(1).strip()
                break
        
        return entities
    
    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats"""
        date_str = date_str.lower().strip()
        today = datetime.now()
        
        if date_str == 'today':
            return today.strftime('%Y-%m-%d')
        elif date_str == 'tomorrow':
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in date_str:
            return (today + timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'monday' in date_str:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        
        try:
            parsed_date = dateutil.parser.parse(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return date_str
    
    def get_missing_fields(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        
        if intent == "schedule_meeting":
            if not entities.get('title') or not entities.get('title').strip():
                missing.append('title')
            if not entities.get('date') or not entities.get('date').strip():
                missing.append('date')
            if not entities.get('time') or not entities.get('time').strip():
                missing.append('time')
            if not entities.get('participants') or not entities.get('participants').strip():
                missing.append('participants')
        
        elif intent == "send_email":
            if not entities.get('recipient') or not entities.get('recipient').strip():
                missing.append('recipient')
            if not entities.get('body') or not entities.get('body').strip():
                missing.append('body')
        
        return missing
    
    def get_next_missing_field_question(self, intent: str, missing_fields: List[str]) -> Optional[str]:
        """Get the next question to ask for missing information"""
        if not missing_fields:
            return None
        
        field = missing_fields[0]  # Ask for the first missing field
        
        if intent == "schedule_meeting":
            questions = {
                'title': "What should I call this meeting?",
                'date': "What date would you like to schedule this meeting?",
                'time': "What time should the meeting be?",
                'participants': "Who should I invite to this meeting? Please provide their email addresses."
            }
            return questions.get(field)
        
        elif intent == "send_email":
            questions = {
                'recipient': "Who should I send the email to? Please provide their email address.",
                'body': "What should the email say?"
            }
            return questions.get(field)
        
        return None
    
    def generate_confirmation(self, intent: str, entities: Dict[str, Any]) -> str:
        """Generate confirmation message"""
        if intent == "schedule_meeting":
            title = entities.get('title', 'Meeting')
            date = entities.get('date', 'unspecified date')
            time = entities.get('time', 'unspecified time')
            participants = entities.get('participants', '')
            
            confirmation = f"Do you want me to book '{title}' on {date} at {time}"
            if participants:
                confirmation += f" with {participants}"
            confirmation += "?"
            return confirmation
        
        elif intent == "send_email":
            recipient = entities.get('recipient', 'unspecified recipient')
            body = entities.get('body', 'unspecified message')
            subject = entities.get('subject', '')
            
            confirmation = f"Do you want me to send an email to {recipient}"
            if subject:
                confirmation += f" with subject '{subject}'"
            confirmation += f" saying: '{body}'?"
            return confirmation
        
        return "Do you want me to proceed with this action?"
    
    def execute_action(self, intent: str, entities: Dict[str, Any]) -> str:
        """Execute the confirmed action"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if intent == "schedule_meeting":
            meeting_data = {
                "type": "meeting",
                "title": entities.get('title', 'Meeting'),
                "date": entities.get('date'),
                "time": entities.get('time'),
                "participants": entities.get('participants', ''),
                "created_at": datetime.now().isoformat()
            }
            
            # Save to JSON files
            self.save_action("meeting", meeting_data, executed=True)
            
            # Save to outbox
            filename = f"outbox/meeting_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(meeting_data, f, indent=2)
            
            return f"✅ Meeting '{meeting_data['title']}' has been booked for {meeting_data['date']} at {meeting_data['time']}. Details saved to files."
        
        elif intent == "send_email":
            email_data = {
                "type": "email",
                "recipient": entities.get('recipient'),
                "subject": entities.get('subject', 'No subject'),
                "body": entities.get('body'),
                "created_at": datetime.now().isoformat()
            }
            
            # Save to JSON files
            self.save_action("email", email_data, executed=True)
            
            # Save to outbox
            filename = f"outbox/email_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(email_data, f, indent=2)
            
            return f"✅ Email sent to {email_data['recipient']}. Details saved to files."
        
        return "Action completed."
    
    def process_message(self, message: str) -> Tuple[str, str]:
        """Process user message and return response + state info"""
        
        # Check if this is a confirmation response
        if self.conversation_state["awaiting_confirmation"]:
            if message.lower().strip() in ['yes', 'y', 'confirm', 'ok', 'okay', 'sure']:
                # Execute the action
                result = self.execute_action(
                    self.conversation_state["intent"],
                    self.conversation_state["entities"]
                )
                
                # Save conversation
                self.save_conversation(message, result, self.conversation_state["intent"], self.conversation_state["entities"], False)
                
                # Reset state completely
                self.conversation_state = {
                    "intent": None,
                    "entities": {},
                    "awaiting_confirmation": False,
                    "pending_action": None,
                    "conversation_context": [],
                    "gathering_info": False,
                    "missing_fields": []
                }
                
                return result, self._get_state_info()
            
            elif message.lower().strip() in ['no', 'n', 'cancel', 'nevermind']:
                # Cancel the action
                response = "Action cancelled. How else can I help you?"
                self.save_conversation(message, response, None, {}, False)
                
                # Reset state completely
                self.conversation_state = {
                    "intent": None,
                    "entities": {},
                    "awaiting_confirmation": False,
                    "pending_action": None,
                    "conversation_context": [],
                    "gathering_info": False,
                    "missing_fields": []
                }
                
                return response, self._get_state_info()
        
        # Check for intent switching if we're currently working on something
        current_intent = self.conversation_state.get("intent")
        if current_intent and (self.conversation_state.get("gathering_info") or self.conversation_state.get("awaiting_confirmation")):
            if self.detect_intent_change(message, current_intent):
                # User wants to switch tasks - reset state and start fresh
                self.conversation_state = {
                    "intent": None,
                    "entities": {},
                    "awaiting_confirmation": False,
                    "pending_action": None,
                    "conversation_context": [],
                    "gathering_info": False,
                    "missing_fields": []
                }
                # Continue with new intent classification below
        
        # Classify intent
        intent = self.classify_intent(message)
        self.conversation_state["intent"] = intent
        
        if intent == "chitchat":
            response = self._handle_chitchat(message)
            self.save_conversation(message, response, intent, {}, False)
            return response, self._get_state_info()
        
        # Extract entities with context
        entities = self.extract_entities_with_context(message, intent)
        
        # Update conversation state
        self.conversation_state["entities"] = entities
        
        # Check for missing entities
        missing_fields = self.get_missing_fields(intent, entities)
        self.conversation_state["missing_fields"] = missing_fields
        
        if missing_fields:
            # We're now in information gathering mode
            self.conversation_state["gathering_info"] = True
            
            # Ask for the next missing field
            missing_field_question = self.get_next_missing_field_question(intent, missing_fields)
            if missing_field_question:
                self.save_conversation(message, missing_field_question, intent, entities, False)
                return missing_field_question, self._get_state_info()
        
        # All required information is available - generate confirmation
        self.conversation_state["gathering_info"] = False
        confirmation = self.generate_confirmation(intent, entities)
        self.conversation_state["awaiting_confirmation"] = True
        self.conversation_state["pending_action"] = {
            "intent": intent,
            "entities": entities.copy()
        }
        
        # Save conversation
        self.save_conversation(message, confirmation, intent, entities, True)
        
        return confirmation, self._get_state_info()
    
    def _handle_chitchat(self, message: str) -> str:
        """Handle general conversation"""
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        if any(greeting in message.lower() for greeting in greetings):
            return "Hello! I can help you schedule meetings or send emails. What would you like to do?"
        
        return "I'm here to help you schedule meetings and send emails. What can I do for you?"
    
    def _get_state_info(self) -> str:
        """Get current state information for the side panel"""
        # Get recent conversation history
        history = self.get_conversation_history(3)
        
        state_info = f"""
**Current State:**
- Intent: {self.conversation_state.get('intent', 'None')}
- Gathering Info: {self.conversation_state.get('gathering_info', False)}
- Awaiting Confirmation: {self.conversation_state.get('awaiting_confirmation', False)}
- Missing Fields: {self.conversation_state.get('missing_fields', [])}
- Session ID: {self.session_id[:8]}...

**Current Entities:**
{json.dumps(self.conversation_state.get('entities', {}), indent=2)}

**Recent History:**
"""
        for conv in history[-2:]:  # Show last 2 exchanges
            state_info += f"• User: {conv['user_message'][:50]}...\n"
            state_info += f"• Bot: {conv['assistant_response'][:50]}...\n"
        
        return state_info

# Initialize the assistant
assistant = GeminiAssistant()

def chat_function(message, history):
    """Main chat function for Gradio"""
    response, state_info = assistant.process_message(message)
    return response, state_info

def new_chat():
    """Start a new chat session"""
    global assistant
    assistant.reset_session()
    return [], "**Current State:**\n- Intent: None\n- Awaiting Confirmation: False\n\n**Current Entities:**\n{}"

# Create Gradio interface
with gr.Blocks(title="Conversational Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Conversational Assistant")
    gr.Markdown("I can help you schedule meetings and send emails. I'll remember our conversation and ask for any missing information step by step!")
    
    with gr.Row():
        with gr.Column(scale=2):
            with gr.Row():
                gr.Markdown("### Chat")
                new_chat_btn = gr.Button("🔄 New Chat", scale=0, size="sm", variant="secondary")
            
            chatbot = gr.Chatbot(
                label="Conversation",
                height=450,
                show_label=False
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message here...",
                    label="Your message",
                    scale=4
                )
                submit_btn = gr.Button("Send", scale=1, variant="primary")
        
        with gr.Column(scale=1):
            state_display = gr.Markdown(
                value="**Current State:**\n- Intent: None\n- Awaiting Confirmation: False\n\n**Current Entities:**\n{}",
                label="Assistant State & History"
            )
    
    # Example inputs
    with gr.Row():
        gr.Examples(
            examples=[
                "I want to send an email",
                "I want to schedule a meeting",
                "Book a meeting with Sara tomorrow at 3pm",
                "john@example.com",
                "Actually, I want to send an email instead",
                "Sorry, I want to schedule a meeting",
                "Hello there!"
            ],
            inputs=msg,
            label="Try these examples:"
        )
    
    def respond(message, chat_history):
        if not message.strip():
            return chat_history, "", ""
        
        response, state_info = chat_function(message, chat_history)
        chat_history.append((message, response))
        return chat_history, "", state_info
    
    # Event handlers
    submit_btn.click(respond, [msg, chatbot], [chatbot, msg, state_display])
    msg.submit(respond, [msg, chatbot], [chatbot, msg, state_display])
    new_chat_btn.click(new_chat, outputs=[chatbot, state_display])

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )