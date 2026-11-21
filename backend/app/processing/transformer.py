"""MahaRERA Data Transformer & JSONB Normalizer.

Transforms raw scraped dictionaries (Summary_of_Apartments/Units, bhk_details,
building_details, All_Parking_Details) into normalized, production-grade JSONB
structures for PostgreSQL storage.

Features:
- Deterministic parsing of apartment types (1 RK, 1 BHK, 2 BHK, 3 BHK, Shop, Office, etc.)
- Carpet area calculations (SqMt & SqFt with min/max ranges)
- Building-wise floor counts, CC status, and unit allocations
- Structured parking summaries (Open, Covered, 2-wheelers, 4-wheelers, Visitors)
- Retains raw tables inside the structured payload for full auditability
"""
import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

SQMT_TO_SQFT = 10.7639


def clean_val(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "null", "") else None


def parse_dict_safely(val: Any) -> Dict[str, Any]:
    """Parse dictionary from dict, JSON string, or Python literal string."""
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "{}"):
        return {}
    try:
        res = json.loads(s)
        if isinstance(res, dict):
            return res
    except Exception:
        pass
    try:
        res = ast.literal_eval(s)
        if isinstance(res, dict):
            return res
    except Exception:
        pass
    return {}


def normalize_unit_type(raw_type: Any) -> str:
    """Standardize raw apartment type strings into clean BHK / Commercial categories."""
    if not raw_type:
        return "Unknown"
    
    t = str(raw_type).strip().upper()
    
    if re.search(r'\b1\s*RK\b', t) or t == '1RK':
        return '1 RK'
    
    m = re.search(r'([1-9])\s*(?:BHK|RHK|B\/HK|BEDROOM)', t)
    if m:
        return f"{m.group(1)} BHK"
    
    if "PENTHOUSE" in t:
        return "Penthouse"
    if "SHOP" in t:
        return "Shop"
    if "OFFICE" in t:
        return "Office"
    if "COMMERCIAL" in t:
        return "Commercial"
    if "RESTAURANT" in t:
        return "Restaurant"
    if "ROW HOUSE" in t or "VILLA" in t:
        return "Row House/Villa"
    if "PLOT" in t:
        return "Plot"
        
    return "Other/Custom"


def extract_bhk_carpet_areas(summary_dict: Dict[str, Any], bhk_dict: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Extract BHK-wise carpet areas, unit counts, and configuration summaries."""
    bhk_summary: Dict[str, Any] = {
        "bhk_configurations": "",
        "total_units": 0,
        "total_residential_units": 0,
        "total_commercial_units": 0,
        "less_than_1bhk_units": 0,
        "less_than_1bhk_carpet_sqmt_min": None,
        "less_than_1bhk_carpet_sqmt_max": None,
        "less_than_1bhk_carpet_sqft_min": None,
        "less_than_1bhk_carpet_sqft_max": None,
        "greater_than_3bhk_units": 0,
        "greater_than_3bhk_carpet_sqmt_min": None,
        "greater_than_3bhk_carpet_sqmt_max": None,
        "greater_than_3bhk_carpet_sqft_min": None,
        "greater_than_3bhk_carpet_sqft_max": None,
        "bhk_wise_min_max_area": None,
        "bhk_wise_carpet_area": None,
    }
    
    detailed_units: List[Dict[str, Any]] = []
    
    # 1. First check if Summary_of_Apartments/Units has Apartment Type
    if summary_dict and isinstance(summary_dict, dict):
        raw_types = summary_dict.get("Apartment Type", [])
        if raw_types and len(raw_types) > 0:
            bld_names = summary_dict.get("Building Name", [])
            sqmts = summary_dict.get("Carpet Area (in Sqmts)", [])
            counts = summary_dict.get("Number of Apartment", [])
            
            n = max(len(raw_types), len(sqmts), len(counts))
            bld_names = bld_names + ["Building 1"] * (n - len(bld_names))
            raw_types = raw_types + [""] * (n - len(raw_types))
            sqmts = sqmts + ["0"] * (n - len(sqmts))
            counts = counts + ["0"] * (n - len(counts))
            
            for bld, r_type, s_str, c_str in zip(bld_names, raw_types, sqmts, counts):
                norm_type = normalize_unit_type(r_type)
                try:
                    sqmt = round(float(s_str), 2)
                except (ValueError, TypeError):
                    sqmt = None
                try:
                    cnt = int(c_str)
                except (ValueError, TypeError):
                    cnt = 0
                sqft = round(sqmt * SQMT_TO_SQFT, 1) if sqmt is not None else None
                detailed_units.append({
                    "building_name": bld or "Building 1",
                    "apartment_type_raw": r_type,
                    "apartment_type_standard": norm_type,
                    "carpet_area_sqmt": sqmt,
                    "carpet_area_sqft": sqft,
                    "number_of_units": cnt
                })

    # 2. If no units from summary_dict, check bhk_dict (nested by building)
    if not detailed_units and bhk_dict and isinstance(bhk_dict, dict):
        for bld_name, content in bhk_dict.items():
            if not isinstance(content, dict):
                continue
            u_types = content.get("Unit Type", [])
            u_sqmts = content.get("Unit Carpet Area (Sq.Mts)", [])
            u_names = content.get("Unit Name", [])
            if not u_types and not u_sqmts:
                continue
            n_b = max(len(u_types), len(u_sqmts), len(u_names))
            u_types = u_types + [""] * (n_b - len(u_types))
            u_sqmts = u_sqmts + ["0"] * (n_b - len(u_sqmts))
            u_names = u_names + [""] * (n_b - len(u_names))
            for ut, us, un in zip(u_types, u_sqmts, u_names):
                norm_type = normalize_unit_type(ut)
                try:
                    sqmt = round(float(us), 2)
                except (ValueError, TypeError):
                    sqmt = None
                sqft = round(sqmt * SQMT_TO_SQFT, 1) if sqmt is not None else None
                detailed_units.append({
                    "building_name": bld_name,
                    "apartment_type_raw": ut or un,
                    "apartment_type_standard": norm_type,
                    "carpet_area_sqmt": sqmt,
                    "carpet_area_sqft": sqft,
                    "number_of_units": 1
                })

    # 3. Aggregate detailed_units into bhk_summary
    grouped: Dict[str, Dict[str, Any]] = {}
    total_units = 0
    res_units = 0
    comm_units = 0
    configs_present: List[str] = []

    for u in detailed_units:
        norm_type = u["apartment_type_standard"]
        cnt = u["number_of_units"]
        sqmt = u["carpet_area_sqmt"]
        total_units += cnt
        if norm_type in ["Shop", "Office", "Commercial", "Restaurant"]:
            comm_units += cnt
        elif norm_type in ["1 RK", "1 BHK", "2 BHK", "3 BHK", "4 BHK", "5 BHK", "Penthouse", "Row House/Villa", "Residential Unit"]:
            res_units += cnt
            
        if norm_type not in grouped:
            grouped[norm_type] = {"areas": [], "units": 0}
            if norm_type not in configs_present and norm_type != "Other/Custom":
                configs_present.append(norm_type)
        if sqmt is not None and sqmt > 0:
            grouped[norm_type]["areas"].append(sqmt)
        grouped[norm_type]["units"] += cnt
        
    bhk_summary["total_units"] = total_units
    bhk_summary["total_residential_units"] = res_units
    bhk_summary["total_commercial_units"] = comm_units
    bhk_summary["bhk_configurations"] = ", ".join(configs_present)
    
    # Extract <1BHK and >3BHK bucket statistics
    lt_1_areas: List[float] = []
    lt_1_units = 0
    gt_3_areas: List[float] = []
    gt_3_units = 0

    for u in detailed_units:
        norm_type = u["apartment_type_standard"]
        raw_type = str(u.get("apartment_type_raw", "")).upper()
        cnt = u["number_of_units"]
        sqmt = u["carpet_area_sqmt"]

        is_lt_1 = False
        if norm_type == "1 RK" or "1 RK" in raw_type or "1RK" in raw_type or "STUDIO" in raw_type or "0.5 BHK" in raw_type or "0.5BHK" in raw_type:
            is_lt_1 = True

        is_gt_3 = False
        m_norm = re.search(r'([4-9])\s*BHK', norm_type)
        m_raw = re.search(r'([4-9])\s*BHK', raw_type)
        if m_norm or m_raw or norm_type in ["4 BHK", "5 BHK", "Penthouse"] or "PENTHOUSE" in raw_type or "DUPLEX" in raw_type:
            is_gt_3 = True

        if is_lt_1:
            lt_1_units += cnt
            if sqmt is not None and sqmt > 0:
                lt_1_areas.append(sqmt)

        if is_gt_3:
            gt_3_units += cnt
            if sqmt is not None and sqmt > 0:
                gt_3_areas.append(sqmt)

    bhk_summary["less_than_1bhk_units"] = lt_1_units
    if lt_1_areas:
        bhk_summary["less_than_1bhk_carpet_sqmt_min"] = min(lt_1_areas)
        bhk_summary["less_than_1bhk_carpet_sqmt_max"] = max(lt_1_areas)
        bhk_summary["less_than_1bhk_carpet_sqft_min"] = round(min(lt_1_areas) * SQMT_TO_SQFT, 1)
        bhk_summary["less_than_1bhk_carpet_sqft_max"] = round(max(lt_1_areas) * SQMT_TO_SQFT, 1)

    bhk_summary["greater_than_3bhk_units"] = gt_3_units
    if gt_3_areas:
        bhk_summary["greater_than_3bhk_carpet_sqmt_min"] = min(gt_3_areas)
        bhk_summary["greater_than_3bhk_carpet_sqmt_max"] = max(gt_3_areas)
        bhk_summary["greater_than_3bhk_carpet_sqft_min"] = round(min(gt_3_areas) * SQMT_TO_SQFT, 1)
        bhk_summary["greater_than_3bhk_carpet_sqft_max"] = round(max(gt_3_areas) * SQMT_TO_SQFT, 1)

    min_max_list: List[str] = []
    carpet_list: List[str] = []
    for norm_name in sorted(grouped.keys()):
        if norm_name in ["Other/Custom", "Unknown"]:
            continue
        areas = grouped[norm_name]["areas"]
        if areas:
            min_m = min(areas)
            max_m = max(areas)
            min_f = round(min_m * SQMT_TO_SQFT, 1)
            max_f = round(max_m * SQMT_TO_SQFT, 1)
            min_max_list.append(f"{norm_name}: {min_m:.1f} - {max_m:.1f} Sq.M ({min_f:.0f} - {max_f:.0f} Sq.Ft)")
            carpet_list.append(f"{norm_name} ({', '.join([str(round(a, 1)) for a in sorted(set(areas))[:4]])} Sq.M)")

    bhk_summary["bhk_wise_min_max_area"] = " ; ".join(min_max_list) if min_max_list else None
    bhk_summary["bhk_wise_carpet_area"] = " | ".join(carpet_list) if carpet_list else None
                
    return bhk_summary, detailed_units


def extract_building_wise_info(
    building_dict: Dict[str, Any],
    apt_dict: Dict[str, Any],
    bhk_dict: Dict[str, Any],
    parking_dict: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Consolidates building_details, Summary_of_Apartments/Units, bhk_details, and All_Parking_Details."""
    buildings: Dict[str, Dict[str, Any]] = {}

    def ensure_building(name: Any) -> Optional[str]:
        clean_name = clean_val(name)
        if not clean_name or clean_name.lower() in ["total", "na", "none", "0"] or clean_name.isdigit():
            return None
        for k in buildings.keys():
            if k.lower() == clean_name.lower():
                return k
        buildings[clean_name] = {
            "building_name": clean_name,
            "sanctioned_floors": None,
            "sanctioned_habitable_floors": None,
            "cc_issued_up_to_floors": None,
            "sanctioned_apartments_total": None,
            "residential_units": 0,
            "non_residential_units": 0,
            "total_units": 0,
            "sold_units": 0,
            "unsold_units": 0,
            "booked_units": 0,
            "rehab_units": 0,
            "mortgage_units": 0,
            "reservation_units": 0,
            "parking": {
                "open_parking": 0,
                "covered_parking": 0,
                "total_parking": 0,
                "two_wheelers": 0,
                "four_wheelers": 0,
                "visitors": 0
            },
            "units": []
        }
        return clean_name

    # 1. Parse building_details
    if building_dict and isinstance(building_dict, dict):
        names = building_dict.get("Identification of Building/ Wing as per Sanctioned Plan") or building_dict.get("Building Name", [])
        floors = building_dict.get("Number of Sanctioned Floors (Including Basement+ Stilt+ Podium+ Service+ Habitable excluding terrace)", [])
        habitable = building_dict.get("Total No. of Building Sanctioned Habitable Floor", [])
        sanctioned_units = building_dict.get("Sanctioned Apartments / Unit (NR+R)", [])
        cc_floors = building_dict.get("CC Issued up-to (No. of Floors)", [])

        for i, raw_name in enumerate(names):
            b_key = ensure_building(raw_name)
            if not b_key:
                continue

            fl = floors[i] if i < len(floors) else None
            hab = habitable[i] if i < len(habitable) else None
            su = sanctioned_units[i] if i < len(sanctioned_units) else None
            cc = cc_floors[i] if i < len(cc_floors) else None

            b_obj = buildings[b_key]
            if fl is not None and str(fl).isdigit():
                b_obj["sanctioned_floors"] = int(fl)
            elif fl is not None:
                b_obj["sanctioned_floors"] = clean_val(fl)

            if hab is not None and str(hab).isdigit():
                b_obj["sanctioned_habitable_floors"] = int(hab)
            elif hab is not None:
                b_obj["sanctioned_habitable_floors"] = clean_val(hab)

            if cc is not None and str(cc).isdigit():
                b_obj["cc_issued_up_to_floors"] = int(cc)
            elif cc is not None:
                b_obj["cc_issued_up_to_floors"] = clean_val(cc)

            if su is not None and str(su).isdigit():
                b_obj["sanctioned_apartments_total"] = int(su)
                if b_obj["total_units"] == 0:
                    b_obj["total_units"] = int(su)
            elif su is not None:
                b_obj["sanctioned_apartments_total"] = clean_val(su)

    # 2. Parse Summary_of_Apartments/Units
    if apt_dict and isinstance(apt_dict, dict):
        if "Identification of Building/ Wing as per Sanctioned Plan" in apt_dict:
            b_names = apt_dict.get("Identification of Building/ Wing as per Sanctioned Plan", [])
            res_units = apt_dict.get("Total No. Of Residential Apartments/ Units", [])
            non_res = apt_dict.get("Total No. Of Non-Residential Apartments/ Units", [])
            tot_units = apt_dict.get("Total Apartments / Unit (NR+R)", [])
            sold = apt_dict.get("Total No. of Sold Units", [])
            unsold = apt_dict.get("Total No. of Unsold Units", [])
            booked = apt_dict.get("Total No. of Booked", [])
            rehab = apt_dict.get("Total No. of Rehab Units", [])
            mortgage = apt_dict.get("Total No. of Mortgage", [])
            reservation = apt_dict.get("Total No. of Reservation", [])

            def to_int(arr: Any, idx: int) -> int:
                if isinstance(arr, list) and idx < len(arr) and arr[idx] is not None:
                    try:
                        return int(arr[idx])
                    except (ValueError, TypeError):
                        pass
                return 0

            for i, raw_name in enumerate(b_names):
                b_key = ensure_building(raw_name)
                if not b_key:
                    continue
                b_obj = buildings[b_key]
                r_u = to_int(res_units, i)
                nr_u = to_int(non_res, i)
                t_u = to_int(tot_units, i)
                b_obj["residential_units"] = r_u
                b_obj["non_residential_units"] = nr_u
                b_obj["total_units"] = t_u if t_u > 0 else (r_u + nr_u if (r_u + nr_u) > 0 else b_obj["total_units"])
                b_obj["sold_units"] = to_int(sold, i)
                b_obj["unsold_units"] = to_int(unsold, i)
                b_obj["booked_units"] = to_int(booked, i)
                b_obj["rehab_units"] = to_int(rehab, i)
                b_obj["mortgage_units"] = to_int(mortgage, i)
                b_obj["reservation_units"] = to_int(reservation, i)

        if "Apartment Type" in apt_dict:
            b_names = apt_dict.get("Building Name", [])
            types = apt_dict.get("Apartment Type", [])
            sqmts = apt_dict.get("Carpet Area (in Sqmts)", [])
            counts = apt_dict.get("Number of Apartment", [])

            n_items = max(len(b_names), len(types), len(sqmts), len(counts))
            b_names = b_names + ["Building 1"] * (n_items - len(b_names))
            types = types + [""] * (n_items - len(types))
            sqmts = sqmts + ["0"] * (n_items - len(sqmts))
            counts = counts + ["0"] * (n_items - len(counts))

            for bld, t, s, c in zip(b_names, types, sqmts, counts):
                b_key = ensure_building(bld) or "Building 1"
                if b_key not in buildings:
                    ensure_building(b_key)
                try:
                    sqmt = round(float(s), 2)
                except (ValueError, TypeError):
                    sqmt = None
                try:
                    cnt = int(c)
                except (ValueError, TypeError):
                    cnt = 0
                sqft = round(sqmt * SQMT_TO_SQFT, 1) if sqmt is not None else None
                norm_type = normalize_unit_type(t)
                buildings[b_key]["units"].append({
                    "apartment_type_raw": t,
                    "apartment_type_standard": norm_type,
                    "carpet_area_sqmt": sqmt,
                    "carpet_area_sqft": sqft,
                    "number_of_units": cnt
                })

    # 3. Parse bhk_details if units exist there
    if bhk_dict and isinstance(bhk_dict, dict):
        for bld_name, content in bhk_dict.items():
            if not isinstance(content, dict):
                continue
            b_key = ensure_building(bld_name)
            if not b_key:
                continue
            b_obj = buildings[b_key]
            if not b_obj["units"]:
                u_types = content.get("Unit Type", [])
                u_sqmts = content.get("Unit Carpet Area (Sq.Mts)", [])
                u_names = content.get("Unit Name", [])
                u_floors = content.get("Floor Number", [])
                n_u = max(len(u_types), len(u_sqmts), len(u_names))
                u_types = u_types + [""] * (n_u - len(u_types))
                u_sqmts = u_sqmts + ["0"] * (n_u - len(u_sqmts))
                u_names = u_names + [""] * (n_u - len(u_names))
                u_floors = u_floors + [""] * (n_u - len(u_floors))
                for ut, us, un, uf in zip(u_types, u_sqmts, u_names, u_floors):
                    if not ut and not us:
                        continue
                    try:
                        sqmt = round(float(us), 2)
                    except (ValueError, TypeError):
                        sqmt = None
                    sqft = round(sqmt * SQMT_TO_SQFT, 1) if sqmt is not None else None
                    norm_type = normalize_unit_type(ut)
                    b_obj["units"].append({
                        "unit_name": un,
                        "floor_number": uf,
                        "apartment_type_raw": ut,
                        "apartment_type_standard": norm_type,
                        "carpet_area_sqmt": sqmt,
                        "carpet_area_sqft": sqft,
                        "number_of_units": 1
                    })

    # 4. Parse parking_details per building
    if parking_dict and isinstance(parking_dict, dict):
        for raw_bld, pdata in parking_dict.items():
            if not isinstance(pdata, dict):
                continue
            clean_b = re.sub(r"^Building\s*Name\s*:\s*", "", str(raw_bld), flags=re.I).strip()
            b_key = ensure_building(clean_b)
            if not b_key:
                continue
            p_types = pdata.get("Parking Type", [])
            totals = pdata.get("Total No Of Parking", [])
            tw = pdata.get("Total No Of Parking 2 Wheelers", [])
            fw = pdata.get("Total No Of Parking 4 Wheelers", [])
            vis = pdata.get("Total No Of Parking Visitors", [])
            open_cnt, cov_cnt, tot_cnt = 0, 0, 0
            tw_cnt, fw_cnt, vis_cnt = 0, 0, 0
            for pt, t in zip(p_types, totals):
                try:
                    c = int(t)
                except (ValueError, TypeError):
                    c = 0
                tot_cnt += c
                if "open" in str(pt).lower():
                    open_cnt += c
                elif "closed" in str(pt).lower() or "covered" in str(pt).lower():
                    cov_cnt += c
            for t in tw:
                try: tw_cnt += int(t)
                except (ValueError, TypeError): pass
            for t in fw:
                try: fw_cnt += int(t)
                except (ValueError, TypeError): pass
            for t in vis:
                try: vis_cnt += int(t)
                except (ValueError, TypeError): pass
            buildings[b_key]["parking"] = {
                "open_parking": open_cnt,
                "covered_parking": cov_cnt,
                "total_parking": tot_cnt,
                "two_wheelers": tw_cnt,
                "four_wheelers": fw_cnt,
                "visitors": vis_cnt
            }

    for b_obj in buildings.values():
        if b_obj["total_units"] == 0 and b_obj["units"]:
            b_obj["total_units"] = sum(u.get("number_of_units", 1) for u in b_obj["units"])
        if b_obj["total_units"] == 0 and (b_obj["sold_units"] + b_obj["unsold_units"] > 0):
            b_obj["total_units"] = b_obj["sold_units"] + b_obj["unsold_units"]

    return list(buildings.values())


def extract_parking_summary(parking_dict: Dict[str, Any]) -> Dict[str, int]:
    """Calculates aggregate parking slot statistics across all buildings."""
    stats = {"total_open_parking": 0, "total_covered_parking": 0, "total_parking_slots": 0}
    if not parking_dict or not isinstance(parking_dict, dict):
        return stats
    open_p, covered_p = 0, 0
    for bld, data in parking_dict.items():
        if not isinstance(data, dict):
            continue
        p_types = data.get("Parking Type", [])
        totals = data.get("Total No Of Parking", [])
        for pt, tot in zip(p_types, totals):
            try:
                cnt = int(tot)
            except (ValueError, TypeError):
                cnt = 0
            if "open" in str(pt).lower():
                open_p += cnt
            elif "closed" in str(pt).lower() or "covered" in str(pt).lower():
                covered_p += cnt
    stats["total_open_parking"] = open_p
    stats["total_covered_parking"] = covered_p
    stats["total_parking_slots"] = open_p + covered_p
    return stats


def transform_raw_to_standard_jsonb(
    bhk_raw: Any,
    building_raw: Any,
    summary_raw: Any,
    parking_raw: Any,
    project_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Converts the 4 raw dictionary columns into clean, normalized JSONB payloads for PostgreSQL.
    
    Returns a dictionary with:
        - 'building_details': structured building list
        - 'bhk_details': structured BHK configurations & carpet area stats
        - 'summary_of_apartments': apartment unit breakdowns
        - 'all_parking_details': structured parking summary
        - 'units_json': complete unified hierarchical project JSON
    """
    bhk_dict = parse_dict_safely(bhk_raw)
    building_dict = parse_dict_safely(building_raw)
    apt_dict = parse_dict_safely(summary_raw)
    parking_dict = parse_dict_safely(parking_raw)
    meta = project_metadata or {}

    # Extract structured objects
    buildings_list = extract_building_wise_info(building_dict, apt_dict, bhk_dict, parking_dict)
    bhk_summary, detailed_units = extract_bhk_carpet_areas(apt_dict, bhk_dict=bhk_dict)
    parking_summary = extract_parking_summary(parking_dict)

    # Full unified JSON hierarchy
    units_json_payload = {
        "registration_number": meta.get("registration_number") or meta.get("rera_id"),
        "project_name": meta.get("project_name"),
        "district": meta.get("district"),
        "total_buildings": len(buildings_list),
        "building_names": [b["building_name"] for b in buildings_list],
        "total_project_units": bhk_summary["total_units"] or sum(b.get("total_units", 0) for b in buildings_list),
        "total_project_booked_units": sum(b.get("sold_units", 0) + b.get("booked_units", 0) for b in buildings_list),
        "bhk_summary": bhk_summary,
        "parking_summary": parking_summary,
        "buildings": buildings_list,
        "units": detailed_units,
        "bank_details": {
            "bank_name": meta.get("bank_name"),
            "ifsc_code": meta.get("ifsc_code"),
            "bank_address": meta.get("bank_address")
        },
        "raw_tables": {
            "building_details": building_dict,
            "summary_of_apartments": apt_dict,
            "bhk_details": bhk_dict,
            "parking_details": parking_dict
        }
    }

    return {
        "building_details": {"buildings": buildings_list, "total_buildings": len(buildings_list)},
        "bhk_details": bhk_summary,
        "summary_of_apartments": {
            "configurations": bhk_summary.get("bhk_configurations"),
            "total_units": bhk_summary.get("total_units", 0),
            "residential_units": bhk_summary.get("total_residential_units", 0),
            "commercial_units": bhk_summary.get("total_commercial_units", 0),
            "units": detailed_units,
        },
        "all_parking_details": parking_summary,
        "units_json": units_json_payload,
    }
