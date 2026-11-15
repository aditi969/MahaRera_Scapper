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

    def extract_project_data(self, driver) -> pd.DataFrame:
        wait = WebDriverWait(driver, 10)

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

        survey_no = self.safe_text(driver, "//*[contains(text(), 'Survey Number')]/following-sibling::*[1]",
                                   field_name="Survey Number")
        Total_Land_Area = self.safe_text(driver, "//*[contains(text(), 'Total Land Area of Approved Layout')]/following-sibling::*[1]",
                                         field_name="Total Land Area")
        Land_Area_for_Project_Applied_for_this_Registration = self.safe_text(
            driver, "//*[contains(text(), 'Land Area for Project Applied for this Registration')]/following-sibling::*[1]",
            field_name="Land Area for Project Applied for this Registration")
        Aggregate_area_in_sqmt_of_recreational_open_space = self.safe_text(
            driver, "//*[contains(text(), 'Land Area for Project Applied for this Registration')]/following-sibling::*[1]",
            field_name="Aggregate area")
        Permissible_Builtup = self.safe_text(driver, "//*[contains(text(), 'Permissible Built-up Area')]/following-sibling::*[1]",
                                             field_name="Permissible Built-up Area")
        Sanctioned_Builtup = self.safe_text(driver, "//*[contains(text(), 'Sanctioned Built-up Area of the Project')]/following-sibling::*[1]",
                                            field_name="Sanctioned Built-up Area")
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

        try:
            Promoter_Type = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Promoter Type')]/following-sibling::*[1]"))
            ).text
            Name_of_Partnership = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Name of Partnership')]/following-sibling::*[1]"))
            ).text
            Promoter_Details = clean_str(f"{Promoter_Type} - {Name_of_Partnership}")
        except Exception:
            Promoter_Details = self.safe_text(
                driver, '//*[@id="hidden_div"]/div/div/div/div/form/fieldset/div[4]/div[1]/fieldset/div/fieldset/form/div/div[2]/div/div/project-general-information-preview/fieldset/form/div[2]/div',
                field_name="Promoter_Details")

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
        if "Parking Details" in driver.page_source:
            opened = False
            for _ in range(3):
                try:
                    parking_button = driver.find_element(By.XPATH, "//button[.//div[contains(., 'Parking Details')]]")
                    driver.execute_script("arguments[0].click();", parking_button)
                    time.sleep(0.4)
                    opened = True
                    break
                except Exception:
                    driver.execute_script("window.scrollBy(0, 150);")
                    time.sleep(0.3)
            if opened:
                tables = driver.find_elements(
                    By.XPATH, "//button[.//div[contains(., 'Parking Details')]]/parent::h2/following-sibling::fieldset//table"
                )
                for table in tables:
                    try:
                        parent_div = table.find_element(By.XPATH, "./parent::div")
                        grandparent_div = parent_div.find_element(By.XPATH, "./parent::div")
                        building_name_div = grandparent_div.find_element(By.XPATH, "./preceding-sibling::div[1]")
                        building_name = clean_str(building_name_div.text)
                        keys = [clean_str(th.text) for th in table.find_elements(By.TAG_NAME, "th")]
                        parking_details = {k: [] for k in keys if k}
                        for tr in table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")[:-1]:
                            for idx, td in enumerate(tr.find_elements(By.TAG_NAME, "td")):
                                if idx < len(keys) and keys[idx]:
                                    parking_details[keys[idx]].append(clean_str(td.text))
                        all_parking_details[building_name] = parking_details
                    except Exception:
                        pass

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

