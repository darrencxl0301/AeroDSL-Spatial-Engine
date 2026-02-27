#core/main.py
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from core.resolver import SymbolResolver
from core.generator import generate_availability
from core.parser import parse_availability
from core.date_utils import normalize_date
from fastapi import HTTPException



app = FastAPI()
resolver = SymbolResolver()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/resolve/{code}")
def resolve_code(code: str):
    result = resolver.resolve_iata(code)
    return result


@app.get("/search")
def search_airports(q: str):
    return resolver.search_airports(q)


@app.post("/generate")
def generate(
    date: str = Form(...),
    origin: str = Form(...),
    destination: str = Form(...)
):
    try:
        date = normalize_date(date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    origin_airport = resolver.resolve_airport_by_name(origin)
    destination_airport = resolver.resolve_airport_by_name(destination)

    if not origin_airport or not destination_airport:
        raise HTTPException(status_code=400, detail="Airport not found")

    origin_code = origin_airport["iata"]
    destination_code = destination_airport["iata"]

    cmd = generate_availability(date, origin_code, destination_code)

    return {
        "intent": "Availability",
        "date": date,
        "origin": origin_airport,
        "destination": destination_airport,
        "compressed": cmd
    }

@app.post("/parse", response_class=HTMLResponse)
def parse_command(
    request: Request,
    command: str = Form(...)
):
    result = parse_availability(command)

    if not result:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Invalid command format"
            }
        )

    origin_airport = resolver.resolve_iata(result["origin"])
    destination_airport = resolver.resolve_iata(result["destination"])

    structured = {
        "intent": result["intent"],
        "date": result["date"],
        "origin": origin_airport,
        "destination": destination_airport
    }

    segments = {
        "prefix": "AN",
        "date": result["date"],
        "origin": result["origin"],
        "destination": result["destination"]
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "structured": structured,
            "segments": segments,
            "command": command
        }
    )