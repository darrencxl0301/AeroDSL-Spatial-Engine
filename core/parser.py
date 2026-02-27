#parser.py
def parse_availability(command: str):
    if not command.startswith("AN"):
        return None
    
    body = command[2:]
    
    date = body[:5]
    origin = body[5:8]
    destination = body[8:11]
    
    return {
        "intent": "availability",
        "date": date,
        "origin": origin,
        "destination": destination
    }