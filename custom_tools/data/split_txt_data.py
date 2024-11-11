def split_text_file(input_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    chunk_size = 25
    num_chunks = 4
    
    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = start_index + chunk_size
        chunk_lines = lines[start_index:end_index]
        
        output_file = f'./custom_tools/data/output_part_{i+1}.txt'
        with open(output_file, 'w', encoding='utf-8') as output:
            output.writelines(chunk_lines)
    
    print("파일이 성공적으로 분할 및 저장되었습니다.")

split_text_file('./custom_tools/data/example_100_lines.txt')