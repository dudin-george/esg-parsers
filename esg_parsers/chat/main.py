import argparse
from gigachat import GigaChat
import json
import os
import re
import sys

# Set your GigaChat credentials
# Get credentials at https://developers.sber.ru/portal/products/gigachat
GIGACHAT_CREDENTIALS = ''

# Initialize GigaChat client
client = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False, model="GigaChat-Pro")

# Get directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def evaluate_article(article_text, scoring_criteria):
    """
    Have GigaChat evaluate if the article matches each criterion (true/false only).
    
    Args:
        article_text (str): The text of the news article to evaluate
        scoring_criteria (dict): Dictionary containing criteria details
        
    Returns:
        dict: Evaluation results and usage info
    """
    # Extract the criteria items for each category
    criteria_items = {}
    
    for category in scoring_criteria:
        if category == "environmental" and isinstance(scoring_criteria[category], dict):
            for subcategory, details in scoring_criteria[category].items():
                if isinstance(details, dict) and 'criteria' in details:
                    criteria_items[subcategory] = details['criteria']
    
    # Create a prompt that asks GigaChat to evaluate each criterion with true/false
    prompt = f"""
    Ты — объективный оценщик новостных статей по экологическим критериям.

    Твоя задача проанализировать следующую новостную статью и определить, какие критерии соответствуют содержанию статьи.
    
    ### Новостная статья:
    {article_text}
    
    ### Инструкции по оценке:
    1. Для КАЖДОГО критерия оцени, есть ли в статье доказательства того, что компания соответствует этому критерию.
    2. Отвечай только "true" если критерий выполняется, или "false" если не выполняется.
    3. Помни, что отсутствие явного упоминания о выполнении критерия означает, что критерий НЕ выполняется (false).
    4. Будь строгим и объективным. Критерий должен ЯВНО соблюдаться в тексте статьи.
    5. Оценивай СТРОГО по содержанию статьи, не делай предположений.
    
    Пожалуйста, оформи свой ответ в виде JSON-объекта с точной структурой:
    ```json
    {{
      "criteria_evaluation": {{
    """
    
    # Add each subcategory and its criteria to the prompt
    for subcategory, items in criteria_items.items():
        prompt += f"""    "{subcategory}": {{
      "items": [
    """
        for item in items:
            prompt += f"""    {{
          "description": "{item['description']}",
          "applicable": true_or_false
        }},
    """
        # Remove the trailing comma and close the array and object
        prompt = prompt.rstrip(",\n    ") + "\n      ]\n    },\n"
    
    # Remove the trailing comma and newline, close the objects
    prompt = prompt.rstrip(",\n") + """
      }
    }
    ```
    
    ВАЖНЫЕ ИНСТРУКЦИИ:
    1. Для КАЖДОГО критерия оцени, есть ли в статье доказательства того, что компания соответствует этому критерию.
    2. Отвечай ТОЛЬКО "true" или "false" для поля "applicable" каждого критерия.
    3. НЕ добавляй никаких объяснений, только JSON-объект.
    4. НЕ пропускай критерии, каждый пункт должен иметь значение "applicable".
    5. НЕ изменяй структуру и не добавляй поля в JSON-ответ.
    """
    
    # Get response from GigaChat
    response = client.chat(prompt)
    
    # Extract usage information
    usage_info = None
    if hasattr(response, 'usage') and response.usage:
        usage_info = {
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        }
    
    # Extract the content from the response
    content = response.choices[0].message.content.strip()
    
    # Extract the JSON result
    try:
        # Try to find JSON within triple backticks
        json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', content, re.DOTALL)
        if json_match:
            evaluation_json = json.loads(json_match.group(1))
        else:
            # Try to find any JSON-like structure
            json_match = re.search(r'({[\s\S]*?"criteria_evaluation"[\s\S]*?})', content, re.DOTALL)
            if json_match:
                evaluation_json = json.loads(json_match.group(1))
            else:
                # Last resort: treat the entire response as JSON
                evaluation_json = json.loads(content)
                
        return {
            'evaluation': evaluation_json,
            'usage': usage_info,
            'raw_response': content
        }
    except Exception as e:
        print(f"Error parsing JSON response: {e}")
        return {
            'error': f"Failed to parse response: {str(e)}",
            'raw_response': content,
            'usage': usage_info
        }

def calculate_scores(evaluation_result, scoring_criteria):
    """
    Calculate scores based on the evaluation results.
    
    Args:
        evaluation_result (dict): Evaluation results from GigaChat
        scoring_criteria (dict): Original scoring criteria with weights and points
        
    Returns:
        dict: Calculated scores and detailed breakdown
    """
    if 'error' in evaluation_result:
        return {
            'error': evaluation_result['error'],
            'score': 0
        }
    
    try:
        # Extract criteria evaluation from the result
        criteria_eval = evaluation_result['evaluation']['criteria_evaluation']
        
        # Calculate scores for each subcategory
        results = {
            'criteria_evaluation': {},
            'subcategory_scores': {}
        }
        
        for category in scoring_criteria:
            if category == "environmental" and isinstance(scoring_criteria[category], dict):
                for subcategory, details in scoring_criteria[category].items():
                    if subcategory in criteria_eval and 'items' in criteria_eval[subcategory]:
                        # Map evaluation results to original criteria
                        evaluated_items = criteria_eval[subcategory]['items']
                        original_items = details['criteria']
                        
                        # Create a list to store matched criteria
                        applicable_items = []
                        raw_score = 0
                        
                        # Match evaluated items to original items by description
                        for i, eval_item in enumerate(evaluated_items):
                            # Find matching original item
                            if i < len(original_items):
                                original_item = original_items[i]
                                
                                # Check if applicable
                                is_applicable = eval_item.get('applicable', False)
                                if isinstance(is_applicable, str):
                                    is_applicable = is_applicable.lower() == 'true'
                                
                                # Add to applicable items list
                                applicable_items.append({
                                    'description': original_item['description'],
                                    'points': original_item['points'],
                                    'applicable': is_applicable
                                })
                                
                                # Add points if applicable
                                if is_applicable:
                                    raw_score += original_item['points']
                        
                        # Calculate normalized score
                        max_points = details['max_points']
                        normalized_score = (raw_score / max_points) * 10 if max_points > 0 else 0
                        
                        # Save results for this subcategory
                        results['criteria_evaluation'][subcategory] = {
                            'raw_score': raw_score,
                            'max_points': max_points,
                            'normalized_score': normalized_score,
                            'weight': details['weight'],
                            'applicable_items': applicable_items
                        }
                        
                        # Store the weighted score
                        results['subcategory_scores'][subcategory] = normalized_score * details['weight']
        
        # Calculate final weighted score
        if results['subcategory_scores']:
            final_score = sum(results['subcategory_scores'].values())
        else:
            final_score = 0
        
        # Add final score to results
        results['final_score'] = final_score
        
        return results
    except Exception as e:
        print(f"Error calculating scores: {e}")
        return {
            'error': f"Error calculating scores: {str(e)}",
            'score': 0
        }

def score_news_article(article_text, scoring_criteria):
    """
    Score a news article based on custom Environmental criteria.
    
    Args:
        article_text (str): The text of the news article to score
        scoring_criteria (dict): Dictionary containing scoring criteria
        
    Returns:
        dict: The scoring results and details
    """
    # Step 1: Have GigaChat evaluate the article against criteria
    evaluation_result = evaluate_article(article_text, scoring_criteria)
    
    # Step 2: Calculate scores based on the evaluation
    scoring_result = calculate_scores(evaluation_result, scoring_criteria)
    
    # Step 3: Combine results
    result = {
        'score': scoring_result.get('final_score', 0),
        'detailed_info': scoring_result,
        'usage': evaluation_result.get('usage'),
        'raw_response': evaluation_result.get('raw_response')
    }
    
    return result

def load_criteria(file_path='criteria.json'):
    """Load scoring criteria from a JSON file."""
    # Use absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, file_path)
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading criteria from {abs_path}: {e}")
        return None

def load_input_text(file_path='input.txt'):
    """Load article text from a text file."""
    # Use absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, file_path)
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading text from {abs_path}: {e}")
        return None

def save_output(result, file_path='output.txt'):
    """Save the score and detailed information to a text file."""
    # Extract components from the result
    score = result.get('score', 0)
    detailed_info = result.get('detailed_info', {})
    usage_info = result.get('usage')
    
    # Use absolute path based on script location
    abs_path = os.path.join(SCRIPT_DIR, file_path)
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            # Always save the score
            f.write(f"Environmental Score (0-10): {score}\n")
            
            # If detailed info is provided, add it to the output
            if detailed_info and 'criteria_evaluation' in detailed_info:
                f.write("\n--- DETAILED CRITERIA EVALUATION ---\n")
                criteria_eval = detailed_info['criteria_evaluation']
                
                for criterion, details in criteria_eval.items():
                    f.write(f"\n{criterion.upper()}:\n")
                    f.write(f"  Raw Score: {details.get('raw_score', 'N/A')} / {details.get('max_points', 'N/A')}\n")
                    f.write(f"  Normalized Score (0-10): {details.get('normalized_score', 'N/A')}\n")
                    f.write(f"  Weight: {details.get('weight', 'N/A')}\n")
                    f.write(f"  Weighted Score: {details.get('normalized_score', 0) * details.get('weight', 0)}\n")
                    
                    if 'applicable_items' in details and details['applicable_items']:
                        f.write("  Individual Criteria:\n")
                        for item in details['applicable_items']:
                            status = "✓" if item.get('applicable', False) else "✗"
                            f.write(f"    {status} {item.get('description', 'Unknown')} ({item.get('points', 0)} points)\n")
                
                f.write("\n--- SCORE CALCULATION ---\n")
                for criterion, details in criteria_eval.items():
                    f.write(f"  {criterion}: {details.get('normalized_score', 0):.2f} × {details.get('weight', 0)} = {details.get('normalized_score', 0) * details.get('weight', 0):.2f}\n")
                
                f.write(f"\nFINAL WEIGHTED SCORE (0-10): {score}\n")
            
            # If usage info is provided, add it to the output
            if usage_info:
                f.write("\n--- TOKEN USAGE ---\n")
                f.write(f"  Prompt tokens: {usage_info['prompt_tokens']}\n")
                f.write(f"  Completion tokens: {usage_info['completion_tokens']}\n")
                f.write(f"  Total tokens: {usage_info['total_tokens']}\n")
                
        print(f"Score saved to {abs_path}")
    except Exception as e:
        print(f"Error saving score to {abs_path}: {e}")

def display_results(result, debug=False):
    """Display results to the console."""
    score = result.get('score', 0)
    detailed_info = result.get('detailed_info', {})
    usage_info = result.get('usage')
    
    print(f"Environmental Score (0-10): {score}")
    
    # Display token usage
    if usage_info:
        print("\nToken Usage:")
        print(f"  Prompt tokens: {usage_info['prompt_tokens']}")
        print(f"  Completion tokens: {usage_info['completion_tokens']}")
        print(f"  Total tokens: {usage_info['total_tokens']}")
    
    # Display detailed criteria information
    if detailed_info and 'criteria_evaluation' in detailed_info:
        print("\nCriteria Evaluation:")
        criteria_eval = detailed_info['criteria_evaluation']
        
        for criterion, details in criteria_eval.items():
            print(f"\n{criterion.upper()}:")
            print(f"  Raw Score: {details.get('raw_score', 'N/A')} / {details.get('max_points', 'N/A')}")
            print(f"  Normalized Score (0-10): {details.get('normalized_score', 'N/A')}")
            print(f"  Weight: {details.get('weight', 'N/A')}")
            print(f"  Weighted Score: {details.get('normalized_score', 0) * details.get('weight', 0)}")
            
            if 'applicable_items' in details and details['applicable_items']:
                print("  Individual Criteria:")
                for item in details['applicable_items']:
                    status = "✓" if item.get('applicable', False) else "✗"
                    print(f"    {status} {item.get('description', 'Unknown')} ({item.get('points', 0)} points)")
        
        print("\nScore Calculation:")
        for criterion, details in criteria_eval.items():
            print(f"  {criterion}: {details.get('normalized_score', 0):.2f} × {details.get('weight', 0)} = {details.get('normalized_score', 0) * details.get('weight', 0):.2f}")
        
        print(f"\nFINAL WEIGHTED SCORE (0-10): {score}")
    
    # Print raw response only in debug mode
    if debug and 'raw_response' in result:
        print("\nRaw Response:")
        print(result['raw_response'])

if __name__ == "__main__":
    # Display usage information if run with no arguments
    if len(sys.argv) == 1:
        print("Usage:")
        print("  python main.py              - Run normal scoring mode")
        print("  python main.py --debug      - Run with debug output (including raw response)")
        print("\nResults will be saved to output.txt")
        
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Score news articles based on environmental criteria')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to show raw response')
    args = parser.parse_args()
    
    # Load criteria from JSON file
    criteria = load_criteria()
    if not criteria:
        print("Failed to load scoring criteria. Exiting...")
        exit(1)
    
    # Load input text
    article_text = load_input_text()
    if not article_text:
        print("Failed to load input text. Exiting...")
        exit(1)
    
    # Score the article and get results
    result = score_news_article(article_text, criteria)
    
    # Display and save results
    display_results(result, debug=args.debug)
    save_output(result) 