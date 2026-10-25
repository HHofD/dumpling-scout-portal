import math

def calculate_dumpling_finances(event: dict, config: dict) -> dict:
    att = float(event.get("estimated_attendance", 500))
    category = str(event.get("category", "General")).lower()
    product_format = str(event.get("product_format", "Both Hot & Frozen"))
    operating_hours = float(event.get("operating_hours", 6.0))
    fulfillment_time_target = float(config.get("fulfillment_time_target", 1.5))
    
    # 1. Demographic Fit & Demand Capture
    is_niche = any(tag in category for tag in ["niche", "gf", "celiac", "vegan", "wellness", "athletic"])
    demo_pct = 0.70 if is_niche else 0.12
    capture_pct = 0.22 if is_niche else 0.09
    projected_patrons = round(att * demo_pct * capture_pct)
    
    # 2. Sales Volume based on Product Format & Sidebar Sliders
    frozen_pct = float(config.get("frozen_upsell_pct", 0.25))
    
    if product_format == "Frozen Only":
        hot_items = 0
        frozen_items = projected_patrons
        packaging_cost = frozen_items * 0.50
    elif product_format == "Hot Cooked Only":
        hot_items = projected_patrons
        frozen_items = 0
        packaging_cost = hot_items * 0.75
    else:  # "Both Hot & Frozen"
        hot_items = round(projected_patrons * (1.0 - frozen_pct))
        frozen_items = round(projected_patrons * frozen_pct)
        packaging_cost = (hot_items * 0.75) + (frozen_items * 0.50)
        
    actual_patrons = hot_items + frozen_items
    gross_revenue = (hot_items * config["item_menu_price"]) + (frozen_items * config["frozen_pack_price"])
    
    # 3. Dynamic Griddle Calculation (No Cap!)
    # 24 dumplings per griddle every 12 mins = 2 dumplings/min capacity per griddle
    # Average order = 4 dumplings
    if hot_items > 0:
        peak_hour_patrons = (hot_items / operating_hours) * 1.5
        dumplings_per_minute_required = (peak_hour_patrons * 4) / 60.0
        
        # Warmers buffer output by 25% (2.0 -> 2.5 dumplings/min per griddle)
        griddle_output_per_minute = 2.0 * 1.25 
        calculated_griddles = int(max(1, math.ceil(dumplings_per_minute_required / griddle_output_per_minute)))
    else:
        calculated_griddles = 0
        
    # Staffing ratio rule:
    # 0 griddles (frozen only) = 1 staff
    # 1 to 3 griddles = 1 cook + 1 cashier = 2 staff
    # 4+ griddles = 2 cooks + 2 FOH = 4 staff
    if calculated_griddles == 0:
        staff_count = 1
    elif calculated_griddles <= 3:
        staff_count = 2
    else:
        staff_count = 4
        
    # 4. Food COGS (4 dumplings per item)
    total_dumplings = (hot_items * 4) + (frozen_items * 4)
    food_cogs = total_dumplings * config["ingredient_cogs"]
    total_cogs = food_cogs + packaging_cost
    
    # 5. Labor & Transit Costs
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
        "projected_customers": int(actual_patrons),
        "required_griddles": calculated_griddles
    }
