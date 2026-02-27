#resolver.py
import json
import os

class SymbolResolver:
    def __init__(self):
        base_path = os.path.dirname(__file__)
        
        with open(os.path.join(base_path, "../data/clean_airports.json"), encoding="utf-8") as f:
            self.airports = json.load(f)

        with open(os.path.join(base_path, "../data/clean_airlines.json"), encoding="utf-8") as f:
            self.airlines = json.load(f)

        self.airport_iata_index = {a["iata"]: a for a in self.airports}
        self.airline_iata_index = {a["iata"]: a for a in self.airlines}

    def resolve_iata(self, code):
        code = code.upper()
        if code in self.airport_iata_index:
            return self.airport_iata_index[code]
        if code in self.airline_iata_index:
            return self.airline_iata_index[code]
        return None
    
    def resolve_airport_by_name(self, query: str):
        query = query.lower()
        
        for airport in self.airports:
            if query in airport["city"].lower() or query in airport["name"].lower():
                return airport
        
        return None
    
    def search_airports(self, query: str, limit: int = 5):
        query = query.lower()
        results = []

        for airport in self.airports:
            if (
                query in airport["city"].lower()
                or query in airport["name"].lower()
                or query in airport["iata"].lower()
            ):
                results.append({
                    "iata": airport["iata"],
                    "name": airport["name"],
                    "city": airport["city"],
                    "country": airport["country"]
                })

            if len(results) >= limit:
                break

        return results