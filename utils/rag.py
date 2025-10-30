"""
RAG (Retrieval Augmented Generation) utility for context-aware responses
Stores and retrieves conversation history to provide personalized suggestions
"""
import json
from models import db, ChatHistory, BusinessContext

def save_chat_to_rag(user_id, message, response, intent, entities=None):
    """Save chat interaction to database for RAG"""
    try:
        chat = ChatHistory(
            user_id=user_id,
            message=message,
            response=response,
            intent=intent,
            entities_extracted=json.dumps(entities) if entities else None
        )
        db.session.add(chat)
        db.session.commit()
        print(f"✅ Saved chat to RAG: user={user_id}, intent={intent}")
    except Exception as e:
        print(f"❌ Error saving chat to RAG: {e}")
        db.session.rollback()

def save_business_context(user_id, context_type, content, location=None):
    """Save business ideas/plans/schemes for future retrieval"""
    try:
        context = BusinessContext(
            user_id=user_id,
            context_type=context_type,
            content=json.dumps(content) if isinstance(content, (dict, list)) else content,
            location=location
        )
        db.session.add(context)
        db.session.commit()
        print(f"✅ Saved business context: user={user_id}, type={context_type}")
    except Exception as e:
        print(f"❌ Error saving business context: {e}")
        db.session.rollback()

def get_user_conversation_history(user_id, limit=10):
    """Retrieve recent conversation history for context"""
    try:
        chats = ChatHistory.query.filter_by(user_id=user_id)\
            .order_by(ChatHistory.timestamp.desc())\
            .limit(limit)\
            .all()
        
        history = []
        for chat in reversed(chats):  # Oldest first
            history.append({
                'message': chat.message,
                'response': chat.response,
                'intent': chat.intent,
                'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return history
    except Exception as e:
        print(f"❌ Error retrieving conversation history: {e}")
        return []

def get_user_business_context(user_id, context_type=None, location=None):
    """Retrieve business context (ideas, plans) for personalized suggestions"""
    try:
        query = BusinessContext.query.filter_by(user_id=user_id)
        
        if context_type:
            query = query.filter_by(context_type=context_type)
        
        if location:
            query = query.filter_by(location=location)
        
        contexts = query.order_by(BusinessContext.timestamp.desc()).limit(5).all()
        
        results = []
        for ctx in contexts:
            try:
                content = json.loads(ctx.content) if ctx.content.startswith('{') or ctx.content.startswith('[') else ctx.content
            except:
                content = ctx.content
            
            results.append({
                'type': ctx.context_type,
                'content': content,
                'location': ctx.location,
                'timestamp': ctx.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return results
    except Exception as e:
        print(f"❌ Error retrieving business context: {e}")
        return []

def get_similar_user_insights(location, interest=None):
    """Get insights from similar users in same location - for better suggestions"""
    try:
        # Find users in same location
        from models import User
        query = User.query.filter_by(village=location)
        
        if interest:
            query = query.filter(User.interests.like(f'%{interest}%'))
        
        similar_users = query.limit(10).all()
        
        if not similar_users:
            return None
        
        # Get their business contexts
        insights = []
        for user in similar_users:
            contexts = BusinessContext.query.filter_by(
                user_id=user.id,
                location=location
            ).all()
            
            for ctx in contexts:
                try:
                    content = json.loads(ctx.content)
                    insights.append({
                        'type': ctx.context_type,
                        'content': content,
                        'user_name': user.name
                    })
                except:
                    pass
        
        return insights
    except Exception as e:
        print(f"❌ Error getting similar user insights: {e}")
        return None

def build_rag_context_for_query(user_id, location, current_message):
    """Build comprehensive context from RAG for answering current query"""
    context_parts = []
    
    # 1. Get user's conversation history
    history = get_user_conversation_history(user_id, limit=5)
    if history:
        context_parts.append("**User's Recent Conversation:**")
        for h in history[-3:]:  # Last 3 exchanges
            context_parts.append(f"User: {h['message']}")
            context_parts.append(f"Bot: {h['response'][:150]}...")
    
    # 2. Get user's business context
    business_ctx = get_user_business_context(user_id)
    if business_ctx:
        context_parts.append("\n**User's Business Journey:**")
        for ctx in business_ctx:
            context_parts.append(f"- {ctx['type']}: {str(ctx['content'])[:100]}...")
    
    # 3. Get similar user insights from same location
    similar_insights = get_similar_user_insights(location)
    if similar_insights and len(similar_insights) > 0:
        context_parts.append(f"\n**What Others in {location} Are Doing:**")
        for insight in similar_insights[:3]:
            context_parts.append(f"- {insight['user_name']}: {str(insight['content'])[:100]}...")
    
    return "\n".join(context_parts) if context_parts else ""
