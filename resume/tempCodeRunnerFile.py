import pandas as pd
import re
def extract_text_from_xlsx():
    df = pd.read_excel("R2025-0051_Accounts_Payable_Specialist_(Open) (1).xlsx")
    indices = [9, 12, 32, 15, 1]
    valid_indices = [index for index in indices if 0 <= index < len(df.columns)]
    result_list = []
    
    for row_number in range(1, 2):
        raw_compensation = df.iloc[row_number, valid_indices[3]] if pd.notna(df.iloc[row_number, valid_indices[3]]) else None  # Column 32
        compensation_match = re.search(r'\d+', str(raw_compensation))  # Extract only numbers
        row_dict = {
            "resume_name": df.iloc[row_number, valid_indices[0]] if pd.notna(df.iloc[row_number, valid_indices[0]]) else None,  # Column 9
            "workday_url": df.iloc[row_number, valid_indices[1]] if pd.notna(df.iloc[row_number, valid_indices[1]]) else None,  # Column 12
            "resume_text": df.iloc[row_number, valid_indices[2]] if pd.notna(df.iloc[row_number, valid_indices[2]]) else None ,  # Column 32
            "candidate_name": df.iloc[row_number, valid_indices[4]] if pd.notna(df.iloc[row_number, valid_indices[4]]) else None ,  # Column 32
            "compensation": int(compensation_match.group()) if compensation_match else None   
        }
        result_list.append(row_dict)
    
    return result_list
print(extract_text_from_xlsx())
