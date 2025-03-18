from app import db
from datetime import datetime
import json

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='chat', lazy=True, cascade="all, delete-orphan")
    memory = db.relationship('ConversationMemory', backref='chat', uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Chat {self.id}: {self.title}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_user = db.Column(db.Boolean, default=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    
    def __repr__(self):
        return f'<Message {self.id}: {"User" if self.is_user else "AI"} - {self.content[:20]}...>'

    @property
    def formatted_timestamp(self):
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')

class ConversationMemory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False, unique=True)
    memory_data = db.Column(db.Text, nullable=False, default='{}')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConversationMemory for Chat {self.chat_id}>'
    
    def set_memory_data(self, memory_dict):
        """Serialize memory dictionary to JSON string"""
        self.memory_data = json.dumps(memory_dict)
    
    def get_memory_data(self):
        """Deserialize JSON string to memory dictionary"""
        try:
            return json.loads(self.memory_data)
        except:
            return {}
