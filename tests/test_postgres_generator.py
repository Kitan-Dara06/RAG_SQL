"""
Quick test of generator2.py with PostgreSQL.
"""
from src.core.generator2 import run_agent, answer_synthesis
from logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Generator2 with PostgreSQL")
    print("=" * 60)
    
    # Test questions
    questions = [
        "How many users are in the database?",
        "What is the total value of all orders?",
        "Which user spent the most money?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n[Question {i}] {question}")
        print("-" * 60)
        
        result = run_agent(question)
        
        if result and result.get("success"):
            print(f"✓ Query succeeded!")
            print(f"Columns: {result['columns']}")
            print(f"Data: {result['data']}")
            
            # Synthesize answer
            answer = answer_synthesis(question, result)
            print(f"\n📝 Answer: {answer}")
        else:
            print(f"✗ Query failed")
            if result:
                print(f"Error: {result.get('error', 'Unknown error')}")
        
        print()
    
    print("=" * 60)
    print("PostgreSQL Test Complete!")
    print("=" * 60)
