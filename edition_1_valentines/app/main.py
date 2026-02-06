from pathlib import Path

from dotenv import load_dotenv

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
    list_regions,
    love_letter_data,
    love_letter_with_ai,
    order_quote,
    recommend_products_with_explanations,
    sales_overview,
    sales_all_products,
    sales_filter_options,
    sales_chat_answer,
    sales_overview_filtered,
    semantic_product_search,
    supply_chain_alerts,
    valentine_experience_plan,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

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
def love_letter_submit(
    request: Request,
    customer_id: str = Form(...),
    tone: str = Form("light and professional"),
):
    customers = list_customers(60)
    customer, events, letter_text, source, error = love_letter_with_ai(
        customer_id, tone
    )
    letter = {
        "customer": customer,
        "events": events,
        "text": letter_text,
        "source": source,
        "error": error,
    }
    return templates.TemplateResponse(
        "love_letter.html",
        {"request": request, "customers": customers, "letter": letter},
    )


@app.get("/recommender", response_class=HTMLResponse)
def recommender_form(request: Request):
    customers = list_customers(60)
    return templates.TemplateResponse(
        "recommender.html",
        {
            "request": request,
            "customers": customers,
            "recommendations": None,
            "selected_customer_id": None,
        },
    )


@app.post("/recommender", response_class=HTMLResponse)
def recommender_submit(request: Request, customer_id: str = Form(...)):
    customers = list_customers(60)
    recommendations, mode = recommend_products_with_explanations(customer_id)
    return templates.TemplateResponse(
        "recommender.html",
        {
            "request": request,
            "customers": customers,
            "recommendations": recommendations,
            "explain_mode": mode.get("mode"),
            "selected_customer_id": customer_id,
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
    filters = {
        "category": request.query_params.get("category") or "",
        "channel": request.query_params.get("channel") or "",
        "country": request.query_params.get("country") or "",
        "month": request.query_params.get("month") or "",
    }
    summary, top_products = sales_overview_filtered(filters)
    all_products = sales_all_products(filters)
    options = sales_filter_options()
    return templates.TemplateResponse(
        "sales_dashboard.html",
        {
            "request": request,
            "summary": summary,
            "top_products": top_products,
            "all_products": all_products,
            "filter_options": options,
            "filters": filters,
            "chat_question": "",
            "chat_response": None,
            "chat_source": None,
            "chat_error": None,
        },
    )


@app.post("/sales-dashboard/chat", response_class=HTMLResponse)
def sales_chat_submit(
    request: Request,
    question: str = Form(...),
    category: str = Form(""),
    channel: str = Form(""),
    country: str = Form(""),
    month: str = Form(""),
):
    filters = {
        "category": category,
        "channel": channel,
        "country": country,
        "month": month,
    }
    summary, top_products = sales_overview_filtered(filters)
    all_products = sales_all_products(filters)
    options = sales_filter_options()
    response, source, error = sales_chat_answer(question, filters)
    return templates.TemplateResponse(
        "sales_dashboard.html",
        {
            "request": request,
            "summary": summary,
            "top_products": top_products,
            "all_products": all_products,
            "filter_options": options,
            "filters": filters,
            "chat_question": question,
            "chat_response": response,
            "chat_source": source,
            "chat_error": error,
        },
    )


@app.post("/sales-dashboard/filter", response_class=HTMLResponse)
def sales_filter_submit(
    request: Request,
    category: str = Form(""),
    channel: str = Form(""),
    country: str = Form(""),
    month: str = Form(""),
):
    filters = {
        "category": category,
        "channel": channel,
        "country": country,
        "month": month,
    }
    summary, top_products = sales_overview_filtered(filters)
    all_products = sales_all_products(filters)
    options = sales_filter_options()
    return templates.TemplateResponse(
        "sales_dashboard.html",
        {
            "request": request,
            "summary": summary,
            "top_products": top_products,
            "all_products": all_products,
            "filter_options": options,
            "filters": filters,
            "chat_question": "",
            "chat_response": None,
            "chat_source": None,
            "chat_error": None,
        },
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


@app.get("/semantic-search", response_class=HTMLResponse)
def semantic_search_form(request: Request):
    return templates.TemplateResponse(
        "semantic_search.html",
        {"request": request, "query": "", "results": None},
    )


@app.post("/semantic-search", response_class=HTMLResponse)
def semantic_search_submit(request: Request, query: str = Form(...)):
    results = semantic_product_search(query)
    return templates.TemplateResponse(
        "semantic_search.html",
        {"request": request, "query": query, "results": results},
    )


@app.get("/valentine-planner", response_class=HTMLResponse)
def valentine_planner_form(request: Request):
    regions = list_regions(50)
    return templates.TemplateResponse(
        "valentine_planner.html",
        {
            "request": request,
            "regions": regions,
            "plan": None,
        },
    )


@app.post("/valentine-planner", response_class=HTMLResponse)
def valentine_planner_submit(
    request: Request,
    budget: float = Form(...),
    persona: str = Form(...),
    delivery_speed: str = Form(...),
    region: str = Form(...),
):
    regions = list_regions(50)
    plan = valentine_experience_plan(budget, persona, delivery_speed, region)
    return templates.TemplateResponse(
        "valentine_planner.html",
        {
            "request": request,
            "regions": regions,
            "plan": plan,
            "budget": budget,
            "persona": persona,
            "delivery_speed": delivery_speed,
            "region": region,
        },
    )
