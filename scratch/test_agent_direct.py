import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to the path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

load_dotenv()

from restaurant_agent.config import load_restaurant_profile
from restaurant_agent.agent import build_restaurant_agent

def main():
    profile = load_restaurant_profile()
    agent = build_restaurant_agent(profile=profile)
    
    raw_text = (
        "SUCCESS: Reservation created. Confirmation code: D53D3E20\n"
        "Thank you! Your request has been sent to our team for approval. We'll notify you as soon as it's confirmed."
    )
    cleaned = agent._clean_response(raw_text)
    print("RAW TEXT:")
    print(repr(raw_text))
    print("\nCLEANED TEXT:")
    print(repr(cleaned))

if __name__ == "__main__":
    main()
