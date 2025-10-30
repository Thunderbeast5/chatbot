from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for storing user information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    village = db.Column(db.String(100))
    interests = db.Column(db.String(200))
    phone = db.Column(db.String(15))
    budget = db.Column(db.Integer)  # Store budget
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with chat history
    chats = db.relationship('ChatHistory', backref='user', lazy=True)
    business_context = db.relationship('BusinessContext', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.name}>'

class ChatHistory(db.Model):
    """Chat history model for storing conversations - RAG source"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50))
    entities_extracted = db.Column(db.Text)  # Store entities as JSON string
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatHistory {self.id}>'

class BusinessContext(db.Model):
    """Store business ideas, plans, and decisions for RAG"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    context_type = db.Column(db.String(50))  # 'idea', 'plan', 'scheme', 'resource'
    content = db.Column(db.Text, nullable=False)  # JSON string
    location = db.Column(db.String(100))  # For location-specific retrieval
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BusinessContext {self.context_type}>'
