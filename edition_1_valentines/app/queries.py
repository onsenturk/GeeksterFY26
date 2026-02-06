from collections import Counter
from math import sqrt

from .ai import (
    generate_experience_summary,
    generate_love_letter,
    generate_recommendation_explanations,
    semantic_search,
)
from .db import get_db


def list_customers(limit=50):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT customer_id, first_name, last_name, loyalty_tier "
            "FROM dim_customer ORDER BY customer_id LIMIT ?",
            (limit,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def list_products(limit=50):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT product_id, product_name, unit_price, category "
            "FROM dim_product ORDER BY product_id LIMIT ?",
            (limit,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def list_matchmaking_users(limit=50):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT user_id, age, location_region "
            "FROM matchmaking ORDER BY user_id LIMIT ?",
            (limit,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def love_letter_data(customer_id):
    conn = get_db()
    try:
        customer = conn.execute(
            "SELECT customer_id, first_name, last_name, city, country_code, "
            "state_province, age_band, preferred_language, loyalty_tier, "
            "consent_marketing "
            "FROM dim_customer WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

        events = conn.execute(
            "SELECT event_type, product_name, gift_persona, delivery_speed, rating "
            "FROM gift_recommender "
            "WHERE customer_id = ? "
            "ORDER BY event_ts DESC LIMIT 3",
            (customer_id,),
        ).fetchall()
        return customer, events
    finally:
        conn.close()


def love_letter_with_ai(customer_id, tone):
    customer, events = love_letter_data(customer_id)
    customer_data = dict(customer) if customer else None
    event_data = [dict(event) for event in events] if events else []
    letter, source, error = generate_love_letter(customer_data, event_data, tone)
    return customer, events, letter, source, error


def recommend_products(customer_id, limit=5):
    conn = get_db()
    try:
        profile = conn.execute(
            "SELECT AVG(avg_order_value_user) AS avg_order_value "
            "FROM gift_recommender WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

        customer_profile = conn.execute(
            "SELECT loyalty_tier, age_band, country_code "
            "FROM dim_customer WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

        top_persona_row = conn.execute(
            "SELECT gift_persona, COUNT(*) AS cnt "
            "FROM gift_recommender WHERE customer_id = ? "
            "GROUP BY gift_persona ORDER BY cnt DESC LIMIT 1",
            (customer_id,),
        ).fetchone()

        top_delivery_row = conn.execute(
            "SELECT delivery_speed, COUNT(*) AS cnt "
            "FROM gift_recommender WHERE customer_id = ? "
            "GROUP BY delivery_speed ORDER BY cnt DESC LIMIT 1",
            (customer_id,),
        ).fetchone()

        top_category_row = conn.execute(
            "SELECT product_category, COUNT(*) AS cnt "
            "FROM gift_recommender WHERE customer_id = ? "
            "GROUP BY product_category ORDER BY cnt DESC LIMIT 1",
            (customer_id,),
        ).fetchone()

        rows = conn.execute(
            "SELECT product_name, product_category, unit_price, AVG(rating) AS rating, "
            "AVG(discount_pct) AS discount_pct, AVG(list_price) AS list_price, "
            "gift_persona, delivery_speed, MAX(event_ts) AS last_event "
            "FROM gift_recommender "
            "WHERE customer_id = ? "
            "AND (returned_flag = 'False' OR returned_flag IS NULL) "
            "GROUP BY product_name, product_category, unit_price, gift_persona, delivery_speed "
            "ORDER BY last_event DESC, rating DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()

        if not rows and customer_profile:
            loyalty_tier = customer_profile["loyalty_tier"]
            age_band = customer_profile["age_band"]
            country_code = customer_profile["country_code"]
            category_filter = top_category_row["product_category"] if top_category_row else None

            tier_sql = (
                "SELECT gr.product_name, gr.product_category, gr.unit_price, "
                "AVG(gr.rating) AS rating, AVG(gr.discount_pct) AS discount_pct, "
                "AVG(gr.list_price) AS list_price, gr.gift_persona, gr.delivery_speed "
                "FROM gift_recommender gr "
                "JOIN dim_customer dc ON gr.customer_id = dc.customer_id "
                "WHERE dc.loyalty_tier = ? "
            )

            params = [loyalty_tier]
            if age_band:
                tier_sql += "AND dc.age_band = ? "
                params.append(age_band)
            if country_code:
                tier_sql += "AND dc.country_code = ? "
                params.append(country_code)
            if category_filter:
                tier_sql += "AND gr.product_category = ? "
                params.append(category_filter)

            tier_sql += (
                "GROUP BY gr.product_name, gr.product_category, gr.unit_price, "
                "gr.gift_persona, gr.delivery_speed "
                "ORDER BY rating DESC LIMIT ?"
            )
            params.append(limit)
            rows = conn.execute(tier_sql, params).fetchall()

        if not rows and top_persona_row:
            rows = conn.execute(
                "SELECT product_name, product_category, unit_price, AVG(rating) AS rating, "
                "AVG(discount_pct) AS discount_pct, AVG(list_price) AS list_price, "
                "gift_persona, delivery_speed "
                "FROM gift_recommender "
                "WHERE gift_persona = ? "
                "GROUP BY product_name, product_category, unit_price, gift_persona, delivery_speed "
                "ORDER BY rating DESC LIMIT ?",
                (top_persona_row["gift_persona"], limit),
            ).fetchall()

        if not rows:
            rows = conn.execute(
                "SELECT product_name, product_category, unit_price, AVG(rating) AS rating, "
                "AVG(discount_pct) AS discount_pct, AVG(list_price) AS list_price, "
                "gift_persona, delivery_speed "
                "FROM gift_recommender "
                "GROUP BY product_name, product_category, unit_price, gift_persona, delivery_speed "
                "ORDER BY rating DESC LIMIT ?",
                (limit,),
            ).fetchall()

        recommendations = []
        target_price = None
        if profile and profile["avg_order_value"]:
            target_price = float(profile["avg_order_value"])

        ratings = [float(row["rating"]) for row in rows if row["rating"] is not None]
        discounts = [float(row["discount_pct"]) for row in rows if row["discount_pct"] is not None]
        prices = [float(row["unit_price"]) for row in rows if row["unit_price"] is not None]

        rating_min = min(ratings) if ratings else 0.0
        rating_max = max(ratings) if ratings else 5.0
        discount_min = min(discounts) if discounts else 0.0
        discount_max = max(discounts) if discounts else 50.0
        price_min = min(prices) if prices else 0.0
        price_max = max(prices) if prices else 1.0

        seen = set()
        for row in rows:
            rating = row["rating"]
            discount = row["discount_pct"]
            unit_price = row["unit_price"]
            persona = row["gift_persona"]
            delivery = row["delivery_speed"]

            product_key = (row["product_name"], row["product_category"]) if row["product_name"] else None
            if product_key in seen:
                continue
            if product_key:
                seen.add(product_key)

            if rating is None or rating_max == rating_min:
                rating_norm = 0.5
            else:
                rating_norm = (float(rating) - rating_min) / (rating_max - rating_min)

            if discount is None or discount_max == discount_min:
                discount_norm = 0.2
            else:
                discount_norm = (float(discount) - discount_min) / (discount_max - discount_min)

            if target_price and unit_price:
                price_gap = abs(float(unit_price) - target_price) / target_price
                price_fit = 1.0 - min(price_gap, 1.0)
            elif unit_price is None or price_max == price_min:
                price_fit = 0.5
            else:
                price_fit = 1.0 - (float(unit_price) - price_min) / (price_max - price_min)

            persona_match = (
                1.0 if persona and top_persona_row and persona == top_persona_row["gift_persona"] else 0.4
            )
            delivery_match = (
                1.0 if delivery and top_delivery_row and delivery == top_delivery_row["delivery_speed"] else 0.5
            )

            score = (
                0.45 * rating_norm
                + 0.2 * discount_norm
                + 0.2 * price_fit
                + 0.1 * persona_match
                + 0.05 * delivery_match
            )
            ai_rating = round(score * 5.0, 2)
            row_dict = dict(row)
            row_dict["ai_rating"] = ai_rating
            recommendations.append(row_dict)

        recommendations.sort(key=lambda item: item["ai_rating"], reverse=True)
        return recommendations[:limit]
    finally:
        conn.close()


def _get_customer_profile(customer_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT customer_id, first_name, last_name, loyalty_tier, age_band, "
            "country_code, preferred_language "
            "FROM dim_customer WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def recommend_products_with_explanations(customer_id, limit=5):
    rows = recommend_products(customer_id, limit)
    recommendations = [dict(row) for row in rows]
    customer = _get_customer_profile(customer_id) or {}
    reasons, source = generate_recommendation_explanations(customer, recommendations)
    for rec, reason in zip(recommendations, reasons):
        rec["why"] = reason
    return recommendations, {"mode": source}


def compatibility_score(user_a, user_b):
    conn = get_db()
    try:
        row_a = conn.execute(
            "SELECT * FROM matchmaking WHERE user_id = ?", (user_a,)
        ).fetchone()
        row_b = conn.execute(
            "SELECT * FROM matchmaking WHERE user_id = ?", (user_b,)
        ).fetchone()
    finally:
        conn.close()

    if not row_a or not row_b:
        return None

    traits = [
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    ]

    diff = 0.0
    for trait in traits:
        diff += abs(float(row_a[trait]) - float(row_b[trait]))
    score = max(0.0, 1.0 - (diff / len(traits)))

    interests_a = set((row_a["interests"] or "").split(","))
    interests_b = set((row_b["interests"] or "").split(","))
    overlap = {item.strip() for item in interests_a & interests_b if item.strip()}

    return {
        "user_a": row_a,
        "user_b": row_b,
        "score": round(score * 100, 1),
        "overlap": sorted(overlap),
    }


def sales_overview():
    conn = get_db()
    try:
        summary = conn.execute(
            "SELECT COUNT(*) AS orders, "
            "SUM(total_amount) AS revenue, "
            "SUM(total_amount - cost_amount) AS profit, "
            "AVG(total_amount) AS avg_order "
            "FROM fact_sales"
        ).fetchone()

        top_products = conn.execute(
            "SELECT dp.product_name, SUM(fs.total_amount) AS revenue, "
            "SUM(fs.quantity_sold) AS units "
            "FROM fact_sales fs "
            "JOIN dim_product dp ON fs.product_id = dp.product_id "
            "GROUP BY dp.product_name "
            "ORDER BY revenue DESC LIMIT 5"
        ).fetchall()
        return summary, top_products
    finally:
        conn.close()


def global_love_metrics():
    conn = get_db()
    try:
        delivery = conn.execute(
            "SELECT region_destination, "
            "AVG(latency_ms) AS avg_latency, "
            "AVG(CASE WHEN delivery_status = 'delivered' THEN 1.0 ELSE 0.0 END) "
            "AS success_rate "
            "FROM love_notes_telemetry "
            "GROUP BY region_destination "
            "ORDER BY avg_latency DESC"
        ).fetchall()

        routing = conn.execute(
            "SELECT region, request_count_per_min, p95_latency_ms, failure_rate "
            "FROM global_routing ORDER BY failure_rate DESC LIMIT 5"
        ).fetchall()
        return delivery, routing
    finally:
        conn.close()


def supply_chain_alerts(limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT sc.product_id, dp.product_name, sc.vendor_lead_time_days, "
            "sc.stock_level, sc.delay_reason, sc.region, sc.cost_per_unit "
            "FROM supply_chain sc "
            "JOIN dim_product dp ON sc.product_id = dp.product_id"
        ).fetchall()
    finally:
        conn.close()

    alerts = []
    for row in rows:
        lead_time = float(row["vendor_lead_time_days"])
        stock = float(row["stock_level"])
        delay_penalty = 5.0 if row["delay_reason"] != "none" else 0.0
        stock_risk = max(0.0, (500.0 - stock) / 500.0) * 30.0
        score = lead_time * 0.7 + stock_risk + delay_penalty
        alerts.append({"row": row, "risk": round(score, 2)})

    alerts.sort(key=lambda item: item["risk"], reverse=True)
    return alerts[:limit]


def gift_concierge(budget, persona, delivery_speed, limit=5):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT product_name, product_category, unit_price, rating, delivery_speed "
            "FROM gift_recommender "
            "WHERE list_price <= ? "
            "AND gift_persona = ? "
            "AND delivery_speed = ? "
            "ORDER BY rating DESC LIMIT ?",
            (budget, persona, delivery_speed, limit),
        ).fetchall()

        if rows:
            return rows

        rows = conn.execute(
            "SELECT product_name, product_category, unit_price, AVG(rating) AS rating, "
            "delivery_speed "
            "FROM gift_recommender "
            "WHERE list_price <= ? "
            "GROUP BY product_name, product_category, unit_price, delivery_speed "
            "ORDER BY rating DESC LIMIT ?",
            (budget, limit),
        ).fetchall()
        return rows
    finally:
        conn.close()


def semantic_product_search(query, limit=8):
    return semantic_search(query, limit=limit)


def list_regions(limit=50):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT region FROM global_routing ORDER BY region LIMIT ?",
            (limit,),
        ).fetchall()
        return [row["region"] for row in rows]
    finally:
        conn.close()


def _supply_chain_risk_map():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT dp.product_name, sc.vendor_lead_time_days, sc.stock_level, "
            "sc.delay_reason "
            "FROM supply_chain sc "
            "JOIN dim_product dp ON sc.product_id = dp.product_id"
        ).fetchall()
    finally:
        conn.close()

    risk_map = {}
    for row in rows:
        lead_time = float(row["vendor_lead_time_days"])
        stock = float(row["stock_level"])
        delay_penalty = 5.0 if row["delay_reason"] != "none" else 0.0
        stock_risk = max(0.0, (500.0 - stock) / 500.0) * 30.0
        score = lead_time * 0.7 + stock_risk + delay_penalty
        risk_map[row["product_name"]] = round(score, 2)

    return risk_map


def _delivery_metrics(region):
    conn = get_db()
    try:
        routing = conn.execute(
            "SELECT request_count_per_min, p95_latency_ms, failure_rate "
            "FROM global_routing WHERE region = ?",
            (region,),
        ).fetchone()

        success = conn.execute(
            "SELECT AVG(CASE WHEN delivery_status = 'delivered' THEN 1.0 ELSE 0.0 END) "
            "AS success_rate "
            "FROM love_notes_telemetry WHERE region_destination = ?",
            (region,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "routing": dict(routing) if routing else None,
        "success_rate": None if not success else success["success_rate"],
    }


def valentine_experience_plan(budget, persona, delivery_speed, region):
    recommendations = gift_concierge(budget, persona, delivery_speed, limit=3)
    recs = [dict(row) for row in recommendations]
    top_gift = recs[0]["product_name"] if recs else None

    risk_map = _supply_chain_risk_map()
    risk_score = risk_map.get(top_gift)

    delivery = _delivery_metrics(region) if region else {"routing": None, "success_rate": None}

    steps = [
        {
            "title": "Select the gift",
            "detail": "Pick a top-rated gift that matches the recipient persona.",
        },
        {
            "title": "Confirm inventory",
            "detail": "Check supply chain risk and stock levels before finalizing.",
        },
        {
            "title": "Lock delivery",
            "detail": "Choose the delivery window and validate regional reliability.",
        },
        {
            "title": "Personalize the moment",
            "detail": "Add a note and a follow-up touchpoint after delivery.",
        },
    ]

    summary = generate_experience_summary(
        {
            "budget": budget,
            "persona": persona,
            "delivery_speed": delivery_speed,
            "region": region,
            "top_gift": top_gift,
        }
    )

    return {
        "recommendations": recs,
        "risk_score": risk_score,
        "delivery": delivery,
        "steps": steps,
        "summary": summary,
    }


def order_quote(product_id, quantity, loyalty_tier):
    conn = get_db()
    try:
        product = conn.execute(
            "SELECT product_id, product_name, unit_price, category "
            "FROM dim_product WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    finally:
        conn.close()

    if not product:
        return None

    discount_map = {
        "Bronze": 0.0,
        "Silver": 0.05,
        "Gold": 0.1,
        "Platinum": 0.12,
    }
    discount = discount_map.get(loyalty_tier, 0.0)
    subtotal = float(product["unit_price"]) * quantity
    total = subtotal * (1.0 - discount)

    return {
        "product": product,
        "quantity": quantity,
        "discount": discount,
        "subtotal": round(subtotal, 2),
        "total": round(total, 2),
    }


def analytics_overview():
    conn = get_db()
    try:
        tables = [
            "dim_customer",
            "dim_product",
            "fact_sales",
            "gift_recommender",
            "supply_chain",
            "matchmaking",
            "behavior_edges",
            "broken_hearts_security",
            "trust_safety",
            "global_routing",
            "love_notes_telemetry",
            "work_dynamics",
        ]
        counts = {}
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            counts[table] = count

        scores = conn.execute(
            "SELECT AVG(rating) AS avg_rating, "
            "AVG(discount_pct) AS avg_discount, "
            "AVG(unit_price) AS avg_price "
            "FROM gift_recommender"
        ).fetchone()
        return counts, scores
    finally:
        conn.close()
