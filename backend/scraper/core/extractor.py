"""Project detail extraction and HTML structure sanitization.

Matches exact selectors, table parsing, and modal BHK extraction
from Cell 5 of RERA_Scrapping_fixed_v3.ipynb.
"""
import time
from typing import Any, Dict, Optional

import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scraper.core.certificate import CertificateExtractor
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


def clean_str(val: Any) -> Optional[str]:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return " ".join(s.split()) if s else None


class ProjectExtractor:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger, cert_extractor: Optional[CertificateExtractor] = None):
        self.config = config
        self.logger = logger
        self.cert_extractor = cert_extractor or CertificateExtractor(config, logger)

    def safe_text(self, driver, xpath: str, by=By.XPATH, timeout: int = 2, default: Optional[str] = None, field_name: str = "", required: bool = False) -> Optional[str]:
        actual_timeout = 6 if required else timeout
        try:
            el = WebDriverWait(driver, actual_timeout).until(EC.visibility_of_element_located((by, xpath)))
            return clean_str(el.text)
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            if required:
                raise
            return default

    def extract_project_data(self, driver, organization: Optional[str] = None) -> pd.DataFrame:
        wait = WebDriverWait(driver, 10)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        Project_Status = self.safe_text(driver, "//*[contains(text(), 'Project Status')]/following::div[1]",
                                        field_name="Project Status")

        Registration_Number = self.safe_text(driver, "//*[contains(text(), 'Registration Number')]/following-sibling::*[1]",
                                             field_name="Registration Number", required=True)
        Date_of_Registration = self.safe_text(driver, "//*[contains(text(), 'Date of Registration')]/following-sibling::*[1]",
                                              field_name="Date of Registration")
        project_location = self.safe_text(driver, "//*[contains(text(), 'Project Location')]/following-sibling::*[1]",
                                          field_name="Project Location")
        project_type = self.safe_text(driver, "//*[contains(text(), 'Project Type')]/following-sibling::*[1]",
                                      field_name="Project Type")
        project_name = self.safe_text(driver, "//*[contains(text(), 'Project Name')]/following-sibling::*[1]",
                                      field_name="Project Name")
        project_proposed_completion_date_original = self.safe_text(
            driver, "//*[contains(text(), 'Proposed Completion Date (Original)')]/following-sibling::*[1]",
            field_name="Proposed Completion Date (Original)")
        project_proposed_completion_date_revised = self.safe_text(
            driver, "//*[contains(text(), 'Proposed Completion Date (Revised)')]/following-sibling::*[1]",
            field_name="Proposed Completion Date (Revised)")

        survey_no = self.safe_text(driver, "//*[contains(normalize-space(.), 'Survey Number')]/following-sibling::*[1]",
                                   field_name="Survey Number")
        def _clean_area_val(v: Optional[str]) -> Optional[str]:
            if not v:
                return None
            s = clean_str(v)
            if not s or s.lower() in ("project status", "none", "nan", "null", ""):
                return None
            return s

        def _extract_area(driver, keyword: str, field_name: str) -> Optional[str]:
            xpaths = [
                f"//div[(contains(@class,'white-box') or contains(@class,'form-group') or contains(@class,'col-')) and .//label[contains(normalize-space(.), '{keyword}')]]//div[contains(@class,'text-font')]",
                f"//label[contains(normalize-space(.), '{keyword}')]/following-sibling::div[contains(@class,'text-font')]",
                f"//label[contains(normalize-space(.), '{keyword}')]/following-sibling::*[1]",
                f"//span[contains(normalize-space(.), '{keyword}')]/following-sibling::*[1]",
            ]
            for xp in xpaths:
                raw_val = self.safe_text(driver, xp, timeout=1.5, field_name=field_name)
                c_val = _clean_area_val(raw_val)
                if c_val:
                    return c_val
            return None

        Total_Land_Area = _extract_area(driver, "Total Land Area of Approved Layout", "Total Land Area")
        Land_Area_for_Project_Applied_for_this_Registration = (
            _extract_area(driver, "Land Area for Project Applied", "Land Area Applied") or
            _extract_area(driver, "Land Area", "Land Area")
        )
        Aggregate_area_in_sqmt_of_recreational_open_space = (
            _extract_area(driver, "Aggregate area", "Aggregate area") or
            _extract_area(driver, "recreational open space", "Recreational open space")
        )
        Permissible_Builtup = _extract_area(driver, "Permissible Built-up Area", "Permissible Builtup")
        Sanctioned_Builtup = _extract_area(driver, "Sanctioned Built-up Area of the Project", "Sanctioned Builtup")
        Longitude = self.safe_text(
            driver, '//*[@id="hidden_div"]/div/div/div/div/form/fieldset/div[4]/div[1]/fieldset/div/fieldset/form/div/div[1]/div/project-geo-tagging-preview/fieldset/form/div/fieldset/div/div[1]/div/div',
            field_name="Longitude")
        Latitude = self.safe_text(
            driver, '//*[@id="hidden_div"]/div/div/div/div/form/fieldset/div[4]/div[1]/fieldset/div/fieldset/form/div/div[1]/div/project-geo-tagging-preview/fieldset/form/div/fieldset/div/div[2]/div/div',
            field_name="Latitude")
        Litigation_Details = self.safe_text(
            driver, '//*[@id="hidden_div"]/div/div/div/div/form/fieldset/div[4]/div[7]/div/div[2]/div[1]/label[2]',
            field_name="Litigation_Details (header)")
        Address = self.safe_text(driver, "//*[contains(text(), 'Address')]/following-sibling::*[1]", field_name="Address")
        Street_Name = self.safe_text(driver, "//*[contains(text(), 'Street Name ')]/following-sibling::*[1]", field_name="Street Name")

        Street_Name1 = self.safe_text(driver, "//*[contains(text(), 'Locality')]/following-sibling::*[1]",
                                      timeout=4, field_name="Locality")

        State_UT = self.safe_text(driver, "//*[contains(text(), 'State/UT')]/following-sibling::*[1]", field_name="State/UT")
        District = self.safe_text(driver, "//*[contains(text(), 'District')]/following-sibling::*[1]", field_name="District")
        Taluka = self.safe_text(driver, "//*[contains(text(), 'Taluka')]/following-sibling::*[1]", field_name="Taluka")
        Village = self.safe_text(driver, "//*[contains(text(), 'Village')]/following-sibling::*[1]",
                                 timeout=4, field_name="Village")

        Pin_Code = self.safe_text(driver, "//*[contains(text(), 'Pin Code')]/following-sibling::*[1]", field_name="Pin Code")
        Boundaries_East = self.safe_text(driver, "//*[contains(text(), 'Boundaries East')]/following-sibling::*[1]", field_name="Boundaries East")
        Boundaries_West = self.safe_text(driver, "//*[contains(text(), 'Boundaries West')]/following-sibling::*[1]", field_name="Boundaries West")
        Boundaries_South = self.safe_text(driver, "//*[contains(text(), 'Boundaries South')]/following-sibling::*[1]", field_name="Boundaries South")
        Boundaries_North = self.safe_text(driver, "//*[contains(text(), 'Boundaries North')]/following-sibling::*[1]", field_name="Boundaries North")

        # --- Robust Promoter Details Extraction ---
        Promoter_Type = self.safe_text(
            driver,
            "//*[contains(normalize-space(.), 'Promoter Type')]/following-sibling::*[1]",
            timeout=2.0,
            field_name="Promoter Type"
        )
        if not Promoter_Type:
            # Sibling or container search
            for p_lbl in soup.find_all(["label", "span", "div"], class_=lambda c: c and ("label" in str(c).lower() or "title" in str(c).lower())):
                if "promoter type" in p_lbl.get_text(strip=True).lower():
                    sib = p_lbl.find_next_sibling(["div", "span", "b", "p"])
                    if sib and sib.get_text(strip=True):
                        Promoter_Type = clean_str(sib.get_text(strip=True))
                        break

        promoter_name_candidates = [
            "//*[contains(normalize-space(.), 'Name of Partnership')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Company Name')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Name of Company')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Name of Proprietorship')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Name of Firm')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Name of LLP')]/following-sibling::*[1]",
            "//*[contains(normalize-space(.), 'Name of Entity')]/following-sibling::*[1]",
            "//div[contains(@class,'form-group') and .//label[normalize-space(.)='Name']]//div[contains(@class,'text-font')]",
            "//*[normalize-space(.)='Name']/following-sibling::*[1]",
        ]
        Promoter_Name = None
        for xp in promoter_name_candidates:
            p_val = self.safe_text(driver, xp, timeout=0.8, field_name="Promoter Name Candidate")
            if p_val and p_val.lower() not in ("promoter type", "none", "null", ""):
                Promoter_Name = p_val
                break

        # Check for Individual promoter components: First Name, Middle Name, Last Name
        if not Promoter_Name:
            first_n = self.safe_text(driver, "//*[contains(normalize-space(.), 'First Name')]/following-sibling::*[1]", timeout=0.8, field_name="First Name")
            last_n = self.safe_text(driver, "//*[contains(normalize-space(.), 'Last Name')]/following-sibling::*[1]", timeout=0.8, field_name="Last Name")
            middle_n = self.safe_text(driver, "//*[contains(normalize-space(.), 'Middle Name')]/following-sibling::*[1]", timeout=0.8, field_name="Middle Name")
            parts = [p for p in [first_n, middle_n, last_n] if p]
            if parts:
                Promoter_Name = " ".join(parts)

        # Fallback to search-card organization if Promoter_Name is still missing
        if not Promoter_Name and organization:
            Promoter_Name = organization

        # Assemble clean, expected output format (e.g. "Partnership - GREEN SPACE INFRA VENTURES")
        if Promoter_Type and Promoter_Name:
            Promoter_Details = clean_str(f"{Promoter_Type} - {Promoter_Name}")
        elif Promoter_Name:
            Promoter_Details = clean_str(Promoter_Name)
        elif Promoter_Type:
            Promoter_Details = clean_str(f"{Promoter_Type} - {organization}") if organization else clean_str(Promoter_Type)
        else:
            Promoter_Details = clean_str(organization) if organization else None

        Are = self.safe_text(
            driver, '//*[@id="hidden_div"]/div/div/div/div/form/fieldset/div[4]/div[6]/div/div[2]/div[1]/label[2]/b',
            field_name="Are there any Investor other than the Promoter")

        past_experience_info = None
        try:
            promoter_btn_xpath = "//button[normalize-space()='Promoter Past Experience Details']"
            button = WebDriverWait(driver, 2.5).until(EC.presence_of_element_located((By.XPATH, promoter_btn_xpath)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", button)

            past_div = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Promoter Past Experience Details')]/following::div[1]"))
            )
            past_experience_info = clean_str(past_div.find_elements(By.TAG_NAME, "div")[0].find_elements(By.TAG_NAME, "label")[1].text)
        except Exception as e:
            self.logger.warning(f"Promoter Past Experience Details not available: {e}")

        summary_bhk = {}
        soup = BeautifulSoup(driver.page_source, "html.parser")
        target = soup.find(string=lambda t: t and "Summary of Apartments/Units" in t)
        if target:
            next_div = target.find_next("div")
            rows = next_div.find_all("tr") if next_div else []
            if rows:
                headers = [clean_str(th.get_text(strip=True)) for th in rows[0].find_all("th")]
                summary_bhk = {h: [] for h in headers if h}
                for row in rows[1:]:
                    for h, cell in zip(headers, row.find_all("td")):
                        if h:
                            summary_bhk[h].append(clean_str(cell.get_text(strip=True)))

        if not summary_bhk:
            for _t in soup.find_all("table"):
                _hdr = " ".join(th.get_text(" ", strip=True) for th in _t.find_all("th"))
                if "Apartment Type" in _hdr and "Carpet Area" in _hdr:
                    rows = _t.find_all("tr")
                    if rows:
                        headers = [clean_str(th.get_text(strip=True)) for th in rows[0].find_all("th")]
                        summary_bhk = {h: [] for h in headers if h}
                        for row in rows[1:]:
                            for h, cell in zip(headers, row.find_all("td")):
                                if h:
                                    summary_bhk[h].append(clean_str(cell.get_text(strip=True)))
                    break

        # Fallback to BeautifulSoup for any missing area or general fields
        if not Land_Area_for_Project_Applied_for_this_Registration or not Aggregate_area_in_sqmt_of_recreational_open_space or not Total_Land_Area:
            for box in soup.find_all("div", class_=lambda c: c and ("white-box" in c or "form-group" in c)):
                lbl = box.find("label") or box.find(class_=lambda c: c and "form-label" in c)
                if not lbl:
                    continue
                lt = lbl.get_text(strip=True).lower()
                val_el = box.find(class_=lambda c: c and "text-font" in c)
                val = val_el.get_text(strip=True) if val_el else ""
                if not val:
                    nd = lbl.find_next_sibling("div")
                    if nd:
                        val = nd.get_text(strip=True)
                if not val:
                    continue
                if "land area for project applied" in lt and not Land_Area_for_Project_Applied_for_this_Registration:
                    Land_Area_for_Project_Applied_for_this_Registration = clean_str(val)
                elif ("aggregate area" in lt or "recreational open space" in lt) and not Aggregate_area_in_sqmt_of_recreational_open_space:
                    Aggregate_area_in_sqmt_of_recreational_open_space = clean_str(val)
                elif "total land area" in lt and not Total_Land_Area:
                    Total_Land_Area = clean_str(val)
                elif "permissible built-up" in lt and not Permissible_Builtup:
                    Permissible_Builtup = clean_str(val)
                elif "sanctioned built-up" in lt and not Sanctioned_Builtup:
                    Sanctioned_Builtup = clean_str(val)

        # Fallback for Aggregate Area from Development Work / Amenities table if still missing or blank
        if not Aggregate_area_in_sqmt_of_recreational_open_space:
            for tr in soup.find_all("tr"):
                row_txt = tr.get_text(" ", strip=True).lower()
                if "aggregate area of recreational" in row_txt:
                    tds = tr.find_all("td")
                    if len(tds) >= 4:
                        is_avail = clean_str(tds[2].get_text(strip=True))
                        comp_pct = clean_str(tds[3].get_text(strip=True))
                        if is_avail.lower() == "no":
                            Aggregate_area_in_sqmt_of_recreational_open_space = "0"
                        elif comp_pct and comp_pct != "0":
                            Aggregate_area_in_sqmt_of_recreational_open_space = comp_pct

        # If the recreational open space field is explicitly present in the form but blank/empty, record "0"
        if not Aggregate_area_in_sqmt_of_recreational_open_space:
            for box in soup.find_all("div", class_=lambda c: c and ("white-box" in c or "form-group" in c)):
                lbl = box.find("label") or box.find(class_=lambda c: c and "form-label" in c)
                if lbl and ("aggregate area" in lbl.get_text(strip=True).lower() or "recreational open space" in lbl.get_text(strip=True).lower()):
                    Aggregate_area_in_sqmt_of_recreational_open_space = "0"
                    break

        # Fallback for Land Area if applied is missing but total land area is known
        if not Land_Area_for_Project_Applied_for_this_Registration and Total_Land_Area:
            Land_Area_for_Project_Applied_for_this_Registration = Total_Land_Area

        bhk_details = {}
        building_details = {}

        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.3)
        except Exception:
            pass

        _BD_TABLE_XPATH = '//table[.//th[contains(normalize-space(.),"Identification of Building")]]'
        try:
            WebDriverWait(driver, 2.5).until(EC.presence_of_element_located((By.XPATH, _BD_TABLE_XPATH)))
        except TimeoutException:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")
        bd_table = None
        for _t in soup.find_all("table"):
            _hdr = " ".join(th.get_text(" ", strip=True) for th in _t.find_all("th"))
            if "Identification of Building" in _hdr:
                bd_table = _t
                break

        if bd_table is None:
            _h = soup.find(lambda tag: tag.name and
                           tag.get_text(strip=True) == "Building Details" and
                           tag.find("table") is None)
            if _h is None:
                _hs = soup.find(string=lambda t: t and "Building Details" in t)
                _h = _hs.find_parent() if _hs else None
            bd_table = _h.find_next("table") if _h else None

        if bd_table is not None:
            rows = bd_table.find_all("tr")
            if rows:
                headers = [clean_str(th.get_text(strip=True)) for th in rows[0].find_all("th")]
                building_details = {h: [] for h in headers if h}
                view_index = headers.index("View") if "View" in headers else None
                name_index = next((i for i, h in enumerate(headers)
                                   if h and h.startswith("Identification of Building")), 1)

                for row in rows[1:]:
                    cells = row.find_all("td")
                    if not cells:
                        continue
                    for h, cell in zip(headers, cells):
                        if h:
                            building_details[h].append(clean_str(cell.get_text(strip=True)))

                if view_index is not None:
                    try:
                        sel_tables = driver.find_elements(By.XPATH, _BD_TABLE_XPATH)
                        selenium_table = sel_tables[0] if sel_tables else None
                        if selenium_table:
                            for row in selenium_table.find_elements(By.TAG_NAME, "tr")[1:]:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) <= max(name_index, view_index):
                                    continue
                                if (clean_str(cells[0].text) or "").lower() == "total":
                                    continue
                                building_name = clean_str(cells[name_index].text)
                                view_btns = cells[view_index].find_elements(
                                    By.XPATH, './/a | .//button | .//*[@role="button"] | .//i'
                                )
                                btn = next((b for b in view_btns if b.is_displayed()), None)
                                if btn is None:
                                    continue
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                                    time.sleep(0.3)
                                    driver.execute_script("arguments[0].click();", btn)

                                    modal_el = WebDriverWait(driver, 8).until(
                                        EC.visibility_of_element_located((By.CSS_SELECTOR, "div.modal.show"))
                                    )
                                    time.sleep(0.5)

                                    modal_soup = BeautifulSoup(modal_el.get_attribute("outerHTML"), "html.parser")
                                    tbl = None
                                    for _mt in modal_soup.find_all("table"):
                                        if _mt.find("thead") and _mt.find("tbody"):
                                            tbl = _mt
                                            break
                                    if tbl is not None:
                                        keys = [clean_str(th.get_text(strip=True)) for th in tbl.find("thead").find_all("th")]
                                        details = {k: [] for k in keys if k}
                                        for r in tbl.find("tbody").find_all("tr"):
                                            for k, cell_td in zip(keys, r.find_all("td")):
                                                if k:
                                                    details[k].append(clean_str(cell_td.get_text(strip=True)))
                                        key_name = building_name
                                        n = 2
                                        while key_name in bhk_details:
                                            key_name = f"{building_name} ({n})"
                                            n += 1
                                        bhk_details[key_name] = details
                                except Exception as e:
                                    self.logger.warning(f"Building modal for {building_name}: {e}")
                                finally:
                                    self.cert_extractor.close_modal(driver)
                                    time.sleep(0.2)
                    except Exception as e:
                        self.logger.warning(f"Building details table: {e}")

        bank_name = ifsc_code = bank_address = None
        try:
            bank_details = driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Bank Details')]/parent::div/following-sibling::div"
            )[0]
            all_details = bank_details.find_elements(By.TAG_NAME, "label")
            bank_name = clean_str(all_details[0].find_element(By.XPATH, "following-sibling::div[1]").text)
            ifsc_code = clean_str(all_details[1].find_element(By.XPATH, "following-sibling::div[1]").text)
            bank_address = clean_str(all_details[2].find_element(By.XPATH, "following-sibling::div[1]").text)
        except Exception:
            pass

        all_parking_details = {}
        if "Parking" in driver.page_source:
            # 1. Attempt to open Parking Details accordion if present
            for _ in range(3):
                try:
                    parking_buttons = driver.find_elements(
                        By.XPATH,
                        "//button[contains(., 'Parking Details')] | "
                        "//a[contains(., 'Parking Details')] | "
                        "//button[.//div[contains(., 'Parking Details')]] | "
                        "//*[contains(@class,'accordion') and contains(., 'Parking Details')]//button"
                    )
                    for pb in parking_buttons:
                        if pb.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pb)
                            driver.execute_script("arguments[0].click();", pb)
                            time.sleep(0.4)
                            break
                    break
                except Exception:
                    driver.execute_script("window.scrollBy(0, 150);")
                    time.sleep(0.3)

            # 2. Extract parking tables via BeautifulSoup for maximum reliability (works even if DOM is nested or partially off-screen)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            parking_tables = []
            for t in soup.find_all("table"):
                t_text = t.get_text(" ", strip=True).lower()
                if "parking type" in t_text or "total no of parking" in t_text or "open space" in t_text:
                    parking_tables.append(t)

            for p_idx, table in enumerate(parking_tables):
                try:
                    # Detect building name associated with this parking table
                    building_name = None
                    prev = table.find_previous(["h2", "h3", "h4", "h5", "div", "b", "strong"])
                    if prev:
                        prev_txt = clean_str(prev.get_text(strip=True))
                        if prev_txt and not prev_txt.lower().startswith("parking"):
                            building_name = prev_txt

                    if not building_name:
                        building_name = f"Building Name : Parking Details {p_idx + 1}" if len(parking_tables) > 1 else "Building Name : All Parking"

                    rows = table.find_all("tr")
                    if not rows:
                        continue

                    # Header row
                    th_cells = rows[0].find_all(["th", "td"])
                    keys = [clean_str(th.get_text(strip=True)) for th in th_cells]
                    keys = [k for k in keys if k]
                    if not keys:
                        continue

                    parking_details = {k: [] for k in keys}
                    for tr in rows[1:]:
                        tds = tr.find_all("td")
                        if not tds:
                            continue
                        row_vals = [clean_str(td.get_text(strip=True)) for td in tds]
                        # Don't skip row unless it is genuinely a "Total" summary footer row
                        if row_vals and (row_vals[0] or "").lower() == "total" and len(rows) > 2:
                            continue
                        for k_idx, val in enumerate(row_vals):
                            if k_idx < len(keys):
                                parking_details[keys[k_idx]].append(val or "0")

                    if any(len(v) > 0 for v in parking_details.values()):
                        all_parking_details[building_name] = parking_details
                except Exception as p_err:
                    self.logger.debug(f"Parking table extraction warning: {p_err}")

        project_details = {
            "Registration Number": [Registration_Number],
            "Date of Registration": [Date_of_Registration],
            "Rera ID": [Registration_Number],
            "Project Location": [project_location],
            "Project Type": [project_type],
            "Project Name": [project_name],
            "survey_no": [survey_no],
            "Permissible Builtup Area": [Permissible_Builtup],
            "Sanctioned Builtup Area": [Sanctioned_Builtup],
            "Total Land Area": [Total_Land_Area],
            "Aggregate area": [Aggregate_area_in_sqmt_of_recreational_open_space],
            "Land Area for Project Applied for this Registration": [Land_Area_for_Project_Applied_for_this_Registration],
            "Project proposed completion date original": [project_proposed_completion_date_original],
            "Project proposed completion date revised": [project_proposed_completion_date_revised],
            "Commencing From": [None],
            "Leftmost Date": [None],
            "Ending With": [None],
            "Longitude": [Longitude],
            "Latitude": [Latitude],
            "Are there any Investor other than the Promoter in the Project": [Are],
            "State_UT": [State_UT],
            "District": [District],
            "Taluka": [Taluka],
            "Village": [Village],
            "Pin_Code": [Pin_Code],
            "Boundaries_East": [Boundaries_East],
            "Boundaries_West": [Boundaries_West],
            "Boundaries_South": [Boundaries_South],
            "Boundaries_North": [Boundaries_North],
            "Promoter_Details": [Promoter_Details],
            "bhk_details": [bhk_details],
            "building_details": [building_details],
            "Summary_of_Apartments/Units": [summary_bhk],
            "past_experience_info": [past_experience_info],
            "Litigations related to the project ?": [Litigation_Details],
            "All_Parking_Details": [all_parking_details],
            "Bank Name": [bank_name],
            "IFSC Code": [ifsc_code],
            "Bank Address": [bank_address],
            "ProjectStatus": [Project_Status],
            "Locality": [Street_Name1],
        }

        return pd.DataFrame(project_details)

