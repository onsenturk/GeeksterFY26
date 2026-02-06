import json
import os
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .db import get_db


@dataclass
class SearchIndex:
    vectorizer: TfidfVectorizer
    matrix: object
    records: list


def _top_value(series):
    if series.empty:
        return None
    return series.value_counts().idxmax()


def llm_available():
    return bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_DEPLOYMENT")) or bool(os.getenv("OPENAI_API_KEY"))


def _call_openai_chat(messages, temperature=0.2, max_tokens=400):
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if azure_endpoint and azure_key and azure_deployment:
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        url = (
            f"{azure_endpoint.rstrip('/')}/openai/deployments/"
            f"{azure_deployment}/chat/completions?api-version={api_version}"
        )
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        headers = {
            "api-key": azure_key,
            "Content-Type": "application/json",
        }
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _call_openai_chat_with_error(messages, temperature=0.2, max_tokens=400):
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    source = "openai"

    if azure_endpoint and azure_key and azure_deployment:
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        url = (
            f"{azure_endpoint.rstrip('/')}/openai/deployments/"
            f"{azure_deployment}/chat/completions?api-version={api_version}"
        )
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        headers = {
            "api-key": azure_key,
            "Content-Type": "application/json",
        }
        source = "azure"
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, "none", "No API key configured"

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"], source, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        detail = f"HTTP {exc.code}: {exc.reason}"
        if body:
            detail = f"{detail} | {body}"
        return None, source, detail
    except Exception as exc:
        return None, source, str(exc)


def generate_recommendation_explanations(customer, recommendations):
    if not recommendations:
        return [], "heuristic"

    if llm_available():
        prompt = {
            "customer": {
                "loyalty_tier": customer.get("loyalty_tier"),
                "preferred_language": customer.get("preferred_language"),
            },
            "recommendations": [
                {
                    "product_name": rec.get("product_name"),
                    "category": rec.get("product_category"),
                    "price": rec.get("unit_price"),
                    "rating": rec.get("rating"),
                    "persona": rec.get("gift_persona"),
                    "delivery_speed": rec.get("delivery_speed"),
                }
                for rec in recommendations
            ],
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that writes short reasons for gift "
                    "recommendations. Return JSON with a 'reasons' array. Each reason "
                    "should be one sentence, <= 18 words. Write in English."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create reasons for each recommendation in order. JSON only. "
                    f"Input: {json.dumps(prompt)}"
                ),
            },
        ]

        response = _call_openai_chat(messages)
        if response:
            try:
                payload = json.loads(response)
                reasons = payload.get("reasons", [])
                if len(reasons) == len(recommendations):
                    return reasons, "llm"
            except json.JSONDecodeError:
                pass

    return _heuristic_recommendation_reasons(recommendations), "heuristic"


def _heuristic_recommendation_reasons(recommendations):
    reasons = []
    for rec in recommendations:
        rating = rec.get("rating")
        category = rec.get("product_category")
        persona = rec.get("gift_persona")
        delivery = rec.get("delivery_speed")
        price = rec.get("unit_price")

        parts = []
        if rating is not None:
            parts.append(f"High rating ({float(rating):.1f})")
        if persona:
            parts.append(f"popular for {persona} gifts")
        if delivery:
            parts.append(f"supports {delivery} delivery")
        if category:
            parts.append(f"strong {category} choice")
        if price is not None:
            parts.append(f"fits around {float(price):.2f}")

        if not parts:
            reasons.append("Strong match based on recent gifting signals.")
        else:
            reasons.append(", ".join(parts[:3]).capitalize() + "."
            )
    return reasons


@lru_cache(maxsize=1)
def build_product_search_index():
    conn = get_db()
    try:
        products = pd.read_sql_query(
            "SELECT product_id, product_name, brand, category, flavor, unit_price "
            "FROM dim_product",
            conn,
        )
        reviews = pd.read_sql_query(
            "SELECT product_name, product_category, product_subcategory, brand, "
            "gift_persona, delivery_speed, rating, event_type "
            "FROM gift_recommender",
            conn,
        )
    finally:
        conn.close()

    if reviews.empty:
        reviews = pd.DataFrame(
            columns=[
                "product_name",
                "product_category",
                "product_subcategory",
                "brand",
                "gift_persona",
                "delivery_speed",
                "rating",
                "event_type",
            ]
        )

    agg = reviews.groupby("product_name").agg(
        product_category=("product_category", "first"),
        product_subcategory=("product_subcategory", "first"),
        brand=("brand", "first"),
        avg_rating=("rating", "mean"),
        review_count=("rating", "count"),
        top_persona=("gift_persona", _top_value),
        top_delivery=("delivery_speed", _top_value),
        top_event=("event_type", _top_value),
    )

    merged = products.merge(agg, on="product_name", how="left")

    records = []
    texts = []
    for _, row in merged.iterrows():
        avg_rating = row.get("avg_rating")
        review_count = row.get("review_count")
        persona = row.get("top_persona") or "mixed"
        delivery = row.get("top_delivery") or "standard"
        category = row.get("category") or row.get("product_category") or ""
        brand = row.get("brand") or ""
        flavor = row.get("flavor") or ""
        subcategory = row.get("product_subcategory") or ""

        if pd.isna(avg_rating) or pd.isna(review_count):
            rating_text = "No ratings yet"
        else:
            rating_text = f"Avg rating {float(avg_rating):.1f} from {int(review_count)} reviews"

        snippet = f"{rating_text}. Popular for {persona} gifts with {delivery} delivery."

        text = " ".join(
            [
                str(row.get("product_name", "")),
                str(brand),
                str(category),
                str(subcategory),
                str(flavor),
                str(row.get("product_category", "")),
                str(row.get("product_subcategory", "")),
                str(persona),
                str(delivery),
                str(row.get("top_event", "")),
                snippet,
            ]
        )

        record = {
            "product_id": row.get("product_id"),
            "product_name": row.get("product_name"),
            "brand": brand,
            "category": category,
            "flavor": flavor,
            "unit_price": row.get("unit_price"),
            "avg_rating": None if pd.isna(avg_rating) else float(avg_rating),
            "review_count": None if pd.isna(review_count) else int(review_count),
            "snippet": snippet,
        }

        records.append(record)
        texts.append(text)

    if not texts:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([""])
    else:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(texts)

    return SearchIndex(vectorizer=vectorizer, matrix=matrix, records=records)


def semantic_search(query, limit=8):
    if not query or not query.strip():
        return []

    index = build_product_search_index()
    if not index.records:
        return []
    vector = index.vectorizer.transform([query])
    scores = cosine_similarity(vector, index.matrix).flatten()

    ranked = scores.argsort()[::-1]
    results = []
    for idx in ranked[:limit]:
        if scores[idx] <= 0:
            continue
        record = dict(index.records[idx])
        record["score"] = float(scores[idx])
        results.append(record)

    return results


def generate_experience_summary(details):
    if llm_available():
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly planner. Write a short, upbeat plan summary "
                    "in 3 sentences."
                ),
            },
            {
                "role": "user",
                "content": f"Plan details: {json.dumps(details)}",
            },
        ]
        response = _call_openai_chat(messages, temperature=0.4, max_tokens=160)
        if response:
            return response.strip()

    persona = details.get("persona")
    gift = details.get("top_gift")
    delivery = details.get("delivery_speed")
    region = details.get("region")

    if gift:
        return (
            f"Start with {gift} as a {persona} favorite, then confirm inventory and "
            f"schedule {delivery} delivery for {region}. Add a personal note and a "
            "simple follow-up touchpoint after delivery."
        )

    return (
        "Pick a gift aligned to the persona, confirm availability, then lock in the "
        "delivery window and personalize the message."
    )


def generate_love_letter(customer, events, tone):
    if not customer:
        return "We could not find that customer yet. Try another profile.", "heuristic", None

    payload = {
        "customer": {
            "first_name": customer.get("first_name"),
            "last_name": customer.get("last_name"),
            "city": customer.get("city"),
            "state_province": customer.get("state_province"),
            "country_code": customer.get("country_code"),
            "age_band": customer.get("age_band"),
            "loyalty_tier": customer.get("loyalty_tier"),
            "preferred_language": customer.get("preferred_language"),
            "consent_marketing": customer.get("consent_marketing"),
        },
        "recent_gifts": [
            {
                "product_name": event.get("product_name"),
                "gift_persona": event.get("gift_persona"),
                "delivery_speed": event.get("delivery_speed"),
                "rating": event.get("rating"),
            }
            for event in events or []
        ],
        "tone": tone,
    }

    if llm_available():
        messages = [
            {
                "role": "system",
                "content": (
                    "You write short, warm love letters for a chocolate brand. "
                    "Keep it professional, light, and a bit funny. 120-160 words. "
                    "Write in English. "
                    "Must include the customer's first name, city/country, loyalty tier, "
                    "and mention 1-2 recent products if available."
                ),
            },
            {
                "role": "user",
                "content": f"Write the letter using this context: {json.dumps(payload)}",
            },
        ]
        response, source, error = _call_openai_chat_with_error(
            messages, temperature=0.6, max_tokens=260
        )
        if response:
            return response.strip(), source, None

    name = customer.get("first_name", "there")
    location = f"{customer.get('city', '')}, {customer.get('state_province', '')}".strip(", ")
    if customer.get("country_code"):
        location = f"{location}, {customer.get('country_code')}".strip(", ")
    persona = None
    delivery = None
    recent_products = []
    if events:
        persona = events[0].get("gift_persona")
        delivery = events[0].get("delivery_speed")
        recent_products = [event.get("product_name") for event in events if event.get("product_name")]

    line_one = f"Dear {name},"
    line_two = (
        f"From {location} to the sweetest moments, we noticed your {customer.get('loyalty_tier', 'loyal')} love style."
    )
    line_three = "We picked something thoughtful to match your gifting vibe"
    if persona:
        line_three += f" for {persona} moments"
    if delivery:
        line_three += f" with {delivery} delivery"
    line_three += "."
    if recent_products:
        line_three += f" Recent favorites include {', '.join(recent_products[:2])}."
    line_four = "May your Valentine be rich in smiles, surprises, and chocolate." 
    closing = "With affection,\nCupid Chocolate Company"

    return "\n\n".join([line_one, line_two, line_three, line_four, closing]), "heuristic", error


def _format_rows(rows, limit=5):
    return rows[:limit] if rows else []


def generate_sales_chat_response(question, context):
    if not question or not question.strip():
        return "Ask a sales question to get started.", "heuristic", None

    compact = {
        "summary": context.get("summary"),
        "top_categories": _format_rows(context.get("by_category"), 5),
        "top_products": _format_rows(context.get("top_products"), 5),
        "channels": context.get("by_channel"),
        "top_countries": _format_rows(context.get("by_country"), 5),
        "monthly": _format_rows(context.get("by_month"), 12),
        "promotions": _format_rows(context.get("by_promo"), 5),
        "loyalty": context.get("by_loyalty"),
    }

    if llm_available():
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a sales analyst. Use only the provided data to answer. "
                    "Be concise, English only. If data is missing, say what is missing."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"Data: {json.dumps(compact)}"
                ),
            },
        ]
        response, source, error = _call_openai_chat_with_error(
            messages, temperature=0.2, max_tokens=260
        )
        if response:
            return response.strip(), source, None
        return "I could not generate an answer from the model.", source, error

    q = question.lower()
    if "product" in q or "sku" in q:
        rows = compact["top_products"]
        if rows:
            items = ", ".join(f"{r['product_name']} ({r['revenue']:.2f})" for r in rows)
            return f"Top products by revenue: {items}.", "heuristic", None
    if "category" in q:
        rows = compact["top_categories"]
        if rows:
            items = ", ".join(f"{r['category']} ({r['revenue']:.2f})" for r in rows)
            return f"Top categories by revenue: {items}.", "heuristic", None
    if "channel" in q:
        rows = compact["channels"] or []
        if rows:
            items = ", ".join(f"{r['channel']} ({r['revenue']:.2f})" for r in rows)
            return f"Revenue by channel: {items}.", "heuristic", None
    if "country" in q or "region" in q:
        rows = compact["top_countries"]
        if rows:
            items = ", ".join(f"{r['country_code']} ({r['revenue']:.2f})" for r in rows)
            return f"Top countries by revenue: {items}.", "heuristic", None
    if "month" in q or "trend" in q:
        rows = compact["monthly"]
        if rows:
            last = rows[-1]
            return (
                f"Latest month revenue: {last['revenue']:.2f} across {last['orders']} orders.",
                "heuristic",
                None,
            )

    summary = compact.get("summary") or {}
    return (
        f"Overall revenue is {summary.get('revenue', 0):.2f} with profit {summary.get('profit', 0):.2f}.",
        "heuristic",
        None,
    )
