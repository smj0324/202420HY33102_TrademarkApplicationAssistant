import os
import re
import pandas as pd
import time
from datetime import datetime
from mains import main_agent
from mains import main_gpt

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
    
    # Get current date and time for file naming
    current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create file paths with date and time
    status_file_path = os.path.join(base_path, f"result_{base_name}_{current_datetime}.txt")
    details_file_path = os.path.join(base_path, f"details_{base_name}_{current_datetime}.txt")
    
    output_results = []
    details_results = []
    
    # Start timing the entire process
    start_time = time.time()
    
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            data = line.strip().split('^B')

            if len(data) > 5:
                application_code = data[0]
                input_brand = data[6]
                # Pass input_brand to parsing_gpt_output_result for output formatting
                predict_registration_status, reason = parsing_gpt_output_result(
                    main_gpt(application_code, input_brand),
                    input_brand
                )
            else:
                input_brand = "N/A"
                predict_registration_status = "N/A"
                reason = "N/A"

            output_results.append(predict_registration_status)
            details_results.append(f"Input Brand: {input_brand}\n")
            details_results.append(f"Registration Status: {predict_registration_status}\n")
            details_results.append(f"Reason: {reason}\n")
            details_results.append("="*40 + "\n")
    
    # End timing the entire process
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Save results
    write_results(status_file_path, details_file_path, output_results, details_results)
    
    # Print total time taken
    print(f"전체 데이터를 처리하는 데 걸린 시간: {elapsed_time:.2f}초")

    
def test_by_myj_test_data(excel_file_path):
    # Get current date and time for file naming
    current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = os.path.basename(excel_file_path).replace('.xlsx', '')  
    status_file_path = os.path.join(base_path, f"predict_status_{base_name}){current_datetime}.txt")
    details_file_path = os.path.join(base_path, f"details_{base_name}_{current_datetime}.txt")

    df = pd.read_excel(excel_file_path)
    application_code_list = df.iloc[:, 0].astype(str).tolist()
    application_code_list = [code[:-2] if code.endswith('.0') else code for code in application_code_list]
    input_brand_list = df.iloc[:, 1].tolist()
    application_status_list = df.iloc[:, 3].tolist()
    
    print(application_code_list, input_brand_list, application_status_list)
    start_time = time.time()
    with open(status_file_path, 'w', encoding='utf-8') as status_file, open(details_file_path, 'w', encoding='utf-8') as details_file:
        for i in range(len(application_code_list)):
            predict_registration_status = main_gpt(application_code_list[i], input_brand_list[i])
            
            status_file.write(f"{predict_registration_status}\n")
            details_file.write(f"Application Code: {application_code_list[i]}\n")
            details_file.write(f"Predict Registration Status: {predict_registration_status}\n")
            details_file.write(f"Registration Status: {application_status_list[i]}\n")
            details_file.write("="*40 + "\n")
    # End timing the entire process
    end_time = time.time()
    elapsed_time = end_time - start_time    
    # Print total time taken
    print(f"전체 데이터를 처리하는 데 걸린 시간: {elapsed_time:.2f}초")

    
    # Print total time taken
    # print(f"전체 데이터를 처리하는 데 걸린 시간: {elapsed_time:.2f}초")
    
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

def parsing_gpt_output_result(output, input_brand):
    status_match = re.search(r"등록 상태:\s*(.+)", output)
    predict_registration_status = status_match.group(1).strip() if status_match else "Unknown"

    reason_match = re.search(r"이유:\s*(.+)", output, re.DOTALL)
    reason = reason_match.group(1).strip() if reason_match else "No reason provided"

    if "승인" in predict_registration_status:
        predict_registration_status = f"{input_brand},O"
    elif "거절" in predict_registration_status:
        predict_registration_status = f"{input_brand},X"
    else:
        predict_registration_status = f"{input_brand},Unknown"

    return predict_registration_status, reason

sample_file_path = '.\\tests\\TB_KT10_bulk_samples.txt'
test_by_sample_data(sample_file_path)
