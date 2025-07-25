import json
import pandas as pd
import xmltodict

class ListsParser:
    def __init__(self, source, from_xml: bool = False):
        if from_xml:
            self.data = xmltodict.parse(source)
        elif isinstance(source, dict):
            self.data = source
        else:
            raise ValueError("Invalid data source provided. Must be dict or XML string.")

        self.lists_records = []

    @staticmethod
    def ensure_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    def safe_get(self, d, keys, default=None):
        """중첩 dict에서 안전하게 값 추출"""
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key)
            else:
                return default
        return d if d is not None else default
    
    def parse(self):
        entries = self.data.get("libraryContent", {}).get("lists", {}).get("entry")
        for item in self.ensure_list(entries):
            if not isinstance(item, dict):
                continue
            list_in_lists = item.get("list", {})
            list_name = list_in_lists.get("@name", None)
            list_id = list_in_lists.get("@id", None)
            list_type_id = list_in_lists.get("@typeId", None)
            list_classifier = list_in_lists.get("@classifier", None)
            list_description = list_in_lists.get("description", None)

            entries = self.safe_get(item, ["list", "content", "listEntry"], [])
            entries_list = self.ensure_list(entries)

            # 리스트인 경우만 처리
            if isinstance(entries_list, list):
                if entries_list:
                    for entry in entries_list:
                        if isinstance(entry, dict):
                            row = {
                                "list_name": list_name,
                                "list_id": list_id,
                                "list_type_id": list_type_id,
                                "list_classifier": list_classifier,
                                "list_description": list_description,
                                **entry,
                            }
                            self.lists_records.append(row)
                else:
                    # 엔트리가 없더라도 리스트 정보는 저장
                    self.lists_records.append(
                        {
                            "list_name": list_name,
                            "list_id": list_id,
                            "list_type_id": list_type_id,
                            "list_classifier": list_classifier,
                            "list_description": list_description,
                        }
                    )

            elif isinstance(entries, dict):
                row = {
                    "list_name": list_name,
                    "list_id": list_id,
                    "list_type_id": list_type_id,
                    "list_classifier": list_classifier,
                    "list_description": list_description,
                    **entries
                }
                self.lists_records.append(row)
        
        return self.lists_records

    def to_excel(self, lists_path: str):
        df_lists = pd.DataFrame(self.lists_records)
        df_lists.to_excel(lists_path, index=False, engine="openpyxl")
