from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
import langchain
from dotenv import load_dotenv
from app.models import ConversationMemory
from app import db
import json
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Configure langchain
langchain.debug = False

class PersistentConversationBufferMemory(ConversationBufferMemory):
    """Extension of ConversationBufferMemory that can load/save state from/to database"""
    
    def __init__(self, chat_id=None, **kwargs):
        super().__init__(**kwargs)
        # Store chat_id as an instance variable, not as a field of the memory object
        self._chat_id = chat_id
        if chat_id is not None:
            self.load_memory_from_db()
    
    @property
    def chat_id(self):
        return self._chat_id
        
    def load_memory_from_db(self):
        """Load memory from database"""
        memory_record = ConversationMemory.query.filter_by(chat_id=self.chat_id).first()
        if memory_record:
            memory_data = memory_record.get_memory_data()
            if 'buffer' in memory_data and memory_data['buffer']:
                # We need to handle the memory format correctly
                try:
                    # Clear existing buffer first
                    self.clear()
                    
                    # If the buffer contains messages in the expected format
                    for msg_data in memory_data['buffer']:
                        # Add each message to memory in the format the memory expects
                        if 'human' in msg_data:
                            self.chat_memory.add_user_message(msg_data['human'])
                        if 'ai' in msg_data:
                            self.chat_memory.add_ai_message(msg_data['ai'])
                except Exception as e:
                    print(f"Error loading memory: {e}")
    
    def save_memory_to_db(self):
        """Save memory to database"""
        if self.chat_id is None:
            return
        
        try:
            # Convert to a format suitable for storage
            # Extract messages from memory
            messages_dict = {'buffer': []}
            
            # Get messages from buffer
            messages = self.chat_memory.messages
            
            # Format messages as a list of dictionaries
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    msg_pair = {
                        'human': messages[i].content,
                        'ai': messages[i + 1].content
                    }
                    messages_dict['buffer'].append(msg_pair)
            
            # Find or create memory record
            memory_record = ConversationMemory.query.filter_by(chat_id=self.chat_id).first()
            if not memory_record:
                memory_record = ConversationMemory(chat_id=self.chat_id)
            
            # Update and save
            memory_record.set_memory_data(messages_dict)
            db.session.add(memory_record)
            db.session.commit()
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Override save_context to persist memory after each update"""
        super().save_context(inputs, outputs)
        self.save_memory_to_db()
    
    def clear(self) -> None:
        """Clear memory and save the cleared state to database"""
        super().clear()
        if self.chat_id is not None:
            try:
                memory_record = ConversationMemory.query.filter_by(chat_id=self.chat_id).first()
                if memory_record:
                    memory_record.set_memory_data({'buffer': []})
                    db.session.add(memory_record)
                    db.session.commit()
            except Exception as e:
                print(f"Error clearing memory: {e}")

class Chatbot:
    def __init__(self):
        self.llm_model = 'gemini-2.0-flash'
        self.llm = ChatGoogleGenerativeAI(model=self.llm_model)
        self.conversations = {}  # In-memory cache of active conversations
        
    def get_conversation(self, chat_id):
        """Get or create a conversation chain for a specific chat"""
        if chat_id not in self.conversations:
            # Create a persistent memory for this chat
            # Using default memory key settings without specifying custom keys
            memory = PersistentConversationBufferMemory(
                chat_id=chat_id,
                return_messages=False
            )
            
            # Create the conversation chain
            self.conversations[chat_id] = ConversationChain(
                llm=self.llm,
                memory=memory,
                verbose=False
            )
        return self.conversations[chat_id]
        
    def get_response(self, user_input, chat_id):
        """Get a response from the chatbot for a specific chat"""
        try:
            conversation = self.get_conversation(chat_id)
            # Use the default input key of ConversationChain which is "input"
            response = conversation.run(user_input)
            return response
        except Exception as e:
            print(f"Error getting response: {str(e)}")
            return f"I'm sorry, I encountered an error: {str(e)}"
    
    def generate_title(self, user_input):
        """Generate a title based on the first user message"""
        try:
            # Use the model to generate a concise, one-line summary
            prompt = f"Summarize the following message as a very short chat title (max 30 chars): '{user_input}'"
            title = self.llm.invoke(prompt).content
            # Clean up and truncate the title
            title = title.strip().strip('"\'').replace('\n', ' ')
            return title[:30]
        except Exception:
            # Fallback to a simple title in case of error
            return user_input[:30] + ("..." if len(user_input) > 30 else "")
    
    def clear_memory(self, chat_id):
        """Clear memory for a specific chat from both cache and database"""
        # Remove from in-memory cache
        if chat_id in self.conversations:
            del self.conversations[chat_id]
        
        # Remove from database
        memory_record = ConversationMemory.query.filter_by(chat_id=chat_id).first()
        if memory_record:
            db.session.delete(memory_record)
            db.session.commit()
