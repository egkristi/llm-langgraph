from typing import Dict, List, Any
from langchain_core.tools import tool

@tool
def analyze_question(question: str) -> str:
    """
    Break down the user's question into key components and requirements.
    
    Args:
        question: The user's original question
    
    Returns:
        Analysis of the question with key components and requirements
    """
    return (f"Question analysis:\n"
            f"- Main topic: {question.split()[0] if question else 'N/A'}\n"
            f"- Question complexity: {'Complex' if len(question.split()) > 15 else 'Simple'}\n"
            f"- Question type: {'Factual' if '?' in question else 'Request/Command'}\n"
            f"- Key elements to address: {', '.join(question.split()[:5]) if question else 'N/A'}")

@tool
def validate_response(original_question: str, response: str) -> str:
    """
    Check if a response adequately addresses the original question.
    
    Args:
        original_question: The original question asked by the user
        response: The response to evaluate
    
    Returns:
        Assessment of how well the response addresses the original question
    """
    # Simple validation logic - a real implementation would be more sophisticated
    question_words = set(original_question.lower().split())
    response_words = set(response.lower().split())
    common_words = question_words.intersection(response_words)
    coverage = len(common_words) / max(1, len(question_words))
    
    if coverage > 0.5:
        assessment = "Response addresses the question well"
    elif coverage > 0.3:
        assessment = "Response partially addresses the question"
    else:
        assessment = "Response does not adequately address the question"
    
    return f"Response validation:\n- {assessment}\n- Coverage score: {coverage:.2f}\n- Key question terms addressed: {', '.join(common_words)}"

@tool
def identify_gaps(original_question: str, existing_responses: str) -> str:
    """
    Identify what parts of the question remain unanswered.
    
    Args:
        original_question: The original question asked by the user
        existing_responses: The collective responses so far
    
    Returns:
        Analysis of what aspects of the question still need to be addressed
    """
    # Extract key question components (this is a simplified implementation)
    question_words = set(original_question.lower().split())
    response_words = set(existing_responses.lower().split())
    
    # Find words in the question that haven't been addressed
    missing_words = question_words - response_words
    
    if not missing_words:
        return "All aspects of the question appear to be addressed."
    
    return f"Gaps in the responses:\n- Missing key terms: {', '.join(list(missing_words)[:10])}\n- Recommendation: Provide information on these aspects to complete the answer."

@tool
def summarize_responses(responses: str) -> str:
    """
    Create a coherent summary from multiple agent responses.
    
    Args:
        responses: The collected responses from different agents
    
    Returns:
        A coherent summary integrating the key points from all responses
    """
    # Split responses by agent (simplified)
    response_lines = responses.split('\n')
    
    # Count the total lines
    total_lines = len(response_lines)
    
    # Create a simple summary (in a real implementation, this would use more sophisticated NLP)
    if total_lines <= 3:
        return f"Summary: {responses}"
    
    # Take first line, middle content overview, and last line
    summary = (f"Summary of agent responses:\n"
               f"- Initial point: {response_lines[0]}\n"
               f"- Main content: {total_lines-2} additional points were discussed\n"
               f"- Conclusion: {response_lines[-1]}")
    
    return summary
