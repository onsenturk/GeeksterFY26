from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .data_loader import ensure_db
from .queries import (
    analytics_overview,
    compatibility_score,
    gift_concierge,
    global_love_metrics,
    list_customers,
    list_matchmaking_users,
    list_products,
    love_letter_data,
    order_quote,
    recommend_products,
    sales_overview,
    supply_chain_alerts,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Valentine's Day Edition")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup_event():
    ensure_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    counts, scores = analytics_overview()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "counts": counts, "scores": scores},
    )


@app.get("/love-letter", response_class=HTMLResponse)
def love_letter_form(request: Request):
    customers = list_customers(60)
    return templates.TemplateResponse(
        "love_letter.html",
        {"request": request, "customers": customers, "letter": None},
    )


@app.post("/love-letter", response_class=HTMLResponse)
def love_letter_submit(request: Request, customer_id: str = Form(...)):
    customers = list_customers(60)
    customer, events = love_letter_data(customer_id)
    letter = {"customer": customer, "events": events}
    return templates.TemplateResponse(
        "love_letter.html",
        {"request": request, "customers": customers, "letter": letter},
    )


@app.get("/recommender", response_class=HTMLResponse)
def recommender_form(request: Request):
    customers = list_customers(60)
    return templates.TemplateResponse(
        "recommender.html",
        {"request": request, "customers": customers, "recommendations": None},
    )


@app.post("/recommender", response_class=HTMLResponse)
def recommender_submit(request: Request, customer_id: str = Form(...)):
    customers = list_customers(60)
    recommendations = recommend_products(customer_id)
    return templates.TemplateResponse(
        "recommender.html",
        {
            "request": request,
            "customers": customers,
            "recommendations": recommendations,
        },
    )


@app.get("/compatibility", response_class=HTMLResponse)
def compatibility_form(request: Request):
    users = list_matchmaking_users(60)
    return templates.TemplateResponse(
        "compatibility.html",
        {"request": request, "users": users, "result": None},
    )


@app.post("/compatibility", response_class=HTMLResponse)
def compatibility_submit(
    request: Request, user_a: str = Form(...), user_b: str = Form(...)
):
    users = list_matchmaking_users(60)
    result = compatibility_score(user_a, user_b)
    return templates.TemplateResponse(
        "compatibility.html",
        {"request": request, "users": users, "result": result},
    )


@app.get("/sales-dashboard", response_class=HTMLResponse)
def sales_dashboard(request: Request):
    summary, top_products = sales_overview()
    return templates.TemplateResponse(
        "sales_dashboard.html",
        {"request": request, "summary": summary, "top_products": top_products},
    )


@app.get("/global-love", response_class=HTMLResponse)
def global_love(request: Request):
    delivery, routing = global_love_metrics()
    return templates.TemplateResponse(
        "global_love.html",
        {"request": request, "delivery": delivery, "routing": routing},
    )


@app.get("/gift-concierge", response_class=HTMLResponse)
def gift_concierge_form(request: Request):
    return templates.TemplateResponse(
        "gift_concierge.html",
        {"request": request, "recommendations": None},
    )


@app.post("/gift-concierge", response_class=HTMLResponse)
def gift_concierge_submit(
    request: Request,
    budget: float = Form(...),
    persona: str = Form(...),
    delivery_speed: str = Form(...),
):
    recommendations = gift_concierge(budget, persona, delivery_speed)
    return templates.TemplateResponse(
        "gift_concierge.html",
        {"request": request, "recommendations": recommendations},
    )


@app.get("/supply-chain", response_class=HTMLResponse)
def supply_chain(request: Request):
    alerts = supply_chain_alerts()
    return templates.TemplateResponse(
        "supply_chain.html",
        {"request": request, "alerts": alerts},
    )


@app.get("/order-app", response_class=HTMLResponse)
def order_form(request: Request):
    products = list_products(60)
    return templates.TemplateResponse(
        "order_app.html",
        {"request": request, "products": products, "quote": None},
    )


@app.post("/order-app", response_class=HTMLResponse)
def order_submit(
    request: Request,
    product_id: str = Form(...),
    quantity: int = Form(...),
    loyalty_tier: str = Form(...),
):
    products = list_products(60)
    quote = order_quote(product_id, quantity, loyalty_tier)
    return templates.TemplateResponse(
        "order_app.html",
        {"request": request, "products": products, "quote": quote},
    )


@app.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request):
    counts, scores = analytics_overview()
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "counts": counts, "scores": scores},
    )
