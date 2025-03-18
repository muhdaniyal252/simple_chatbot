from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from app.models import Chat, Message, ConversationMemory
from app import db
from app.chatbot import Chatbot
import json

main_bp = Blueprint('main', __name__)

# Create a chatbot instance
chatbot = Chatbot()

@main_bp.route('/')
def index():
    # Get all chats for the sidebar
    chats = Chat.query.order_by(Chat.created_at.desc()).all()
    return render_template('index.html', chats=chats)

@main_bp.route('/chat/<int:chat_id>')
def chat(chat_id):
    # Get all chats for the sidebar
    chats = Chat.query.order_by(Chat.created_at.desc()).all()
    
    # Get the current chat
    current_chat = Chat.query.get_or_404(chat_id)
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
    
    return render_template('chat.html', chats=chats, current_chat=current_chat, messages=messages)

@main_bp.route('/new_chat')
def new_chat():
    # Create a new chat
    new_chat = Chat(title="New Chat")
    db.session.add(new_chat)
    db.session.commit()
    
    # Initialize an empty memory record for this chat
    memory_record = ConversationMemory(chat_id=new_chat.id)
    db.session.add(memory_record)
    db.session.commit()
    
    return redirect(url_for('main.chat', chat_id=new_chat.id))

@main_bp.route('/send_message', methods=['POST'])
def send_message():
    chat_id = request.form.get('chat_id')
    user_message = request.form.get('message')
    
    # Get the current chat
    current_chat = Chat.query.get_or_404(chat_id)
    
    # Check if this is the first message in this chat
    is_first_message = Message.query.filter_by(chat_id=chat_id).count() == 0
    
    # Create a new user message
    user_msg = Message(is_user=True, content=user_message, chat_id=chat_id)
    db.session.add(user_msg)
        
    # Get response from the chatbot using the chat_id
    ai_response = chatbot.get_response(user_message, int(chat_id))
    
    # Create a new AI message
    ai_msg = Message(is_user=False, content=ai_response, chat_id=chat_id)
    db.session.add(ai_msg)
    
    # Update the chat title if it's the first message
    if current_chat.title == "New Chat" and user_message:
        # Generate a title for the chat based on the user's first message
        generated_title = chatbot.generate_title(user_message)
        current_chat.title = generated_title
        db.session.add(current_chat)
    
    db.session.commit()
    
    return jsonify({
        'user_message': user_message,
        'ai_response': ai_response
    })

@main_bp.route('/delete_chat/<int:chat_id>', methods=['POST'])
def delete_chat(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    
    # Clear the memory for this specific chat_id
    chatbot.clear_memory(chat_id)
    
    # Delete the chat (this will cascade delete messages and memory)
    db.session.delete(chat)
    db.session.commit()
    
    return redirect(url_for('main.index'))
