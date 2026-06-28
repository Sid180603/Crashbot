"""
PHASE 5: Conversational Chat
Allow users to ask follow-up questions about crash analysis
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.llm.analyzer import LLMAnalyzer
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMessage:
    """Chat message"""
    def __init__(self, role: str, content: str, timestamp: datetime = None):
        self.role = role  # 'user' or 'assistant'
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc)


class CrashChatbot:
    """Conversational chatbot for crash analysis follow-ups"""
    
    def __init__(self, crash_data: Dict[str, Any], analysis: Dict[str, Any]):
        self.crash_data = crash_data
        self.analysis = analysis
        self.conversation_history: List[ConversationMessage] = []
        self.llm = LLMAnalyzer()
    
    def ask(self, question: str) -> str:
        """
        Ask a follow-up question about the crash
        
        Args:
            question: User's question
            
        Returns:
            Assistant's answer
        """
        logger.info(f"Chat question: {question}")
        
        # Add user message to history
        self.conversation_history.append(
            ConversationMessage(role="user", content=question)
        )
        
        # Build context-aware prompt
        prompt = self._build_chat_prompt(question)
        
        # Get LLM response
        try:
            response = self.llm.send_prompt(prompt)
            
            # Add assistant response to history
            self.conversation_history.append(
                ConversationMessage(role="assistant", content=response)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return "I apologize, but I encountered an error processing your question."
    
    def _build_chat_prompt(self, question: str) -> str:
        """Build context-aware prompt with conversation history"""
        
        # Crash context
        context = f"""CRASH CONTEXT:
Exception: {self.crash_data.get('exception_code', 'Unknown')}
Module: {self.crash_data.get('faulting_module', 'Unknown')}
Root Cause: {self.analysis.get('root_cause', 'Unknown')}

PREVIOUS ANALYSIS:
{self.analysis.get('explanation', 'No analysis available')}
"""
        
        # Conversation history
        history = ""
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            history += f"{msg.role.upper()}: {msg.content}\n"
        
        prompt = f"""{context}

CONVERSATION HISTORY:
{history}

USER QUESTION:
{question}

Please provide a helpful, technical answer based on the crash context and previous analysis. 
Be specific and reference the crash details when relevant.
"""
        
        return prompt
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get formatted conversation history"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in self.conversation_history
        ]


# Example usage:
# chatbot = CrashChatbot(crash_data, analysis)
# answer = chatbot.ask("What if I revert the last commit?")
# answer = chatbot.ask("Is this related to memory corruption?")
