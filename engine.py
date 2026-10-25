def calculate_dumpling_finances(event: dict, config: dict) -> dict:
    att = float(event.get("estimated_attendance", 500))
    category = str(event.get("category", "General")).lower()
    product_format = str(event.get("product_format", "Both Hot & Frozen"))
    num_griddles = int(event.get("num_griddles", 2))
    
    is_niche = any(tag in category for tag in ["niche", "gf", "celiac", "vegan", "wellness", "athletic"])
    demo_pct = 0.70 if is_niche else 0.12
    capture_pct = 0.22 if is_niche else 0.09
    projected_patrons = round(att * demo_pct * capture_pct)
    
    operating_hours = float(event.get("operating_hours", 6.0))
    max_items_per_hr = num_griddles * 30
    max_capacity_items = round(max_items_per_hr * operating_hours)
    
    if product_format == "Frozen Only":
        hot_items = 0
        frozen_items = min(projected_patrons, round(60 * operating_hours))
        actual_patrons = frozen_items
        staff_count = 1
        packaging_cost = frozen_items * 0.50
    elif product_format == "Hot Cooked Only":
        actual_patrons = min(projected_patrons, max_capacity_items)
        hot_items = actual_patrons
        frozen_items = 0
        packaging_cost = hot_items * 0.75
        staff_count = 2 if num_griddles <= 2 else (3 if num_griddles == 3 else 4)
    else:
        actual_hot = min(round(projected_patrons * 0.75), max_capacity_items)
        actual_frozen = round(projected_patrons * 0.25)
        hot_items = actual_hot
        frozen_items = actual_frozen
        actual_patrons = hot_items + frozen_items
        packaging_cost = (hot_items * 0.75) + (frozen_items * 0.50)
        staff_count = 2 if num_griddles <= 2 else (3 if num_griddles == 3 else 4)
        
    gross_revenue = (hot_items * config["item_menu_price"]) + (frozen_items * config["frozen_pack_price"])
    total_dumplings = (hot_items * 4) + (frozen_items * 4)
    food_cogs = total_dumplings * config["ingredient_cogs"]
    total_cogs = food_cogs + packaging_cost
    
    dist_miles = float(event.get("distance_from_tucson_miles", 0.0))
    transit_hours = (dist_miles / 55.0) * 2.0
    total_shift_hours = operating_hours + 1.5 + transit_hours
    on_site_labor = staff_count * total_shift_hours * config["hourly_wage"]
    
    mileage_cost = dist_miles * 2.0 * 0.35
    lodging_cost = 220.00 if dist_miles > 180 else 0.00
    
    loc_lower = str(event.get("location", "")).lower()
    permit_fee = 0.00 if dist_miles <= 50 else (200.00 if "maricopa" in loc_lower or "phoenix" in loc_lower or "scottsdale" in loc_lower else 150.00)
    booth_fee = float(event.get("vendor_fee_usd", 150.00))
    utility_fee = 40.00 if (not event.get("power_available", True) and product_format != "Frozen Only") else 0.00
    
    total_expenses = total_cogs + on_site_labor + mileage_cost + lodging_cost + permit_fee + booth_fee + utility_fee
    net_profit = gross_revenue - total_expenses
    roi = (net_profit / total_expenses) if total_expenses > 0 else 0.0
    
    tier = "Tier 1: Green Light" if net_profit >= 1100.0 and roi >= 0.75 else ("Tier 2: Tactical Fill-In" if net_profit >= 450.0 else "Tier 3: Pass / Archive")
    
    return {
        "gross_revenue": round(gross_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(net_profit, 2),
        "roi_text": f"{round(roi * 100, 1)}%",
        "decision_tier": tier,
        "prep_dumplings": int(total_dumplings),
        "projected_customers": int(actual_patrons)
    }
