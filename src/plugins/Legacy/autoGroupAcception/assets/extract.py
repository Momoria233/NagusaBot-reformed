#用于从bd的cache/birthday/student.json中提取姓名的脚本

import json, os

def extract_and_combine_names(input_file, output_file):
    """
    Extracts "FamilyName", "PersonalName", and "Name" from a JSON file,
    combines "FamilyName" and "PersonalName", and outputs the results
    to a new JSON file, removing duplicate entries.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output JSON file.
    """

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{input_file}'.")
        return

    combined_names = []
    seen_names = set()  # To keep track of unique full names

    for student in data:
        try:
            family_name = student.get("FamilyName", "")
            personal_name = student.get("PersonalName", "")
            name = student.get("Name", "")

            full_name = f"{family_name}{personal_name}" if family_name and personal_name else ""

            # Create a tuple to represent the combination of names for uniqueness check
            name_tuple = (full_name, name, family_name, personal_name)

            # Only include if at least one of the names exists AND it's a unique combination
            if full_name not in seen_names:
                combined_names.append({
                    "FullName": full_name,
                    "FamilyName": family_name,
                    "PersonalName": personal_name
                })
                seen_names.add(full_name)  # Add the name to the set of seen names
        except AttributeError as e:
            print(f"Skipping entry due to error: {e}")
            continue

    try:
        if os.path.exists(output_file):
            os.remove(output_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_names, f, indent=4, ensure_ascii=False)
        print(f"Successfully extracted and combined names to '{output_file}'.")
    except IOError:
        print(f"Error: Could not write to output file '{output_file}'.")


# Example usage:
input_file = r'C:\Users\123\Desktop\fileC\NagusaBot\NagusaBot-dev\cache\birthday\students.json'  # Replace with the actual path to your input file
output_file = r'C:\Users\123\Desktop\fileC\NagusaBot\NagusaBot-dev\cache\birthday\replacement.json'  # Replace with the desired path for the output file
extract_and_combine_names(input_file, output_file)