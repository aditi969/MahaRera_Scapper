"""CSV and Excel export engine with column splitting for Excel character limits.

Matches exact logic from Cell 2 of RERA_Scrapping_fixed_v3.ipynb.
"""
import os
from typing import List
import pandas as pd

from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


class CsvWriter:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger):
        self.config = config
        self.logger = logger

    @staticmethod
    def sanitize_dataframe_strings(df: pd.DataFrame) -> pd.DataFrame:
        clean_df = df.copy()
        for col in clean_df.columns:
            if clean_df[col].dtype == object or clean_df[col].dtype == 'string':
                def _clean_cell(v):
                    if v is None or pd.isna(v):
                        return ""
                    s = str(v).strip()
                    if s == "{}" or (s.startswith("{") and s.endswith("}")):
                        return s
                    return " ".join(s.split())
                clean_df[col] = clean_df[col].apply(_clean_cell)
        return clean_df

    def split_all_large_columns(self, df: pd.DataFrame, limit: int = 32000) -> pd.DataFrame:
        df_copy = self.sanitize_dataframe_strings(df)
        cols_to_check = list(df_copy.columns)

        for col in cols_to_check:
            s_series = df_copy[col].astype(str)
            max_len = s_series.str.len().max()
            if max_len <= limit:
                continue

            n_parts = int(max_len // limit) + 1
            part_cols = {f"{col}_part{part+2}": [] for part in range(n_parts - 1)}

            for val in s_series:
                chunks = [val[i:i+limit] for i in range(0, len(val), limit)]
                for part in range(n_parts - 1):
                    part_cols[f"{col}_part{part+2}"].append(
                        chunks[part+1] if part+1 < len(chunks) else ""
                    )

            df_copy[col] = s_series.str[:limit]
            col_idx = df_copy.columns.get_loc(col)
            for i, (part_name, part_data) in enumerate(part_cols.items()):
                df_copy.insert(col_idx + 1 + i, part_name, part_data)

        return df_copy

    def save_scraped_project_row(self, df: pd.DataFrame, output_csv_path: str, limit: int = 32000, is_update: bool = False) -> pd.DataFrame:
        split_df = self.split_all_large_columns(df, limit=limit)

        rera_id = None
        for id_c in ["Registration Number", "Rera ID", "rera_id"]:
            if id_c in split_df.columns and len(split_df[id_c]) > 0:
                rera_id = str(split_df[id_c].iloc[0]).strip()
                break

        EXCLUDE_INTERNAL_METADATA = {"source_url", "cert_extraction_status", "Cert_Date_Source"}

        if not os.path.exists(output_csv_path):
            initial_cols = list(self.config.standard_columns)
            for col in split_df.columns:
                if col not in initial_cols and col not in EXCLUDE_INTERNAL_METADATA:
                    base_col = col.split("_part")[0]
                    insert_idx = len(initial_cols)
                    for idx, c in enumerate(initial_cols):
                        if c == base_col or c.startswith(f"{base_col}_part"):
                            insert_idx = idx + 1
                    initial_cols.insert(insert_idx, col)

            row_to_write = split_df.reindex(columns=initial_cols, fill_value="")
            row_to_write.to_csv(output_csv_path, index=False, encoding="utf-8")
            return split_df

        try:
            full_df = pd.read_csv(output_csv_path, dtype=str)
        except Exception:
            full_df = pd.DataFrame()

        if full_df.empty:
            split_df = split_df.reindex(columns=self.config.standard_columns, fill_value="")
            split_df.to_csv(output_csv_path, index=False, encoding="utf-8")
            return split_df

        existing_cols = full_df.columns.tolist()
        new_cols = [c for c in split_df.columns if c not in existing_cols and c not in EXCLUDE_INTERNAL_METADATA]

        # Expand columns if new columns detected
        merged_cols = list(existing_cols)
        if new_cols:
            self.logger.info(f"Dynamic schema expansion: adding new columns {new_cols} to {output_csv_path}...")
            for nc in new_cols:
                base_col = nc.split("_part")[0]
                insert_idx = len(merged_cols)
                for idx, c in enumerate(merged_cols):
                    if c == base_col or c.startswith(f"{base_col}_part"):
                        insert_idx = idx + 1
                merged_cols.insert(insert_idx, nc)
            full_df = full_df.reindex(columns=merged_cols, fill_value="")

        row_formatted = split_df.reindex(columns=merged_cols, fill_value="")

        # Check for existing record to update instead of duplicating
        existing_row_idx = None
        matched_id_col = None
        if rera_id:
            rera_id_clean = str(rera_id).strip().upper()
            for id_c in ["Registration Number", "Rera ID", "rera_id", "Registration_Number", "Rera_ID"]:
                if id_c in full_df.columns:
                    matches = full_df.index[full_df[id_c].astype(str).str.strip().str.upper() == rera_id_clean].tolist()
                    if matches:
                        existing_row_idx = matches[0]
                        matched_id_col = id_c
                        break

        if existing_row_idx is not None:
            self.logger.info(f"🔄 Updating existing CSV row for RERA ID '{rera_id}' in {output_csv_path} (no duplicate row).")
            # Preserve existing non-empty values if newly extracted field is empty
            for col in merged_cols:
                new_val = row_formatted[col].iloc[0]
                old_val = full_df.at[existing_row_idx, col]
                if (new_val is None or str(new_val).strip() == "") and (old_val is not None and str(old_val).strip() != ""):
                    continue  # Preserve existing valid value
                full_df.at[existing_row_idx, col] = new_val

            # Prevent duplicate rows for same RERA ID
            if matched_id_col and matched_id_col in full_df.columns:
                full_df = full_df.drop_duplicates(subset=[matched_id_col], keep="first")

            full_df.to_csv(output_csv_path, index=False, encoding="utf-8")
        else:
            combined = pd.concat([full_df, row_formatted], ignore_index=True)
            for id_c in ["Registration Number", "Rera ID", "rera_id"]:
                if id_c in combined.columns:
                    combined = combined.drop_duplicates(subset=[id_c], keep="last")
                    break
            combined.to_csv(output_csv_path, index=False, encoding="utf-8")

        return split_df

    def export_and_verify_dataset(self, csv_path: str, xlsx_path: str, limit: int = 32000) -> bool:
        if not os.path.exists(csv_path):
            if self.logger:
                self.logger.info(f"No CSV file found at {csv_path} to export.")
            return False

        try:
            if self.logger:
                self.logger.info(f"Loading {csv_path} for Excel export and character validation...")
            df = pd.read_csv(csv_path, dtype=str)
            df_split = self.split_all_large_columns(df, limit=limit)

            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
                df_split.to_excel(writer, index=False, sheet_name="RERA_Projects")
                try:
                    ws = writer.sheets["RERA_Projects"]
                    for col in ws.columns:
                        col_name = str(col[0].value or "")
                        # Sample first few rows to set reasonable column width
                        sample_lens = [len(str(cell.value or "")) for cell in col[:15]]
                        max_l = max([len(col_name)] + sample_lens) if sample_lens else len(col_name)
                        col_letter = col[0].column_letter
                        ws.column_dimensions[col_letter].width = min(max(max_l + 3, 14), 45)
                except Exception:
                    pass

            if self.logger:
                self.logger.info(f"✅ Excel export verified and written successfully to {xlsx_path} ({len(df_split)} rows, {len(df_split.columns)} columns).")
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Excel export encountered an issue: {e}")
            return False

    def export_to_xlsx(self, csv_path: str, xlsx_path: str, limit: int = 32000) -> bool:
        return self.export_and_verify_dataset(csv_path, xlsx_path, limit=limit)

