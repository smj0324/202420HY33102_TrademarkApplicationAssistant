import os
import re
import pandas as pd
from main import final_execute_gpt

output_results = []
base_path = '.\\tests\\'

KIPRIS_API_KEY = os.getenv('_KIPRIS_API_KEY')


def test_data():
    # Placeholder for additional test data processing logic
    pass



def write_results(status_file_path, details_file_path, output_results, details_results):
    with open(status_file_path, 'w', encoding='utf-8') as status_file:
        status_file.write("\n".join(output_results))

    with open(details_file_path, 'w', encoding='utf-8') as details_file:
        details_file.writelines(details_results)


def test_by_sample_data(file_path):
    base_name = os.path.basename(file_path)  
    status_file_path = os.path.join(base_path, f"result_{base_name}")
    details_file_path = os.path.join(base_path, f"details_{base_name}")
    
    with open(status_file_path, 'a', encoding='utf-8') as status_file, open(details_file_path, 'a', encoding='utf-8') as details_file:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                data = line.strip().split('^B')

                if len(data) > 5:
                    application_code = data[0]
                    input_brand = data[6]
                    predict_registration_status, reason = parsing_agent_output_result(final_execute_gpt(application_code, input_brand))
                else:
                    input_brand = "N/A"
                    predict_registration_status = "N/A"
                    reason = "N/A"

                status_file.write(f"{predict_registration_status}\n")
                details_file.write(f"Input Brand: {input_brand}\n")
                details_file.write(f"Registration Status: {predict_registration_status}\n")
                details_file.write(f"Reason: {reason}\n")
                details_file.write("="*40 + "\n")


def test_by_myj_test_data(excel_file_path):
    base_name = os.path.basename(excel_file_path).replace('.xlsx', '')  
    status_file_path = os.path.join(base_path, f"predict_status_{base_name}.txt")
    details_file_path = os.path.join(base_path, f"details_{base_name}.txt")

    df = pd.read_excel(excel_file_path)
    application_code_list = df.iloc[:, 0].astype(str).tolist()
    application_code_list = [code[:-2] if code.endswith('.0') else code for code in application_code_list]
    input_brand_list = df.iloc[:, 1].tolist()
    application_status_list = df.iloc[:, 3].tolist()

    with open(status_file_path, 'a', encoding='utf-8') as status_file, open(details_file_path, 'w', encoding='utf-8') as details_file:
        for i in range(len(application_code_list)):
            if i == 1:
                break
            predict_registration_status, reason = parsing_agent_output_result(final_execute_gpt(application_code_list[i], input_brand_list[i]))
            
            status_file.write(f"{predict_registration_status}\n")
            details_file.write(f"Application Code: {application_code_list[i]}\n")
            details_file.write(f"Predict Registration Status: {predict_registration_status}\n")
            details_file.write(f"Reason: {reason}\n")
            details_file.write(f"Registration Status: {application_status_list[i]}\n")
            details_file.write("="*40 + "\n")


def parsing_agent_output_result(text):
    lines = text.splitlines()
    lines = [line.strip() for line in lines if line.strip()]

    status = None
    reason = None

    for line in lines:
        if "Trademark Status:" in line or "Predict Status:" in line:
            status = line.split(":")[-1].strip()
        elif "Reason:" in line:
            reason = line.split("Reason:")[-1].strip()

    return status, reason



def parsing_gpt_output_result(output):
    # Placeholder for GPT parsing function logic
    pass
   

# sample_file_path = '.\\tests\\TB_KT10_bulk_samples.txt'
sample_file_path = '.\\tests\\TB_KT10.txt_samples.txt'
myj_exl_file = '.\\tests\\MYJ_TEST_DATA.xlsx'
# test_by_myj_test_data(myj_exl_file)
test_by_sample_data(sample_file_path)