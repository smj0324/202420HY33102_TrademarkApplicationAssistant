import os
import re
import pandas as pd
from mains import main_agent

output_results = []
file_path = '.\\custom_tools\\data\\sorted_output.json'
base_path = '.\\tests\\'

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
    
    output_results = []
    details_results = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            data = line.strip().split('^B')

            if len(data) > 5:
                application_code = data[0]
                input_brand = data[6]
                predict_registration_status, reason = parsing_agent_output_result(main_agent(application_code, input_brand)['output'])
            else:
                input_brand = "N/A"
                predict_registration_status = "N/A"
                reason = "N/A"

            output_results.append(predict_registration_status)
            details_results.append(f"Input Brand: {input_brand}\n")
            details_results.append(f"Registration Status: {predict_registration_status}\n")
            details_results.append(f"Reason: {reason}\n")
            details_results.append("="*40 + "\n")

    write_results(status_file_path, details_file_path, output_results, details_results)


def test_by_myj_test_data(excel_file_path):
    base_name = os.path.basename(excel_file_path).replace('.xlsx', '')  
    status_file_path = os.path.join(base_path, f"predict_status_{base_name}.txt")
    details_file_path = os.path.join(base_path, f"details_{base_name}.txt")

    output_results = []
    details_results = []

    df = pd.read_excel(excel_file_path)
    application_code_list = df.iloc[:, 0].tolist() 
    input_brand_list = df.iloc[:, 1].tolist()
    application_status_list = df.iloc[:, 3].tolist()

    for i in range(len(application_code_list)):
        predict_registration_status, reason = parsing_agent_output_result(main_agent(application_code_list[i], input_brand_list[i])['output'])
        
        output_results.append(predict_registration_status)
        details_results.append(f"Application Code: {application_code_list[i]}\n")
        details_results.append(f"Predict Registration Status: {predict_registration_status}\n")
        details_results.append(f"Reason: {reason}\n")
        details_results.append(f"Registration Status: {application_status_list[i]}\n")
        details_results.append("="*40 + "\n")

    write_results(status_file_path, details_file_path, output_results, details_results)


def parsing_agent_output_result(output):
    status_match = re.search(r"등록 상태:\s*(.+)", output)
    predict_registration_status = status_match.group(1).strip() if status_match else "Unknown"

    reason_match = re.search(r"이유:\s*(.+)", output, re.DOTALL)
    reason = reason_match.group(1).strip() if reason_match else "No reason provided"

    return predict_registration_status, reason


def parsing_gpt_output_result(output):
    # Placeholder for GPT parsing function logic
    pass


sample_file_path = '.\\tests\\TB_KT10_bulk_samples.txt'
test_by_sample_data(sample_file_path)