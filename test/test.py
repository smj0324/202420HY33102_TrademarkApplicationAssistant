from main import main_agent

output_results = []
file_path = '/content/TB_KT10.txt_samples.txt'


# TODO: result parsing 하는 코드 추가 필요
with open(file_path, 'r', encoding='utf-8') as file:
    for line in file:
        data = line.strip().split('^B')

        application_code = data[0] if len(data) > 0 else ""
        input_brand = data[6] if len(data) > 6 else ""

        result = main_agent(application_code, input_brand)
        output_results.append(result)

print("\n".join(output_results))
