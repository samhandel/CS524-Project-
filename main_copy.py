import requests
import time
import csv

def read_food_items_from_file(file_path):
    with open(file_path, 'r') as file:
        # This will read each line, strip leading/trailing whitespace, and ignore empty lines
        return [line.strip() for line in file if line.strip()]


def read_existing_data(csv_file):
    existing_items = set()
    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_items.add(row['Item'].lower())
    except FileNotFoundError:
        pass
    return existing_items

def append_to_csv(csv_file, formatted_food_nutrients):
    fieldnames = ['Item', 'Description', 'Brand', 'Calories', 'Serving Size', 'Nutrients']
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0:
            writer.writeheader()

        for item, details in formatted_food_nutrients.items():
            writer.writerow({
                'Item': item,
                'Description': details['description'],
                'Brand': details['brand'],
                'Calories': details['calories'],
                'Serving Size': f"{details['servingSize']} {details['servingSizeUnit']}",
                'Nutrients': ', '.join([f"{k}: {v}" for k, v in details['nutrients'].items()])
            })

def search_food_item(api_key, query):
    """Search for a food item and return its FDC ID."""
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['foods']:
            return data['foods'][0]['fdcId']
    return None

def get_food_details(api_key, fdc_id):
    """Get detailed information about a food item using its FDC ID."""
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def format_nutrient_data(food_data):
    """Format the nutrient data into a readable format."""
    if not food_data:
        return {}

    nutrients = {}
    calories = None
    for nutrient in food_data.get('foodNutrients', []):
        nutrient_name = nutrient.get('nutrient', {}).get('name')
        amount = nutrient.get('amount')
        unit = nutrient.get('nutrient', {}).get('unitName')
        if nutrient_name and amount is not None:
            nutrients[nutrient_name] = f"{amount} {unit}"
            if nutrient_name.lower() == 'energy':
                calories = f"{amount} {unit}"

    return {
        "description": food_data.get("description"),
        "brand": food_data.get("brandOwner", "Not specified"),
        "calories": calories,
        "nutrients": nutrients,
        "servingSize": food_data.get("servingSize"),
        "servingSizeUnit": food_data.get("servingSizeUnit"),
    }

def get_food_nutrients(api_key, food_items, csv_file):
    existing_items = read_existing_data(csv_file)
    formatted_food_details = {}
    max_retries = 5

    for item in food_items:
        if item.lower() in existing_items:
            print(f"'{item}' is already in the CSV file. Skipping.")
            continue
        for attempt in range(max_retries):
            fdc_id = search_food_item(api_key, item)
            if fdc_id:
                details = get_food_details(api_key, fdc_id)
                if details and details.get("description") is not None:  # Check if details are valid
                    formatted_details = format_nutrient_data(details)
                    formatted_food_details[item] = formatted_details
                    break
                else:
                    print(f"Attempt {attempt+1}: Failed to retrieve valid data for '{item}'. Retrying...")
            time.sleep(5)
        else:
            print(f"Failed to retrieve data for '{item}' after {max_retries} attempts.")

    return formatted_food_details


# Main execution
api_key = 'sPvrji6g4b0EghbDaxmXWYITiVMWZvHtkGikpB5q'
csv_file = 'food_nutrients.csv'
txt_file = 'food.txt'

try:
    food_items = read_food_items_from_file(txt_file)
    formatted_food_nutrients = get_food_nutrients(api_key, food_items, csv_file)
    append_to_csv(csv_file, formatted_food_nutrients)
    for item, details in formatted_food_nutrients.items():
        print(f"{item.title()}:")
        print(f"  Description: {details['description']}")
        print(f"  Brand: {details['brand']}")
        print(f"  Calories: {details['calories']}")
        print(f"  Serving Size: {details['servingSize']} {details['servingSizeUnit']}")
        print("  Nutrients:")
        for nutrient, value in details['nutrients'].items():
            print(f"    {nutrient}: {value}")
        print()
except Exception as e:
    print(str(e))
