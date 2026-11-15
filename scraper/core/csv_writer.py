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

    def save_scraped_project_row(self, df: pd.DataFrame, output_csv_path: str, limit: int = 32000) -> pd.DataFrame:
        split_df = self.split_all_large_columns(df, limit=limit)

        if not os.path.exists(output_csv_path):
            initial_cols = list(self.config.standard_columns)
            for col in split_df.columns:
                if col not in initial_cols:
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
            existing_cols = pd.read_csv(output_csv_path, nrows=0).columns.tolist()
        except Exception:
            existing_cols = []

        if not existing_cols:
            split_df.to_csv(output_csv_path, index=False, encoding="utf-8")
            return split_df

        new_cols = [c for c in split_df.columns if c not in existing_cols]
        if not new_cols:
            row_to_append = split_df.reindex(columns=existing_cols, fill_value="")
            row_to_append.to_csv(output_csv_path, mode="a", index=False, header=False, encoding="utf-8")
        else:
            self.logger.info(f"Dynamic schema expansion: adding new columns {new_cols} to {output_csv_path}...")
            try:
                full_existing_df = pd.read_csv(output_csv_path, dtype=str)
                merged_cols = list(existing_cols)
                for nc in new_cols:
                    base_col = nc.split("_part")[0]
                    insert_idx = len(merged_cols)
                    for idx, c in enumerate(merged_cols):
                        if c == base_col or c.startswith(f"{base_col}_part"):
                            insert_idx = idx + 1
                    merged_cols.insert(insert_idx, nc)

                full_existing_df = full_existing_df.reindex(columns=merged_cols, fill_value="")
                row_to_append = split_df.reindex(columns=merged_cols, fill_value="")
                combined = pd.concat([full_existing_df, row_to_append], ignore_index=True)
                combined.to_csv(output_csv_path, index=False, encoding="utf-8")
            except Exception as e:
                self.logger.warning(f"Error during schema expansion ({e}), appending aligned row directly.")
                row_to_append = split_df.reindex(columns=existing_cols, fill_value="")
                row_to_append.to_csv(output_csv_path, mode="a", index=False, header=False, encoding="utf-8")

        return split_df

    def export_and_verify_dataset(self, csv_path: str, xlsx_path: str, limit: int = 32000) -> bool:
        if not os.path.exists(csv_path):
            self.logger.info(f"No CSV file found at {csv_path} to export.")
            return False

        try:
            self.logger.info(f"Loading {csv_path} for Excel export and character validation...")
            df = pd.read_csv(csv_path, dtype=str)
            df_split = self.split_all_large_columns(df, limit=limit)

            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
                df_split.to_excel(writer, index=False, sheet_name="RERA_Projects")

            self.logger.info(f"✅ Excel export verified and written successfully to {xlsx_path} ({len(df_split)} rows, {len(df_split.columns)} columns).")
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Excel export encountered an issue: {e}")
            return False

