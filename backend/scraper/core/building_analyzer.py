"""Building-wise and unit-wise details analyzer for MahaRERA projects.

Analyzes the four source columns:
1. building_details
2. Summary_of_Apartments/Units
3. bhk_details
4. All_Parking_Details

Generates the structured analyzed_building_wise_details JSON object matching
the exact specification for CSV, Excel, and PostgreSQL JSONB insertion.
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple

SQMT_TO_SQFT = 10.7639


def clean_val(val: Any) -> Optional[str]:
    """Clean string value or return None if empty/NaN."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "null", "") else None


def parse_dict_safely(val: Any) -> Dict[str, Any]:
    """Safely parse dictionary from dict, JSON string, or Python string representation."""
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


def extract_building_wise_info(
    building_dict: Dict[str, Any],
    apt_dict: Dict[str, Any],
    bhk_dict: Dict[str, Any],
    parking_dict: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Consolidates data across building_details, Summary_of_Apartments/Units,
    bhk_details, and All_Parking_Details into a list of structured building objects.
    """
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
        # Case A: Building-level unit status table
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

        # Case B: Apartment Type configuration table
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

    # Recalculate building total_units if still 0 but units list exists
    for b_obj in buildings.values():
        if b_obj["total_units"] == 0 and b_obj["units"]:
            b_obj["total_units"] = sum(u.get("number_of_units", 1) for u in b_obj["units"])
        if b_obj["total_units"] == 0 and (b_obj["sold_units"] + b_obj["unsold_units"] > 0):
            b_obj["total_units"] = b_obj["sold_units"] + b_obj["unsold_units"]

    return list(buildings.values())


def generate_analyzed_building_wise_details(row: Any) -> Dict[str, Any]:
    """Generates the standardized analyzed_building_wise_details dictionary
    by analyzing the four source columns:
    1. building_details
    2. Summary_of_Apartments/Units
    3. bhk_details
    4. All_Parking_Details
    """
    if row is None:
        return {}
        
    get_fn = row.get if hasattr(row, "get") else lambda k, default=None: getattr(row, k, default)

    reg_no = clean_val(get_fn("Registration Number") or get_fn("Rera ID") or get_fn("registration_number") or get_fn("rera_id"))
    proj_name = clean_val(get_fn("Project Name") or get_fn("project_name"))
    district = clean_val(get_fn("District") or get_fn("district"))

    # Four source columns
    building_raw = get_fn("building_details")
    apt_raw = get_fn("Summary_of_Apartments/Units") or get_fn("summary_of_apartments")
    bhk_raw = get_fn("bhk_details")
    parking_raw = get_fn("All_Parking_Details") or get_fn("all_parking_details")

    building_dict = parse_dict_safely(building_raw)
    apt_dict = parse_dict_safely(apt_raw)
    bhk_dict = parse_dict_safely(bhk_raw)
    parking_dict = parse_dict_safely(parking_raw)

    buildings_list = extract_building_wise_info(building_dict, apt_dict, bhk_dict, parking_dict)

    # Unit calculations
    total_project_units = sum(b.get("total_units", 0) for b in buildings_list)
    total_booked_count = sum(b.get("sold_units", 0) + b.get("booked_units", 0) for b in buildings_list)

    # Bank details
    bank_name = clean_val(get_fn("Bank Name") or get_fn("bank_name"))
    ifsc_code = clean_val(get_fn("IFSC Code") or get_fn("ifsc_code"))
    bank_address = clean_val(get_fn("Bank Address") or get_fn("bank_address"))

    payload: Dict[str, Any] = {
        "registration_number": reg_no,
        "project_name": proj_name,
        "district": district,
        "total_buildings": len(buildings_list),
        "building_names": [b["building_name"] for b in buildings_list],
        "total_project_units": total_project_units if total_project_units > 0 else None,
        "total_project_booked_units": total_booked_count if total_booked_count > 0 else None,
        "buildings": buildings_list,
        "bank_details": {
            "bank_name": bank_name,
            "ifsc_code": ifsc_code,
            "bank_address": bank_address
        },
        "raw_tables": {
            "building_details": building_dict,
            "summary_of_apartments": apt_dict,
            "bhk_details": bhk_dict,
            "parking_details": parking_dict
        }
    }

    return payload
