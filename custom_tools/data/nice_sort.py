import json
import re
import sys
import os

def load_json(file_path):
    """
    Loads JSON data from the specified file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Error decoding JSON: {e}")

def save_json(data, file_path):
    """
    Saves JSON data to the specified file.

    Args:
        data (dict): The JSON data to save.
        file_path (str): The path to the output JSON file.
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print(f"Processed data has been saved to '{file_path}'.")

def process_codes(data):
    """
    Processes the JSON data by sorting codes within each string where applicable.

    Args:
        data (dict): The JSON data to process.

    Returns:
        dict: The processed JSON data.
    """
    # Compile a regex pattern to match codes starting with G or S followed by at least four digits
    pattern = re.compile(r'^[GS]\d{4,}$')

    # Iterate over each key and its corresponding list
    for key, codes_list in data.items():
        for idx, code_str in enumerate(codes_list):
            # Split the string by commas and strip whitespace from each code
            codes = [code.strip() for code in code_str.split(',')]

            # Check if there are two or more codes and all codes match the pattern
            if len(codes) >= 2 and all(pattern.match(code) for code in codes):
                # Sort the codes in ascending (lexicographical) order
                sorted_codes = sorted(codes)
                # Join them back into a comma-separated string
                sorted_code_str = ','.join(sorted_codes)
                # Replace the original string with the sorted string
                data[key][idx] = sorted_code_str

    return data

def main(input_file, output_file):
    """
    Main function to load, process, and save JSON data.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output JSON file.
    """
    try:
        # Load JSON data from the input file
        data = load_json(input_file)
        print(f"Loaded data from '{input_file}' successfully.")

        # Process the data
        processed_data = process_codes(data)
        print("Data processing complete.")

        # Save the processed data to the output file
        save_json(processed_data, output_file)

    except FileNotFoundError as fnf_error:
        print(fnf_error)
    except json.JSONDecodeError as json_error:
        print(json_error)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Default file names (you can change these or pass as command-line arguments)
    DEFAULT_INPUT_FILE = 'custom_tools/data/_nice_to_similar.json'
    DEFAULT_OUTPUT_FILE = 'sorted_output.json'

    # Check if user provided custom file names via command-line arguments
    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    elif len(sys.argv) == 1:
        input_file = DEFAULT_INPUT_FILE
        output_file = DEFAULT_OUTPUT_FILE
    else:
        print("Usage: python script_name.py [input_file.json output_file.json]")
        sys.exit(1)

    main(input_file, output_file)
